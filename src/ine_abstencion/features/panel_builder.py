"""Construccion de paneles Gold (Municipal, Estatal y Seccional) desde Parquet Silver."""

from __future__ import annotations

import numpy as np
import polars as pl
from rich.console import Console

from ine_abstencion.config import AppConfig
from ine_abstencion.ingestion.catalogs import get_entidades_df

console = Console()


def _aggregate_year_municipal(lf: pl.LazyFrame, year: int, is_intermedia: int) -> pl.DataFrame:
    """Agrega un anio electoral a nivel Municipio INE con descomposicion demografica y territorial."""
    return (
        lf.group_by(["AELEC", "EDOCVE", "MPIOCVE", "ID_MUN_INE"])
        .agg(
            pl.col("SECCION").n_unique().alias("N_SECCIONES"),
            pl.col("DEF").mode().first().alias("DEF"),
            pl.col("LN").cast(pl.Int64).sum().alias("LN"),
            pl.col("SV").cast(pl.Int64).sum().alias("SV"),
            pl.col("NV").cast(pl.Int64).sum().alias("NV"),
            pl.col("NS").cast(pl.Int64).sum().alias("NS"),
            # Edad promedio ponderada por LN
            (
                (pl.col("EDAD").clip(18, 95).cast(pl.Float64) * pl.col("LN").cast(pl.Float64)).sum()
                / pl.col("LN").cast(pl.Float64).sum().clip(lower_bound=1.0)
            ).alias("EDAD_PROMEDIO_LN"),
            # Cohortes etarias: LN y NV
            pl.col("LN").filter(pl.col("EDAD").is_between(18, 19)).cast(pl.Int64).sum().alias("LN_18_19"),
            pl.col("NV").filter(pl.col("EDAD").is_between(18, 19)).cast(pl.Int64).sum().alias("NV_18_19"),
            pl.col("LN").filter(pl.col("EDAD").is_between(18, 29)).cast(pl.Int64).sum().alias("LN_18_29"),
            pl.col("NV").filter(pl.col("EDAD").is_between(18, 29)).cast(pl.Int64).sum().alias("NV_18_29"),
            pl.col("LN").filter(pl.col("EDAD").is_between(30, 39)).cast(pl.Int64).sum().alias("LN_30_39"),
            pl.col("NV").filter(pl.col("EDAD").is_between(30, 39)).cast(pl.Int64).sum().alias("NV_30_39"),
            pl.col("LN").filter(pl.col("EDAD").is_between(30, 59)).cast(pl.Int64).sum().alias("LN_30_59"),
            pl.col("NV").filter(pl.col("EDAD").is_between(30, 59)).cast(pl.Int64).sum().alias("NV_30_59"),
            pl.col("LN").filter(pl.col("EDAD").is_between(40, 59)).cast(pl.Int64).sum().alias("LN_40_59"),
            pl.col("NV").filter(pl.col("EDAD").is_between(40, 59)).cast(pl.Int64).sum().alias("NV_40_59"),
            pl.col("LN").filter(pl.col("EDAD") >= 60).cast(pl.Int64).sum().alias("LN_60_MAS"),
            pl.col("NV").filter(pl.col("EDAD") >= 60).cast(pl.Int64).sum().alias("NV_60_MAS"),
            # Sexo: 0 = Mujer, 1 = Hombre
            pl.col("LN").filter(pl.col("SEXO") == 0).cast(pl.Int64).sum().alias("LN_MUJERES"),
            pl.col("NV").filter(pl.col("SEXO") == 0).cast(pl.Int64).sum().alias("NV_MUJERES"),
            pl.col("LN").filter(pl.col("SEXO") == 1).cast(pl.Int64).sum().alias("LN_HOMBRES"),
            pl.col("NV").filter(pl.col("SEXO") == 1).cast(pl.Int64).sum().alias("NV_HOMBRES"),
            # Tipo de seccion: U = Urbana, R = Rural, M = Mixta
            pl.col("LN").filter(pl.col("TIPOSEC") == "U").cast(pl.Int64).sum().alias("LN_URBANA"),
            pl.col("NV").filter(pl.col("TIPOSEC") == "U").cast(pl.Int64).sum().alias("NV_URBANA"),
            pl.col("LN").filter(pl.col("TIPOSEC") == "R").cast(pl.Int64).sum().alias("LN_RURAL"),
            pl.col("NV").filter(pl.col("TIPOSEC") == "R").cast(pl.Int64).sum().alias("NV_RURAL"),
            pl.col("LN").filter(pl.col("TIPOSEC") == "M").cast(pl.Int64).sum().alias("LN_MIXTA"),
            pl.col("NV").filter(pl.col("TIPOSEC") == "M").cast(pl.Int64).sum().alias("NV_MIXTA"),
        )
        .with_columns(
            pl.lit(is_intermedia, dtype=pl.Int8).alias("ES_INTERMEDIA"),
        )
        .collect(engine="streaming")
    )


