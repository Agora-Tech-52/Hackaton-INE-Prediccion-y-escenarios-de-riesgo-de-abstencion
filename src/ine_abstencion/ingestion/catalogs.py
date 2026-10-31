"""Catalogos canonicos de Entidades Federativas y Circunscripciones Electorales del INE."""

from __future__ import annotations

import polars as pl

# Catalogo oficial de las 32 entidades federativas y su Circunscripcion Electoral INE (1 a 5)
ENTIDADES_CATALOG: list[dict[str, object]] = [
    {"EDOCVE": 1, "CVE_ENT": "01", "ENTIDAD_NOM": "Aguascalientes", "ABREV": "AGS", "CIRCUNSCRIPCION": 2},
    {"EDOCVE": 2, "CVE_ENT": "02", "ENTIDAD_NOM": "Baja California", "ABREV": "BC", "CIRCUNSCRIPCION": 1},
    {"EDOCVE": 3, "CVE_ENT": "03", "ENTIDAD_NOM": "Baja California Sur", "ABREV": "BCS", "CIRCUNSCRIPCION": 1},
    {"EDOCVE": 4, "CVE_ENT": "04", "ENTIDAD_NOM": "Campeche", "ABREV": "CAMP", "CIRCUNSCRIPCION": 3},
    {"EDOCVE": 5, "CVE_ENT": "05", "ENTIDAD_NOM": "Coahuila", "ABREV": "COAH", "CIRCUNSCRIPCION": 2},
    {"EDOCVE": 6, "CVE_ENT": "06", "ENTIDAD_NOM": "Colima", "ABREV": "COL", "CIRCUNSCRIPCION": 5},
    {"EDOCVE": 7, "CVE_ENT": "07", "ENTIDAD_NOM": "Chiapas", "ABREV": "CHIS", "CIRCUNSCRIPCION": 3},
    {"EDOCVE": 8, "CVE_ENT": "08", "ENTIDAD_NOM": "Chihuahua", "ABREV": "CHIH", "CIRCUNSCRIPCION": 1},
    {"EDOCVE": 9, "CVE_ENT": "09", "ENTIDAD_NOM": "Ciudad de México", "ABREV": "CDMX", "CIRCUNSCRIPCION": 4},
    {"EDOCVE": 10, "CVE_ENT": "10", "ENTIDAD_NOM": "Durango", "ABREV": "DGO", "CIRCUNSCRIPCION": 1},
    {"EDOCVE": 11, "CVE_ENT": "11", "ENTIDAD_NOM": "Guanajuato", "ABREV": "GTO", "CIRCUNSCRIPCION": 2},
    {"EDOCVE": 12, "CVE_ENT": "12", "ENTIDAD_NOM": "Guerrero", "ABREV": "GRO", "CIRCUNSCRIPCION": 4},
    {"EDOCVE": 13, "CVE_ENT": "13", "ENTIDAD_NOM": "Hidalgo", "ABREV": "HGO", "CIRCUNSCRIPCION": 4},
    {"EDOCVE": 14, "CVE_ENT": "14", "ENTIDAD_NOM": "Jalisco", "ABREV": "JAL", "CIRCUNSCRIPCION": 1},
    {"EDOCVE": 15, "CVE_ENT": "15", "ENTIDAD_NOM": "Estado de México", "ABREV": "MEX", "CIRCUNSCRIPCION": 5},
    {"EDOCVE": 16, "CVE_ENT": "16", "ENTIDAD_NOM": "Michoacán", "ABREV": "MICH", "CIRCUNSCRIPCION": 5},
    {"EDOCVE": 17, "CVE_ENT": "17", "ENTIDAD_NOM": "Morelos", "ABREV": "MOR", "CIRCUNSCRIPCION": 4},
    {"EDOCVE": 18, "CVE_ENT": "18", "ENTIDAD_NOM": "Nayarit", "ABREV": "NAY", "CIRCUNSCRIPCION": 1},
    {"EDOCVE": 19, "CVE_ENT": "19", "ENTIDAD_NOM": "Nuevo León", "ABREV": "NL", "CIRCUNSCRIPCION": 2},
    {"EDOCVE": 20, "CVE_ENT": "20", "ENTIDAD_NOM": "Oaxaca", "ABREV": "OAX", "CIRCUNSCRIPCION": 3},
    {"EDOCVE": 21, "CVE_ENT": "21", "ENTIDAD_NOM": "Puebla", "ABREV": "PUE", "CIRCUNSCRIPCION": 4},
    {"EDOCVE": 22, "CVE_ENT": "22", "ENTIDAD_NOM": "Querétaro", "ABREV": "QRO", "CIRCUNSCRIPCION": 5},
    {"EDOCVE": 23, "CVE_ENT": "23", "ENTIDAD_NOM": "Quintana Roo", "ABREV": "QROO", "CIRCUNSCRIPCION": 3},
    {"EDOCVE": 24, "CVE_ENT": "24", "ENTIDAD_NOM": "San Luis Potosí", "ABREV": "SLP", "CIRCUNSCRIPCION": 2},
    {"EDOCVE": 25, "CVE_ENT": "25", "ENTIDAD_NOM": "Sinaloa", "ABREV": "SIN", "CIRCUNSCRIPCION": 1},
    {"EDOCVE": 26, "CVE_ENT": "26", "ENTIDAD_NOM": "Sonora", "ABREV": "SON", "CIRCUNSCRIPCION": 1},
    {"EDOCVE": 27, "CVE_ENT": "27", "ENTIDAD_NOM": "Tabasco", "ABREV": "TAB", "CIRCUNSCRIPCION": 3},
    {"EDOCVE": 28, "CVE_ENT": "28", "ENTIDAD_NOM": "Tamaulipas", "ABREV": "TAMPS", "CIRCUNSCRIPCION": 2},
    {"EDOCVE": 29, "CVE_ENT": "29", "ENTIDAD_NOM": "Tlaxcala", "ABREV": "TLAX", "CIRCUNSCRIPCION": 4},
    {"EDOCVE": 30, "CVE_ENT": "30", "ENTIDAD_NOM": "Veracruz", "ABREV": "VER", "CIRCUNSCRIPCION": 3},
    {"EDOCVE": 31, "CVE_ENT": "31", "ENTIDAD_NOM": "Yucatán", "ABREV": "YUC", "CIRCUNSCRIPCION": 3},
    {"EDOCVE": 32, "CVE_ENT": "32", "ENTIDAD_NOM": "Zacatecas", "ABREV": "ZAC", "CIRCUNSCRIPCION": 2},
]


def get_entidades_df() -> pl.DataFrame:
    return pl.DataFrame(
        ENTIDADES_CATALOG,
        schema={
            "EDOCVE": pl.Int8,
            "CVE_ENT": pl.String,
            "ENTIDAD_NOM": pl.String,
            "ABREV": pl.String,
            "CIRCUNSCRIPCION": pl.Int8,
        },
    )

