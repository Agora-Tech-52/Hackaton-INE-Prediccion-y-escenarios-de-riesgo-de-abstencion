"""Generacion de las 8 figuras editoriales en 300 DPI para el Reporte Metodologico y Presentacion."""

from __future__ import annotations

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import polars as pl
import seaborn as sns

from ine_abstencion.config import AppConfig

INE_MAGENTA = "#9D2449"
INE_PURPLE = "#5B1F56"
INE_NAVY = "#1D3557"
SEMAFORO_PALETTE = {
    "Bajo": "#2A9D8F",
    "Moderado": "#E9C46A",
    "Alto": "#F4A261",
    "Crítico": "#E63946",
}


def _setup_style() -> None:
    sns.set_theme(style="whitegrid")
    plt.rcParams["font.sans-serif"] = ["DejaVu Sans", "Arial", "Helvetica"]
    plt.rcParams["axes.unicode_minus"] = False
    plt.rcParams["figure.dpi"] = 300


def generate_all_figures(
    cfg: AppConfig,
    audit_df: pl.DataFrame,
    df_mun: pl.DataFrame,
    corr_summary: pd.DataFrame,
    corr_matrix: pd.DataFrame,
    metrics_df: pd.DataFrame,
    coef_df: pd.DataFrame,
    df_sim_mun: pd.DataFrame,
    scenarios_summary: pd.DataFrame,
) -> list[str]:
    """Genera las 8 figuras clave en alta resolucion (300 DPI)."""
    _setup_style()
    saved: list[str] = []
    fig_dir = cfg.paths.figures_dir

    # --- FIGURA 1: Serie historica 2009-2024 y Proyeccion 2027/2030 (Efecto Ciclo Electoral) ---
    fig, ax = plt.subplots(figsize=(10.5, 5.2))
    aud = audit_df.to_pandas().sort_values("AELEC")
    years_hist = aud["AELEC"].to_numpy()
    abst_hist = aud["tasa_abstencion_pct"].to_numpy()
    part_hist = aud["tasa_participacion_pct"].to_numpy()

    abst_2027_base = float(
        scenarios_summary.loc[
            scenarios_summary["escenario"].str.startswith("0."), "tasa_abstencion_nacional_pct"
        ].iloc[0]
    )
    abst_2027_int = float(
        scenarios_summary.loc[
            scenarios_summary["escenario"].str.startswith("3B."), "tasa_abstencion_nacional_pct"
        ].iloc[0]
    )

    ax.plot(years_hist, abst_hist, marker="o", linewidth=2.8, markersize=8, color=INE_MAGENTA, label="Abstención Observada CCPC (2009–2024)")
    ax.plot(years_hist, part_hist, marker="s", linewidth=2.2, markersize=7, color=INE_NAVY, linestyle="--", alpha=0.8, label="Participación Observada CCPC (2009–2024)")

    # Conectar 2024 -> 2027 Sin vs Con intervencion
    ax.plot([2024, 2027], [abst_hist[-1], abst_2027_base], marker="D", markersize=9, linewidth=2.6, linestyle=":", color="#E63946", label=f"Proyección 2027 Sin Intervención ({abst_2027_base:.1f}%)")
    ax.plot([2024, 2027], [abst_hist[-1], abst_2027_int], marker="^", markersize=9, linewidth=2.6, linestyle="-.", color="#2A9D8F", label=f"Proyección 2027 Con Intervención INE ({abst_2027_int:.1f}%)")

    for x, y, tipo in zip(years_hist, abst_hist, aud["TIPO_ELECCION"]):
        tag = "Int." if tipo == "Intermedia" else "Pres."
        ax.annotate(f"{y:.1f}%\n({tag})", (x, y), textcoords="offset points", xytext=(0, 9), ha="center", fontsize=8.5, fontweight="bold")

    ax.set_title("Dinámica Histórica de Abstención (2009–2024) y Escenarios 2027 por Ciclo Electoral", fontsize=13, fontweight="bold", pad=12)
    ax.set_xlabel("Año de Proceso Electoral Federal", fontsize=11)
    ax.set_ylabel("Porcentaje de la Lista Nominal (%)", fontsize=11)
    ax.set_xticks([2009, 2012, 2015, 2018, 2021, 2024, 2027])
    ax.set_ylim(25, 68)
    ax.legend(loc="lower left", frameon=True, fontsize=9)
    plt.tight_layout()
    p1 = fig_dir / "fig1_evolucion_ciclo_electoral_2009_2024.png"
    plt.savefig(p1, dpi=300)
    plt.close()
    saved.append(str(p1))

    # --- FIGURA 2: Curva de Abstencion por Edad y Sexo (2009-2024) ---
    df_age = pl.read_parquet(cfg.paths.gold_dir / "curvas_edad_sexo_tiposec_2009_2024.parquet")
    age_24 = (
        df_age.filter((pl.col("AELEC").is_in([2021, 2024])) & (pl.col("SEXO").is_in([0, 1])) & (pl.col("EDAD_CLIP") <= 85))
        .group_by(["AELEC", "SEXO", "EDAD_CLIP"])
        .agg(pl.col("LN").sum().alias("LN"), pl.col("NV").sum().alias("NV"))
        .with_columns((100.0 * pl.col("NV") / pl.col("LN")).alias("ABST_PCT"))
        .sort(["AELEC", "SEXO", "EDAD_CLIP"])
        .to_pandas()
    )
    fig, ax = plt.subplots(figsize=(10.5, 5.2))
    palette_lines = {
        (2021, 0): ("#F4A261", "--", "Mujeres - Intermedia 2021"),
        (2021, 1): ("#E63946", "-", "Hombres - Intermedia 2021"),
        (2024, 0): ("#2A9D8F", "--", "Mujeres - Presidencial 2024"),
        (2024, 1): ("#1D3557", "-", "Hombres - Presidencial 2024"),
    }
    for (yr, sx), (col, ls, lbl) in palette_lines.items():
        sub = age_24[(age_24["AELEC"] == yr) & (age_24["SEXO"] == sx)]
        ax.plot(sub["EDAD_CLIP"], sub["ABST_PCT"], color=col, linestyle=ls, linewidth=2.3, label=lbl)

    ax.axvspan(19, 29, color="#E63946", alpha=0.12, label="Zona Crítica de Abstención Juvenil (19–29 años)")
    ax.set_title("Curva de Abstención por Edad y Sexo: Brecha Juvenil y Diferencial de Ciclo (2021 vs 2024)", fontsize=12.5, fontweight="bold")
    ax.set_xlabel("Edad Cumplida (años)", fontsize=11)
    ax.set_ylabel("Tasa de Abstención (%)", fontsize=11)
    ax.set_xlim(18, 85)
    ax.legend(loc="upper right", frameon=True, fontsize=9)
    plt.tight_layout()
    p2 = fig_dir / "fig2_curva_edad_sexo_abstencion.png"
    plt.savefig(p2, dpi=300)
    plt.close()
    saved.append(str(p2))

    # --- FIGURA 3: Matriz de Correlacion de Variables Clave ---
    short_labels = {
        "TASA_ABSTENCION": "Abstención (t)",
        "ABST_LAG2_HOMOLOGO_6A": "Abstención (t-6)",
        "ABST_LAG1_3A": "Abstención (t-3)",
        "ES_INTERMEDIA": "Elección Intermedia",
        "PROP_JOVENES_18_29": "% Jóvenes 18-29",
        "PROP_MAYORES_60_MAS": "% Mayores 60+",
        "BRECHA_JUVENIL_ABST": "Brecha Juvenil",
        "BRECHA_GENERO_ABST": "Brecha Hombres-Mujeres",
        "PROP_URBANA": "% LN Urbana",
        "CRECIMIENTO_LN_3A": "Crecimiento LN",
    }
    cm = corr_matrix.rename(index=short_labels, columns=short_labels)
    fig, ax = plt.subplots(figsize=(9.5, 7.5))
    sns.heatmap(cm, annot=True, fmt=".2f", cmap="RdBu_r", vmin=-0.85, vmax=0.85, center=0, square=True, cbar_kws={"shrink": 0.8}, ax=ax)
    ax.set_title("Matriz de Correlación de Pearson entre Abstención y Predictores Territoriales", fontsize=12.5, fontweight="bold", pad=12)
    plt.xticks(rotation=35, ha="right", fontsize=9.5)
    plt.yticks(rotation=0, fontsize=9.5)
    plt.tight_layout()
    p3 = fig_dir / "fig3_matriz_correlacion_variables.png"
    plt.savefig(p3, dpi=300)
    plt.close()
    saved.append(str(p3))

    # --- FIGURA 4: Coeficientes Estandarizados del Modelo Interpretable y Backtesting ---
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13.5, 5.5), gridspec_kw={"width_ratios": [1.15, 1.0]})
    c_top = coef_df.head(10).sort_values("efecto_marginal_1sd_pp", ascending=True)
    colors_c = ["#E63946" if v > 0 else "#2A9D8F" for v in c_top["efecto_marginal_1sd_pp"]]
    ax1.barh(c_top["descripcion"], c_top["efecto_marginal_1sd_pp"], color=colors_c, edgecolor="black", linewidth=0.5)
    ax1.axvline(0, color="black", linewidth=1)
    ax1.set_title("A) Efecto Marginal (+1 DE) sobre Abstención", fontsize=11, fontweight="bold")
    ax1.set_xlabel("Cambio en Tasa de Abstención (pp)", fontsize=10)
    ax1.tick_params(axis="y", labelsize=8.5)

    # Subplot B: Comparativa WMAE y R2 en Backtesting
    m_2021 = metrics_df[metrics_df["corte_validacion"].str.startswith("Backtest Intermedia 2021")].copy()
    x_pos = np.arange(len(m_2021))
    bars = ax2.bar(x_pos, m_2021["MAE_ponderado_LN_pp"], color=["#8D99AE", INE_NAVY, INE_PURPLE, INE_MAGENTA], width=0.55)
    ax2.set_xticks(x_pos)
    ax2.set_xticklabels(["Baseline\nHomólogo", "Logit\nRegularizado", "HistGBR\n(ML)", "Ensamble\nHíbrido INE"], fontsize=9)
    ax2.set_ylabel("Error Absoluto Medio Ponderado por LN (pp)", fontsize=10)
    ax2.set_title("B) Backtesting Intermedia 2021 (Menor = Mejor)", fontsize=11, fontweight="bold")
    for b, r2v in zip(bars, m_2021["R2_ponderado"]):
        h = b.get_height()
        ax2.annotate(f"{h:.2f} pp\n(R²={r2v:.2f})", (b.get_x() + b.get_width() / 2, h), ha="center", va="bottom", fontsize=8.5, fontweight="bold", xytext=(0, 3), textcoords="offset points")
    ax2.set_ylim(0, max(m_2021["MAE_ponderado_LN_pp"]) * 1.25)
    plt.tight_layout()
    p4 = fig_dir / "fig4_backtesting_y_coeficientes_modelo.png"
    plt.savefig(p4, dpi=300)
    plt.close()
    saved.append(str(p4))

    # --- FIGURA 5: Semaforo Estatal Comparativo 2027 (Sin vs Con Intervencion) ---
    st_df = pd.read_csv(cfg.paths.tables_dir / "semaforo_estatal_escenarios_2027.csv").sort_values(
        "abst_2027_sin_int_pct", ascending=True
    )
    fig, ax = plt.subplots(figsize=(11, 8.5))
    y_idx = np.arange(len(st_df))
    ax.hlines(y=y_idx, xmin=st_df["abst_2027_con_int_pct"], xmax=st_df["abst_2027_sin_int_pct"], color="#6C757D", alpha=0.7, linewidth=2)
    ax.scatter(st_df["abst_2027_sin_int_pct"], y_idx, color="#E63946", s=65, label="Sin Intervención (Inercial 2027)", zorder=3)
    ax.scatter(st_df["abst_2027_con_int_pct"], y_idx, color="#2A9D8F", s=65, marker="D", label="Con Intervención (Portafolio Óptimo INE)", zorder=3)
    ax.set_yticks(y_idx)
    ax.set_yticklabels(st_df["ENTIDAD_NOM"], fontsize=9)
    ax.set_xlabel("Tasa de Abstención Proyectada 2027 (%)", fontsize=11)
    ax.set_title("Reducción de Abstención por Entidad Federativa (2027): Sin vs. Con Intervención", fontsize=12.5, fontweight="bold")
    ax.legend(loc="lower right", frameon=True, fontsize=9.5)
    plt.tight_layout()
    p5 = fig_dir / "fig5_semaforo_estatal_comparativo_2027.png"
    plt.savefig(p5, dpi=300)
    plt.close()
    saved.append(str(p5))

    # --- FIGURA 6: Transicion del Semaforo Municipal y Votos Recuperados por Escenario ---
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12.5, 5.2))
    cats = ["Bajo", "Moderado", "Alto", "Crítico"]
    sin_counts = [int((df_sim_mun["SEMAFORO_SIN_INT"] == c).sum()) for c in cats]
    con_counts = [int((df_sim_mun["SEMAFORO_CON_INT"] == c).sum()) for c in cats]
    x_c = np.arange(len(cats))
    w_b = 0.36
    b1 = ax1.bar(x_c - w_b / 2, sin_counts, width=w_b, color="#E63946", alpha=0.85, label="Sin Intervención")
    b2 = ax1.bar(x_c + w_b / 2, con_counts, width=w_b, color="#2A9D8F", alpha=0.90, label="Con Intervención (Portafolio INE)")
    ax1.set_xticks(x_c)
    ax1.set_xticklabels(["Bajo\n(Verde)", "Moderado\n(Amarillo)", "Alto\n(Naranja)", "Crítico\n(Rojo)"], fontsize=9.5, fontweight="bold")
    ax1.set_ylabel("Número de Municipios INE", fontsize=10.5)
    ax1.set_title("A) Desplazamiento del Semáforo Territorial (Municipios)", fontsize=11.5, fontweight="bold")
    ax1.legend(frameon=True)
    for b in list(b1) + list(b2):
        ax1.annotate(f"{int(b.get_height())}", (b.get_x() + b.get_width() / 2, b.get_height()), ha="center", va="bottom", fontsize=8.5, fontweight="bold")

    # Subplot B: Votos adicionales recuperados por escenario (en millones)
    sc_plot = scenarios_summary.iloc[1:].copy()
    votos_m = sc_plot["votos_adicionales_recuperados"] / 1e6
    short_sc = [
        "Esc. 1: Juventudes\n(18-29 años)",
        "Esc. 2: Brigadas\nRural/Mixto",
        "Esc. 3A: Portafolio\n(Conservador)",
        "Esc. 3B: Portafolio\n(Central INE)",
        "Esc. 3C: Portafolio\n(Optimista)",
    ]
    bars_v = ax2.barh(short_sc, votos_m, color=["#457B9D", "#F4A261", "#A8DADC", INE_MAGENTA, "#2A9D8F"], edgecolor="black", linewidth=0.5)
    ax2.set_xlabel("Votos Adicionales Recuperados (Millones de Ciudadanos)", fontsize=10)
    ax2.set_title("B) Retorno Cívico Estimado por Escenario en 2027", fontsize=11.5, fontweight="bold")
    for b in bars_v:
        w_val = b.get_width()
        ax2.annotate(f" +{w_val:.2f} M", (w_val, b.get_y() + b.get_height() / 2), va="center", ha="left", fontsize=9, fontweight="bold")
    ax2.set_xlim(0, max(votos_m) * 1.25)
    plt.tight_layout()
    p6 = fig_dir / "fig6_impacto_escenarios_y_semaforo.png"
    plt.savefig(p6, dpi=300)
    plt.close()
    saved.append(str(p6))

    # --- FIGURA 7: Distribucion de Municipios por Arquetipo de Riesgo Territorial ---
    fig, ax = plt.subplots(figsize=(10, 5.0))
    arq_counts = (
        df_sim_mun.groupby("ARQUETIPO_RIESGO", as_index=False)
        .agg(municipios=("ID_MUN_INE", "count"), ln_total=("LN_PROY_2027", "sum"), abst_media=("ABST_PROY_2027_SIN_INT", "mean"))
        .sort_values("municipios", ascending=True)
    )
    bars_a = ax.barh(arq_counts["ARQUETIPO_RIESGO"], arq_counts["municipios"], color=INE_PURPLE, alpha=0.88)
    ax.set_xlabel("Número de Municipios", fontsize=10.5)
    ax.set_title("Tipología Diagnóstica de Municipios según Causa Principal de Riesgo (2027)", fontsize=12, fontweight="bold")
    for b, abst_m in zip(bars_a, arq_counts["abst_media"]):
        w_val = b.get_width()
        ax.annotate(f" {int(w_val)} mun. (Abst. media: {abst_m*100:.1f}%)", (w_val, b.get_y() + b.get_height() / 2), va="center", ha="left", fontsize=9, fontweight="bold")
    ax.set_xlim(0, max(arq_counts["municipios"]) * 1.48)
    plt.tight_layout()
    p7 = fig_dir / "fig7_arquetipos_territoriales_riesgo.png"
    plt.savefig(p7, dpi=300)
    plt.close()
    saved.append(str(p7))

    # --- FIGURA 8: Curva de Pareto de Priorizacion Estrategica de Recursos del INE ---
    df_sorted_ret = df_sim_mun.sort_values("VOTOS_RECUPERADOS_CON_INT", ascending=False).copy()
    cum_mun_pct = np.arange(1, len(df_sorted_ret) + 1) / len(df_sorted_ret) * 100.0
    total_rec = max(df_sorted_ret["VOTOS_RECUPERADOS_CON_INT"].sum(), 1)
    cum_votos_pct = df_sorted_ret["VOTOS_RECUPERADOS_CON_INT"].cumsum().to_numpy() / total_rec * 100.0

    fig, ax = plt.subplots(figsize=(9.5, 5.0))
    ax.plot(cum_mun_pct, cum_votos_pct, color=INE_MAGENTA, linewidth=3.0, label="Curva de Concentración de Impacto Cívico (Modelo INE)")
    ax.plot([0, 100], [0, 100], color="gray", linestyle="--", label="Asignación Uniforme No Focalizada")
    idx_15 = int(0.15 * len(df_sorted_ret))
    y_15 = cum_votos_pct[idx_15]
    ax.scatter([15.0], [y_15], color="#2A9D8F", s=100, zorder=5)
    ax.annotate(
        f"Top 15% de Municipios captura\nel {y_15:.1f}% del retorno cívico potencial",
        xy=(15.0, y_15),
        xytext=(28.0, max(y_15 - 18.0, 45.0)),
        arrowprops={"arrowstyle": "->", "color": "#1D3557", "lw": 1.8},
        fontsize=10,
        fontweight="bold",
        bbox={"boxstyle": "round,pad=0.4", "facecolor": "#F1FAEE", "edgecolor": "#2A9D8F"},
    )
    ax.set_title("Eficiencia Presupuestal INE: Curva de Pareto de Votos Recuperables por Focalización", fontsize=12, fontweight="bold")
    ax.set_xlabel("% Acumulado de Municipios Intervenidos (Ordenados por Prioridad Estratégica)", fontsize=10.5)
    ax.set_ylabel("% Acumulado de Votos Potenciales Recuperados", fontsize=10.5)
    ax.legend(loc="lower right", frameon=True)
    plt.tight_layout()
    p8 = fig_dir / "fig8_curva_concentracion_pareto_ine.png"
    plt.savefig(p8, dpi=300)
    plt.close()
    saved.append(str(p8))

    return saved

