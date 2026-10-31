"""Simulacion de escenarios de intervencion civica INE y optimizacion de portafolio territorial."""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import norm

from ine_abstencion.config import AppConfig
from ine_abstencion.modeling.risk_index import _robust_zscore, classify_semaforo


def simulate_scenarios(
    cfg: AppConfig,
    df_mun_risk: pd.DataFrame,
    df_sec_risk: pd.DataFrame,
    thresholds: tuple[float, float, float],
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Simula los escenarios contrafactuales 2027:
      - Escenario 0: Sin Intervencion (Inercial)
      - Escenario 1: Focalizacion Juvenil 18-29 ('Mi Primer Voto / Universidades') en zonas Alto/Critico
      - Escenario 2: Brigadas Territoriales Rurales y Mixtas en zonas Alto/Critico
      - Escenario 3: Portafolio Estrategico Optimo INE (Top 15% de municipios de mayor retorno civico
                     y paquete integral diferenciado segun Arquetipo de Riesgo)
    """
    df = df_mun_risk.copy()

    ln_2027 = df["LN_PROY_2027"].to_numpy(dtype=float)
    abst_base = df["ABST_PROY_2027_SIN_INT"].to_numpy(dtype=float)
    prop_youth = df["PROP_JOVENES_18_29"].to_numpy(dtype=float)
    youth_gap = np.clip(df["BRECHA_JUVENIL_ABST"].fillna(0.10).to_numpy(dtype=float), 0.04, 0.35)
    prop_rm = df["PROP_RURAL_MIXTA"].to_numpy(dtype=float)
    fatigue = np.clip((df["ABST_PROY_2027_SIN_INT"] - df["ABST_2024_OBS"]).to_numpy(dtype=float), 0.03, 0.35)

    is_high_or_crit = df["SEMAFORO_SIN_INT"].isin(["Alto", "Crítico"]).to_numpy()

    # --- ESCENARIO 1: Intervencion Focalizada en Juventudes (18-29) en zonas Alto/Critico ---
    # Reduce la brecha juvenil en 20% (moderado) + 4.5 pp de movilizacion directa en el estrato 18-29
    delta_youth_mod = is_high_or_crit.astype(float) * prop_youth * (
        cfg.scenarios["youth_gap_reduction_moderate"] * youth_gap + 0.045
    )
    df["ABST_2027_ESC1_JUVENTUD"] = np.clip(abst_base - delta_youth_mod, 0.05, 0.95)
    df["VOTOS_RECUP_ESC1_JUVENTUD"] = np.round(ln_2027 * (abst_base - df["ABST_2027_ESC1_JUVENTUD"])).astype(int)

    # --- ESCENARIO 2: Brigadas Comunitarias en Secciones Rurales y Mixtas (Alto/Critico) ---
    # Reduce la fatiga intermedia y rezago en secciones rurales/mixtas
    delta_rural_mod = is_high_or_crit.astype(float) * prop_rm * (
        cfg.scenarios["rural_fatigue_reduction_moderate"] * fatigue + 0.038
    )
    df["ABST_2027_ESC2_RURAL"] = np.clip(abst_base - delta_rural_mod, 0.05, 0.95)
    df["VOTOS_RECUP_ESC2_RURAL"] = np.round(ln_2027 * (abst_base - df["ABST_2027_ESC2_RURAL"])).astype(int)

    # --- ESCENARIO 3: Portafolio Estrategico Optimo INE (Con Intervencion Hipotetica Principal) ---
    # Calculamos el potencial de reduccion de abstencion adaptando la intervencion al Arquetipo de cada zona
    potential_reduction_rate = (
        prop_youth * (cfg.scenarios["youth_gap_reduction_moderate"] * youth_gap + 0.045)
        + prop_rm * (cfg.scenarios["rural_fatigue_reduction_moderate"] * fatigue + 0.030)
        + (1.0 - prop_rm) * 0.20 * fatigue
    )
    potential_reduction_rate = np.clip(potential_reduction_rate, 0.025, 0.115)

    # Optimizacion de recursos del INE: priorizar el Top K% (15%) de municipios elegibles (Alto/Critico)
    # o el conjunto que maximiza el impacto ponderado por severidad de riesgo y volumen de votos recuperables
    priority_utility = (
        is_high_or_crit.astype(float)
        * (ln_2027 ** 0.75)
        * potential_reduction_rate
        * (df["SCORE_RIESGO_SIN_INT"].to_numpy(dtype=float) / 100.0)
    )
    k_mun = int(np.ceil(len(df) * float(cfg.scenarios["budget_coverage_fraction"])))
    top_indices = np.argsort(priority_utility)[::-1][:k_mun]
    intervened_mask = np.zeros(len(df), dtype=bool)
    intervened_mask[top_indices] = True
    # Tambien intervenimos con campana preventiva ligera todos los municipios en Riesgo Critico
    intervened_mask = intervened_mask | (df["SEMAFORO_SIN_INT"].to_numpy() == "Crítico")

    df["INTERVENIDO_PORTAFOLIO_INE"] = intervened_mask
    # En zonas priorizadas se aplica el paquete integral; en zonas Moderadas/Altas no priorizadas llega
    # difusion digital nacional (efecto spillover de 1.2 pp)
    spillover = (~intervened_mask & df["SEMAFORO_SIN_INT"].isin(["Moderado", "Alto"])).astype(float) * 0.012
    effect_opt_mod = intervened_mask.astype(float) * potential_reduction_rate + spillover

    # Bandas de sensibilidad (Conservadora = 65% del efecto moderado, Optimista = 135% del efecto moderado)
    effect_opt_cons = 0.65 * effect_opt_mod
    effect_opt_opt = 1.35 * effect_opt_mod

    df["ABST_PROY_2027_CON_INT_CONSERVADOR"] = np.clip(abst_base - effect_opt_cons, 0.05, 0.95)
    df["ABST_PROY_2027_CON_INT"] = np.clip(abst_base - effect_opt_mod, 0.05, 0.95)
    df["ABST_PROY_2027_CON_INT_OPTIMISTA"] = np.clip(abst_base - effect_opt_opt, 0.05, 0.95)

    df["REDUCCION_ABST_PP"] = np.round((abst_base - df["ABST_PROY_2027_CON_INT"]) * 100.0, 2)
    df["NV_PROY_2027_CON_INT"] = np.round(ln_2027 * df["ABST_PROY_2027_CON_INT"]).astype(int)
    df["SV_PROY_2027_CON_INT"] = df["LN_PROY_2027"] - df["NV_PROY_2027_CON_INT"]
    df["VOTOS_RECUPERADOS_CON_INT"] = df["NV_PROY_2027_SIN_INT"] - df["NV_PROY_2027_CON_INT"]

    # Recalcular Score de Riesgo y Semaforo post-intervencion usando la misma escala base
    level_base = abst_base
    trend_base = (df["ABST_PROY_2027_SIN_INT"] - df["ABST_2015"]).fillna(0.0).to_numpy(dtype=float)
    vol_base = np.log1p(df["NV_PROY_2027_SIN_INT"].to_numpy(dtype=float))

    def _transform_like_base(x_new: np.ndarray, x_ref: np.ndarray) -> np.ndarray:
        med = np.nanmedian(x_ref)
        iqr = np.nanpercentile(x_ref, 75) - np.nanpercentile(x_ref, 25)
        scale = iqr / 1.349 if iqr > 1e-6 else np.nanstd(x_ref)
        return np.clip((x_new - med) / max(scale, 1e-6), -3.5, 3.5)

    z_l_new = _transform_like_base(df["ABST_PROY_2027_CON_INT"].to_numpy(dtype=float), level_base)
    z_t_new = _transform_like_base(
        (df["ABST_PROY_2027_CON_INT"] - df["ABST_2015"]).fillna(0.0).to_numpy(dtype=float), trend_base
    )
    z_v_new = _transform_like_base(np.log1p(df["NV_PROY_2027_CON_INT"].to_numpy(dtype=float)), vol_base)

    w_l = float(cfg.risk_index["w_level"])
    w_t = float(cfg.risk_index["w_trend"])
    w_v = float(cfg.risk_index["w_volume"])
    raw_new = w_l * z_l_new + w_t * z_t_new + w_v * z_v_new
    df["SCORE_RIESGO_CON_INT"] = np.round(norm.cdf(raw_new) * 100.0, 2)
    df["SEMAFORO_CON_INT"] = classify_semaforo(df["SCORE_RIESGO_CON_INT"].to_numpy(), thresholds)

    # Propagar efecto de intervencion a nivel Seccion Electoral
    sec = df_sec_risk.merge(
        df[["ID_MUN_INE", "INTERVENIDO_PORTAFOLIO_INE", "REDUCCION_ABST_PP", "ARQUETIPO_RIESGO"]],
        on="ID_MUN_INE",
        how="left",
    )
    sec["ABST_PROY_2027_CON_INT"] = np.clip(
        sec["ABST_PROY_2027_SIN_INT"] - (sec["REDUCCION_ABST_PP"].fillna(0.0) / 100.0), 0.05, 0.95
    )
    sec["NV_PROY_2027_CON_INT"] = np.round(sec["LN"] * sec["ABST_PROY_2027_CON_INT"]).astype(int)
    sec["VOTOS_RECUPERADOS_CON_INT"] = sec["NV_PROY_2027_SIN_INT"] - sec["NV_PROY_2027_CON_INT"]

    # Tabla resumen comparativa de todos los escenarios a nivel nacional
    tot_ln = int(df["LN_PROY_2027"].sum())
    scenarios_summary: list[dict[str, object]] = []

    def _row_summary(nombre: str, col_abst: str, semaforo_col: str | None = None) -> dict[str, object]:
        nv_s = np.round(ln_2027 * df[col_abst].to_numpy(dtype=float)).astype(int)
        sv_s = int(tot_ln - nv_s.sum())
        abst_nac = 100.0 * float(nv_s.sum()) / tot_ln
        part_nac = 100.0 - abst_nac
        votos_rec = int(df["NV_PROY_2027_SIN_INT"].sum() - nv_s.sum())
        if semaforo_col is not None:
            sem = df[semaforo_col]
        else:
            z_ln = _transform_like_base(df[col_abst].to_numpy(dtype=float), level_base)
            z_tn = _transform_like_base(
                (df[col_abst] - df["ABST_2015"]).fillna(0.0).to_numpy(dtype=float), trend_base
            )
            z_vn = _transform_like_base(np.log1p(nv_s.astype(float)), vol_base)
            sc = np.round(norm.cdf(w_l * z_ln + w_t * z_tn + w_v * z_vn) * 100.0, 2)
            sem = pd.Series(classify_semaforo(sc, thresholds))
        return {
            "escenario": nombre,
            "ln_proyectada_2027": tot_ln,
            "tasa_abstencion_nacional_pct": round(abst_nac, 2),
            "tasa_participacion_nacional_pct": round(part_nac, 2),
            "abstencionistas_esperados": int(nv_s.sum()),
            "votantes_esperados": sv_s,
            "votos_adicionales_recuperados": votos_rec,
            "municipios_riesgo_critico": int((sem == "Crítico").sum()),
            "municipios_riesgo_alto": int((sem == "Alto").sum()),
            "municipios_riesgo_moderado": int((sem == "Moderado").sum()),
            "municipios_riesgo_bajo": int((sem == "Bajo").sum()),
        }

    scenarios_summary.append(_row_summary("0. Línea Base (Sin Intervención 2027)", "ABST_PROY_2027_SIN_INT", "SEMAFORO_SIN_INT"))
    scenarios_summary.append(_row_summary("1. Intervención Focalizada Juventudes (18-29)", "ABST_2027_ESC1_JUVENTUD"))
    scenarios_summary.append(_row_summary("2. Brigadas Comunitarias Rurales y Mixtas", "ABST_2027_ESC2_RURAL"))
    scenarios_summary.append(
        _row_summary("3A. Portafolio Óptimo INE (Banda Conservadora)", "ABST_PROY_2027_CON_INT_CONSERVADOR")
    )
    scenarios_summary.append(
        _row_summary("3B. Portafolio Óptimo INE (Escenario Central Con Intervención)", "ABST_PROY_2027_CON_INT", "SEMAFORO_CON_INT")
    )
    scenarios_summary.append(
        _row_summary("3C. Portafolio Óptimo INE (Banda Optimista)", "ABST_PROY_2027_CON_INT_OPTIMISTA")
    )

    summary_df = pd.DataFrame(scenarios_summary)
    summary_df.to_csv(cfg.paths.tables_dir / "resumen_escenarios_2027.csv", index=False)

    # Resumen por Entidad Federativa (32 estados)
    state_summary = (
        df.groupby(["EDOCVE", "CVE_ENT", "ENTIDAD_NOM", "ABREV", "CIRCUNSCRIPCION"], as_index=False)
        .agg(
            municipios=("ID_MUN_INE", "count"),
            municipios_intervenidos=("INTERVENIDO_PORTAFOLIO_INE", "sum"),
            municipios_criticos_sin_int=("SEMAFORO_SIN_INT", lambda s: int((s == "Crítico").sum())),
            municipios_criticos_con_int=("SEMAFORO_CON_INT", lambda s: int((s == "Crítico").sum())),
            ln_2024=("LN", "sum"),
            nv_2024=("NV", "sum"),
            ln_proy_2027=("LN_PROY_2027", "sum"),
            nv_proy_2027_sin_int=("NV_PROY_2027_SIN_INT", "sum"),
            nv_proy_2027_con_int=("NV_PROY_2027_CON_INT", "sum"),
            votos_recuperados=("VOTOS_RECUPERADOS_CON_INT", "sum"),
            score_riesgo_medio_sin_int=("SCORE_RIESGO_SIN_INT", "mean"),
            score_riesgo_medio_con_int=("SCORE_RIESGO_CON_INT", "mean"),
        )
    )
    state_summary["abst_2024_pct"] = np.round(100.0 * state_summary["nv_2024"] / state_summary["ln_2024"], 2)
    state_summary["abst_2027_sin_int_pct"] = np.round(
        100.0 * state_summary["nv_proy_2027_sin_int"] / state_summary["ln_proy_2027"], 2
    )
    state_summary["abst_2027_con_int_pct"] = np.round(
        100.0 * state_summary["nv_proy_2027_con_int"] / state_summary["ln_proy_2027"], 2
    )
    state_summary["reduccion_abst_pp"] = np.round(
        state_summary["abst_2027_sin_int_pct"] - state_summary["abst_2027_con_int_pct"], 2
    )
    state_summary = state_summary.sort_values("abst_2027_sin_int_pct", ascending=False)
    state_summary.to_csv(cfg.paths.tables_dir / "semaforo_estatal_escenarios_2027.csv", index=False)

    return df, sec, summary_df

