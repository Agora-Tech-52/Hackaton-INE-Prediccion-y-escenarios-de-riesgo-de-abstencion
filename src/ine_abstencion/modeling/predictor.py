"""Entrenamiento, validacion historica (backtesting) y proyeccion 2027/2030 de abstencion."""

from __future__ import annotations

import numpy as np
import pandas as pd
import polars as pl
from rich.console import Console
from scipy import stats
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.inspection import permutation_importance
from sklearn.linear_model import ElasticNetCV, RidgeCV
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from ine_abstencion.config import AppConfig

console = Console()

MODEL_FEATURES: list[str] = [
    "ABST_LAG2_HOMOLOGO_6A",
    "ABST_LAG1_3A",
    "ES_INTERMEDIA",
    "PROP_JOVENES_18_29",
    "PROP_PRIMER_VOTO_18_19",
    "PROP_MAYORES_60_MAS",
    "BRECHA_JUVENIL_ABST",
    "BRECHA_GENERO_ABST",
    "PROP_URBANA",
    "PROP_RURAL_MIXTA",
    "CRECIMIENTO_LN_3A",
    "CIRC_1",
    "CIRC_2",
    "CIRC_3",
    "CIRC_4",
]

FEATURE_LABELS_ES: dict[str, str] = {
    "ABST_LAG2_HOMOLOGO_6A": "Abstención Elección Homóloga Previa (t-6)",
    "ABST_LAG1_3A": "Abstención Elección Inmediata Anterior (t-3)",
    "ES_INTERMEDIA": "Efecto Elección Intermedia (vs Presidencial)",
    "PROP_JOVENES_18_29": "Proporción de Jóvenes 18-29 años en LN",
    "PROP_PRIMER_VOTO_18_19": "Proporción Primer Voto 18-19 años en LN",
    "PROP_MAYORES_60_MAS": "Proporción Adultos Mayores 60+ en LN",
    "BRECHA_JUVENIL_ABST": "Brecha Local de Abstención Juvenil (18-29 vs 30-59)",
    "BRECHA_GENERO_ABST": "Brecha de Abstención por Sexo (Hombres - Mujeres)",
    "PROP_URBANA": "Grado de Urbanización (% LN Urbana)",
    "PROP_RURAL_MIXTA": "Proporción LN en Secciones Rurales y Mixtas",
    "CRECIMIENTO_LN_3A": "Tasa de Crecimiento del Padrón (3 años)",
    "CIRC_1": "1ª Circunscripción (Noroeste)",
    "CIRC_2": "2ª Circunscripción (Noreste / Bajío)",
    "CIRC_3": "3ª Circunscripción (Sur / Golfo-Sureste)",
    "CIRC_4": "4ª Circunscripción (Centro / Pacífico Sur)",
}


def _logit(p: np.ndarray) -> np.ndarray:
    p_clip = np.clip(p, 0.005, 0.995)
    return np.log(p_clip / (1.0 - p_clip))


def _expit(x: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-np.clip(x, -12.0, 12.0)))


def _prepare_design_df(df_mun: pl.DataFrame) -> pd.DataFrame:
    pdf = df_mun.to_pandas()
    for c in (1, 2, 3, 4):
        pdf[f"CIRC_{c}"] = (pdf["CIRCUNSCRIPCION"] == c).astype(float)
    # Imputacion jerarquica suave por anio y circunscripcion para lags en municipios nuevos
    for col in MODEL_FEATURES:
        if col in pdf.columns:
            pdf[col] = pdf.groupby(["AELEC", "CIRCUNSCRIPCION"])[col].transform(
                lambda s: s.fillna(s.median())
            )
            pdf[col] = pdf[col].fillna(pdf[col].median())
    return pdf


def _evaluate_predictions(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    ln_weights: np.ndarray,
    model_name: str,
    horizon_label: str,
) -> dict[str, object]:
    mae = mean_absolute_error(y_true, y_pred) * 100.0
    w_mae = float(np.average(np.abs(y_true - y_pred), weights=ln_weights) * 100.0)
    rmse = float(np.sqrt(mean_squared_error(y_true, y_pred)) * 100.0)
    r2 = float(r2_score(y_true, y_pred, sample_weight=ln_weights))
    rho, _ = stats.spearmanr(y_true, y_pred)

    # Precision@Top20%: coincidencia en el quintil superior de mayor abstencion
    q80_true = np.quantile(y_true, 0.80)
    q80_pred = np.quantile(y_pred, 0.80)
    top_true = y_true >= q80_true
    top_pred = y_pred >= q80_pred
    prec_top20 = float(np.sum(top_true & top_pred) / max(np.sum(top_pred), 1))

    return {
        "corte_validacion": horizon_label,
        "modelo": model_name,
        "MAE_pp": round(mae, 3),
        "MAE_ponderado_LN_pp": round(w_mae, 3),
        "RMSE_pp": round(rmse, 3),
        "R2_ponderado": round(r2, 4),
        "Spearman_rho": round(float(rho), 4),
        "Precision_Top20_pct": round(prec_top20 * 100.0, 2),
    }


