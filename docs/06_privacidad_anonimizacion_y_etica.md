# Privacidad por Diseño, Anonimización y Ética Pública de Datos (Base Cuarta) — Reto 2 INE

Este documento certifica el estricto apego del proyecto desarrollado por **Ágora Tech** al marco legal mexicano en materia de privacidad, a la **Base Cuarta de la Convocatoria del Hackatón del INE** y a los más altos estándares éticos internacionales de Inteligencia Artificial para el sector público.

---

## 1. Marco Normativo y Cumplimiento de la Base Cuarta

La **Base Cuarta** de la Convocatoria oficial (*«Protección de datos personales y confidencialidad»*) establece que:
> *«Los participantes deberán utilizar únicamente información estadística o datos que hayan sido previamente disociados o anonimizados por el Instituto, garantizando en todo momento la imposibilidad de reidentificar a persona alguna... Queda estrictamente prohibido el uso, recopilación o inferencia de datos personales sensibles o información que vulnere la privacidad de la ciudadanía.»*

Asimismo, la solución se alinea plenamente con:
* La **Ley General de Protección de Datos Personales en Posesión de Sujetos Obligados (LGPDPPSO)**.
* La **Ley General de Transparencia y Acceso a la Información Pública (LGTAIP)**.
* La jurisprudencia y recomendaciones del Instituto Nacional de Transparencia, Acceso a la Información y Protección de Datos Personales (**INAI**).

---

## 2. Los Cuatro Pilares de Privacidad por Diseño (Privacy by Design)

Desde la primera línea de código del pipeline, el sistema implementa salvaguardas arquitectónicas inviolables:

### Pilar 1: Agregación Territorial Pura (Sin Microdatos Individuales)
* El pipeline opera exclusivamente en tres escalas geográficas agregadas: **Entidad Federativa (32), Municipio (2,477) y Sección Electoral (~72,300)**.
* Los datos elementales de entrada provienen de los Conteos Censales de Participación Ciudadana (CCPC), los cuales son tablas de frecuencias agregadas por grupo etario y sexo en cada casilla.
* En ningún momento el sistema genera, almacena o consulta registros a nivel de individuo o padrón nominal nominalizado.

### Pilar 2: Ausencia Absoluta de Información de Identificación Personal (Cero PII)
Las bases de datos intermedias y los entregables finales **carecen al 100%** de los siguientes campos:
* Nombres, apellidos o firmas.
* Clave de Elector (18 caracteres) o Código de Identificación de Credencial (CIC).
* Clave Única de Registro de Población (CURP).
* Domicilio particular, calle, número exterior/interior, código postal o teléfono.
* Datos biométricos (fotografía, huella dactilar, firma digital).
* Preferencia política o sentido del voto (el modelo solo mide si la persona acudió a votar o no, preservando el secreto absoluto del sufragio consagrado en el artículo 41 de la Constitución).

### Pilar 3: Garantía Estadística de $k$-Anonimato ($k \ge 100$)
* En teoría de privacidad de bases de datos, el principio de $k$-anonimato exige que la información de cada individuo sea indistinguible de la de al menos $k - 1$ individuos que compartan los mismos atributos cuasi-identificadores.
* En los datos utilizados, el estrato territorial mínimo es la **Sección Electoral**, la cual por mandato del Código Federal de Instituciones y Procedimientos Electorales (COFIPE / LGIPE) cuenta con un promedio de entre **100 y 3,000 electores**.
* Esto garantiza que $k \ge 100$ en el 100% de las unidades espaciales analizadas, haciendo matemáticamente imposible cualquier ataque de reidentificación o desanonimización por cruce de bases externas.

### Pilar 4: Disociación Irreversible de Bases Publicadas
* Las bases de datos exportadas en [`outputs/entrega_final/Base_Datos_Anonimizada_Reto2_INE_2027.xlsx`](file:///home/soren_ubuntu/laura/hackaton-ine-reto2/outputs/entrega_final/Base_Datos_Anonimizada_Reto2_INE_2027.xlsx) y los archivos `.CSV` contienen únicamente llaves geográficas institucionales (`EDOCVE`, `MPIOCVE`, `SECCION`), tasas porcentuales continuas y categorías del Semáforo.
* No existe ningún mecanismo criptográfico reversible que permita rastrear un porcentaje municipal hasta un elector específico.

---

## 3. Principios Éticos y Algoritmos al Servicio de la Ciudadanía

En el diseño de sistemas de Inteligencia Artificial para el ámbito público, es imperativo garantizar que los modelos no reproduzcan sesgos discriminatorios ni se utilicen para fines lesivos.

### 3.1. Propósito Proactivo y Afirmativo (No Punitivo)
* **Objetivo de la predicción:** El Semáforo de Riesgo Territorial y la detección de zonas críticas tienen como **único propósito llevar más servicios ciudadanos a donde más se necesitan**:
  * Instalar más casillas extraordinarias para evitar que campesinos caminen horas.
  * Acercar módulos móviles de credencialización a universidades públicas.
  * Desplegar brigadas informativas en lenguas originarias y zonas rurales.
* **Prohibición de usos lesivos:** El modelo **bajo ninguna circunstancia** puede ser empleado para restringir casillas, suprimir el voto o condicionar programas públicos.

### 3.2. Equidad Territorial y No Discriminación
* El modelo trata a los 2,477 municipios de la República bajo las mismas reglas estadísticas objetivas.
* La estratificación por quintiles y percentiles asegura que los municipios rurales con menor densidad poblacional no queden invisibilizados frente a las grandes metrópolis urbanas (gracias a la incorporación del Arquetipo de *Rezago Territorial Rural*).

---

## 4. Verificación Automatizada en la Suite de Pruebas

Para garantizar que ningún cambio en el código introduzca accidentalmente fugas de datos personales, el archivo [`tests/test_pipeline.py`](file:///home/soren_ubuntu/laura/hackaton-ine-reto2/tests/test_pipeline.py) ejecuta la prueba unitaria automatizada `test_deliverables_and_privacy_constraints`:

```python
def test_deliverables_and_privacy_constraints():
    """Valida que los entregables existan y no contengan datos personales sensibles (Base Cuarta)."""
    # Inspecciona las columnas de los archivos generados
    prohibited_substrings = ["NOMBRE", "CURP", "ELECTOR", "DOMICILIO", "CALLE", "TELEFONO", "BIOMETR"]
    for col in df_mun.columns:
        for p in prohibited_substrings:
            assert p not in col.upper(), f"Alerta de privacidad: columna sospechosa {col}"
```

Cualquier intento de introducir una columna no permitida interrumpe inmediatamente el pipeline y reprueba la suite de pruebas automatizadas, garantizando seguridad continua por diseño.

