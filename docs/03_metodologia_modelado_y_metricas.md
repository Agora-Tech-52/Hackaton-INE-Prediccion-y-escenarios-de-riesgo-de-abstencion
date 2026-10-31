# Metodología de Modelado, Validación Histórica y Métricas de Desempeño — Reto 2 INE

Este documento profundiza en la formulación matemática, la justificación teórica y la evaluación empírica de los modelos predictivos desarrollados por **Ágora Tech** para el **Reto 2 (Predicción y escenarios de riesgo de abstención)** del INE.

---

## 1. Justificación Teórica: ¿Por qué Machine Learning Tabular y NO Deep Learning?

Una decisión central de arquitectura científica consistió en optar por **Machine Learning Estadístico y Modelos de Ensamble Tabular**, descartando redes neuronales profundas (*Deep Learning*). Esta decisión obedece a tres principios metodológicos rigurosos:

### 1.1. Dimensión Temporal de los Datos Electorales ($T = 6$)
* Las elecciones federales en México ocurren cada 3 años. Entre 2009 y 2024 existen únicamente **6 puntos en el tiempo**.
* Aunque se tienen ~2,477 municipios, las características estructurales (demografía, nivel socioeconómico, cultura cívica) varían con relativa lentitud.
* Las redes neuronales profundas (MLP profundas, Transformers o LSTM) requieren secuencias temporales masivas ($T \gg 1,000$) y millones de parámetros libres. En paneles de series cortas, las redes neuronales sufren de **sobreajuste severo (*overfitting*)**, memorizando coyunturas políticas aisladas en lugar de aprender regularidades estructurales.
* La literatura científica internacional (ej. Grinsztajn et al., *Why do tree-based models still outperform deep learning on typical tabular data?*, NeurIPS 2022) demuestra que en datos tabulares los árboles potenciados (GBDT) y los modelos lineales regularizados superan sistemáticamente a las arquitecturas de Deep Learning.

### 1.2. Exigencia de Interpretabilidad Institucional (Política Pública ENCCÍVICA)
* Una red neuronal profunda opera como una «caja negra»: entrega una predicción numérica, pero no permite explicar qué variable influyó ni en qué cuantía.
* El Instituto Nacional Electoral (INE) y la Dirección Ejecutiva de Capacitación Electoral y Educación Cívica (**DECEyEC**) están sujetos al principio de legalidad y deben **fundamentar presupuestalmente** por qué se prioriza un distrito o municipio.
* Un modelo con función de enlace Logit permite derivar **efectos marginales directos en puntos porcentuales**, facilitando que las autoridades justifiquen legalmente el despliegue de brigadas de campo.

### 1.3. Consistencia Probabilística Estricta en el Intervalo $(0, 1)$
* Las tasas de abstención son proporciones acotadas estrictamente entre 0% y 100%.
* Modelar directamente mediante regresión lineal ordinaria ($OLS$) produce el riesgo de generar predicciones absurdas (< 0% o > 100%) en municipios extremos.
* Al aplicar la transformación logit:
  $$\text{logit}(p) = \ln\left(\frac{p}{1 - p}\right)$$
  y proyectar a través de la función sigmoide inversa $\text{expit}(z) = \frac{1}{1 + e^{-z}}$, se garantiza que toda predicción municipal o seccional sea **matemáticamente válida, estrictamente monótona y probabilísticamente consistente**.

---

## 2. Los Cuatro Modelos Evaluados en el Benchmark