def _aggregate_year_sectional(lf: pl.LazyFrame, year: int) -> pl.DataFrame:
    """Agrega un anio electoral a nivel Seccion Electoral INE."""
    return (
        lf.group_by(["AELEC", "EDOCVE", "MPIOCVE", "ID_MUN_INE", "SECCION", "ID_SEC_INE"])
        .agg(
            pl.col("TIPOSEC").first().alias("TIPOSEC"),
            pl.col("DEF").first().alias("DEF"),
            pl.col("LN").cast(pl.Int64).sum().alias("LN"),
            pl.col("SV").cast(pl.Int64).sum().alias("SV"),
            pl.col("NV").cast(pl.Int64).sum().alias("NV"),
            pl.col("LN").filter(pl.col("EDAD").is_between(18, 29)).cast(pl.Int64).sum().alias("LN_18_29"),
            pl.col("NV").filter(pl.col("EDAD").is_between(18, 29)).cast(pl.Int64).sum().alias("NV_18_29"),
            pl.col("LN").filter(pl.col("EDAD").is_between(30, 59)).cast(pl.Int64).sum().alias("LN_30_59"),
            pl.col("NV").filter(pl.col("EDAD").is_between(30, 59)).cast(pl.Int64).sum().alias("NV_30_59"),
            pl.col("LN").filter(pl.col("SEXO") == 1).cast(pl.Int64).sum().alias("LN_HOMBRES"),
            pl.col("NV").filter(pl.col("SEXO") == 1).cast(pl.Int64).sum().alias("NV_HOMBRES"),
        )
        .collect(engine="streaming")
    )


