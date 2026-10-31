# Guía de Ejecución Local Detallada — Reto 2 INE (Ágora Tech)

Esta guía proporciona instrucciones exhaustivas, reproducibles y paso a paso para desplegar, auditar, ejecutar y validar localmente el pipeline completo del **Reto 2 (Predicción y escenarios de riesgo de abstención)** desarrollado por **Ágora Tech** para el hackatón *«Hackea la participación: Datos que construyen democracia»* (INE 2026).

---

## 1. Requisitos de Sistema y Entorno

### Hardware Mínimo Recomendado
* **Procesador (CPU):** 4 núcleos (x86_64 o ARM64 / Apple Silicon).
* **Memoria RAM:** Mínimo 8 GB (Recomendado 16 GB para acelerar la ingesta Polars de los 54.8 millones de filas).
* **Almacenamiento en Disco:** Al menos 10 GB de espacio libre (los archivos crudos ocupan 3.56 GB, y las capas Silver y Gold en Parquet optimizado ocupan ~400 MB).

### Sistema Operativo Compatible
* **Linux:** Ubuntu 20.04 LTS o superior, Debian 11+, Fedora 38+, Arch Linux.
* **Windows:** Mediante **WSL2 (Windows Subsystem for Linux)** con Ubuntu 20.04/22.04/24.04.
* **macOS:** macOS Monterey (12.0) o superior con Homebrew.