def train_and_project(cfg: AppConfig, df_mun: pl.DataFrame, df_sec: pl.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Ejecuta backtesting (2021 y 2024), extrae coeficientes y proyecta 2027 y 2030."""
    console.print("[bold cyan]Entrenando modelos predictivos y ejecutando backtesting temporal...[/bold cyan]")
    pdf = _prepare_design_df(df_mun)

    # Usamos elecciones con lag homologo completo (2015, 2018, 2021, 2024)
    pdf_model = pdf[pdf["AELEC"].isin([2015, 2018, 2021, 2024])].copy()
    metrics_rows: list[dict[str, object]] = []

    backtest_splits = [
        ("Backtest Intermedia 2021 (Entrena <=2018)", [2015, 2018], 2021),
        ("Backtest Presidencial 2024 (Entrena <=2021)", [2015, 2018, 2021], 2024),
    ]

    for label, train_years, test_year in backtest_splits:
        tr = pdf_model[pdf_model["AELEC"].isin(train_years)]
        te = pdf_model[pdf_model["AELEC"] == test_year]

        X_tr = tr[MODEL_FEATURES].to_numpy(dtype=float)
        y_tr_logit = _logit(tr["TASA_ABSTENCION"].to_numpy(dtype=float))
        w_tr = np.sqrt(np.clip(tr["LN"].to_numpy(dtype=float), 1.0, None))

        X_te = te[MODEL_FEATURES].to_numpy(dtype=float)
        y_te = te["TASA_ABSTENCION"].to_numpy(dtype=float)
        w_te_ln = np.clip(te["LN"].to_numpy(dtype=float), 1.0, None)

        # 1. Baseline Homologo
        y_pred_base = np.clip(te["ABST_LAG2_HOMOLOGO_6A"].to_numpy(dtype=float), 0.01, 0.99)
        metrics_rows.append(_evaluate_predictions(y_te, y_pred_base, w_te_ln, "1. Baseline Homólogo (t-6)", label))

        # 2. Modelo Principal Interpretable: Ridge / ElasticNet en escala Logit ponderado por sqrt(LN)
        enet_pipe = Pipeline(
            [
                ("scaler", StandardScaler()),
                ("reg", RidgeCV(alphas=np.logspace(-2, 3, 40))),
            ]
        )
        enet_pipe.fit(X_tr, y_tr_logit, reg__sample_weight=w_tr)
        y_pred_enet = _expit(enet_pipe.predict(X_te))
        metrics_rows.append(
            _evaluate_predictions(y_te, y_pred_enet, w_te_ln, "2. Regresión Logit Regularizada (Principal)", label)
        )

        # 3. Modelo Benchmark No Lineal: HistGradientBoosting
        gbr = HistGradientBoostingRegressor(
            max_iter=150,
            learning_rate=0.05,
            max_depth=4,
            min_samples_leaf=30,
            l2_regularization=2.0,
            random_state=42,
        )
        gbr.fit(X_tr, y_tr_logit, sample_weight=w_tr)
        y_pred_gbr = _expit(gbr.predict(X_te))
        metrics_rows.append(
            _evaluate_predictions(y_te, y_pred_gbr, w_te_ln, "3. HistGradientBoosting Logit (Benchmark ML)", label)
        )

        # 4. Ensamble Hibrido (70% Logit Regularizado + 30% HistGBR)
        y_pred_ens = 0.70 * y_pred_enet + 0.30 * y_pred_gbr
        metrics_rows.append(
            _evaluate_predictions(y_te, y_pred_ens, w_te_ln, "4. Ensamble Híbrido INE (70% Lineal + 30% GBDT)", label)
        )

    metrics_df = pd.DataFrame(metrics_rows)
    metrics_df.to_csv(cfg.paths.tables_dir / "metricas_backtesting_modelos.csv", index=False)

    # Entrenamiento final con toda la historia 2015-2024
    X_all = pdf_model[MODEL_FEATURES].to_numpy(dtype=float)
    y_all_logit = _logit(pdf_model["TASA_ABSTENCION"].to_numpy(dtype=float))
    w_all = np.sqrt(np.clip(pdf_model["LN"].to_numpy(dtype=float), 1.0, None))

    final_linear = Pipeline(
        [
            ("scaler", StandardScaler()),
            ("reg", ElasticNetCV(l1_ratio=[0.1, 0.5, 0.9], alphas=np.logspace(-4, 1, 40), cv=5, random_state=42)),
        ]
    )
    final_linear.fit(X_all, y_all_logit, reg__sample_weight=w_all)

    final_gbr = HistGradientBoostingRegressor(
        max_iter=180,
        learning_rate=0.05,
        max_depth=4,
        min_samples_leaf=30,
        l2_regularization=2.0,
        random_state=42,
    )
    final_gbr.fit(X_all, y_all_logit, sample_weight=w_all)

    # Residuales para intervalos de prediccion al 90%
    pred_all_logit = 0.70 * final_linear.predict(X_all) + 0.30 * final_gbr.predict(X_all)
    resid_std = float(np.sqrt(np.average((y_all_logit - pred_all_logit) ** 2, weights=w_all)))

    # Exportar tabla de coeficientes e importancia de variables
    scaler: StandardScaler = final_linear.named_steps["scaler"]
    reg: ElasticNetCV = final_linear.named_steps["reg"]
    perm_imp = permutation_importance(
        final_gbr, X_all, y_all_logit, sample_weight=w_all, n_repeats=5, random_state=42
    )
    p_bar = float(np.average(pdf_model["TASA_ABSTENCION"], weights=pdf_model["LN"]))
    marginal_scale = p_bar * (1.0 - p_bar) * 100.0  # Efecto marginal en puntos porcentuales cerca de la media

    coef_rows: list[dict[str, object]] = []
    for i, feat in enumerate(MODEL_FEATURES):
        beta_std = float(reg.coef_[i])
        beta_raw = float(reg.coef_[i] / scaler.scale_[i])
        coef_rows.append(
            {
                "variable": feat,
                "descripcion": FEATURE_LABELS_ES.get(feat, feat),
                "coef_logit_estandarizado": round(beta_std, 4),
                "efecto_marginal_1sd_pp": round(beta_std * marginal_scale, 3),
                "coef_logit_original": round(beta_raw, 4),
                "importancia_permutacion_gbdt": round(float(perm_imp.importances_mean[i]), 4),
            }
        )
    coef_df = pd.DataFrame(coef_rows).sort_values(
        by="coef_logit_estandarizado", key=lambda s: s.abs(), ascending=False
    )
    coef_df.to_csv(cfg.paths.tables_dir / "importancia_y_coeficientes_modelo.csv", index=False)

    # Construir base de proyeccion 2027 (Intermedia) y 2030 (Presidencial) para todos los municipios vigentes en 2024
    df_2024 = pdf[pdf["AELEC"] == 2024].copy().sort_values("ID_MUN_INE")
    df_2021 = pdf[pdf["AELEC"] == 2021][["ID_MUN_INE", "TASA_ABSTENCION"]].rename(
        columns={"TASA_ABSTENCION": "ABST_2021"}
    )
    df_2018 = pdf[pdf["AELEC"] == 2018][["ID_MUN_INE", "TASA_ABSTENCION"]].rename(
        columns={"TASA_ABSTENCION": "ABST_2018"}
    )
    df_2015 = pdf[pdf["AELEC"] == 2015][["ID_MUN_INE", "TASA_ABSTENCION"]].rename(
        columns={"TASA_ABSTENCION": "ABST_2015"}
    )

    proj = (
        df_2024.merge(df_2021, on="ID_MUN_INE", how="left")
        .merge(df_2018, on="ID_MUN_INE", how="left")
        .merge(df_2015, on="ID_MUN_INE", how="left")
    )
    proj["ABST_2021"] = proj["ABST_2021"].fillna(proj["TASA_ABSTENCION"] + 0.08)
    proj["ABST_2018"] = proj["ABST_2018"].fillna(proj["TASA_ABSTENCION"])
    proj["ABST_2015"] = proj["ABST_2015"].fillna(proj["ABST_2021"])

    # Vector de predictores para 2027 (Eleccion Intermedia: t-6 = 2021, t-3 = 2024, ES_INTERMEDIA = 1)
    X_2027_df = proj[MODEL_FEATURES].copy()
    X_2027_df["ABST_LAG2_HOMOLOGO_6A"] = proj["ABST_2021"]
    X_2027_df["ABST_LAG1_3A"] = proj["TASA_ABSTENCION"]
    X_2027_df["ES_INTERMEDIA"] = 1.0
    X_2027 = X_2027_df.to_numpy(dtype=float)

    logit_2027_lin = final_linear.predict(X_2027)
    logit_2027_gbr = final_gbr.predict(X_2027)
    logit_2027_ens = 0.70 * logit_2027_lin + 0.30 * logit_2027_gbr

    proj["ABST_2024_OBS"] = proj["TASA_ABSTENCION"]
    proj["ABST_PROY_2027_LINEAL"] = _expit(logit_2027_lin)
    proj["ABST_PROY_2027_GBDT"] = _expit(logit_2027_gbr)
    proj["ABST_PROY_2027_SIN_INT"] = _expit(logit_2027_ens)
    proj["ABST_PROY_2027_IC90_INF"] = _expit(logit_2027_ens - 1.645 * resid_std)
    proj["ABST_PROY_2027_IC90_SUP"] = _expit(logit_2027_ens + 1.645 * resid_std)

    # Proyeccion demografica de Lista Nominal a 2027 (crecimiento acotado entre -5% y +12% trienal)
    growth_3a = np.clip(proj["CRECIMIENTO_LN_3A"].fillna(0.03).to_numpy(dtype=float), -0.05, 0.12)
    proj["LN_PROY_2027"] = np.round(proj["LN"].to_numpy(dtype=float) * (1.0 + growth_3a)).astype(int)
    proj["NV_PROY_2027_SIN_INT"] = np.round(proj["LN_PROY_2027"] * proj["ABST_PROY_2027_SIN_INT"]).astype(int)
    proj["SV_PROY_2027_SIN_INT"] = proj["LN_PROY_2027"] - proj["NV_PROY_2027_SIN_INT"]

    # Vector de predictores para 2030 (Eleccion Presidencial: t-6 = 2024, t-3 = 2027 proyectado, ES_INTERMEDIA = 0)
    X_2030_df = proj[MODEL_FEATURES].copy()
    X_2030_df["ABST_LAG2_HOMOLOGO_6A"] = proj["ABST_2024_OBS"]
    X_2030_df["ABST_LAG1_3A"] = proj["ABST_PROY_2027_SIN_INT"]
    X_2030_df["ES_INTERMEDIA"] = 0.0
    X_2030 = X_2030_df.to_numpy(dtype=float)
    logit_2030_ens = 0.70 * final_linear.predict(X_2030) + 0.30 * final_gbr.predict(X_2030)
    proj["ABST_PROY_2030_PRESIDENCIAL"] = _expit(logit_2030_ens)

    # Proyeccion jerarquica a nivel Seccion Electoral (para las ~70,000 secciones de 2024)
    sec_2024 = df_sec.filter(pl.col("AELEC") == 2024).to_pandas()
    mun_shift = proj[["ID_MUN_INE", "ABST_2024_OBS", "ABST_PROY_2027_SIN_INT"]].copy()
    mun_shift["DELTA_LOGIT_MUN_2024_2027"] = _logit(mun_shift["ABST_PROY_2027_SIN_INT"].to_numpy()) - _logit(
        mun_shift["ABST_2024_OBS"].to_numpy()
    )
    sec_proj = sec_2024.merge(
        mun_shift[["ID_MUN_INE", "DELTA_LOGIT_MUN_2024_2027", "ABST_PROY_2027_SIN_INT"]],
        on="ID_MUN_INE",
        how="left",
        suffixes=("", "_MUN"),
    )
    # Suavizado Empirical Bayes para secciones pequenas (peso segun LN de la seccion)
    ln_s = sec_proj["LN"].to_numpy(dtype=float)
    eb_weight = ln_s / (ln_s + 250.0)
    sec_logit_2024 = _logit(sec_proj["TASA_ABSTENCION"].to_numpy(dtype=float))
    sec_lag_hom = _logit(sec_proj["ABST_LAG2_HOMOLOGO_6A"].fillna(sec_proj["TASA_ABSTENCION"] + 0.08).to_numpy())
    sec_logit_2027_raw = 0.55 * (sec_logit_2024 + sec_proj["DELTA_LOGIT_MUN_2024_2027"].to_numpy()) + 0.45 * sec_lag_hom
    mun_logit_2027 = _logit(sec_proj["ABST_PROY_2027_SIN_INT"].to_numpy(dtype=float))
    sec_proj["ABST_PROY_2027_SIN_INT"] = _expit(eb_weight * sec_logit_2027_raw + (1.0 - eb_weight) * mun_logit_2027)
    sec_proj["NV_PROY_2027_SIN_INT"] = np.round(sec_proj["LN"] * sec_proj["ABST_PROY_2027_SIN_INT"]).astype(int)

    console.print("  [green]✓[/green] Modelos entrenados y proyecciones 2027/2030 generadas.")
    return proj, sec_proj

