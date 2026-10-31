"""Ingesta streaming de los 192 CSVs territoriales y 2 modales hacia Parquet Silver."""

from __future__ import annotations

import re
from pathlib import Path

import polars as pl
from rich.console import Console

from ine_abstencion.config import AppConfig
from ine_abstencion.ingestion.catalogs import get_entidades_df
from ine_abstencion.ingestion.schema import (
    SPECIAL_MODAL_FILES,
    TERRITORIAL_POLARS_SCHEMA,
)

console = Console()

TERRITORIAL_PATTERN = re.compile(
    r"^datosabiertos_deceyec_conteoscensales(?P<year>2009|2012|2015|2018|2021|2024)_(?P<state>[a-z]+)\.csv$"
)


def discover_raw_files(raw_dir: Path) -> tuple[dict[int, list[Path]], list[Path]]:
    """Separa los 192 archivos territoriales por anio y aisla los 2 archivos modales 2024."""
    by_year: dict[int, list[Path]] = {y: [] for y in (2009, 2012, 2015, 2018, 2021, 2024)}
    modal_files: list[Path] = []

    for p in sorted(raw_dir.glob("*.csv")):
        if p.name in SPECIAL_MODAL_FILES:
            modal_files.append(p)
            continue
        m = TERRITORIAL_PATTERN.match(p.name)
        if m:
            year = int(m.group("year"))
            by_year[year].append(p)

    return by_year, modal_files


def ingest_all_to_silver(cfg: AppConfig, force: bool = False) -> pl.DataFrame:
    """Convierte los 192 CSVs territoriales a Parquet particionado por anio y genera auditoria."""
    by_year, modal_files = discover_raw_files(cfg.paths.raw_data_dir)
    total_territorial = sum(len(v) for v in by_year.values())
    console.print(
        f"[bold cyan]Archivos detectados:[/bold cyan] {total_territorial} territoriales "
        f"({len(by_year)} elecciones) + {len(modal_files)} modales especiales."
    )
    if total_territorial != 192:
        raise RuntimeError(f"Se esperaban 192 archivos territoriales y se encontraron {total_territorial}")

    audit_rows: list[dict[str, object]] = []
    entidades_df = get_entidades_df()

    for year, file_list in sorted(by_year.items()):
        out_parquet = cfg.paths.silver_dir / f"ccpc_{year}.parquet"
        if out_parquet.exists() and not force:
            console.print(f"  [green]✓[/green] Silver {year} ya existe: {out_parquet.name}")
            lf = pl.scan_parquet(out_parquet)
        else:
            console.print(f"  [yellow]→[/yellow] Procesando eleccion {year} ({len(file_list)} estados)...")
            str_paths = [str(p) for p in file_list]
            lf = (
                pl.scan_csv(
                    str_paths,
                    schema_overrides=TERRITORIAL_POLARS_SCHEMA,
                    null_values=["", "NA", "N/A", "null"],
                    encoding="utf8-lossy",
                    ignore_errors=False,
                )
                .with_columns(
                    pl.col("TIPOSEC").str.strip_chars().str.to_uppercase(),
                    (pl.col("EDOCVE").cast(pl.Int32) * 1000 + pl.col("MPIOCVE").cast(pl.Int32)).alias(
                        "ID_MUN_INE"
                    ),
                    (pl.col("EDOCVE").cast(pl.Int32) * 100000 + pl.col("SECCION").cast(pl.Int32)).alias(
                        "ID_SEC_INE"
                    ),
                )
            )
            lf.sink_parquet(out_parquet, compression="zstd")
            console.print(f"  [green]✓[/green] Guardado {out_parquet.name}")
            lf = pl.scan_parquet(out_parquet)

        # Estadisticas de auditoria por anio en streaming
        stats = (
            lf.select(
                pl.len().alias("filas"),
                pl.col("EDOCVE").n_unique().alias("entidades"),
                pl.col("ID_MUN_INE").n_unique().alias("municipios_ine"),
                pl.col("ID_SEC_INE").n_unique().alias("secciones_ine"),
                pl.col("LN").cast(pl.Int64).sum().alias("ln_total"),
                pl.col("SV").cast(pl.Int64).sum().alias("sv_total"),
                pl.col("NV").cast(pl.Int64).sum().alias("nv_total"),
                pl.col("NS").cast(pl.Int64).sum().alias("ns_total"),
                (pl.col("LN") != (pl.col("SV") + pl.col("NV") + pl.col("NS")))
                .cast(pl.Int64)
                .sum()
                .alias("filas_descuadre_ln"),
                pl.col("DEL").is_null().cast(pl.Int64).sum().alias("nulos_del"),
                (pl.col("SEXO") == 2).cast(pl.Int64).sum().alias("registros_sexo_nobinario"),
            )
            .collect(engine="streaming")
            .to_dicts()[0]
        )
        ln_tot = max(int(stats["ln_total"]), 1)
        stats["AELEC"] = year
        stats["TIPO_ELECCION"] = "Presidencial" if year in cfg.elections["presidencial_years"] else "Intermedia"
        stats["archivos_csv"] = len(file_list)
        stats["tasa_participacion_pct"] = round(100.0 * int(stats["sv_total"]) / ln_tot, 4)
        stats["tasa_abstencion_pct"] = round(100.0 * int(stats["nv_total"]) / ln_tot, 4)
        stats["tasa_ns_pct"] = round(100.0 * int(stats["ns_total"]) / ln_tot, 4)
        audit_rows.append(stats)

    # Extraer catalogo canonico municipal desde 2024 (nombres oficiales mas recientes)
    lf_2024 = pl.scan_parquet(cfg.paths.silver_dir / "ccpc_2024.parquet")
    cat_mun_2024 = (
        lf_2024.group_by(["EDOCVE", "MPIOCVE", "ID_MUN_INE"])
        .agg(
            pl.col("MPIONOM").first().str.strip_chars().alias("MPIONOM_CANONICO"),
            pl.col("DEF").mode().first().alias("DEF_PRINCIPAL_2024"),
        )
        .join(entidades_df.lazy(), on="EDOCVE", how="left")
        .sort("ID_MUN_INE")
        .collect(engine="streaming")
    )
    cat_mun_2024.write_parquet(cfg.paths.silver_dir / "catalogo_municipios_2024.parquet")

    # Procesar archivos modales especiales 2024 por separado (anexo informativo)
    modal_summary: list[dict[str, object]] = []
    for mp in modal_files:
        df_m = pl.read_csv(mp, encoding="utf8-lossy")
        modal_summary.append(
            {
                "archivo": mp.name,
                "registros": df_m.height,
                "columnas": ",".join(df_m.columns),
                "mujeres_sexo0": int((df_m["SEXO"] == 0).sum()) if "SEXO" in df_m.columns else 0,
                "hombres_sexo1": int((df_m["SEXO"] == 1).sum()) if "SEXO" in df_m.columns else 0,
            }
        )
    if modal_summary:
        pl.DataFrame(modal_summary).write_csv(
            cfg.paths.tables_dir / "anexo_modalidades_especiales_2024.csv"
        )

    audit_df = pl.DataFrame(audit_rows).sort("AELEC")
    audit_df.write_csv(cfg.paths.tables_dir / "auditoria_calidad_datos_2009_2024.csv")
    return audit_df

