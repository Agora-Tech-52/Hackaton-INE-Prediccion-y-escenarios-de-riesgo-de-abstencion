"""Construccion del Indice Compuesto de Riesgo Territorial, Semaforo y Arquetipos."""

from __future__ import annotations

import numpy as np
import pandas as pd

from ine_abstencion.config import AppConfig


def _robust_zscore(x: np.ndarray) -> np.ndarray:
    med = np.nanmedian(x)
    iqr = np.nanpercentile(x, 75) - np.nanpercentile(x, 25)
    scale = iqr / 1.349 if iqr > 1e-6 else np.nanstd(x)
    scale = scale if scale > 1e-6 else 1.0
    return np.clip((x - med) / scale, -3.5, 3.5)


def classify_semaforo(scores_0_100: np.ndarray, thresholds: tuple[float, float, float]) -> np.ndarray:
    q_mod, q_alt, q_crit = thresholds
    out = np.full(len(scores_0_100), "Bajo", dtype=object)
    out[scores_0_100 >= q_mod] = "Moderado"
    out[scores_0_100 >= q_alt] = "Alto"
    out[scores_0_100 >= q_crit] = "Crítico"
    return out


def assign_risk_index_and_archetypes(
    cfg: AppConfig, proj_mun: pd.DataFrame, proj_sec: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame, tuple[float, float, float]]:
    """Calcula el Score de Riesgo (0-100), el Semaforo de 4 niveles y el Arquetipo Diagnostico."""
    df = proj_mun.copy()

    # 1. Tres dimensiones del riesgo: Nivel proyectado 2027, Deterioro estructural y Masa critica (log NV)
    level = df["ABST_PROY_2027_SIN_INT"].to_numpy(dtype=float)
    trend = (df["ABST_PROY_2027_SIN_INT"] - df["ABST_2015"]).fillna(0.0).to_numpy(dtype=float)
    volume = np.log1p(df["NV_PROY_2027_SIN_INT"].to_numpy(dtype=float))

    z_level = _robust_zscore(level)
    z_trend = _robust_zscore(trend)
    z_vol = _robust_zscore(volume)

    w_l = float(cfg.risk_index["w_level"])
    w_t = float(cfg.risk_index["w_trend"])
    w_v = float(cfg.risk_index["w_volume"])

    raw_score = w_l * z_level + w_t * z_trend + w_v * z_vol
    # Escalar a 0-100 mediante CDF normal estandar suavizada
    from scipy.stats import norm

    score_0_100 = np.round(norm.cdf(raw_score) * 100.0, 2)
    df["SCORE_RIESGO_SIN_INT"] = score_0_100
    df["DETERIORO_INTERMEDIAS_PP"] = np.round(trend * 100.0, 2)
    df["FATIGA_CICLO_INTERMEDIA_PP"] = np.round(
        (df["ABST_PROY_2027_SIN_INT"] - df["ABST_2024_OBS"]).to_numpy(dtype=float) * 100.0, 2
    )

    # Umbrales fijos del Semaforo (calibrados sobre la distribucion sin intervencion)
    q_mod = float(np.quantile(score_0_100, cfg.risk_index["p_moderado"]))
    q_alt = float(np.quantile(score_0_100, cfg.risk_index["p_alto"]))
    q_crit = float(np.quantile(score_0_100, cfg.risk_index["p_critico"]))
    thresholds = (q_mod, q_alt, q_crit)

    df["SEMAFORO_SIN_INT"] = classify_semaforo(score_0_100, thresholds)

    # Asignacion del Arquetipo Diagnostico Principal por territorio
    z_youth = _robust_zscore(
        (df["PROP_JOVENES_18_29"] * df["BRECHA_JUVENIL_ABST"].clip(lower=0.02)).to_numpy(dtype=float)
    )
    z_rural = _robust_zscore(
        (df["PROP_RURAL_MIXTA"] * df["ABST_RURAL_MIXTA"].fillna(df["ABST_2024_OBS"])).to_numpy(dtype=float)
    )
    z_fatigue = _robust_zscore((df["ABST_PROY_2027_SIN_INT"] - df["ABST_2024_OBS"]).to_numpy(dtype=float))
    z_periph = _robust_zscore((df["PROP_URBANA"] * df["CRECIMIENTO_LN_3A"].clip(lower=0.0)).to_numpy(dtype=float))

    drivers = np.vstack([z_youth, z_rural, z_fatigue, z_periph]).T
    driver_names = [
        "1. Brecha Juvenil y Primer Voto (18-29)",
        "2. Rezago Territorial Rural / Mixto",
        "3. Fatiga Aguda en Elección Intermedia",
        "4. Periferia Urbana en Expansión Demográfica",
    ]
    best_idx = np.argmax(drivers, axis=1)
    arquetipos = [driver_names[idx] for idx in best_idx]
    df["ARQUETIPO_RIESGO"] = np.where(
        df["SEMAFORO_SIN_INT"] == "Bajo",
        "0. Participación Resiliente (Mantenimiento)",
        arquetipos,
    )

    # Clasificar tambien las secciones electorales para focalizacion micro-territorial
    sec = proj_sec.copy()
    sec_level = sec["ABST_PROY_2027_SIN_INT"].to_numpy(dtype=float)
    sec_trend = (
        sec["ABST_PROY_2027_SIN_INT"] - sec["ABST_LAG2_HOMOLOGO_6A"].fillna(sec["TASA_ABSTENCION"])
    ).to_numpy(dtype=float)
    sec_vol = np.log1p(sec["NV_PROY_2027_SIN_INT"].to_numpy(dtype=float))
    sec_raw = w_l * _robust_zscore(sec_level) + w_t * _robust_zscore(sec_trend) + w_v * _robust_zscore(sec_vol)
    sec["SCORE_RIESGO_SIN_INT"] = np.round(norm.cdf(sec_raw) * 100.0, 2)
    q_s_mod = float(np.quantile(sec["SCORE_RIESGO_SIN_INT"], cfg.risk_index["p_moderado"]))
    q_s_alt = float(np.quantile(sec["SCORE_RIESGO_SIN_INT"], cfg.risk_index["p_alto"]))
    q_s_crit = float(np.quantile(sec["SCORE_RIESGO_SIN_INT"], cfg.risk_index["p_critico"]))
    sec["SEMAFORO_SIN_INT"] = classify_semaforo(
        sec["SCORE_RIESGO_SIN_INT"].to_numpy(), (q_s_mod, q_s_alt, q_s_crit)
    )

    return df, sec, thresholds