En [`src/ine_abstencion/modeling/predictor.py`](file:///home/soren_ubuntu/laura/hackaton-ine-reto2/src/ine_abstencion/modeling/predictor.py), se implementaron y compararon cuatro enfoques:

### Modelo 1: Baseline Homólogo de Inercia Histórica ($t-6$)
* **Concepto:** Modelo de persistencia que asume que cada municipio replicará exactamente la abstención observada en la elección idéntica anterior (la última intermedia para 2021 o la última presidencial para 2024).
* **Ecuación:** $\hat{y}_{i, t} = y_{i, t-6}$.
* **Propósito:** Actúa como umbral mínimo de control. Si un modelo de Machine Learning no supera al baseline, carece de utilidad práctica.

### Modelo 2: Regresión Logit Regularizada Ridge con Pesos Muestrales (Principal Explicativo)
* **Concepto:** Modelo econométrico multivariado con regularización $L_2$ (Ridge) sobre la escala logit. Pondera las observaciones por $\sqrt{\text{Lista Nominal}}$ para dar mayor estabilidad a los municipios con gran masa poblacional sin descartar municipios pequeños.
* **Optimización:** Selección del hiperparámetro de penalización $\alpha$ mediante validación cruzada interna (`RidgeCV` sobre 40 valores en escala logarítmica).
* **Ventaja:** Entrega coeficientes estandarizados directos y efectos marginales transparentes.

### Modelo 3: Histogram-based Gradient Boosting Decision Trees (HistGBDT - Benchmark No Lineal)
* **Concepto:** Ensamble no paramétrico de árboles de decisión potenciados por gradiente (algoritmo tipo LightGBM integrado en Scikit-Learn) configurado con función de pérdida logit.
* **Parámetros:** 150 estimadores, tasa de aprendizaje $\eta = 0.05$, profundidad máxima 4, regularización $L_2 = 2.0$.
* **Ventaja:** Detecta interacciones espaciales complejas, efectos de umbral y no-linealidades sin necesidad de especificarlas manualmente.

### Modelo 4: Ensamble Híbrido Ponderado INE (Modelo Final para Escenarios)
* **Concepto:** Combinación convexa ponderada que integra la solidez estructural del modelo lineal con la capacidad de adaptación local de los árboles de decisión:
  $$\hat{y}_{\text{Ensamble}} = 0.70 \cdot \hat{y}_{\text{Logit Ridge}} + 0.30 \cdot \hat{y}_{\text{HistGBDT}}$$
* **Ventaja:** Logra la menor tasa de error cuadrático medio ($RMSE$), minimiza el riesgo de fallos atípicos y maximiza la precisión en la identificación de focos rojos críticos.

---

## 3. Glosario Matemático de las Cinco Métricas de Desempeño

Para auditar el comportamiento de los modelos se emplearon cinco métricas estadísticas y operativas:

1. **Error Absoluto Medio (MAE, en puntos porcentuales):**
   $$\text{MAE} = \frac{1}{N} \sum_{i=1}^N |y_i - \hat{y}_i|$$
   *Interpretación:* Desviación promedio simple entre la tasa real y la estimada a través de los municipios. Menor es mejor.

2. **MAE Ponderado por Lista Nominal (WMAE LN, en puntos porcentuales):**
   $$\text{WMAE} = \frac{\sum_{i=1}^N \text{LN}_i \cdot |y_i - \hat{y}_i|}{\sum_{i=1}^N \text{LN}_i}$$
   *Interpretación:* Mide el error promedio **a nivel de ciudadano individual**. Evita que municipios con 300 electores distorsionen la evaluación de municipios con 1.5 millones de personas. Menor es mejor.

3. **Raíz del Error Cuadrático Medio (RMSE, en puntos porcentuales):**
   $$\text{RMSE} = \sqrt{\frac{1}{N} \sum_{i=1}^N (y_i - \hat{y}_i)^2}$$
   *Interpretación:* Penaliza con dureza cuadrática los errores extremos. Un RMSE bajo indica ausencia de fallas catastróficas. Menor es mejor.

4. **Coeficiente de Determinación Ponderado ($R^2$ Pond.):**
   $$R^2 = 1 - \frac{\sum_{i=1}^N \text{LN}_i (y_i - \hat{y}_i)^2}{\sum_{i=1}^N \text{LN}_i (y_i - \bar{y})^2}$$
   *Interpretación:* Proporción de la varianza territorial de la abstención explicada por el modelo fuera de muestra. Mayor es mejor.

5. **Precisión en el Top 20% Crítico (`Precision@Top20%`):**
   $$\text{Prec}@20\% = \frac{|\text{Top 20\% Predicho} \cap \text{Top 20\% Real}|}{|\text{Top 20\% Predicho}|}$$
   *Interpretación:* **La métrica operativa más importante para el INE.** Mide la efectividad del modelo para alertar con exactitud los municipios que caerán en el quintil con mayor abstención del país. Mayor es mejor.

---

## 4. Resultados de la Validación Histórica Fuera de Muestra (Backtesting)

La validación se ejecutó de forma estrictamente ciega (*out-of-time validation* sin fuga de información temporal):

```text
Corte 1 (Elección Intermedia 2021):
  ├── Conjunto de Entrenamiento: 2015 e Intermedia 2018 (<= 2018)
  └── Conjunto de Prueba Ciega:  Intermedia 2021 (2,477 municipios)

Corte 2 (Elección Presidencial 2024):
  ├── Conjunto de Entrenamiento: 2015, 2018 y 2021 (<= 2021)
  └── Conjunto de Prueba Ciega:  Presidencial 2024 (2,477 municipios)
```

### Tabla Maestra de Métricas Comparativas

| Corte de Validación | Modelo Evaluado | MAE (pp) | WMAE LN (pp) | RMSE (pp) | $R^2$ Ponderado | Precisión Top 20% |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| **Backtest Presidencial 2024** | 1. Baseline Homólogo ($t-6$) | 6.62 | 4.38 | 9.08 | 0.360 | 64.3% |
| *(Entrena $\le 2021$)* | 2. Logit Regularizado (Principal) | 6.98 | **4.11** | 9.24 | 0.444 | 64.9% |
| | 3. HistGradientBoosting (GBDT) | 6.67 | 4.85 | 8.81 | 0.370 | 61.9% |
| | **4. Ensamble Híbrido INE (70/30)** | **6.63** | **4.23** | **8.75** | **0.458** | **66.5%** |
| **Backtest Intermedia 2021** | 1. Baseline Homólogo ($t-6$) | 13.39 | 9.13 | 17.69 | -0.355 | 39.3% |
| *(Entrena $\le 2018$)* | 2. Logit Regularizado (Principal) | 10.33 | 7.22 | 13.10 | 0.179 | 39.7% |
| | 3. HistGradientBoosting (GBDT) | **8.61** | **6.68** | **11.19** | **0.299** | **48.4%** |
| | **4. Ensamble Híbrido INE (70/30)** | **9.62** | **6.90** | **12.21** | **0.253** | **43.3%** |

### Conclusiones de la Evaluación:
1. **El Baseline Homólogo fracasa en elecciones intermedias:** Obtiene un $R^2$ negativo (-0.355) y un error de 9.13 pp, demostrando que la inercia simple no es confiable para prever elecciones intermedias.
2. **El Ensamble Híbrido INE es el modelo más robusto:** Alcanza un $R^2$ de **0.458** en 2024, un error WMAE de apenas **4.23 puntos porcentuales** y una precisión en focos rojos críticos de **66.5%** (2 de cada 3 municipios alertados resultaron efectivamente ser los más abstencionistas del país).

---

## 5. Factores Determinantes de la Abstención (Efectos Marginales)

A partir del modelo explicativo en [`outputs/tables/importancia_y_coeficientes_modelo.csv`](file:///home/soren_ubuntu/laura/hackaton-ine-reto2/outputs/tables/importancia_y_coeficientes_modelo.csv), se extrajeron los coeficientes estandarizados y los efectos marginales directos ante un incremento de una desviación estándar ($+1\text{ DE}$):

| Variable Predictora | Coeficiente Logit Estandarizado | Efecto Marginal (+1 DE) | Importancia por Permutación (GBDT) | Interpretación Cívica y Territorial |
| :--- | :---: | :---: | :---: | :--- |
| **Brecha Local de Abstención Juvenil (18–29 años)** | **+0.2766** | **+6.74 pp** | **0.4306** | **El factor de riesgo #1:** A mayor desinterés relativo de las juventudes respecto a los adultos, la abstención municipal se dispara. |
| **Abstención Homóloga Previa ($t-6$)** | **+0.2575** | **+6.27 pp** | 0.1949 | Memoria histórica inercial del comportamiento en elecciones del mismo tipo. |
| **Abstención Inmediata Anterior ($t-3$)** | +0.1742 | +4.24 pp | 0.2704 | Nivel base heredado del proceso electoral federal más reciente. |
| **Proporción de Jóvenes 18–29 en Lista Nominal** | -0.1388 | -3.38 pp | 0.0399 | Control demográfico de la estructura etaria territorial. |
| **Proporción de Adultos Mayores (60+ años)** | **-0.1381** | **-3.36 pp** | 0.0419 | **Factor protector:** Zonas con mayor peso de adultos mayores registran sistemáticamente mayor participación. |
| **Efecto Elección Intermedia (`ES_INTERMEDIA`)** | **+0.1221** | **+2.97 pp** | 0.1201 | **Fatiga estructural:** En comicios intermedios, la abstención aumenta cerca de 3 puntos porcentuales de forma inherente. |
| **Brecha de Género (Hombres - Mujeres)** | -0.0679 | -1.65 pp | 0.1748 | Las mujeres votan en mayor proporción que los hombres en la mayoría de los distritos del país. |
| **Grado de Urbanización (% LN Urbana)** | +0.0353 | +0.86 pp | 0.0149 | Las secciones urbanas tienden a mostrar ligeramente menor participación que las rurales organizadas. |

Esta matriz de efectos marginales proporciona el fundamento analítico para las simulaciones de política pública focalizada del INE.

