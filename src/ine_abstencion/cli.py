"""Interfaz de linea de comandos (CLI) para ejecutar el pipeline completo del Reto 2."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd
import polars as pl
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from ine_abstencion.config import load_config
from ine_abstencion.features.correlations import compute_correlation_analysis
from ine_abstencion.features.panel_builder import build_gold_panels
from ine_abstencion.ingestion.loader import ingest_all_to_silver
from ine_abstencion.modeling.predictor import train_and_project
from ine_abstencion.modeling.risk_index import assign_risk_index_and_archetypes
from ine_abstencion.reporting.deliverables import (
    export_anonymized_databases,
    generate_pdf_report_and_slides,
)
from ine_abstencion.reporting.geospatial import export_geospatial_deliverables
from ine_abstencion.reporting.plots import generate_all_figures
from ine_abstencion.scenarios.simulator import simulate_scenarios

console = Console()


def run_pipeline(stage: str = "all", force_ingest: bool = False) -> None:
    cfg = load_config()
    console.print(
        Panel.fit(
            "[bold white]INE — Hackea la Participación (Reto 2)[/bold white]\n"
            "[cyan]Pipeline Predictivo, Semáforo Territorial y Simulador de Escenarios (2009–2027)[/cyan]",
            border_style="magenta",
        )
    )

    if stage in ("all", "ingest"):
        audit_df = ingest_all_to_silver(cfg, force=force_ingest)
    else:
        audit_df = pl.read_csv(cfg.paths.tables_dir / "auditoria_calidad_datos_2009_2024.csv")

    if stage == "ingest":
        return

    if stage in ("all", "features"):
        df_mun, df_sec = build_gold_panels(cfg)
        corr_summary, corr_matrix = compute_correlation_analysis(cfg, df_mun)
    else:
        df_mun = pl.read_parquet(cfg.paths.gold_dir / "panel_municipal_2009_2024.parquet")
        df_sec = pl.read_parquet(cfg.paths.gold_dir / "panel_seccional_2015_2024.parquet")
        corr_summary = pd.read_csv(cfg.paths.tables_dir / "correlaciones_abstencion.csv")
        corr_matrix = pd.read_csv(cfg.paths.tables_dir / "matriz_correlacion_completa.csv", index_col=0)

    if stage == "features":
        return

    if stage in ("all", "model", "simulate"):
        proj_mun, proj_sec = train_and_project(cfg, df_mun, df_sec)
        df_mun_risk, df_sec_risk, thresholds = assign_risk_index_and_archetypes(cfg, proj_mun, proj_sec)
        df_sim_mun, df_sim_sec, scenarios_summary = simulate_scenarios(
            cfg, df_mun_risk, df_sec_risk, thresholds
        )
        df_sim_mun.to_parquet(cfg.paths.gold_dir / "proyeccion_y_escenarios_municipios_2027.parquet", index=False)
        df_sim_sec.to_parquet(cfg.paths.gold_dir / "proyeccion_y_escenarios_secciones_2027.parquet", index=False)
    elif stage == "deliverables":
        df_sim_mun = pd.read_parquet(cfg.paths.gold_dir / "proyeccion_y_escenarios_municipios_2027.parquet")
        df_sim_sec = pd.read_parquet(cfg.paths.gold_dir / "proyeccion_y_escenarios_secciones_2027.parquet")
        scenarios_summary = pd.read_csv(cfg.paths.tables_dir / "resumen_escenarios_2027.csv")

    if stage in ("model", "simulate"):
        return

    metrics_df = pd.read_csv(cfg.paths.tables_dir / "metricas_backtesting_modelos.csv")
    coef_df = pd.read_csv(cfg.paths.tables_dir / "importancia_y_coeficientes_modelo.csv")

    console.print("[bold cyan]Generando figuras editoriales (300 DPI)...[/bold cyan]")
    figs = generate_all_figures(
        cfg,
        audit_df,
        df_mun,
        corr_summary,
        corr_matrix,
        metrics_df,
        coef_df,
        df_sim_mun,
        scenarios_summary,
    )
    console.print(f"  [green]✓[/green] {len(figs)} gráficas generadas en {cfg.paths.figures_dir}")

    console.print("[bold cyan]Generando cartografía (.GPKG, .GeoJSON) y Tablero Web Interactivo (.HTML)...[/bold cyan]")
    geo_paths = export_geospatial_deliverables(cfg, df_sim_mun)
    for k, p in geo_paths.items():
        console.print(f"  [green]✓[/green] {k}: {p.name}")

    console.print("[bold cyan]Exportando Base de Datos Agregada y Anonimizada (.CSV y .XLSX)...[/bold cyan]")
    db_paths = export_anonymized_databases(
        cfg, df_sim_mun, df_sim_sec, scenarios_summary, corr_summary, coef_df, metrics_df
    )
    for k, p in db_paths.items():
        console.print(f"  [green]✓[/green] {k}: {p.name}")

    console.print("[bold cyan]Compilando Reporte Metodológico PDF (12 cuartillas) y Presentación Ejecutiva PDF (10 láminas)...[/bold cyan]")
    doc_paths = generate_pdf_report_and_slides(
        cfg, audit_df, corr_summary, metrics_df, coef_df, df_sim_mun, scenarios_summary
    )
    for k, p in doc_paths.items():
        console.print(f"  [green]✓[/green] {k}: {p.name}")

    # Mostrar tabla resumen ejecutiva en consola
    t = Table(title="Resumen Nacional de Escenarios 2027 (Reto 2 INE)")
    t.add_column("Escenario", style="cyan")
    t.add_column("Abstención 2027", justify="right")
    t.add_column("Participación 2027", justify="right")
    t.add_column("Votos Recuperados", justify="right", style="green")
    t.add_column("Mun. Críticos", justify="right", style="red")
    for _, r in scenarios_summary.iterrows():
        t.add_row(
            str(r["escenario"]),
            f"{float(r['tasa_abstencion_nacional_pct']):.2f}%",
            f"{float(r['tasa_participacion_nacional_pct']):.2f}%",
            f"+{int(r['votos_adicionales_recuperados']):,}",
            str(int(r["municipios_riesgo_critico"])),
        )
    console.print(t)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="ine-riesgo",
        description="CLI del Reto 2 Hackaton INE 2026: Prediccion y escenarios de riesgo de abstencion",
    )
    parser.add_argument(
        "command",
        nargs="?",
        default="run-all",
        choices=["run-all", "ingest", "features", "model", "simulate", "deliverables"],
        help="Etapa del pipeline a ejecutar (por defecto: run-all)",
    )
    parser.add_argument("--force-ingest", action="store_true", help="Re-procesar CSVs crudos aunque exista Silver")
    args = parser.parse_args(argv if argv is not None else sys.argv[1:])

    stage_map = {
        "run-all": "all",
        "ingest": "ingest",
        "features": "features",
        "model": "model",
        "simulate": "simulate",
        "deliverables": "deliverables",
    }
    run_pipeline(stage=stage_map[args.command], force_ingest=args.force_ingest)


if __name__ == "__main__":
    main()

