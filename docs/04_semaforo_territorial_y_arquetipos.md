# Semáforo de Riesgo Territorial y Arquetipos Diagnósticos — Reto 2 INE

Este documento describe la formulación matemática, la calibración de umbrales y la aplicación operativa del **Índice Compuesto de Riesgo Territorial (Score 0 a 100)** y la **Tipología de Cinco Arquetipos Diagnósticos**, implementados en [`src/ine_abstencion/modeling/risk_index.py`](file:///home/soren_ubuntu/laura/hackaton-ine-reto2/src/ine_abstencion/modeling/risk_index.py).

---

## 1. El Índice Compuesto de Riesgo Territorial (Score 0 a 100)

Para que el personal directivo y operativo del INE (Junta General Ejecutiva, Juntas Locales y Distritales) pueda priorizar territorialmente las acciones preventivas, se diseñó un índice sintético normalizado.

El índice evita depender de una sola variable y sintetiza **tres dimensiones complementarias** del fenómeno electoral mediante estandarización estadística robusta.

### 1.1. Estandarización Robusta ante Casos Atípicos
Para prevenir distorsiones causadas por municipios con dinámicas anómalas, se utiliza el puntaje Z robusto basado en la mediana y el rango intercuartílico ($\text{IQR}$):

$$Z_{\text{robusto}}(X) = \text{clip}\left(\frac{X - \text{Mediana}(X)}{\text{IQR}(X) / 1.349}, -3.5, +3.5\right)$$

### 1.2. Las Tres Dimensiones del Riesgo

1. **Dimensión 1 — Nivel de Abstención Inercial Proyectado 2027 ($w_{\text{nivel}} = 0.55$):**
   Mide la magnitud esperada de la abstención en la elección intermedia de 2027 sin intervención. Representa el 55% del puntaje total.
2. **Dimensión 2 — Velocidad de Deterioro Estructural ($w_{\text{tendencia}} = 0.25$):**
   Calcula la variación respecto a ciclos intermedios homólogos previos ($\text{Abstención}_{2027} - \text{Abstención}_{2015}$). Identifica municipios donde la participación ciudadana se está erosionando rápidamente. Representa el 25% del puntaje.
3. **Dimensión 3 — Masa Crítica de Abstencionistas Esperados ($w_{\text{volumen}} = 0.20$):**
   Evalúa el logaritmo de la cantidad absoluta de ciudadanos que no votarían: $\ln(1 + NV_{2027})$. Evita que micro-municipios con 200 habitantes desplacen a grandes concentraciones urbanas donde cientos de miles de ciudadanos no acudirán a las urnas. Representa el 20% del puntaje.

### 1.3. Agregación y Transformación a Escala 0–100
El puntaje compuesto bruto se calcula como:

$$\text{Puntaje Bruto} = 0.55 \cdot Z_{\text{nivel}} + 0.25 \cdot Z_{\text{tendencia}} + 0.20 \cdot Z_{\text{volumen}}$$

Finalmente, para que sea intuitivo para los operadores institucionales, se transforma a una escala continua de **0 a 100** a través de la función de distribución acumulada normal ($\Phi$):

$$\text{Score de Riesgo} = 100 \times \Phi(\text{Puntaje Bruto})$$

---

## 2. Los Cuatro Niveles del Semáforo de Riesgo Territorial

Los umbrales del Semáforo se calibraron sobre la distribución inercial 2027 sin intervención para garantizar una estratificación nítida del territorio nacional:

| Nivel del Semáforo | Percentil Calibrado | Rango de Score (0–100) | Número de Municipios | Descripción Operativa para el INE |
| :--- | :---: | :---: | :---: | :--- |
| **<font color='#2A9D8F'>●</font> Riesgo Bajo** | Percentil 0 – 40 | 0.00 – 43.12 | **991 municipios** | **Resiliencia cívica:** Zonas con alta participación sostenida (> 70%). Solo requieren mantenimiento institucional ordinario. |
| **<font color='#D4A300'>●</font> Riesgo Moderado** | Percentil 40 – 70 | 43.13 – 57.84 | **703 municipios** | **Vulnerabilidad intermedia:** Participación media que suele decaer en elecciones legislativas. Requieren refuerzo informativo. |
| **<font color='#F4A261'>●</font> Riesgo Alto** | Percentil 70 – 88 | 57.85 – 72.40 | **445 municipios** | **Prioridad preventiva:** Focos de baja participación que requieren despliegue anticipado de módulos y brigadas cívicas. |
| **<font color='#E63946'>●</font> Riesgo Crítico** | Percentil 88 – 100 | 72.41 – 100.0 | **298 municipios** | **Alerta temprana máxima:** Alta abstención esperada combinada con gran masa de electores o deterioro acelerado. Foco rojo del INE. |

---

## 3. Tipología Diagnóstica de Cinco Arquetipos Territoriales

Para evitar aplicar intervenciones genéricas e ineficientes, el sistema asigna a cada municipio una **causa principal de abstención**.

### Algoritmo de Asignación por Máxima Intensidad Relativa
Para los municipios clasificados en Riesgo Moderado, Alto o Crítico, el sistema calcula 4 puntajes normalizados correspondientes a los motores estructurales de la abstención:

$$Z_{\text{juventud}} = Z_{\text{robusto}}\left(\text{PROP\_JOVENES}_{18\_29} \times \text{BRECHA\_JUVENIL}\right)$$
$$Z_{\text{rural}} = Z_{\text{robusto}}\left(\text{PROP\_RURAL\_MIXTA} \times \text{ABST\_RURAL\_MIXTA}\right)$$
$$Z_{\text{fatiga}} = Z_{\text{robusto}}\left(\text{ABST\_PROY}_{2027} - \text{ABST\_OBS}_{2024}\right)$$
$$Z_{\text{periferia}} = Z_{\text{robusto}}\left(\text{PROP\_URBANA} \times \text{CRECIMIENTO\_LN}_{3\text{A}}\right)$$

Mediante la función `np.argmax([Z_juventud, Z_rural, Z_fatiga, Z_periferia])`, el sistema identifica cuál es el factor con mayor severidad relativa en cada territorio. Si el municipio pertenece al nivel de Riesgo Bajo, se etiqueta automáticamente como *Participación Resiliente*.

```text
Distribución Nacional de Arquetipos (2,477 municipios):
├── 0. Participación Resiliente:                  991 mun. (Abstención media: 28.6%)
├── 4. Periferia Urbana en Expansión Demográfica: 535 mun. (Abstención media: 45.3%)
├── 1. Brecha Juvenil y Primer Voto (18-29):      385 mun. (Abstención media: 46.8%)
├── 2. Rezago Territorial Rural / Mixto:          334 mun. (Abstención media: 47.9%)
└── 3. Fatiga Aguda en Elección Intermedia:       232 mun. (Abstención media: 48.2%)
```

---

## 4. Descripción Detallada y Estrategia de Intervención por Arquetipo

### Arquetipo 0: Participación Resiliente (Mantenimiento)
* **Cantidad y Abstención Media:** 991 municipios | 28.6% de abstención (71.4% de participación).
* **Diagnóstico Socio-Electoral:** Comunidades con fuerte cohesión comunitaria, municipios indígenas con sistemas normativos internos activos o entidades con arraigada cultura de voto (ej. municipios de Yucatán, Oaxaca rural, Tlaxcala).
* **Estrategia INE (ENCCÍVICA):** Reconocimiento ciudadano, preservación de buenas prácticas y garantía de suficiencia de boletas y casillas sin alterar sus dinámicas comunitarias.

### Arquetipo 1: Brecha Juvenil y Primer Voto (18–29 años)
* **Cantidad y Abstención Media:** 385 municipios | 46.8% de abstención.
* **Diagnóstico Socio-Electoral:** Ciudades intermedias y centros urbanos universitarios donde los adultos mayores votan activamente (70%+), pero las personas de 19 a 29 años se abstienen masivamente (60%+), generando brechas de hasta 20 puntos porcentuales. Existe desconexión frente a la oferta partidista y falta de incentivos tangibles para el primer voto.
* **Estrategia INE (ENCCÍVICA):**
  * Campañas digitales hiperfocalizadas en redes sociales (TikTok, Instagram, YouTube) diseñadas con lenguaje joven y sin tecnicismos electorales.
  * Módulos Móviles de Actualización y entrega de Credencial para Votar directamente en campus universitarios, preparatorias e institutos tecnológicos.
  * Alianzas con cámaras de comercio y empresas para otorgar incentivos cívicos (descuentos, promociones) al mostrar el pulgar entintado tras votar por primera vez.

### Arquetipo 2: Rezago Territorial Rural / Mixto
* **Cantidad y Abstención Media:** 334 municipios | 47.9% de abstención.
* **Diagnóstico Socio-Electoral:** Secciones con alta dispersión territorial en sierras, valles aislados o costas. La ciudadanía no se abstiene por desinterés político, sino por **barreras económicas y físicas de movilidad** (caminar horas bajo el sol o gastar sumas significativas de transporte familiar para llegar a la casilla).
* **Estrategia INE (ENCCÍVICA):**
  * Instalación intensiva de **Casillas Extraordinarias y Especiales** más próximas a los asentamientos alejados.
  * Implementación de **Brigadas Comunitarias de Traslado Cívico** en coordinación con autoridades locales imparciales.
  * Módulos itinerantes del Registro Federal de Electores con visitas programadas con meses de antelación.

### Arquetipo 3: Fatiga Aguda en Elección Intermedia
* **Cantidad y Abstención Media:** 232 municipios | 48.2% de abstención (la más alta del país).
* **Diagnóstico Socio-Electoral:** Municipios con fuerte politización en elecciones presidenciales que sufren caídas abruptas de entre 15 y 20 puntos porcentuales cuando solo se eligen diputaciones federales y locales. La ciudadanía percibe erróneamente que las elecciones legislativas intermedias «no cambian su realidad cotidiana».
* **Estrategia INE (ENCCÍVICA):**
  * Pedagogía cívica institucional sobre las funciones sustantivas de la Cámara de Diputados: aprobación del Presupuesto de Egresos de la Federación, asignación de recursos públicos locales y fiscalización de cuentas.
  * Organización de debates distritales accesibles y foros cívicos locales entre candidaturas a diputaciones para reanimar el interés ciudadano.

### Arquetipo 4: Periferia Urbana en Expansión Demográfica
* **Cantidad y Abstención Media:** 535 municipios | 45.3% de abstención.
* **Diagnóstico Socio-Electoral:** «Ciudades dormitorio» y nuevos desarrollos habitacionales periféricos en las principales zonas metropolitanas (Valle de México, Monterrey, Guadalajara, Querétaro, Tijuana, Cancún). Cuentan con un crecimiento acelerado del padrón electoral en personas que trabajan lejos de su residencia, pasan hasta 4 horas al día en transporte público y no han actualizado su domicilio en la credencial.
* **Estrategia INE (ENCCÍVICA):**
  * Campañas masivas de **Actualización Domiciliaria de la Credencial** con módulos de fin de semana en plazas comerciales, paraderos de autobuses y estaciones de metro/tren suburbano.
  * Instalación de casillas en nodos de gran afluencia peatonal para facilitar el ejercicio del voto sin desvíos geográficos significativos.

