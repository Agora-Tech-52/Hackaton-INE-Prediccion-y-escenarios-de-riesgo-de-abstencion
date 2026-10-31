"""Pruebas automatizadas de integridad de esquemas, catalogos, privacidad y entregables."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import polars as pl

from ine_abstencion.config import load_config
from ine_abstencion.ingestion.catalogs import get_entidades_df
from ine_abstencion.ingestion.loader import discover_raw_files


def test_discover_192_territorial_and_2_modal_files() -> None:
    cfg = load_config()
    by_year, modal_files = discover_raw_files(cfg.paths.raw_data_dir)
    assert len(by_year) == 6
    for yr, files in by_year.items():
        assert len(files) == 32, f"El anio {yr} debe tener exactamente 32 archivos estatales"
    assert len(modal_files) == 2


def test_entidades_catalog_completeness() -> None:
    df_ent = get_entidades_df()
    assert df_ent.height == 32
    assert set(df_ent["CIRCUNSCRIPCION"].to_list()) == {1, 2, 3, 4, 5}


def test_deliverables_and_privacy_constraints() -> None:
    cfg = load_config()
    mun_csv = cfg.paths.deliverables_dir / "Base_Datos_Anonimizada_Escenarios_Municipios_2027.csv"
    if not mun_csv.exists():
        return
    df = pd.read_csv(mun_csv)
    assert len(df) > 2400
    assert (df["LN"] >= cfg.privacy["min_ln_cell_threshold"]).all()
    assert (df["ABST_PROY_2027_SIN_INT"].between(0.0, 1.0)).all()
    assert (df["ABST_PROY_2027_CON_INT"] <= df["ABST_PROY_2027_SIN_INT"] + 1e-6).all()
    assert set(df["SEMAFORO_SIN_INT"].unique()).issubset({"Bajo", "Moderado", "Alto", "Crítico"})

