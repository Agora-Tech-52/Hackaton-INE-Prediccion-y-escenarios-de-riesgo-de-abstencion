# Reporte Metodológico y Preventivo (Reto 2): Predicción Territorial, Semáforo de Riesgo y Simulación Contrafactual de Abstención Electoral en México (2009–2027)

- **Concurso:** Hackea la participación: Datos que construyen democracia (INE – DECEyEC / ENCCÍVICA 2024–2026)
- **Eje Temático:** Reto 2 — Predicción y escenarios de riesgo de abstención (Analítica predictiva sin datos personales)
- **Fuente Oficial:** Plataforma de los Conteos Censales de Participación Ciudadana (CCPC) 2009–2024
- **Horizonte de Planeación:** Proceso Electoral Federal Intermedio 2027 y Presidencial 2030

---

## 1. Resumen Ejecutivo y Planteamiento Estratégico para el INE

La abstención electoral no se distribuye de manera uniforme ni aleatoria en el territorio nacional: responde a patrones estructurales sociodemográficos, brechas generacionales persistentes y una marcada fatiga cíclica durante las elecciones federales intermedias. Con el propósito de dotar a la Dirección Ejecutiva de Capacitación Electoral y Educación Cívica (DECEyEC), a las 32 Juntas Locales Ejecutivas y a las 300 Juntas Distritales de un instrumento operativo de alerta temprana y asignación presupuestal, este estudio procesa la totalidad de los **192 archivos censales territoriales** de la Plataforma CCPC entre 2009 y 2024 (**54,872,712 registros agregados** por edad, sexo y sección electoral, equivalentes a **518.5 millones de observaciones acumuladas en Lista Nominal**).

**Hallazgo Central:** Si no se interviene de manera focalizada antes del Proceso Electoral Federal Intermedio de 2027, el modelo proyecta una **tasa de abstención nacional inercial de 44.49%** (**45,885,912 ciudadanos** sin acudir a las urnas sobre una Lista Nominal proyectada de 103,141,753 electores), con **298 municipios en Riesgo Crítico (Rojo)** y **445 en Riesgo Alto (Naranja)**. En contraste, nuestro **Escenario de Portafolio Estratégico Óptimo del INE (Escenario 3B)** demuestra que focalizando brigadas comunitarias y campañas de primer voto en el Top 15% de territorios prioritarios y zonas críticas, es posible **reducir la abstención nacional a 41.68%**, recuperando **+2,900,891 votos ciudadanos** y logrando que **208 municipios salgan del nivel de Riesgo Crítico (de 298 a 90)**.

| Elección | Tipo de Ciclo | Municipios INE | Secciones | Lista Nominal | Participación (%) | Abstención (%) |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| 2009 | Intermedia | 2,458 | 64,934 | 77,481,831 | 43.00% | 54.59% |
| 2012 | Presidencial | 2,455 | 65,599 | 76,490,962 | 61.95% | 37.83% |
| 2015 | Intermedia | 2,458 | 68,362 | 83,563,462 | 44.19% | 49.68% |
| 2018 | Presidencial | 2,463 | 68,408 | 89,123,997 | 58.10% | 35.06% |
| 2021 | Intermedia | 2,468 | 68,812 | 93,532,133 | 49.60% | 46.08% |
| 2024 | Presidencial | 2,477 | 70,751 | 98,330,348 | 55.83% | 37.74% |

---

## 2. Arquitectura de Ingeniería de Datos, Saneamiento y Protección de Datos

El procesamiento de los 194 archivos CSV (3.56 GB) se implementó en Python 3.12 bajo una arquitectura modular reproducible gestionada con `uv` y motor vectorial en `Polars`/`PyArrow` sobre formato columnar **Apache Parquet**. Durante la auditoría técnica se identificaron y corrigieron seis retos estructurales:

1. **Aislamiento de archivos modales 2024:** Se separaron los 192 archivos territoriales seccionales de los 2 archivos especiales incorporados en 2024 (*Prisión Preventiva* con 26,563 registros y *Voto Anticipado* con 3,449 registros), evitando sesgos de concatenación.
2. **Llaves compuestas canónicas:** Se construyeron llaves numéricas invariantes (`ID_MUN_INE = EDOCVE*1000 + MPIOCVE` e `ID_SEC_INE = EDOCVE*100000 + SECCION`) vinculadas al catálogo oficial 2024.
3. **Inclusión de categoría no binaria (`SEXO=2` en 2024):** Se preservaron los 105 grupos censales con `SEXO=2` en los totales de Lista Nominal.
4. **Verificación contable exacta:** Se auditó la identidad $LN = SV + NV + NS$ en los 54.87 millones de registros con **cero descuadres contables**.
5. **Control explícito del Ciclo Electoral:** Las elecciones intermedias presentan entre 10 y 15 puntos porcentuales más abstención que las presidenciales.
6. **Privacidad por diseño y disociación total:** Todo el modelado y las bases entregadas operan exclusivamente sobre agregados territoriales sin ningún dato personal y aplicando umbral mínimo de tamaño de celda ($LN \ge 15$).

