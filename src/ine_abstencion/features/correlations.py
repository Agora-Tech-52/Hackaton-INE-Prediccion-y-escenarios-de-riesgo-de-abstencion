"""Analisis de correlacion (Pearson, Spearman) y diagnostico de multicolinealidad (VIF)."""

from __future__ import annotations

import numpy as np
import pandas as pd
import polars as pl
from scipy import stats

from ine_abstencion.config import AppConfig

CORRELATION_FEATURES: dict[str, str] = {
    "TASA_ABSTENCION": "Tasa de Abstención (t)",
    "ABST_LAG2_HOMOLOGO_6A": "Abstención Elección Homóloga Previa (t-6)",
    "ABST_LAG1_3A": "Abstención Elección Inmediata Anterior (t-3)",
    "ES_INTERMEDIA": "Ciclo Electoral Intermedio (1=Sí, 0=Presidencial)",
    "PROP_JOVENES_18_29": "Proporción Jóvenes 18-29 años (% LN)",
    "PROP_PRIMER_VOTO_18_19": "Proporción Primer Voto 18-19 años (% LN)",
    "PROP_ADULTOS_40_59": "Proporción Adultos 40-59 años (% LN)",
    "PROP_MAYORES_60_MAS": "Proporción Adultos Mayores 60+ (% LN)",
    "EDAD_PROMEDIO_LN": "Edad Promedio del Padrón (años)",
    "BRECHA_JUVENIL_ABST": "Brecha de Abstención Juvenil vs Adultos",
    "BRECHA_GENERO_ABST": "Brecha de Abstención por Sexo (Hombres - Mujeres)",
    "PROP_URBANA": "Proporción Lista Nominal Urbana (%)",
    "PROP_RURAL_MIXTA": "Proporción Lista Nominal Rural/Mixta (%)",
    "CRECIMIENTO_LN_3A": "Crecimiento Demográfico del Padrón (3 años)",
    "LN_POR_SECCION": "Densidad Media Electores por Sección",
}


def compute_correlation_analysis(cfg: AppConfig, df_mun: pl.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Calcula correlaciones de Pearson y Spearman contra TASA_ABSTENCION y matriz completa + VIF."""
    cols = list(CORRELATION_FEATURES.keys())
    pdf = df_mun.select(cols + ["LN"]).drop_nulls().to_pandas()

    target = pdf["TASA_ABSTENCION"].to_numpy()
    rows: list[dict[str, object]] = []

    # Matriz de diseno para VIF (excluyendo variable objetivo y complementos colineales exactos)
    vif_cols = [
        "ABST_LAG2_HOMOLOGO_6A",
        "ABST_LAG1_3A",
        "ES_INTERMEDIA",
        "PROP_JOVENES_18_29",
        "PROP_MAYORES_60_MAS",
        "BRECHA_JUVENIL_ABST",
        "BRECHA_GENERO_ABST",
        "PROP_URBANA",
        "CRECIMIENTO_LN_3A",
        "LN_POR_SECCION",
    ]
    X_vif = pdf[vif_cols].to_numpy(dtype=float)
    X_std = (X_vif - X_vif.mean(axis=0)) / np.where(X_vif.std(axis=0) == 0, 1.0, X_vif.std(axis=0))
    corr_vif = np.corrcoef(X_std, rowvar=False)
    inv_corr = np.linalg.pinv(corr_vif)
    vif_map = {col: float(inv_corr[i, i]) for i, col in enumerate(vif_cols)}

    for col, label in CORRELATION_FEATURES.items():
        if col == "TASA_ABSTENCION":
            continue
        x = pdf[col].to_numpy(dtype=float)
        r_p, p_p = stats.pearsonr(x, target)
        r_s, p_s = stats.spearmanr(x, target)
        # Correlacion ponderada por Lista Nominal
        w = pdf["LN"].to_numpy(dtype=float)
        w = w / w.sum()
        mx = np.sum(w * x)
        my = np.sum(w * target)
        cov_xy = np.sum(w * (x - mx) * (target - my))
        r_w = cov_xy / np.sqrt(np.sum(w * (x - mx) ** 2) * np.sum(w * (target - my) ** 2))

        rows.append(
            {
                "variable": col,
                "etiqueta": label,
                "pearson_r": round(float(r_p), 4),
                "pearson_p_valor": float(p_p),
                "spearman_rho": round(float(r_s), 4),
                "spearman_p_valor": float(p_s),
                "pearson_ponderado_ln": round(float(r_w), 4),
                "vif": round(vif_map.get(col, np.nan), 2) if col in vif_map else np.nan,
            }
        )

    summary_df = pd.DataFrame(rows).sort_values(
        by="pearson_ponderado_ln", key=lambda s: s.abs(), ascending=False
    )
    summary_df.to_csv(cfg.paths.tables_dir / "correlaciones_abstencion.csv", index=False)

    # Matriz de correlacion de Pearson completa con nombres legibles
    matrix_cols = [
        "TASA_ABSTENCION",
        "ABST_LAG2_HOMOLOGO_6A",
        "ABST_LAG1_3A",
        "ES_INTERMEDIA",
        "PROP_JOVENES_18_29",
        "PROP_MAYORES_60_MAS",
        "BRECHA_JUVENIL_ABST",
        "BRECHA_GENERO_ABST",
        "PROP_URBANA",
        "CRECIMIENTO_LN_3A",
    ]
    corr_matrix = pdf[matrix_cols].corr(method="pearson").round(4)
    corr_matrix.to_csv(cfg.paths.tables_dir / "matriz_correlacion_completa.csv")

    return summary_df, corr_matrix

