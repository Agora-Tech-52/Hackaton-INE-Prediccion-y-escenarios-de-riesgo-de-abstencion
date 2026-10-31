# Simulador de Escenarios Contrafactuales y Política Pública Preventiva (ENCCÍVICA) — Reto 2 INE

Este documento detalla el motor de simulación contrafactual, los supuestos de elasticidad cívica basados en la **Estrategia Nacional de Cultura Cívica (ENCCÍVICA)** y los resultados proyectados para las elecciones federales de **2027 (Intermedia)** y **2030 (Presidencial)**, implementados en [`src/ine_abstencion/scenarios/simulator.py`](file:///home/soren_ubuntu/laura/hackaton-ine-reto2/src/ine_abstencion/scenarios/simulator.py).

---

## 1. Horizonte Temporal de Simulación: ¿Por qué 2027 como Eje Central?

En México, la siguiente cita electoral federal son los **comicios intermedios de 2027**, en los que se renovará la totalidad de la H. Cámara de Diputados (500 diputaciones federales).

Históricamente, las elecciones intermedias representan el **mayor desafío de legitimidad y participación para el INE**, ya que la abstención suele dispararse entre 10 y 15 puntos porcentuales respecto a las elecciones presidenciales debido a la fatiga del ciclo y a la ausencia de la boleta presidencial.

Por ello, el simulador adopta **2027 como horizonte principal de alerta temprana** y proyecta complementariamente **2030** para evaluar la sostenibilidad cívica a mediano plazo.

---

## 2. Modelación de Elasticidades y Mecanismos de Intervención

A partir de los coeficientes de efectos marginales obtenidos por el modelo econométrico Logit, se modelaron tres palancas de intervención pública focalizada:

1. **Reducción de la Brecha de Abstención Juvenil ($\Delta \text{Brecha Juvenil}$):**
   * El modelo demostró que $+1\text{ DE}$ en la brecha juvenil incrementa la abstención municipal en $+6.74$ pp.
   * Mediante campañas digitales focalizadas, módulos móviles en campus universitarios y convenios comerciales para incentivar el primer voto, se simula una reducción relativa de la brecha juvenil:
     * Banda Conservadora: -10% de la brecha local.
     * **Escenario Central Moderado:** **-20% de la brecha local**.
     * Banda Optimista: -30% de la brecha local.
2. **Mitigación de la Fatiga y Barrera Geográfica en Zonas Rurales y Mixtas ($\Delta \text{Rezago Rural}$):**
   * En secciones rurales y mixtas, la abstención está mediada por barreras de transporte y distancia.
   * Mediante casillas extraordinarias y brigadas de traslado cívico, se simula una reducción de la fatiga territorial:
     * Banda Conservadora: -12% de fatiga.
     * **Escenario Central Moderado:** **-22% de fatiga**.
     * Banda Optimista: -32% de fatiga.
3. **Restricción Presupuestal y Portafolio Óptimo (Regla del 15%):**
   * El INE no cuenta con presupuesto ilimitado para intervenir los 2,477 municipios del país con la misma intensidad.
   * Se parametriza una cobertura presupuestal concentrada en el **Top 15% de municipios de mayor retorno cívico** (ordenados por el ratio de votos potencialmente recuperables entre costo logístico) más la totalidad de los municipios clasificados en **Riesgo Crítico**.

---

## 3. Resultados de los Escenarios Nacionales para 2027

La tabla maestra de simulación ([`outputs/tables/resumen_escenarios_2027.csv`](file:///home/soren_ubuntu/laura/hackaton-ine-reto2/outputs/tables/resumen_escenarios_2027.csv)) sintetiza los impactos comparativos a escala nacional:

| Escenario de Simulación | Abstención Proyectada 2027 | Participación Estimada 2027 | Votos Ciudadanos Recuperados | Municipios en Riesgo Crítico | Municipios en Riesgo Alto |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **0. Línea Base (Sin Intervención 2027)** | **44.49%** | **55.51%** | **0** | **298** | **445** |
| **1. Intervención Juventudes (18–29 años)** | 43.35% | 56.65% | +1,175,046 | 210 | 441 |
| **2. Brigadas Rurales y Mixtas** | 43.71% | 56.29% | +797,555 | 173 | 435 |
| **3A. Portafolio Óptimo INE (Conservador)** | 42.66% | 57.34% | +1,885,560 | 147 | 370 |
| **3B. Portafolio Óptimo INE (Escenario Central)** | **41.68%** | **58.32%** | **+2,900,891** | **90** | **318** |
| **3C. Portafolio Óptimo INE (Optimista)** | 40.69% | 59.31% | +3,916,191 | 58 | 269 |

### Diagnóstico del Escenario Central (3B):
* **Recuperación masiva del sufragio:** Se rescatan **2,900,891 votos adicionales** que de otro modo se habrían abstenido en la elección intermedia.
* **Aumento de la participación nacional:** La participación ciudadana asciende de **55.51% a 58.32%** (+2.81 puntos porcentuales netos).
* **Desactivación de focos rojos:** **208 municipios salen de Riesgo Crítico**, reduciéndose de 298 a tan solo 90 a nivel nacional.

---

## 4. Análisis de Eficiencia Presupuestal de Pareto (Concentración Territorial)

Uno de los hallazgos más contundentes para el Comité Evaluador y las autoridades del INE es la **Curva de Concentración del Retorno Cívico** ([`outputs/figures/fig8_curva_concentracion_pareto_ine.png`](file:///home/soren_ubuntu/laura/hackaton-ine-reto2/outputs/figures/fig8_curva_concentracion_pareto_ine.png)):

```text
Distribución Acumulada de Votos Recuperados por Cobertura Municipal:
├── Top 5% de municipios intervenidos:   Captura el 64.2% del retorno nacional (+1.86M votos)
├── Top 10% de municipios intervenidos:  Captura el 81.5% del retorno nacional (+2.36M votos)
├── Top 15% de municipios intervenidos:  Captura el 90.7% del retorno nacional (+2.63M votos)
└── Restante 85% de municipios:         Aporta únicamente el 9.3% del retorno adicional
```

### ¿Por qué ocurre esta concentración?
En México, la población con credencial para votar se encuentra fuertemente concentrada en zonas metropolitanas e intermedias (Valle de México, Guadalajara, Monterrey, Puebla, Tijuana, Juárez, León, Toluca, etc.).

Al combinar la priorización matemática de municipios con gran masa de electores jóvenes desconectados y zonas de alto riesgo de abstención, **el INE puede lograr más del 90% del impacto cívico nacional concentrando sus recursos en solo 372 municipios estratégicos**, optimizando el gasto público y maximizando el costo-beneficio de la ENCCÍVICA.

---

## 5. Impacto del Semáforo a Nivel Entidad Federativa

A nivel estatal, la simulación del Portafolio Óptimo INE genera las mayores recuperaciones de votos en las entidades con mayor padrón electoral y altas brechas juveniles previas:

| Entidad Federativa | Abstención Proyectada Sin Intervención | Abstención Con Portafolio Óptimo | Reducción Neta de Abstención | Votos Ciudadanos Recuperados |
| :--- | :---: | :---: | :---: | :---: |
| **Estado de México** | 45.12% | 41.98% | -3.14 pp | **+407,812 votos** |
| **Ciudad de México** | 39.85% | 36.92% | -2.93 pp | **+232,450 votos** |
| **Jalisco** | 46.20% | 42.85% | -3.35 pp | **+221,180 votos** |
| **Veracruz** | 44.80% | 41.65% | -3.15 pp | **+193,420 votos** |
| **Puebla** | 43.90% | 40.82% | -3.08 pp | **+152,690 votos** |
| **Guanajuato** | 47.10% | 43.75% | -3.35 pp | **+161,240 votos** |
| **Nuevo León** | 48.50% | 44.90% | -3.60 pp | **+158,910 votos** |

La tabla estatal completa con las 32 entidades federativas se encuentra disponible en [`outputs/tables/semaforo_estatal_escenarios_2027.csv`](file:///home/soren_ubuntu/laura/hackaton-ine-reto2/outputs/tables/semaforo_estatal_escenarios_2027.csv) y en la pestaña `SEMAFORO_ESTATAL` del libro de Excel.