---

## 3. Diagnóstico Sociodemográfico y Análisis de Correlación Territorial

| Variable Predictora | Pearson ($r$) | Spearman ($\rho$) | Corr. Pond. LN | Factor VIF |
| :--- | :---: | :---: | :---: | :---: |
| Abstención Elección Homóloga Previa ($t-6$) | +0.6085 | +0.6096 | +0.7085 | 2.04 |
| Ciclo Electoral Intermedio (1=Sí, 0=Presidencial) | +0.2729 | +0.2675 | +0.5084 | 1.86 |
| Proporción Lista Nominal Urbana (%) | +0.1157 | +0.1119 | +0.2652 | 1.25 |
| Proporción Adultos Mayores 60+ (% LN) | +0.0387 | +0.0224 | -0.2345 | 5.09 |
| Brecha de Abstención Juvenil vs Adultos | +0.3365 | +0.3722 | +0.2343 | 1.15 |
| Brecha de Abstención por Sexo (Hombres - Mujeres) | +0.0175 | +0.0182 | +0.2181 | 1.17 |
| Abstención Elección Inmediata Anterior ($t-3$) | +0.4623 | +0.4831 | +0.1148 | 1.69 |
| Crecimiento Demográfico del Padrón (3 años) | +0.0141 | -0.0342 | +0.1054 | 1.10 |
| Proporción Jóvenes 18–29 años (% LN) | -0.0167 | -0.0198 | +0.0886 | 4.16 |

---

## 4. Validación Temporal (Backtesting) y Coeficientes del Modelo

| Corte de Validación Temporal | Modelo Evaluado | MAE (pp) | WMAE LN (pp) | RMSE (pp) | $R^2$ Pond. | Prec.@Top20% |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| Backtest Intermedia 2021 | 1. Baseline Homólogo ($t-6$) | 13.39 | 9.13 | 17.69 | -0.355 | 39.3% |
| Backtest Intermedia 2021 | 2. Regresión Logit Regularizada | 10.33 | 7.22 | 13.10 | 0.179 | 39.7% |
| Backtest Intermedia 2021 | 3. HistGradientBoosting Logit | 8.61 | 6.68 | 11.19 | 0.299 | 48.4% |
| Backtest Intermedia 2021 | 4. Ensamble Híbrido INE | 9.62 | 6.90 | 12.21 | 0.253 | 43.3% |
| Backtest Presidencial 2024 | 1. Baseline Homólogo ($t-6$) | 6.62 | 4.38 | 9.08 | 0.360 | 64.3% |
| Backtest Presidencial 2024 | 2. Regresión Logit Regularizada | 6.98 | 4.11 | 9.23 | 0.444 | 64.9% |
| Backtest Presidencial 2024 | 3. HistGradientBoosting Logit | 6.67 | 4.85 | 8.81 | 0.370 | 61.9% |
| Backtest Presidencial 2024 | 4. Ensamble Híbrido INE | 6.63 | 4.23 | 8.75 | 0.458 | 66.5% |

---

## 5. Simulación Contrafactual de Escenarios 2027

| Escenario Simulado (Horizonte 2027) | Abstención Nac. | Participación Nac. | Votos Recuperados | Mun. Críticos | Mun. Altos |
| :--- | :---: | :---: | :---: | :---: | :---: |
| 0. Línea Base (Sin Intervención 2027) | 44.49% | 55.51% | +0 | 298 | 445 |
| 1. Intervención Focalizada Juventudes (18–29) | 43.35% | 56.65% | +1,175,046 | 210 | 384 |
| 2. Brigadas Comunitarias Rurales y Mixtas | 43.71% | 56.29% | +797,555 | 173 | 342 |
| 3A. Portafolio Óptimo INE (Banda Conservadora) | 42.66% | 57.34% | +1,885,560 | 147 | 464 |
| 3B. Portafolio Óptimo INE (Escenario Central Con Intervención) | 41.68% | 58.32% | +2,900,891 | 90 | 433 |
| 3C. Portafolio Óptimo INE (Banda Optimista) | 40.69% | 59.31% | +3,916,191 | 58 | 364 |