def build_gold_panels(cfg: AppConfig) -> tuple[pl.DataFrame, pl.DataFrame]:
    """Construye los paneles longitudinales Municipal y Seccional con ingenieria de variables."""
    console.print("[bold cyan]Construyendo paneles analiticos Gold (2009-2024)...[/bold cyan]")
    mun_frames: list[pl.DataFrame] = []
    sec_frames: list[pl.DataFrame] = []

    intermedias = set(cfg.elections["intermedia_years"])
    for year in cfg.elections["years"]:
        parquet_path = cfg.paths.silver_dir / f"ccpc_{year}.parquet"
        lf = pl.scan_parquet(parquet_path)
        is_int = 1 if year in intermedias else 0
        mun_frames.append(_aggregate_year_municipal(lf, year, is_int))
        if year in (2015, 2018, 2021, 2024):
            sec_frames.append(_aggregate_year_sectional(lf, year))

    cat_mun = pl.read_parquet(cfg.paths.silver_dir / "catalogo_municipios_2024.parquet")
    entidades_df = get_entidades_df()

    # 1. Panel Municipal completo 2009-2024
    df_mun = pl.concat(mun_frames, how="vertical").sort(["ID_MUN_INE", "AELEC"])

    ln_f = pl.col("LN").cast(pl.Float64).clip(lower_bound=1.0)
    df_mun = (
        df_mun.with_columns(
            (pl.col("NV").cast(pl.Float64) / ln_f).alias("TASA_ABSTENCION"),
            (pl.col("SV").cast(pl.Float64) / ln_f).alias("TASA_PARTICIPACION"),
            (pl.col("NS").cast(pl.Float64) / ln_f).alias("TASA_NS"),
            (pl.col("LN_18_19").cast(pl.Float64) / ln_f).alias("PROP_PRIMER_VOTO_18_19"),
            (pl.col("LN_18_29").cast(pl.Float64) / ln_f).alias("PROP_JOVENES_18_29"),
            (pl.col("LN_30_39").cast(pl.Float64) / ln_f).alias("PROP_ADULTOS_30_39"),
            (pl.col("LN_40_59").cast(pl.Float64) / ln_f).alias("PROP_ADULTOS_40_59"),
            (pl.col("LN_60_MAS").cast(pl.Float64) / ln_f).alias("PROP_MAYORES_60_MAS"),
            (pl.col("LN_MUJERES").cast(pl.Float64) / ln_f).alias("PROP_MUJERES"),
            (pl.col("LN_HOMBRES").cast(pl.Float64) / ln_f).alias("PROP_HOMBRES"),
            (pl.col("LN_URBANA").cast(pl.Float64) / ln_f).alias("PROP_URBANA"),
            (pl.col("LN_RURAL").cast(pl.Float64) / ln_f).alias("PROP_RURAL"),
            (pl.col("LN_MIXTA").cast(pl.Float64) / ln_f).alias("PROP_MIXTA"),
            ((pl.col("LN_RURAL") + pl.col("LN_MIXTA")).cast(pl.Float64) / ln_f).alias("PROP_RURAL_MIXTA"),
            (ln_f / pl.col("N_SECCIONES").cast(pl.Float64).clip(lower_bound=1.0)).alias("LN_POR_SECCION"),
            # Tasas especificas por estrato
            (
                pl.col("NV_18_29").cast(pl.Float64)
                / pl.col("LN_18_29").cast(pl.Float64).clip(lower_bound=1.0)
            ).alias("ABST_JOVENES_18_29"),
            (
                pl.col("NV_30_59").cast(pl.Float64)
                / pl.col("LN_30_59").cast(pl.Float64).clip(lower_bound=1.0)
            ).alias("ABST_ADULTOS_30_59"),
            (
                pl.col("NV_60_MAS").cast(pl.Float64)
                / pl.col("LN_60_MAS").cast(pl.Float64).clip(lower_bound=1.0)
            ).alias("ABST_MAYORES_60_MAS"),
            (
                pl.col("NV_MUJERES").cast(pl.Float64)
                / pl.col("LN_MUJERES").cast(pl.Float64).clip(lower_bound=1.0)
            ).alias("ABST_MUJERES"),
            (
                pl.col("NV_HOMBRES").cast(pl.Float64)
                / pl.col("LN_HOMBRES").cast(pl.Float64).clip(lower_bound=1.0)
            ).alias("ABST_HOMBRES"),
            (
                (pl.col("NV_RURAL") + pl.col("NV_MIXTA")).cast(pl.Float64)
                / (pl.col("LN_RURAL") + pl.col("LN_MIXTA")).cast(pl.Float64).clip(lower_bound=1.0)
            ).alias("ABST_RURAL_MIXTA"),
        )
        .with_columns(
            (pl.col("ABST_JOVENES_18_29") - pl.col("ABST_ADULTOS_30_59")).alias("BRECHA_JUVENIL_ABST"),
            (pl.col("ABST_HOMBRES") - pl.col("ABST_MUJERES")).alias("BRECHA_GENERO_ABST"),
        )
        .sort(["ID_MUN_INE", "AELEC"])
        .with_columns(
            pl.col("TASA_ABSTENCION").shift(1).over("ID_MUN_INE").alias("ABST_LAG1_3A"),
            pl.col("TASA_ABSTENCION").shift(2).over("ID_MUN_INE").alias("ABST_LAG2_HOMOLOGO_6A"),
            pl.col("TASA_ABSTENCION").shift(3).over("ID_MUN_INE").alias("ABST_LAG3_9A"),
            pl.col("TASA_ABSTENCION").shift(4).over("ID_MUN_INE").alias("ABST_LAG4_HOMOLOGO_12A"),
            pl.col("LN").shift(1).over("ID_MUN_INE").alias("LN_LAG1_3A"),
        )
        .with_columns(
            (pl.col("TASA_ABSTENCION") - pl.col("ABST_LAG2_HOMOLOGO_6A")).alias("TENDENCIA_HOMOLOGA_6A"),
            (pl.col("TASA_ABSTENCION") - pl.col("ABST_LAG1_3A")).alias("CAMBIO_ULTIMA_ELECCION_3A"),
            (
                (pl.col("LN").cast(pl.Float64) - pl.col("LN_LAG1_3A").cast(pl.Float64))
                / pl.col("LN_LAG1_3A").cast(pl.Float64).clip(lower_bound=1.0)
            ).alias("CRECIMIENTO_LN_3A"),
        )
        .join(
            cat_mun.select(["ID_MUN_INE", "MPIONOM_CANONICO", "DEF_PRINCIPAL_2024"]),
            on="ID_MUN_INE",
            how="left",
        )
        .join(entidades_df, on="EDOCVE", how="left")
    )

    df_mun.write_parquet(cfg.paths.gold_dir / "panel_municipal_2009_2024.parquet")
    console.print(
        f"  [green]✓[/green] Panel Municipal Gold: {df_mun.height:,} filas "
        f"({df_mun['ID_MUN_INE'].n_unique():,} municipios unicos)."
    )

    # 2. Panel Seccional (2015-2024 para focalizacion micro-territorial)
    df_sec = pl.concat(sec_frames, how="vertical").sort(["ID_SEC_INE", "AELEC"])
    ln_sec = pl.col("LN").cast(pl.Float64).clip(lower_bound=1.0)
    df_sec = (
        df_sec.with_columns(
            (pl.col("NV").cast(pl.Float64) / ln_sec).alias("TASA_ABSTENCION"),
            (pl.col("LN_18_29").cast(pl.Float64) / ln_sec).alias("PROP_JOVENES_18_29"),
            (
                pl.col("NV_18_29").cast(pl.Float64)
                / pl.col("LN_18_29").cast(pl.Float64).clip(lower_bound=1.0)
            ).alias("ABST_JOVENES_18_29"),
            (
                pl.col("NV_30_59").cast(pl.Float64)
                / pl.col("LN_30_59").cast(pl.Float64).clip(lower_bound=1.0)
            ).alias("ABST_ADULTOS_30_59"),
            (pl.col("LN_HOMBRES").cast(pl.Float64) / ln_sec).alias("PROP_HOMBRES"),
        )
        .with_columns(
            (pl.col("ABST_JOVENES_18_29") - pl.col("ABST_ADULTOS_30_59")).alias("BRECHA_JUVENIL_ABST"),
            pl.col("TASA_ABSTENCION").shift(1).over("ID_SEC_INE").alias("ABST_LAG1_3A"),
            pl.col("TASA_ABSTENCION").shift(2).over("ID_SEC_INE").alias("ABST_LAG2_HOMOLOGO_6A"),
        )
        .join(
            cat_mun.select(["ID_MUN_INE", "MPIONOM_CANONICO"]),
            on="ID_MUN_INE",
            how="left",
        )
        .join(entidades_df.select(["EDOCVE", "ENTIDAD_NOM", "ABREV", "CIRCUNSCRIPCION"]), on="EDOCVE", how="left")
    )
    df_sec.write_parquet(cfg.paths.gold_dir / "panel_seccional_2015_2024.parquet")
    console.print(
        f"  [green]✓[/green] Panel Seccional Gold: {df_sec.height:,} filas "
        f"({df_sec['ID_SEC_INE'].n_unique():,} secciones electorales)."
    )

    # 3. Curva nacional edad x sexo x ciclo electoral para analisis y graficas
    age_curves: list[pl.DataFrame] = []
    for year in cfg.elections["years"]:
        lf = pl.scan_parquet(cfg.paths.silver_dir / f"ccpc_{year}.parquet")
        c = (
            lf.with_columns(pl.col("EDAD").clip(18, 90).alias("EDAD_CLIP"))
            .group_by(["AELEC", "SEXO", "TIPOSEC", "EDAD_CLIP"])
            .agg(
                pl.col("LN").cast(pl.Int64).sum().alias("LN"),
                pl.col("SV").cast(pl.Int64).sum().alias("SV"),
                pl.col("NV").cast(pl.Int64).sum().alias("NV"),
            )
            .collect(engine="streaming")
        )
        age_curves.append(c)
    df_age = pl.concat(age_curves, how="vertical").sort(["AELEC", "SEXO", "TIPOSEC", "EDAD_CLIP"])
    df_age.write_parquet(cfg.paths.gold_dir / "curvas_edad_sexo_tiposec_2009_2024.parquet")

    return df_mun, df_sec