### Software Base Necesario
* **Python:** Versión **3.12** instalada en el sistema.
* **Gestor de Paquetes `uv`:** [Astral uv](https://docs.astral.sh/uv/) (gestor ultra-rápido basado en Rust).
* **Git:** Para clonar el repositorio y gestionar versiones.

---

## 2. Instalación Paso a Paso con `uv`

### Paso 2.1. Instalar `uv` (si aún no lo tienes)
En Linux, WSL2 o macOS, ejecuta en tu terminal:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Verifica la instalación:
```bash
uv --version
# Debe responder uv 0.4.x o superior
```

### Paso 2.2. Clonar o Navegar al Directorio del Proyecto
```bash
cd /home/soren_ubuntu/laura/hackaton-ine-reto2
```

### Paso 2.3. Sincronizar el Entorno Virtual Determinista
`uv` leerá automáticamente el archivo [`uv.lock`](file:///home/soren_ubuntu/laura/hackaton-ine-reto2/uv.lock) e instalará las dependencias exactas con verificación criptográfica de hashes:

```bash
uv sync
```

Esto creará la carpeta `.venv/` con todas las bibliotecas científicas requeridas:
* Procesamiento masivo: `polars`, `pyarrow`, `pandas`, `openpyxl`.
* Modelado y analítica: `scikit-learn`, `numpy`, `scipy`.
* Cartografía y SIG: `geopandas`, `folium`, `shapely`, `pyogrio`.
* Compilación y visualización: `reportlab`, `matplotlib`, `seaborn`, `rich`, `click`, `pytest`.

---

## 3. Configuración de Rutas de Datos

El proyecto está diseñado bajo una arquitectura de **«cero duplicación de datos»**. Lee directamente los 194 archivos CSV originales desde su ubicación original sin copiarlos ni moverlos.

La configuración se gestiona en [`configs/config.toml`](file:///home/soren_ubuntu/laura/hackaton-ine-reto2/configs/config.toml):

```toml
[paths]
# Ruta donde se encuentran los 194 archivos CSV crudos (3.56 GB)
raw_data_dir = "../Datos para intregrar BD"

# Carpetas de datos intermedios y finales
silver_data_dir = "data/silver"
gold_data_dir = "data/gold"
outputs_dir = "outputs"
tables_dir = "outputs/tables"
figures_dir = "outputs/figures"
deliverables_dir = "outputs/entrega_final"
geospatial_dir = "data/geospatial"
```

Si deseas ejecutar el proyecto en otra máquina o ruta, únicamente ajusta `raw_data_dir` en [`configs/config.toml`](file:///home/soren_ubuntu/laura/hackaton-ine-reto2/configs/config.toml).

---

## 4. Ejecución del Pipeline: Comandos CLI (`ine-riesgo`)

El proyecto cuenta con un CLI profesional empaquetado como [`ine-riesgo`](file:///home/soren_ubuntu/laura/hackaton-ine-reto2/src/ine_abstencion/cli.py). Puedes consultar la ayuda general en cualquier momento:

```bash
uv run ine-riesgo --help
```

### Opción A: Ejecución Integral Automática (Recomendada)
Para correr absolutamente todas las fases del proyecto de principio a fin con un solo comando:

```bash
uv run ine-riesgo run-all
```

El pipeline tardará aproximadamente **2 a 3 minutos** en procesar los 54.8 millones de votos, entrenar los modelos, simular los escenarios y compilar todos los entregables.

---

### Opción B: Ejecución Modular por Fases

Si deseas auditar, experimentar o ejecutar el pipeline paso a paso:

#### Fase 1: Ingesta Vectorial y Saneamiento (Bronze a Silver)
Lee los 192 archivos territoriales y los 2 archivos modales con Polars Streaming, valida la integridad contable $LN = SV + NV + NS$, genera las llaves invariantes y escribe en Parquet:
```bash
uv run ine-riesgo ingest
```
*Salida:* `data/silver/ccpc_2009.parquet` ... `ccpc_2024.parquet` y `outputs/tables/auditoria_calidad_datos_2009_2024.csv`.

#### Fase 2: Ingeniería de Características y Diagnóstico Estadístico (Silver a Gold)
Construye los paneles longitudinales a nivel municipal (2,477 municipios × 6 elecciones = 14,779 observaciones) y seccional, calcula brechas de edad y género, correlaciones y VIF:
```bash
uv run ine-riesgo features
```
*Salida:* `data/gold/panel_municipal_2009_2024.parquet`, `panel_seccional_2015_2024.parquet`, `outputs/tables/correlaciones_abstencion.csv` y `outputs/tables/matriz_correlacion_completa.csv`.

#### Fase 3: Entrenamiento de Modelos y Backtesting Histórico
Ejecuta la validación ciega fuera de muestra en las elecciones de 2021 (intermedia) y 2024 (presidencial), ajusta el Ensamble Híbrido INE y proyecta la abstención inercial para 2027 y 2030:
```bash
uv run ine-riesgo train
```
*Salida:* `outputs/tables/metricas_backtesting_modelos.csv` e `importancia_y_coeficientes_modelo.csv`.

#### Fase 4: Simulación Contrafactual de Escenarios 2027
Calcula el Índice Compuesto de Riesgo (0-100), asigna el Semáforo de 4 niveles, etiqueta los 5 Arquetipos Diagnósticos y simula las intervenciones de política pública (Juventudes, Brigadas Rurales y Portafolio Óptimo INE):
```bash
uv run ine-riesgo simulate
```
*Salida:* `data/gold/proyeccion_y_escenarios_municipios_2027.parquet`, `outputs/tables/resumen_escenarios_2027.csv` y `outputs/tables/semaforo_estatal_escenarios_2027.csv`.

#### Fase 5: Compilación de Entregables Oficiales (Base Sexta)
Genera las 8 figuras a 300 DPI, el tablero web interactivo DualMap en HTML, la cartografía SIG (.GPKG y .GeoJSON), el libro Excel anonimizado y compila los dos reportes ejecutivos en PDF:
```bash
uv run ine-riesgo deliverables
```
*Salida:* Todos los archivos de la carpeta [`outputs/entrega_final/`](file:///home/soren_ubuntu/laura/hackaton-ine-reto2/outputs/entrega_final/).

---

## 5. Pruebas Automatizadas de Calidad y Privacidad

Para garantizar que el software cumple con estándares de ingeniería de software robustos y no vulnera la privacidad de los votantes:

```bash
uv run pytest -v
```

El conjunto de pruebas automatizadas en [`tests/test_pipeline.py`](file:///home/soren_ubuntu/laura/hackaton-ine-reto2/tests/test_pipeline.py) verifica:
1. `test_discover_192_territorial_and_2_modal_files`: Que se descubran y lean exactamente los 192 archivos territoriales y los 2 modales especiales de 2024 sin omisiones.
2. `test_entidades_catalog_completeness`: Que las 32 entidades federativas y sus 5 circunscripciones plurinominales estén perfectamente codificadas según la cartografía oficial del INE.
3. `test_deliverables_and_privacy_constraints`: Que todos los entregables de la Base Sexta existan, tengan contenido válido, y que las bases de datos anonimizadas **no contengan ninguna columna de datos personales** (nombres, CURP, claves electorales o domicilios).

---

## 6. Cómo Visualizar los Resultados y Entregables

### 6.1. Tablero Web Interactivo DualMap (`.HTML`)
* **Archivo:** [`outputs/entrega_final/Tablero_Interactivo_Escenarios_Sin_vs_Con_Intervencion_2027.html`](file:///home/soren_ubuntu/laura/hackaton-ine-reto2/outputs/entrega_final/Tablero_Interactivo_Escenarios_Sin_vs_Con_Intervencion_2027.html)
* **Cómo abrirlo:**
  * En Windows / WSL2: Haz doble clic en el archivo o navega a `\\wsl.localhost\Ubuntu-20.04\home\soren_ubuntu\laura\hackaton-ine-reto2\outputs\entrega_final\Tablero_Interactivo_Escenarios_Sin_vs_Con_Intervencion_2027.html` desde cualquier navegador (Chrome, Edge, Firefox, Brave).
  * En Linux: `xdg-open outputs/entrega_final/Tablero_Interactivo_Escenarios_Sin_vs_Con_Intervencion_2027.html`.
* **Características:**
  * Panel izquierdo: Escenario Base Inercial 2027 (Sin Intervención).
  * Panel derecho: Portafolio Óptimo INE 2027 (Con Intervención ENCCÍVICA).
  * Polígonos reales de los 32 estados coloreados según el Semáforo de Riesgo (**Bajo**, **Moderado**, **Alto**, **Crítico**).
  * Zoom sincronizado entre ambos mapas. Al hacer clic en cualquier estado o municipio, se despliega una ficha emergente con votos recuperados, tasa proyectada y arquetipo diagnóstico.

### 6.2. Cartografía SIG (.GPKG y .GeoJSON)
* **Archivos:**
  * GeoPackage: [`outputs/entrega_final/Mapa_Escenarios_Riesgo_Abstencion_2027.gpkg`](file:///home/soren_ubuntu/laura/hackaton-ine-reto2/outputs/entrega_final/Mapa_Escenarios_Riesgo_Abstencion_2027.gpkg) (contiene 2 capas: `entidades_2027` y `municipios_2027`).
  * GeoJSON: [`outputs/entrega_final/Mapa_Escenarios_Entidades_2027.geojson`](file:///home/soren_ubuntu/laura/hackaton-ine-reto2/outputs/entrega_final/Mapa_Escenarios_Entidades_2027.geojson) y [`outputs/entrega_final/Mapa_Escenarios_Municipios_2027.geojson`](file:///home/soren_ubuntu/laura/hackaton-ine-reto2/outputs/entrega_final/Mapa_Escenarios_Municipios_2027.geojson).
* **Cómo abrirlos:** Arrastra directamente el archivo `.gpkg` a **QGIS**, **ArcGIS Pro** o súbelos a **Mapbox / Keplar.gl**.

### 6.3. Documentos Oficiales en PDF
* **Reporte Metodológico Oficial (12 cuartillas):** [`outputs/entrega_final/Reporte_Metodologico_y_Preventivo_Reto2_INE.pdf`](file:///home/soren_ubuntu/laura/hackaton-ine-reto2/outputs/entrega_final/Reporte_Metodologico_y_Preventivo_Reto2_INE.pdf)
* **Presentación Ejecutiva (10 láminas para Jurado):** [`outputs/entrega_final/Presentacion_Ejecutiva_10_Diapositivas_Reto2_INE.pdf`](file:///home/soren_ubuntu/laura/hackaton-ine-reto2/outputs/entrega_final/Presentacion_Ejecutiva_10_Diapositivas_Reto2_INE.pdf)

### 6.4. Base de Datos Anonimizada (.XLSX y .CSV)
* **Libro de Excel:** [`outputs/entrega_final/Base_Datos_Anonimizada_Reto2_INE_2027.xlsx`](file:///home/soren_ubuntu/laura/hackaton-ine-reto2/outputs/entrega_final/Base_Datos_Anonimizada_Reto2_INE_2027.xlsx)
  * Pestaña `DICCIONARIO`: Metadatos y definición de variables.
  * Pestaña `RESUMEN_ESCENARIOS`: Comparativa nacional de votos rescatados.
  * Pestaña `SEMAFORO_ESTATAL`: Resumen de las 32 entidades.
  * Pestaña `MUNICIPIOS_2027`: Base completa con los 2,477 municipios clasificados.
  * Pestaña `TOP1000_SECCIONES_CRITICAS`: Priorización micro-territorial de casillas.

---

## 7. Solución de Problemas Comunes (Troubleshooting)

1. **Error: `FileNotFoundError: ../Datos para intregrar BD`**
   * *Causa:* La carpeta con los 194 archivos CSV no se encuentra en la ruta relativa especificada.
   * *Solución:* Abre [`configs/config.toml`](file:///home/soren_ubuntu/laura/hackaton-ine-reto2/configs/config.toml) y coloca la ruta absoluta exacta donde guardaste la carpeta de datos.
2. **El mapa interactivo muestra error de conexión:**
   * *Causa:* El mapa utiliza teselas ligeras de CartoDB Positron y Esri que requieren conexión a Internet la primera vez que se cargan en el navegador.
   * *Solución:* Asegúrate de tener conexión a Internet al abrir el HTML para que descargue el lienzo cartográfico base.
3. **Memoria insuficiente durante la ingesta:**
   * *Causa:* Ejecutar el pipeline en una máquina con menos de 4 GB de RAM disponibles.
   * *Solución:* El loader utiliza Polars con motor de streaming (`engine="streaming"`), optimizado para procesar grandes volúmenes en lotes pequeños sin saturar la memoria RAM.

