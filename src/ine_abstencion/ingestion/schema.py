"""Contratos de datos y esquemas Polars para los archivos CCPC 2009-2024."""

from __future__ import annotations

import polars as pl

TERRITORIAL_COLUMNS: tuple[str, ...] = (
    "AELEC",
    "FELECCION",
    "EDOCVE",
    "EDONOM",
    "MPIOCVE",
    "MPIONOM",
    "SECCION",
    "TIPOSEC",
    "DEF",
    "DEL",
    "SEXO",
    "EDAD",
    "LN",
    "SV",
    "NV",
    "NS",
)

TERRITORIAL_POLARS_SCHEMA: dict[str, pl.DataType] = {
    "AELEC": pl.Int16,
    "FELECCION": pl.String,
    "EDOCVE": pl.Int8,
    "EDONOM": pl.String,
    "MPIOCVE": pl.Int16,
    "MPIONOM": pl.String,
    "SECCION": pl.Int32,
    "TIPOSEC": pl.String,
    "DEF": pl.Int16,
    "DEL": pl.Int16,
    "SEXO": pl.Int8,
    "EDAD": pl.Int16,
    "LN": pl.Int32,
    "SV": pl.Int32,
    "NV": pl.Int32,
    "NS": pl.Int32,
}

SPECIAL_MODAL_FILES: tuple[str, ...] = (
    "datosabiertos_deceyec_conteoscensales_prisionpreventiva2024.csv",
    "datosabiertos_deceyec_conteoscensales_votoanticipado2024.csv",
)

