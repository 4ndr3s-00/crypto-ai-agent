#!/usr/bin/env python3
"""
Generador automatizado de tareas ultradetalladas para GitHub Issues,
GitHub Projects v2 y archivo de importación para Linear CSV/GraphQL.
"""

import csv
import json
import os
import subprocess
import time

REPO = "4ndr3s-00/crypto-ai-agent"
PROJECT_NUMBER = 2
PROJECT_OWNER = "4ndr3s-00"

TASKS = [
    {
        "id": "US-01",
        "title": "[US-01] Infraestructura Base: MinIO Data Lake y Docker Compose Mínimo",
        "epic": "epic: 1-infra-minio",
        "sprint": "sprint: 1-foundation",
        "milestone": 1,
        "priority": "priority: Must Have",
        "linear_priority": "Urgent",
        "points": "points: 5",
        "story_points": 5,
        "team": "team: Andrés Teherán",
        "assignee": "Andrés Teherán",
        "description": """### 📌 Resumen de la Historia

| Atributo | Detalle |
| :--- | :--- |
| **ID** | US-01 |
| **Épica** | Épica 1: Infraestructura MinIO Data Lake y Docker Compose |
| **Responsable Principal** | Andrés Teherán (DevOps & Data Pipelines Lead) |
| **Sprint / Ciclo** | Sprint 1: Cimientos, Ingesta Real y Lakehouse MinIO + DuckDB |
| **Prioridad** | Must Have (Crítica) |
| **Story Points** | 5 SP |

---

### 📖 Descripción
**Como** Ingeniero de Infraestructura y DevOps,  
**Quiero** configurar un `docker-compose.yml` mínimo y optimizado que levante MinIO S3 junto con un script de inicialización idempotente de buckets (`market-lake`) y credenciales IAM de servicio,  
**Para** proporcionar el lago de almacenamiento duradero para los datos de mercado sin la sobrecarga de Spark, Kafka ni Airflow.

---

### 🔍 Contexto Técnico y Fundamento (Lo Obvio Explicado)
- **Eliminación de bloat:** No se levantan clústeres Spark, ni brokers Kafka, ni ZooKeeper, ni Postgres pesados. Solo MinIO (`cgr.dev/chainguard/minio:latest`) y su inicializador.
- **Puertos:** `9000` (API S3) y `9001` (Consola Web de MinIO).
- **Bucket principal:** `market-lake`.
- **Estructura de prefijos en S3:** `historical/source=binance/symbol={SYMBOL}/date={YYYY-MM-DD}/data.parquet`.
- **Políticas IAM:** Crear usuario de lectura/escritura para ingesta y usuario de solo lectura para el backend/DuckDB.

---

### 🧪 Criterios de Aceptación (BDD)

#### Escenario 1: Inicialización idempotente del Data Lake
- **Dado que** el entorno está limpio o se ejecuta `docker compose up -d`,
- **Cuando** el contenedor `minio-init` termina su ejecución,
- **Entonces** el bucket `market-lake` debe existir, ser accesible en `http://localhost:9000`, y las políticas de acceso de lectura/escritura deben quedar configuradas sin errores.

#### Escenario 2: Persistencia y Healthcheck verificado
- **Dado que** MinIO está corriendo en segundo plano,
- **Cuando** se ejecuta la prueba de salud (`test: ["CMD", "curl", "-f", "http://localhost:9000/minio/health/live"]`),
- **Entonces** el contenedor debe reportar estado `healthy` y los datos deben persistirse en el volumen local `minio_data`.

#### Escenario 3: Verificación de rendimiento y bajo consumo
- **Dado que** el stack de MinIO está encendido,
- **Cuando** se inspecciona el uso de recursos con `docker stats`,
- **Entonces** el consumo total de memoria RAM debe ser inferior a 150 MB (frente a los 6+ GB de la plataforma anterior).

---

### 🛠️ Tareas Técnicas del Equipo
- [ ] Crear archivo `docker-compose.yml` con servicio `minio` y `minio-init` - Andrés Teherán
- [ ] Configurar variables de entorno seguras en `.env.example` y script de inicialización de buckets `infra/minio/init-buckets.sh` - Andrés Teherán
- [ ] Configurar volúmenes duraderos y permisos de carpetas locales - Andrés Teherán
- [ ] Validar conectividad S3 con cliente CLI `mc` o script Python `boto3` - Samuel Roncancio
""",
    },
    {
        "id": "US-02",
        "title": "[US-02] Ingesta Real: Extractor REST de Binance para Klines Históricas",
        "epic": "epic: 2-binance-ingestion",
        "sprint": "sprint: 1-foundation",
        "milestone": 1,
        "priority": "priority: Must Have",
        "linear_priority": "Urgent",
        "points": "points: 8",
        "story_points": 8,
        "team": "team: Samuel Benavidez",
        "assignee": "Samuel Benavidez",
        "description": """### 📌 Resumen de la Historia

| Atributo | Detalle |
| :--- | :--- |
| **ID** | US-02 |
| **Épica** | Épica 2: Ingesta Real de Mercado Binance REST & Parquet |
| **Responsable Principal** | Samuel Benavidez (Realtime Ingestion & Exchange Connectors) |
| **Sprint / Ciclo** | Sprint 1: Cimientos, Ingesta Real y Lakehouse MinIO + DuckDB |
| **Prioridad** | Must Have (Crítica) |
| **Story Points** | 8 SP |

---

### 📖 Descripción
**Como** Desarrollador de Datos de Mercado,  
**Quiero** desarrollar un módulo de extracción REST robusto que consuma la API pública de Binance (`https://data-api.binance.vision` o `https://api.binance.com`), descargando velas de 1 minuto paginadas día a día para símbolos configurados (`BTCUSDT`, `ETHUSDT`, `SOLUSDT`),  
**Para** garantizar la ingesta continua de datos reales de mercado con validación de contrato canónico y cero datos simulados.

---

### 🔍 Contexto Técnico y Fundamento (Lo Obvio Explicado)
- **Cero Mocks:** No inventar precios bajo ninguna circunstancia.
- **Paginación Binance:** Un día tiene 1440 minutos. Como Binance limita a 1000 velas por petición, cada día exige exactamente dos requests paginados usando `startTime` y `endTime` en milisegundos UTC.
- **Rate Limiting:** Respetar el límite de peso de Binance (1200 request weight/min) agregando un retardo controlado de 50 ms entre llamadas y reintentos con retroceso exponencial (`backoff`).
- **Contrato de Datos:** Cada vela cruda `[time, open, high, low, close, volume, close_time, ...]` debe mapearse a un diccionario validado por Pydantic: `event_id`, `symbol`, `timestamp`, `open`, `high`, `low`, `close`, `volume`, `trades_count`.

---

### 🧪 Criterios de Aceptación (BDD)

#### Escenario 1: Extracción exitosa de un día completo de velas 1m
- **Dado que** se solicita extraer las velas del día `2026-11-01` para el par `BTCUSDT`,
- **Cuando** el extractor ejecuta la paginación de endpoints `/api/v3/klines`,
- **Entonces** debe retornar exactamente 1440 registros canónicos validados sin faltantes temporales.

#### Escenario 2: Resiliencia ante desconexiones y rate limits (HTTP 429)
- **Dado que** Binance devuelve un código `429 Too Many Requests` o timeout de red,
- **Cuando** el cliente HTTP procesa la excepción,
- **Entonces** debe aplicar retroceso exponencial (1s, 2s, 4s) hasta 3 reintentos antes de fallar con log estructurado y timestamp exacto.

#### Escenario 3: Detección de duplicados en la ingesta
- **Dado que** se reintenta extraer una fecha ya procesada previamente,
- **Cuando** se generan los eventos,
- **Entonces** el identificador unívoco determinista `binance_{symbol}_{open_time_ms}` debe evitar colisiones y registros repetidos.

---

### 🛠️ Tareas Técnicas del Equipo
- [ ] Crear módulo `ingestion/connectors/binance_rest.py` con métodos `fetch_daily_klines()` y `extract_range()` - Samuel Benavidez
- [ ] Implementar modelo Pydantic v2 `MarketEvent` en `ingestion/schemas.py` con validación estricta de tipos numéricos - Samuel Benavidez
- [ ] Agregar manejo de reintentos con `tenacity` o decorador `backoff` - Samuel Benavidez
- [ ] Crear test unitario `tests/test_binance_extractor.py` con respuestas grabadas de Binance - Samuel Roncancio
""",
    },
    {
        "id": "US-03",
        "title": "[US-03] Almacenamiento Columnar: Escritor de Particiones Parquet hacia MinIO",
        "epic": "epic: 2-binance-ingestion",
        "sprint": "sprint: 1-foundation",
        "milestone": 1,
        "priority": "priority: Must Have",
        "linear_priority": "High",
        "points": "points: 5",
        "story_points": 5,
        "team": "team: Andrés Teherán",
        "assignee": "Andrés Teherán",
        "description": """### 📌 Resumen de la Historia

| Atributo | Detalle |
| :--- | :--- |
| **ID** | US-03 |
| **Épica** | Épica 2: Ingesta Real de Mercado Binance REST & Parquet |
| **Responsable Principal** | Andrés Teherán (DevOps & Data Pipelines Lead) |
| **Sprint / Ciclo** | Sprint 1: Cimientos, Ingesta Real y Lakehouse MinIO + DuckDB |
| **Prioridad** | Must Have (Crítica) |
| **Story Points** | 5 SP |

---

### 📖 Descripción
**Como** Ingeniero de Datos,  
**Quiero** convertir los lotes diarios de eventos de mercado a archivos **Apache Parquet** comprimidos con `Snappy` y subirlos a MinIO mediante `pyarrow` o `fastparquet`,  
**Para** optimizar el almacenamiento del lago de datos, reducir el ancho de banda y permitir consultas analíticas instantáneas por partición de fecha y símbolo.

---

### 🔍 Contexto Técnico y Fundamento (Lo Obvio Explicado)
- **Esquema Hive Particionado:** La ruta en MinIO debe seguir el estándar:  
  `market-lake/historical/source=binance/symbol=BTCUSDT/date=2026-11-01/data.parquet`.
- **Ventajas de Parquet:** Almacenamiento columnar comprimido; en vez de leer JSONs gigantescos de texto plano, Parquet almacena metadatos de mínimos y máximos por bloque, permitiendo filtrar en microsegundos.
- **Idempotencia:** Si un archivo de fecha ya existe, se sobrescribe limpiamente esa partición específica sin afectar al resto del historial.

---

### 🧪 Criterios de Aceptación (BDD)

#### Escenario 1: Conversión y escritura columnar exitosa en MinIO
- **Dado que** el extractor devuelve 1440 eventos validados de un día,
- **Cuando** el módulo `parquet_writer.py` procesa los datos,
- **Entonces** debe generar un archivo Parquet con compresión Snappy y escribirlo en la URI S3 correspondiente en MinIO.

#### Escenario 2: Verificación de compresión y tamaño de archivo
- **Dado que** un día en JSON pesa ~300 KB,
- **Cuando** se convierte a Parquet con compresión Snappy,
- **Entonces** el archivo generado en MinIO no debe superar los 40 KB (reducción > 85%).

#### Escenario 3: Sobrescritura atómica e idempotente
- **Dado que** se re-ejecuta la ingesta para una fecha ya existente,
- **Cuando** finaliza la carga a MinIO,
- **Entonces** solo debe existir un único archivo Parquet válido en la partición y no debe haber duplicación de registros.

---

### 🛠️ Tareas Técnicas del Equipo
- [ ] Desarrollar módulo `ingestion/parquet_writer.py` usando `pyarrow.parquet` y `boto3` - Andrés Teherán
- [ ] Implementar mecanismo de escritura atómica en S3 (upload multipart con reemplazo de clave) - Andrés Teherán
- [ ] Implementar script de catch-up automático `ingestion/catchup_historical.py` que detecte días faltantes y los complete - Andrés Teherán
- [ ] Test de lectura e integridad del Parquet generado contra MinIO - Samuel Roncancio
""",
    },
    {
        "id": "US-04",
        "title": "[US-04] Motor OLAP Embebido: Configuración y Optimización de DuckDB con S3/MinIO",
        "epic": "epic: 3-duckdb-olap",
        "sprint": "sprint: 1-foundation",
        "milestone": 1,
        "priority": "priority: Must Have",
        "linear_priority": "Urgent",
        "points": "points: 8",
        "story_points": 8,
        "team": "team: Andrés Blanco",
        "assignee": "Andrés Blanco",
        "description": """### 📌 Resumen de la Historia

| Atributo | Detalle |
| :--- | :--- |
| **ID** | US-04 |
| **Épica** | Épica 3: Motor Analítico OLAP DuckDB sobre MinIO S3 |
| **Responsable Principal** | Andrés Blanco (Big Data Architect & OLAP Lead) |
| **Sprint / Ciclo** | Sprint 1: Cimientos, Ingesta Real y Lakehouse MinIO + DuckDB |
| **Prioridad** | Must Have (Crítica) |
| **Story Points** | 8 SP |

---

### 📖 Descripción
**Como** Arquitecto de Datos y Rendimiento,  
**Quiero** configurar el motor OLAP embebido **DuckDB** dentro del servicio backend, habilitando la extensión `httpfs` conectada al MinIO local con endpoint S3,  
**Para** sustituir la pesada infraestructura de Spark y permitir consultas analíticas SQL directamente sobre los archivos Parquet en el lago con latencia inferior a 50 ms.

---

### 🔍 Contexto Técnico y Fundamento (Lo Obvio Explicado)
- **Por qué DuckDB reemplaza a Spark:** Spark requiere JVM, asignación de memoria estática (2-4GB) y comunicación entre master y workers. DuckDB es un motor OLAP columnar en C++ embebido en el proceso Python; lee archivos Parquet vía HTTP S3 (`httpfs`) paralelizando hilos nativos sin sobrecarga de red interna.
- **Configuraciones S3 de DuckDB:**
  ```sql
  INSTALL httpfs; LOAD httpfs;
  SET s3_endpoint='localhost:9000';
  SET s3_use_ssl=false;
  SET s3_url_style='path';
  SET s3_access_key_id='minioadmin';
  SET s3_secret_access_key='miniopassword123';
  ```
- **Pool de Conexiones:** Manejar conexiones DuckDB en modo solo lectura (`read_only=True`) para concurrencia segura sin bloqueos de archivo.

---

### 🧪 Criterios de Aceptación (BDD)

#### Escenario 1: Conexión y consulta exitosa a Parquet en MinIO
- **Dado que** MinIO contiene particiones Parquet de `BTCUSDT` de los últimos 30 días,
- **Cuando** DuckDB ejecuta `SELECT count(*) FROM read_parquet('s3://market-lake/historical/source=binance/symbol=BTCUSDT/*/*.parquet')`,
- **Entonces** debe retornar el recuento exacto de registros en menos de 50 milisegundos.

#### Escenario 2: Resiliencia ante particiones inexistentes
- **Dado que** se consulta un símbolo que no tiene datos en MinIO (ej. `ADAUSDT`),
- **Cuando** DuckDB intenta evaluar el glob S3,
- **Entonces** el cliente debe interceptar la excepción de archivo no encontrado y devolver un resultado vacío controlado (`count = 0`) sin tumbar el proceso.

#### Escenario 3: Concurrencia de múltiples hilos
- **Dado que** 10 peticiones simultáneas consultan DuckDB sobre MinIO,
- **Cuando** se ejecutan en paralelo,
- **Entonces** ninguna petición debe lanzar error de bloqueo (`database is locked`) y la latencia promedio debe mantenerse por debajo de 80 ms.

---

### 🛠️ Tareas Técnicas del Equipo
- [ ] Desarrollar `backend/app/database/duckdb_client.py` con singleton y configuración S3/httpfs - Andrés Blanco
- [ ] Implementar pool de conexiones con context manager seguro (`get_duckdb_connection()`) - Andrés Blanco
- [ ] Validar soporte de proyecciones y filtros por fecha (Partition Pruning en DuckDB) - Andrés Blanco
- [ ] Crear tests de rendimiento y latencia en `tests/test_duckdb_queries.py` - Samuel Roncancio
""",
    },
    {
        "id": "US-05",
        "title": "[US-05] Servicios Analíticos: Métricas Agregadas en Tiempo Récord (VWAP, Retornos, Volatilidad)",
        "epic": "epic: 3-duckdb-olap",
        "sprint": "sprint: 1-foundation",
        "milestone": 1,
        "priority": "priority: Must Have",
        "linear_priority": "High",
        "points": "points: 5",
        "story_points": 5,
        "team": "team: Andrés Blanco",
        "assignee": "Andrés Blanco",
        "description": """### 📌 Resumen de la Historia

| Atributo | Detalle |
| :--- | :--- |
| **ID** | US-05 |
| **Épica** | Épica 3: Motor Analítico OLAP DuckDB sobre MinIO S3 |
| **Responsable Principal** | Andrés Blanco (Big Data Architect & OLAP Lead) |
| **Sprint / Ciclo** | Sprint 1: Cimientos, Ingesta Real y Lakehouse MinIO + DuckDB |
| **Prioridad** | Must Have (Crítica) |
| **Story Points** | 5 SP |

---

### 📖 Descripción
**Como** Analista Cuantitativo de Datos,  
**Quiero** implementar consultas analíticas vectorizadas en DuckDB que calculen métricas clave de mercado (precio de cierre, retorno porcentual 24h, VWAP ponderado por volumen, varianza y rango máximo/mínimo) en ventanas temporales configurables (`1h`, `4h`, `24h`, `7d`),  
**Para** alimentar instantáneamente las herramientas del agente y los componentes del dashboard con cálculos matemáticos precisos.

---

### 🔍 Contexto Técnico y Fundamento (Lo Obvio Explicado)
- **Cálculo del VWAP (Volume Weighted Average Price):**
  $$\text{VWAP} = \frac{\sum (\text{Price} \times \text{Volume})}{\sum \text{Volume}}$$
- **Retorno 24h:**
  $$\text{Return} = \frac{\text{Close}_{\text{actual}} - \text{Close}_{24h}}{\text{Close}_{24h}} \times 100$$
- **Re-muestreo Temporal (Downsampling):** DuckDB permite agrupar datos de 1 minuto a velas de 15m, 1h o 1d usando funciones de fecha nativas: `date_trunc('hour', timestamp)` de forma instantánea.

---

### 🧪 Criterios de Aceptación (BDD)

#### Escenario 1: Cálculo exacto de métricas en ventana de 24 horas
- **Dado que** existen datos de `ETHUSDT` de las últimas 24 horas en MinIO,
- **Cuando** se invoca `get_metrics(symbol='ETHUSDT', window='24h')`,
- **Entonces** debe retornar un diccionario con: `current_price`, `return_24h`, `volume_24h`, `vwap`, `high_24h`, `low_24h`, todos calculados con precisión flotante de 64 bits.

#### Escenario 2: Re-muestreo de series de tiempo para gráficos
- **Dado que** se solicitan velas de 1 hora para los últimos 7 días (168 velas),
- **Cuando** DuckDB ejecuta la agregación OHLCV,
- **Entonces** debe devolver exactamente 168 objetos `Candle` ordenados cronológicamente sin huecos temporales.

#### Escenario 3: Tiempo de respuesta del cálculo analítico
- **Dado que** la consulta abarca más de 100,000 registros de velas de 1 minuto,
- **Cuando** DuckDB procesa el cálculo analítico,
- **Entonces** el tiempo total de ejecución debe ser inferior a 35 milisegundos.

---

### 🛠️ Tareas Técnicas del Equipo
- [ ] Implementar queries de agregación OHLCV e indicadores en `backend/app/database/queries.py` - Andrés Blanco
- [ ] Añadir métodos `query_ohlcv_resampled()` y `query_financial_metrics()` - Andrés Blanco
- [ ] Implementar tests unitarios comparando cálculos de DuckDB con resultados conocidos - Diego
- [ ] Benchmark de consumo de memoria en consultas analíticas masivas - Samuel Roncancio
""",
    },
    {
        "id": "US-06",
        "title": "[US-06] Servidor Backend FastAPI: Arquitectura Modular, Modelos Pydantic v2 y Configuración",
        "epic": "epic: 4-ai-agent-groq",
        "sprint": "sprint: 2-agent-guardrails",
        "milestone": 2,
        "priority": "priority: Must Have",
        "linear_priority": "High",
        "points": "points: 5",
        "story_points": 5,
        "team": "team: Sebastián",
        "assignee": "Sebastián",
        "description": """### 📌 Resumen de la Historia

| Atributo | Detalle |
| :--- | :--- |
| **ID** | US-06 |
| **Épica** | Épica 4: Cerebro del Agente IA Inferencia Groq & Ollama |
| **Responsable Principal** | Sebastián (AI Engineer & LLM Specialist) |
| **Sprint / Ciclo** | Sprint 2: Cerebro del Agente IA y Motor Anti-Alucinación |
| **Prioridad** | Must Have (Crítica) |
| **Story Points** | 5 SP |

---

### 📖 Descripción
**Como** Desarrollador Backend,  
**Quiero** estructurar la aplicación FastAPI modular con Pydantic v2 Settings, middlewares de CORS seguros, contratos de datos estrictos (`ChatRequest`, `ChatResponse`, `ChatChart`, `ReportSpec`) y endpoints de salud (`/health`, `/api/chat`, `/api/market/*`),  
**Para** proporcionar la API REST y SSE de alto rendimiento que comunicará al agente con el frontend.

---

### 🔍 Contexto Técnico y Fundamento (Lo Obvio Explicado)
- **FastAPI + Uvicorn:** Permite manejar miles de peticiones asíncronas con bajísima latencia.
- **Pydantic v2:** Validación C-Rust (`pydantic-core`) 10x más rápida que Pydantic v1.
- **Configuración centralizada (`config.py`):** Carga claves de API (`GROQ_API_KEY`, credenciales MinIO, URLs de Ollama) validando tipos en el arranque de la app.
- **CORS:** Configuración explícita para el origen del frontend Next.js (`http://localhost:3000`).

---

### 🧪 Criterios de Aceptación (BDD)

#### Escenario 1: Arranque y verificación del endpoint de salud
- **Dado que** el backend FastAPI está levantado en `http://localhost:8000`,
- **Cuando** se realiza un `GET /health`,
- **Entonces** debe responder en menos de 5 ms con estado `200 OK`, listando el estado de conectividad con MinIO, DuckDB y Groq.

#### Escenario 2: Validación estricta de esquemas de entrada
- **Dado que** un cliente envía un payload con campos extras no permitidos o tipos incorrectos,
- **Cuando** Pydantic v2 evalúa el request (`extra="forbid"`),
- **Entonces** debe retornar un código `422 Unprocessable Entity` con el detalle del campo erróneo sin ejecutar código downstream.

#### Escenario 3: Documentación OpenAPI generada automáticamente
- **Dado que** se consulta `http://localhost:8000/docs`,
- **Cuando** se carga la interfaz Swagger,
- **Entonces** todos los modelos, contratos de chat, gráficos y reportes deben estar correctamente tipados y documentados.

---

### 🛠️ Tareas Técnicas del Equipo
- [ ] Crear estructura base en `backend/app/main.py` y `backend/app/config.py` - Sebastián
- [ ] Definir modelos Pydantic v2 en `backend/app/models.py` (`ChatRequest`, `ChatResponse`, `ChatChart`) - Sebastián
- [ ] Configurar middleware de CORS y manejo global de excepciones - Sebastián
- [ ] Test unitario de validación de modelos y endpoint `/health` - Samuel Roncancio
""",
    },
    {
        "id": "US-07",
        "title": "[US-07] Orquestación de Inferencia: Cliente Groq (Llama-3.3-70b) con Fallback a Ollama Local",
        "epic": "epic: 4-ai-agent-groq",
        "sprint": "sprint: 2-agent-guardrails",
        "milestone": 2,
        "priority": "priority: Must Have",
        "linear_priority": "Urgent",
        "points": "points: 8",
        "story_points": 8,
        "team": "team: Sebastián",
        "assignee": "Sebastián",
        "description": """### 📌 Resumen de la Historia

| Atributo | Detalle |
| :--- | :--- |
| **ID** | US-07 |
| **Épica** | Épica 4: Cerebro del Agente IA Inferencia Groq & Ollama |
| **Responsable Principal** | Sebastián (AI Engineer & LLM Specialist) |
| **Sprint / Ciclo** | Sprint 2: Cerebro del Agente IA y Motor Anti-Alucinación |
| **Prioridad** | Must Have (Crítica) |
| **Story Points** | 8 SP |

---

### 📖 Descripción
**Como** Ingeniero de IA,  
**Quiero** implementar el cliente de inferencia de ultrabaja latencia con **Groq Cloud** utilizando el modelo `llama-3.3-70b-versatile`, con capacidad de Function Calling y fallback automático a **Ollama local** (`qwen2.5-coder:7b`),  
**Para** obtener respuestas analíticas complejas en menos de 800 ms y mantener resiliencia operativa offline si la API externa no está disponible.

---

### 🔍 Contexto Técnico y Fundamento (Lo Obvio Explicado)
- **Por qué Groq:** Los procesadores LPU (Language Processing Units) de Groq alcanzan entre 300 y 500 tokens por segundo. Una consulta analítica promedio se completa en 300-600 ms, vital para generar gráficos y reportes en segundos.
- **Por qué Fallback a Ollama:** Si no hay internet, se agota la cuota de Groq o hay fallo de red, el sistema cambia limpiamente a Ollama sin lanzar error 500 al usuario.
- **Loop de Function Calling:** El LLM recibe la pregunta del usuario junto con las definiciones de herramientas (`tools`). Si decide ejecutar una herramienta, emite un `tool_call`, el backend ejecuta la herramienta de inmediato y le reinyecta el resultado para que redacte la conclusión. Máximo 3 iteraciones para evitar bucles.

---

### 🧪 Criterios de Aceptación (BDD)

#### Escenario 1: Inferencia subsegundo con Groq y Function Calling
- **Dado que** se envía una consulta analítica ("¿Cuál es el precio y volumen de BTC hoy?"),
- **Cuando** el orquestador invoca Groq con herramientas autorizadas,
- **Entonces** el modelo debe invocar `query_metrics`, recibir los datos reales y emitir la respuesta final con latencia total inferior a 800 ms.

#### Escenario 2: Conmutación transparente a fallback Ollama
- **Dado que** la variable `GROQ_API_KEY` es inválida o Groq devuelve un error `429/500`,
- **Cuando** se detecta la excepción `GroqUnavailable`,
- **Entonces** el sistema conmuta automáticamente a Ollama local registrando un warning y completando la respuesta exitosamente.

#### Escenario 3: Fallback determinista final
- **Dado que** ni Groq ni Ollama responden,
- **Cuando** se agota el tiempo de espera,
- **Entonces** el sistema debe recurrir al fallback determinista local (resumen estadístico directo de la tool) garantizando que el usuario jamás reciba un error 500.

---

### 🛠️ Tareas Técnicas del Equipo
- [ ] Desarrollar `backend/app/agent/llm_service.py` con métodos `_run_groq()` y `_run_ollama()` - Sebastián
- [ ] Implementar el bucle de ejecución de Function Calling con límite de 3 saltos - Sebastián
- [ ] Diseñar el System Prompt en `backend/app/agent/prompts.py` con directrices de síntesis analítica y tono profesional Arca - Sebastián
- [ ] Crear tests de integración simulando caídas de API externa - Samuel Roncancio
""",
    },
    {
        "id": "US-08",
        "title": "[US-08] Herramientas Tipadas de Solo Lectura: Function Calling para Consultas DuckDB y Binance Live",
        "epic": "epic: 4-ai-agent-groq",
        "sprint": "sprint: 2-agent-guardrails",
        "milestone": 2,
        "priority": "priority: Must Have",
        "linear_priority": "Urgent",
        "points": "points: 8",
        "story_points": 8,
        "team": "team: Sebastián",
        "assignee": "Sebastián",
        "description": """### 📌 Resumen de la Historia

| Atributo | Detalle |
| :--- | :--- |
| **ID** | US-08 |
| **Épica** | Épica 4: Cerebro del Agente IA Inferencia Groq & Ollama |
| **Responsable Principal** | Sebastián (AI Engineer & LLM Specialist) |
| **Sprint / Ciclo** | Sprint 2: Cerebro del Agente IA y Motor Anti-Alucinación |
| **Prioridad** | Must Have (Crítica) |
| **Story Points** | 8 SP |

---

### 📖 Descripción
**Como** Desarrollador del Agente de IA,  
**Quiero** exponer un registro de herramientas (`ToolRegistry`) de solo lectura con tipado estricto (`query_metrics`, `query_timeseries`, `get_market_overview`), conectadas a DuckDB sobre MinIO y al cliente directo de Binance en vivo,  
**Para** permitir que el modelo extraiga información empírica real de mercado sin acceso a shell, sistema de archivos ni sentencias DDL/DML.

---

### 🔍 Contexto Técnico y Fundamento (Lo Obvio Explicado)
- **Aislamiento Absoluto:** El LLM no escribe SQL crudo directamente en la base de datos; invoca funciones Python tipadas con argumentos validados por Pydantic (`symbol`, `window`, `interval`, `limit`).
- **Resolución Dual:**
  1. Si se piden métricas en tiempo real de los últimos minutos: se consulta el cliente Binance Live (`exchange_client`).
  2. Si se piden métricas históricas, promedios, tendencias o agregaciones semanales: se consulta DuckDB leyendo Parquet en MinIO.
- **Estructura del ToolResult:** Toda herramienta retorna: `name`, `arguments`, `payload`, `summary`, `source`, `cutoff_time`, `provenance`, `ok` y `error`.

---

### 🧪 Criterios de Aceptación (BDD)

#### Escenario 1: Ejecución exitosa de tool `query_metrics`
- **Dado que** el LLM decide invocar `query_metrics` con argumentos `{"symbol": "BTCUSDT", "window": "24h"}`,
- **Cuando** el `ToolRegistry` despacha la ejecución,
- **Entonces** debe retornar los datos validados con `source="binance_live"` o `"minio_parquet"` y la marca de tiempo `cutoff_time` en formato ISO 8601 UTC.

#### Escenario 2: Bloqueo de herramientas no registradas o parámetros inválidos
- **Dado que** el modelo intenta invocar una función inexistente (ej. `drop_table` o `execute_shell`),
- **Cuando** el registry valida la llamada,
- **Entonces** debe rechazar la ejecución con error `"herramienta no autorizada"` y reportar `ok=False` de inmediato.

#### Escenario 3: Tiempo de ejecución de herramientas
- **Dado que** se invoca `query_timeseries` con límite de 96 velas,
- **Cuando** se ejecuta la consulta hacia DuckDB o el exchange,
- **Entonces** la herramienta debe retornar su payload en menos de 100 milisegundos.

---

### 🛠️ Tareas Técnicas del Equipo
- [ ] Desarrollar `backend/app/agent/tools.py` con decoradores de tipado y `TOOL_SPECS` - Sebastián
- [ ] Integrar herramientas con el cliente DuckDB y cliente Binance Live - Andrés Blanco
- [ ] Implementar serialización segura de payloads numéricos (evitar floats infinitos o NaN) - Sebastián
- [ ] Tests unitarios de validación de parámetros en `tests/test_agent_tools.py` - Samuel Roncancio
""",
    },
    {
        "id": "US-09",
        "title": "[US-09] Router Semántico Local: Clasificación de Intenciones y Filtro de Dominio",
        "epic": "epic: 5-anti-hallucination",
        "sprint": "sprint: 2-agent-guardrails",
        "milestone": 2,
        "priority": "priority: Must Have",
        "linear_priority": "High",
        "points": "points: 5",
        "story_points": 5,
        "team": "team: Sebastián",
        "assignee": "Sebastián",
        "description": """### 📌 Resumen de la Historia

| Atributo | Detalle |
| :--- | :--- |
| **ID** | US-09 |
| **Épica** | Épica 5: Sistema de Integridad Factual y Guardrails |
| **Responsable Principal** | Sebastián (AI Engineer & LLM Specialist) |
| **Sprint / Ciclo** | Sprint 2: Cerebro del Agente IA y Motor Anti-Alucinación |
| **Prioridad** | Must Have (Crítica) |
| **Story Points** | 5 SP |

---

### 📖 Descripción
**Como** Ingeniero de Seguridad y Optimización de LLM,  
**Quiero** implementar un enrutador semántico local (`SemanticRouter`) basado en embeddings ligeros o reglas de similitud de coseno,  
**Para** clasificar la intención del usuario (saludos, despedidas, preguntas de catálogo o consultas analíticas) y rechazar preguntas fuera de dominio en menos de 5 ms sin enviar llamadas innecesarias al modelo de lenguaje.

---

### 🔍 Contexto Técnico y Fundamento (Lo Obvio Explicado)
- **Ahorro de Costos y Latencia:** Saludos como "Hola", "¿Quién eres?", "Gracias", o preguntas fuera de alcance como "¿Cómo cocinar pizza?", se responden con plantillas deterministas pre-compiladas sin gastar tokens ni tiempo de inferencia en Groq.
- **Filtro Fuera de Dominio (Domain Guardrail):** Si la consulta no tiene relación alguna con mercado crypto, datos financieros o el sistema, se devuelve un mensaje cortés explicando el alcance del asistente.
- **Caché de Embeddings:** Los vectores de prototipos de intenciones se calculan una sola vez al iniciar la aplicación.

---

### 🧪 Criterios de Aceptación (BDD)

#### Escenario 1: Enrutamiento instantáneo de saludos y despedidas
- **Dado que** el usuario escribe "Hola, buenos días",
- **Cuando** el router semántico analiza el texto,
- **Entonces** debe clasificarlo como `greeting`, devolver la respuesta predefinida y reportar latencia inferior a 5 milisegundos.

#### Escenario 2: Bloqueo de preguntas fuera de dominio
- **Dado que** el usuario pregunta "¿Cuál es la capital de Francia?",
- **Cuando** el router evalúa la similitud contra el espacio de mercado crypto,
- **Entonces** debe clasificarlo como `out_of_scope` y devolver la respuesta de guardrail sin tocar la base de datos ni invocar a Groq.

#### Escenario 3: Paso transparente a consultas analíticas
- **Dado que** el usuario pregunta "¿Cómo está el precio de Solana?",
- **Cuando** el router identifica una consulta analítica de mercado,
- **Entonces** debe derivar la petición inmediatamente al orquestador del agente (`decision.kind == 'analytics'`).

---

### 🛠️ Tareas Técnicas del Equipo
- [ ] Desarrollar `backend/app/agent/semantic_router.py` con prototipos de intención - Sebastián
- [ ] Configurar caché de embeddings local y función de similitud de coseno vectorizada - Sebastián
- [ ] Definir respuestas canónicas en español e inglés sin emojis - Sebastián
- [ ] Crear suite de pruebas de clasificación con 50 frases en `tests/test_semantic_router.py` - Samuel Roncancio
""",
    },
    {
        "id": "US-10",
        "title": "[US-10] Sistema Anti-Alucinación: Zero-Mock, Fact-Checking y Trazabilidad Obligatoria de Fuentes",
        "epic": "epic: 5-anti-hallucination",
        "sprint": "sprint: 2-agent-guardrails",
        "milestone": 2,
        "priority": "priority: Must Have",
        "linear_priority": "Urgent",
        "points": "points: 8",
        "story_points": 8,
        "team": "team: Diego",
        "assignee": "Diego",
        "description": """### 📌 Resumen de la Historia

| Atributo | Detalle |
| :--- | :--- |
| **ID** | US-10 |
| **Épica** | Épica 5: Sistema de Integridad Factual y Guardrails |
| **Responsable Principal** | Diego (Quantitative Analyst & Data Governance Lead) |
| **Sprint / Ciclo** | Sprint 2: Cerebro del Agente IA y Motor Anti-Alucinación |
| **Prioridad** | Must Have (Crítica) |
| **Story Points** | 8 SP |

---

### 📖 Descripción
**Como** Oficial de Integridad Factual y Riesgo de Datos,  
**Quiero** implementar un pipeline de verificación anti-alucinación que contraste cada cifra emitida en la respuesta del modelo contra los datos reales devueltos por las herramientas, inyectando metadatos obligatorios de trazabilidad (`source`, `cutoff_time`, `disclaimer`),  
**Para** garantizar que el agente jamás invente precios, retornos o estadísticas falsas bajo ninguna circunstancia.

---

### 🔍 Contexto Técnico y Fundamento (Lo Obvio Explicado)
- **Directivas estrictas del System Prompt:** Prohibición absoluta de inferir o adivinar números. Si los datos no están disponibles en la herramienta, el agente debe declarar explícitamente: "No se cuenta con información en el sistema para ese rango".
- **Fact-Checking Pass (Paso de Verificación Factual):** Un analizador sintáctico revisa los números clave en el texto final generado (ej. `$68,450.20`) y verifica que existan dentro del payload devuelto por `ToolResult`. Si hay discrepancia o alucinación, se reemplaza por el resumen estructurado determinista.
- **Descargo de Responsabilidad Obligatorio:** Toda respuesta lleva el pie: `"Información exclusivamente referencial con fines analíticos. No constituye asesoramiento financiero ni recomendación de inversión."`

---

### 🧪 Criterios de Aceptación (BDD)

#### Escenario 1: Detección y prevención de cifras inventadas
- **Dado que** el LLM intenta generar un precio que no figura en los datos de la herramienta,
- **Cuando** el validador anti-alucinación audita la respuesta,
- **Entonces** debe detectar la anomalía y conmutar inmediatamente al resumen determinista verificado de la herramienta.

#### Escenario 2: Comportamiento ante datos vacíos o caída de exchange
- **Dado que** Binance no responde o el bucket de MinIO está vacío para un activo solicitado,
- **Cuando** el agente procesa la solicitud,
- **Entonces** debe responder informando que los datos no están disponibles en la fuente real, reportar `data_source="no_data_available"` y jamás generar datos de relleno.

#### Escenario 3: Metadatos de linaje y corte temporal presentes
- **Dado que** una respuesta exitosa es enviada al frontend,
- **Cuando** se inspecciona el JSON `ChatResponse`,
- **Entonces** debe incluir obligatoriamente los campos: `source`, `cutoff_time`, `disclaimer`, `provenance` y el registro completo de `tool_calls`.

---

### 🛠️ Tareas Técnicas del Equipo
- [ ] Implementar módulo de validación factual `backend/app/agent/anti_hallucination.py` - Diego
- [ ] Desarrollar verificador de concordancia numérica entre texto y payload - Diego
- [ ] Configurar inyección de disclaimer legal y metadatos de linaje en `ChatResponse` - Diego
- [ ] Crear tests con casos de intento de inducción de alucinación en `tests/test_anti_hallucination.py` - Samuel Roncancio
""",
    },
    {
        "id": "US-11",
        "title": "[US-11] Generador de Especificaciones de Gráficos (ChartSpec) en Milisegundos",
        "epic": "epic: 6-chart-generation",
        "sprint": "sprint: 3-charts-frontend",
        "milestone": 3,
        "priority": "priority: Must Have",
        "linear_priority": "Urgent",
        "points": "points: 8",
        "story_points": 8,
        "team": "team: Camilo",
        "assignee": "Camilo",
        "description": """### 📌 Resumen de la Historia

| Atributo | Detalle |
| :--- | :--- |
| **ID** | US-11 |
| **Épica** | Épica 6: Generador Instantáneo de Diagramas y Gráficos |
| **Responsable Principal** | Camilo (Frontend Lead & Data Visualization) |
| **Sprint / Ciclo** | Sprint 3: Gráficos Instantáneos y Frontend Next.js 15 |
| **Prioridad** | Must Have (Crítica) |
| **Story Points** | 8 SP |

---

### 📖 Descripción
**Como** Ingeniero de Visualización y Experiencia de Usuario,  
**Quiero** desarrollar un generador de especificaciones de gráficos (`chart_builder.py`) que transforme los resultados de DuckDB y Binance en objetos `ChatChart` normalizados (velas japonesas OHLCV, líneas de tendencia, volumen y medias móviles),  
**Para** permitir que el agente devuelva diagramas interactivos listos para ser renderizados por el frontend en menos de 2 segundos desde que el usuario hace la pregunta.

---

### 🔍 Contexto Técnico y Fundamento (Lo Obvio Explicado)
- **El reto de latencia:** Para cumplir con la exigencia de gráficos en "segundos", el backend no genera imágenes pesadas en el servidor ni screenshots. Genera una estructura JSON compacta y tipada que el cliente procesa en Canvas WebGL a 60 FPS en menos de 10 ms.
- **Tipos de Gráficos soportados:**
  - `candlestick`: Velas japonesas con Open, High, Low, Close y timestamp.
  - `volume_histogram`: Barras de volumen por debajo de las velas.
  - `line_metric`: Gráfico de línea para seguimiento continuo de precio o VWAP.
  - `distribution_bar`: Comparación de volumen o retornos entre múltiples activos.
- **Estructura del Chart Payload:**
  ```json
  {
    "symbol": "BTCUSDT",
    "interval": "1h",
    "chart_type": "candlestick",
    "candles": [{"time": 1700000000, "open": 68000, "high": 68500, "low": 67800, "close": 68300, "volume": 1200}],
    "indicators": {"vwap": 68150.0, "return_pct": 2.15}
  }
  ```

---

### 🧪 Criterios de Aceptación (BDD)

#### Escenario 1: Construcción automática de chart ante consulta de precios
- **Dado que** el usuario pregunta "¿Cómo ha variado el precio de BTC en las últimas 24 horas?",
- **Cuando** el agente finaliza la ejecución de las herramientas,
- **Entonces** el campo `chart` en `ChatResponse` no debe ser nulo y debe contener la serie completa de velas ordenadas por tiempo.

#### Escenario 2: Sanitización y validación de tipos numéricos
- **Dado que** los datos provienen de DuckDB,
- **Cuando** el ensamblador genera el array de velas,
- **Entonces** cada valor de precio y volumen debe ser un flotante finito válido (sin strings, NaN ni None) y los timestamps deben ser enteros Unix o ISO 8601 UTC.

#### Escenario 3: Tiempo total de construcción del chart
- **Dado que** la serie contiene hasta 168 velas (7 días en 1h),
- **Cuando** `chart_builder.py` procesa y serializa el payload,
- **Entonces** el tiempo de ensamblado no debe superar los 15 milisegundos.

---

### 🛠️ Tareas Técnicas del Equipo
- [ ] Implementar módulo `backend/app/agent/chart_builder.py` - Camilo
- [ ] Definir contratos Pydantic v2 para `ChatChart`, `CandlePoint`, `IndicatorOverlay` - Camilo
- [ ] Agregar soporte para overlays de indicadores (medias móviles EMA 20/50 y VWAP) - Diego
- [ ] Tests unitarios de integridad y serialización de charts en `tests/test_chart_builder.py` - Samuel Roncancio
""",
    },
    {
        "id": "US-12",
        "title": "[US-12] Motor Cuantitativo de Reportes Financieros Ejecutivos (Markdown & Exportación)",
        "epic": "epic: 7-reports-quant",
        "sprint": "sprint: 3-charts-frontend",
        "milestone": 3,
        "priority": "priority: Should Have",
        "linear_priority": "High",
        "points": "points: 5",
        "story_points": 5,
        "team": "team: Diego",
        "assignee": "Diego",
        "description": """### 📌 Resumen de la Historia

| Atributo | Detalle |
| :--- | :--- |
| **ID** | US-12 |
| **Épica** | Épica 7: Motor Cuantitativo y Reportes Financieros |
| **Responsable Principal** | Diego (Quantitative Analyst & Data Governance Lead) |
| **Sprint / Ciclo** | Sprint 3: Gráficos Instantáneos y Frontend Next.js 15 |
| **Prioridad** | Should Have (Alta) |
| **Story Points** | 5 SP |

---

### 📖 Descripción
**Como** Gestor de Portafolio o Analista de Inversiones,  
**Quiero** que el agente pueda generar reportes financieros ejecutivos completos bajo demanda (con secciones de Resumen de Mercado, Niveles de Soporte/Resistencia, Comportamiento de Volumen y Diagnóstico de Volatilidad),  
**Para** exportar informes profesionales en formato Markdown limpio y PDF listo para presentación ejecutiva.

---

### 🔍 Contexto Técnico y Fundamento (Lo Obvio Explicado)
- **Estructura estándar del Reporte:**
  1. *Executive Summary:* Activo, precio actual, variación neta y rango de la ventana.
  2. *Market Dynamics:* VWAP, volumen base acumulado, presión compradora/vendedora.
  3. *Technical Levels:* Máximos y mínimos locales calculados matemáticamente desde DuckDB.
  4. *Volatility Profile:* Varianza porcentual y rango medio verdadero (ATR aproximado).
  5. *Lineage & Metadata:* Corte temporal exacto y descargo legal.
- **Exportación:** El reporte se expone como un artefacto descargable tanto desde la API (`/api/reports/{id}/export`) como desde el frontend.

---

### 🧪 Criterios de Aceptación (BDD)

#### Escenario 1: Generación de reporte completo vía prompt del usuario
- **Dado que** el usuario solicita "Genera un reporte ejecutivo de Ethereum de los últimos 7 días",
- **Cuando** el agente ejecuta la herramienta `generate_market_report`,
- **Entonces** debe generar un informe estructurado con todas las secciones cuantitativas y metadatos verificados.

#### Escenario 2: Exactitud matemática de los niveles de soporte y resistencia
- **Dado que** DuckDB calcula los percentiles y extremos de precio del periodo,
- **Cuando** se redacta la sección de niveles técnicos,
- **Entonces** los soportes y resistencias citados deben coincidir exactamente con los mínimos y máximos locales de los datos reales.

#### Escenario 3: Exportación en formato Markdown limpio
- **Dado que** el usuario pulsa "Exportar Reporte",
- **Cuando** se descarga el archivo `.md`,
- **Entonces** debe mantener un formato Markdown impecable, sin caracteres rotos ni artefactos de chat.

---

### 🛠️ Tareas Técnicas del Equipo
- [ ] Desarrollar herramienta `generate_market_report` en `backend/app/agent/tools.py` - Diego
- [ ] Diseñar plantilla ejecutiva cuantitativa en `backend/app/agent/report_templates.py` - Diego
- [ ] Endpoint de exportación de reportes en `backend/app/main.py` - Sebastián
- [ ] Pruebas de consistencia de reportes financieros en `tests/test_report_generator.py` - Samuel Roncancio
""",
    },
    {
        "id": "US-13",
        "title": "[US-13] Frontend Next.js 15: Configuración Base, Tailwind CSS v4 y Componentes de Consola (Sin Emojis)",
        "epic": "epic: 8-frontend-nextjs",
        "sprint": "sprint: 3-charts-frontend",
        "milestone": 3,
        "priority": "priority: Must Have",
        "linear_priority": "Urgent",
        "points": "points: 8",
        "story_points": 8,
        "team": "team: Camilo",
        "assignee": "Camilo",
        "description": """### 📌 Resumen de la Historia

| Atributo | Detalle |
| :--- | :--- |
| **ID** | US-13 |
| **Épica** | Épica 8: Dashboard Web Next.js 15 React 19 Lucide |
| **Responsable Principal** | Camilo (Frontend Lead & Data Visualization) |
| **Sprint / Ciclo** | Sprint 3: Gráficos Instantáneos y Frontend Next.js 15 |
| **Prioridad** | Must Have (Crítica) |
| **Story Points** | 8 SP |

---

### 📖 Descripción
**Como** Diseñador y Desarrollador Frontend,  
**Quiero** inicializar la nueva aplicación web con **Next.js 15** (App Router), **React 19**, **Tailwind CSS v4** y **Lucide Icons**, implementando una interfaz financiera profesional tipo terminal (estilo Arca/TradingView Dark),  
**Para** sustituir el frontend heredado por una interfaz rápida, limpia, sin animaciones pesadas y con prohibición estricta de emojis.

---

### 🔍 Contexto Técnico y Fundamento (Lo Obvio Explicado)
- **Cero Emojis:** Prohibición absoluta de emojis en toda la interfaz. Toda la iconografía se implementa con `lucide-react` (ej. `TrendingUp`, `BarChart3`, `Database`, `ShieldCheck`, `Terminal`, `ArrowUpRight`, `Activity`).
- **Arquitectura de Componentes:**
  - `ConsoleView`: Consola interactiva del agente con stream de mensajes y badges de estado.
  - `MessageItem`: Despliegue de respuesta ejecutiva, trazabilidad de fuentes, tiempo de latencia y herramientas ejecutadas.
  - `QuickPrompts`: Botones de acceso rápido para consultas analíticas frecuentes.
  - `StatusPill`: Indicador de salud de MinIO, DuckDB y el motor de inferencia.
- **Tipado TypeScript estricto:** Interfaces sincronizadas con los contratos Pydantic del backend (`types/api.ts`).

---

### 🧪 Criterios de Aceptación (BDD)

#### Escenario 1: Renderizado responsivo y modo oscuro profesional
- **Dado que** el usuario ingresa a `http://localhost:3000`,
- **Cuando** se carga la página principal,
- **Entonces** debe desplegar la interfaz en tema oscuro de alta gama, sin parpadeos, con fuentes Geist y tiempo de First Contentful Paint (FCP) inferior a 800 ms.

#### Escenario 2: Ausencia total de emojis en la interfaz
- **Dado que** se inspecciona el DOM de la aplicación,
- **Cuando** se auditan todos los textos, botones e indicadores,
- **Entonces** no debe existir ni un solo carácter Unicode del bloque de emojis; todos los símbolos deben ser iconos vectoriales SVG de Lucide.

#### Escenario 3: Interacción fluida con el backend vía API Client
- **Dado que** el usuario envía una consulta por la consola,
- **Cuando** se invoca el backend FastAPI,
- **Entonces** debe mostrar un indicador de carga sutil, recibir el payload estructurado y renderizar el mensaje sin bloquear la UI.

---

### 🛠️ Tareas Técnicas del Equipo
- [ ] Inicializar proyecto Next.js 15 en `frontend/` con TypeScript y Tailwind CSS v4 - Camilo
- [ ] Instalar y configurar `lucide-react` para iconografía profesional - Camilo
- [ ] Implementar componentes de chat y consola en `frontend/src/components/chat/` - Camilo
- [ ] Configurar cliente de peticiones HTTP en `frontend/src/lib/apiClient.ts` - Camilo
""",
    },
    {
        "id": "US-14",
        "title": "[US-14] Componente de Gráficos Financieros Interactivos con TradingView Lightweight Charts",
        "epic": "epic: 8-frontend-nextjs",
        "sprint": "sprint: 3-charts-frontend",
        "milestone": 3,
        "priority": "priority: Must Have",
        "linear_priority": "Urgent",
        "points": "points: 8",
        "story_points": 8,
        "team": "team: Camilo",
        "assignee": "Camilo",
        "description": """### 📌 Resumen de la Historia

| Atributo | Detalle |
| :--- | :--- |
| **ID** | US-14 |
| **Épica** | Épica 8: Dashboard Web Next.js 15 React 19 Lucide |
| **Responsable Principal** | Camilo (Frontend Lead & Data Visualization) |
| **Sprint / Ciclo** | Sprint 3: Gráficos Instantáneos y Frontend Next.js 15 |
| **Prioridad** | Must Have (Crítica) |
| **Story Points** | 8 SP |

---

### 📖 Descripción
**Como** Usuario Analista,  
**Quiero** visualizar gráficos financieros interactivos de velas japonesas (OHLCV) y líneas de tendencia renderizados mediante **TradingView Lightweight Charts** dentro del flujo de respuestas del agente,  
**Para** explorar visualmente precios, máximos, mínimos y volumen con zoom, scroll y tooltips interactivos en milisegundos.

---

### 🔍 Contexto Técnico y Fundamento (Lo Obvio Explicado)
- **Por qué Lightweight Charts de TradingView:** Es la librería estándar de la industria para finanzas: pesa solo ~45 KB (frente a los 1+ MB de Chart.js o Plotly), se dibuja en HTML5 Canvas con aceleración por hardware y maneja 10,000+ puntos a 60 FPS sin lag.
- **Interactividad:** Permite hacer zoom con la rueda del ratón, paneo lateral, visualización de tooltips con precio exacto al pasar el cursor y cambio reactivo entre modo velas y modo línea.
- **Integración con Next.js:** Carga dinámica (`next/dynamic` con `ssr: false`) para evitar errores de renderizado en el servidor (SSR) ya que Canvas requiere el objeto `window`.

---

### 🧪 Criterios de Aceptación (BDD)

#### Escenario 1: Renderizado instantáneo de velas desde el payload del agente
- **Dado que** la respuesta del agente contiene un bloque `chart` con 96 velas,
- **Cuando** el componente `InteractiveChart.tsx` monta el Canvas,
- **Entonces** las velas verdes (alza) y rojas (baja) deben aparecer dibujadas en pantalla en menos de 15 milisegundos.

#### Escenario 2: Comportamiento interactivo de tooltips y zoom
- **Dado que** el usuario pasa el ratón por encima de una vela específica,
- **Cuando** el cursor intersecta la coordenada temporal,
- **Entonces** debe desplegar un tooltip flotante con: Fecha/Hora UTC, Open, High, Low, Close y Volumen con formato de moneda (`$68,450.00`).

#### Escenario 3: Limpieza y desmonte seguro de memoria (Cleanup)
- **Dado que** el usuario cambia de vista o elimina el mensaje con el gráfico,
- **Cuando** el componente React se desmonta,
- **Entonces** debe ejecutar `chart.remove()` liberando las instancias de Canvas sin fugas de memoria en el navegador.

---

### 🛠️ Tareas Técnicas del Equipo
- [ ] Instalar dependencia `lightweight-charts` en `frontend/package.json` - Camilo
- [ ] Desarrollar componente dinámico `frontend/src/components/charts/InteractiveChart.tsx` - Camilo
- [ ] Implementar panel de indicadores superpuestos (VWAP y volumen) - Camilo
- [ ] Pruebas de rendimiento y responsividad en distintos tamaños de pantalla - Samuel Roncancio
""",
    },
    {
        "id": "US-15",
        "title": "[US-15] Suite de Pruebas Automatizadas Unitarias, Integración y Anti-Regresión",
        "epic": "epic: 9-testing-cicd",
        "sprint": "sprint: 4-hardening-demo",
        "milestone": 4,
        "priority": "priority: Must Have",
        "linear_priority": "High",
        "points": "points: 5",
        "story_points": 5,
        "team": "team: Samuel Roncancio",
        "assignee": "Samuel Roncancio",
        "description": """### 📌 Resumen de la Historia

| Atributo | Detalle |
| :--- | :--- |
| **ID** | US-15 |
| **Épica** | Épica 9: Testing Automatizado Pruebas de Carga y CI/CD |
| **Responsable Principal** | Samuel Roncancio (QA & Testing Automation Engineer) |
| **Sprint / Ciclo** | Sprint 4: Hardening, Pruebas de Carga y Entrega Final |
| **Prioridad** | Must Have (Crítica) |
| **Story Points** | 5 SP |

---

### 📖 Descripción
**Como** Ingeniero de Calidad de Software (QA),  
**Quiero** desarrollar una suite exhaustiva de pruebas automatizadas con `pytest` y `pytest-asyncio` que valide la ingesta, las consultas DuckDB, el sistema anti-alucinación y los contratos de API,  
**Para** garantizar cero regresiones y certificar que no existan datos simulados en ninguna parte del repositorio antes de la entrega final.

---

### 🔍 Contexto Técnico y Fundamento (Lo Obvio Explicado)
- **Regla Estricta:** Auditoría automatizada que falle las pruebas si se detectan palabras como `mock_data`, `fake_prices` o datos inventados en los módulos de producción.
- **Categorías de Pruebas:**
  1. `tests/unit/`: Pruebas de esquemas Pydantic, cálculo de VWAP en DuckDB, router semántico y formateador de klines.
  2. `tests/integration/`: Pruebas reales contra el contenedor MinIO y el exchange Binance.
  3. `tests/security/`: Pruebas de inyección SQL, prompts maliciosos y bloqueo de comandos destructivos.
- **Ejecución Unificada:** Comando simple `pytest tests -v` configurable en un runner de GitHub Actions.

---

### 🧪 Criterios de Aceptación (BDD)

#### Escenario 1: Ejecución completa de la suite de pruebas
- **Dado que** se corre el comando `pytest tests -v`,
- **Cuando** finalizan todas las suites de prueba,
- **Entonces** el 100% de los tests deben pasar exitosamente con una cobertura de código superior al 85% en módulos centrales.

#### Escenario 2: Certificación de ausencia de mocks en producción
- **Dado que** el test de auditoría de código escanea el repositorio,
- **Cuando** busca dependencias o funciones de simulación de datos,
- **Entonces** debe verificar que los endpoints siempre consulten datos reales o retornen estados vacíos explícitos.

#### Escenario 3: Detección y bloqueo de inyecciones en consultas
- **Dado que** se envían entradas maliciosas como `' OR 1=1 --` en el símbolo o parámetros,
- **Cuando** pasan por las capas de validación,
- **Entonces** deben ser neutralizadas antes de llegar al motor DuckDB.

---

### 🛠️ Tareas Técnicas del Equipo
- [ ] Desarrollar fixtures y configuración de `pytest.ini` - Samuel Roncancio
- [ ] Implementar pruebas de integración de MinIO + DuckDB en `tests/test_duckdb_queries.py` - Samuel Roncancio
- [ ] Implementar test de validación anti-alucinación en `tests/test_anti_hallucination.py` - Samuel Roncancio
- [ ] Configurar workflow de GitHub Actions en `.github/workflows/ci.yml` - Andrés Teherán
""",
    },
    {
        "id": "US-16",
        "title": "[US-16] Benchmark de Latencia Concurrente (< 2s p95) y Documentación Técnica Final",
        "epic": "epic: 9-testing-cicd",
        "sprint": "sprint: 4-hardening-demo",
        "milestone": 4,
        "priority": "priority: Must Have",
        "linear_priority": "High",
        "points": "points: 5",
        "story_points": 5,
        "team": "team: Andrés Blanco",
        "assignee": "Andrés Blanco",
        "description": """### 📌 Resumen de la Historia

| Atributo | Detalle |
| :--- | :--- |
| **ID** | US-16 |
| **Épica** | Épica 9: Testing Automatizado Pruebas de Carga y CI/CD |
| **Responsable Principal** | Andrés Blanco (Big Data Architect & OLAP Lead) & Andrés Teherán |
| **Sprint / Ciclo** | Sprint 4: Hardening, Pruebas de Carga y Entrega Final |
| **Prioridad** | Must Have (Crítica) |
| **Story Points** | 5 SP |

---

### 📖 Descripción
**Como** Líder Técnico del Proyecto,  
**Quiero** ejecutar un benchmark formal de rendimiento y latencia bajo concurrencia, documentando la arquitectura, la guía de despliegue y los resultados empíricos en un manual técnico exhaustivo,  
**Para** demostrar y certificar que el agente responde preguntas y genera gráficos interactivos en menos de 2 segundos en el percentil 95 (p95).

---

### 🔍 Contexto Técnico y Fundamento (Lo Obvio Explicado)
- **Métricas a certificar:**
  - Latencia de consulta DuckDB sobre Parquet en MinIO: $< 50\text{ ms}$.
  - Latencia de inferencia Groq (Llama-3.3-70b): $< 600\text{ ms}$.
  - Latencia de ensamblado y serialización de Gráficos: $< 20\text{ ms}$.
  - Renderizado en cliente Canvas: $< 15\text{ ms}$.
  - **Latencia Total End-to-End:** $< 1.5\text{ s}$ nominal, $< 2.0\text{ s}$ en p95.
- **Entregables de Documentación:**
  - `README.md` exhaustivo con arquitectura, puertos y guía rápida.
  - `MANUAL_TECNICO.md` con explicación de cada módulo, decisiones de diseño y resultados del benchmark.
  - `Makefile` con comandos estándar (`make up`, `make ingest`, `make test`, `make dev`).

---

### 🧪 Criterios de Aceptación (BDD)

#### Escenario 1: Certificación de latencia en percentil 95 (p95)
- **Dado que** se lanza un test de carga con 20 usuarios concurrentes haciendo consultas analíticas con gráficos,
- **Cuando** se mide el tiempo de respuesta completo,
- **Entonces** el p95 debe ser inferior a 2.0 segundos sin degradación del sistema.

#### Escenario 2: Despliegue con un solo comando
- **Dado que** un nuevo integrante del equipo clona el repositorio,
- **Cuando** ejecuta `make up && make ingest`,
- **Entonces** el sistema debe levantar MinIO, inicializar buckets, extraer datos reales y estar listo para responder en menos de 60 segundos.

#### Escenario 3: Documentación técnica completa y verificada
- **Dado que** se revisa la documentación de entrega,
- **Cuando** se validan los diagramas de arquitectura y especificaciones,
- **Entonces** debe detallar de forma cristalina por qué se eliminaron Spark, Kafka y Atlas, y cómo la arquitectura Lean MinIO+DuckDB+Groq resuelve el problema con máxima eficiencia.

---

### 🛠️ Tareas Técnicas del Equipo
- [ ] Desarrollar script de benchmark concurrente en `tests/benchmark_agent.py` - Andrés Blanco
- [ ] Ejecutar pruebas de carga y generar reporte de latencias - Andrés Blanco & Samuel Roncancio
- [ ] Redactar `README.md` y `MANUAL_TECNICO.md` exhaustivo - Andrés Blanco & Andrés Teherán
- [ ] Configurar `Makefile` para automatización total de tareas - Andrés Teherán
""",
    },
]


def generate_linear_csv():
    csv_path = "/home/andres/Projects/crypto-ai-agent/linear_tasks_import.csv"
    fieldnames = [
        "Title",
        "Description",
        "Status",
        "Priority",
        "Estimate",
        "Assignee",
        "Labels",
        "Project",
        "Cycle",
    ]

    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for t in TASKS:
            writer.writerow(
                {
                    "Title": t["title"],
                    "Description": t["description"],
                    "Status": "Backlog",
                    "Priority": t["linear_priority"],
                    "Estimate": t["story_points"],
                    "Assignee": t["assignee"],
                    "Labels": f"{t['epic']}, {t['sprint']}",
                    "Project": "Crypto AI Agent Platform",
                    "Cycle": f"Sprint {t['milestone']}",
                }
            )
    print(f"Generated Linear CSV at: {csv_path}")


def generate_linear_sync_script():
    script_path = "/home/andres/Projects/crypto-ai-agent/sync_to_linear.py"
    content = '''#!/usr/bin/env python3
"""
Sincronizador automático de tareas hacia Linear API (GraphQL).
Uso:
    export LINEAR_API_KEY="lin_api_..."
    python3 sync_to_linear.py
"""

import os
import sys
import json
import httpx

LINEAR_API_URL = "https://api.linear.app/graphql"
API_KEY = os.environ.get("LINEAR_API_KEY")

if not API_KEY:
    print("Error: La variable de entorno LINEAR_API_KEY no está configurada.")
    print("Para importar a Linear, puedes:")
    print("1. Subir directamente el archivo generado 'linear_tasks_import.csv' en Linear -> Settings -> Import / Export -> CSV")
    print("2. O configurar tu API Key: set -x LINEAR_API_KEY 'lin_api_...' (Fish) y volver a ejecutar este script.")
    sys.exit(1)

HEADERS = {
    "Authorization": API_KEY,
    "Content-Type": "application/json"
}

def query_linear(query, variables=None):
    payload = {"query": query}
    if variables:
        payload["variables"] = variables
    response = httpx.post(LINEAR_API_URL, headers=HEADERS, json=payload, timeout=30.0)
    data = response.json()
    if "errors" in data:
        raise RuntimeError(f"Error en Linear GraphQL: {data['errors']}")
    return data.get("data", {})

def main():
    print("Conectando con Linear API...")
    viewer = query_linear("{ viewer { id name email } teams { nodes { id name key } } }")
    print(f"Autenticado como: {viewer['viewer']['name']} ({viewer['viewer']['email']})")
    
    teams = viewer.get("teams", {}).get("nodes", [])
    if not teams:
        print("No se encontraron equipos en esta cuenta de Linear.")
        sys.exit(1)
        
    team = teams[0]
    print(f"Usando equipo: {team['name']} ({team['key']})")
    
    # Crear o buscar proyecto
    project_title = "Crypto AI Agent Platform"
    print(f"Creando proyecto '{project_title}'...")
    create_proj_query = """
    mutation CreateProject($teamId: String!, $name: String!, $description: String!) {
        projectCreate(input: { teamIds: [$teamId], name: $name, description: $description }) {
            success
            project { id name }
        }
    }
    """
    try:
        res = query_linear(create_proj_query, {
            "teamId": team["id"],
            "name": project_title,
            "description": "Plataforma de Agente de IA para Mercado Crypto con DuckDB, MinIO y generación instantánea de gráficos."
        })
        project_id = res["projectCreate"]["project"]["id"]
        print(f"Proyecto creado con ID: {project_id}")
    except Exception as e:
        print(f"Proyecto ya existente o aviso: {e}")
        # buscar id
        projs = query_linear("{ projects { nodes { id name } } }")
        project_id = next((p["id"] for p in projs.get("projects", {}).get("nodes", []) if p["name"] == project_title), None)

    # Importar tareas
    from generate_tasks import TASKS
    
    create_issue_query = """
    mutation CreateIssue($teamId: String!, $projectId: String, $title: String!, $description: String!, $priority: Int, $estimate: Int) {
        issueCreate(input: {
            teamId: $teamId,
            projectId: $projectId,
            title: $title,
            description: $description,
            priority: $priority,
            estimate: $estimate
        }) {
            success
            issue { id identifier title url }
        }
    }
    """
    
    priority_map = {"Urgent": 1, "High": 2, "Medium": 3, "Low": 4}
    
    for t in TASKS:
        p_val = priority_map.get(t["linear_priority"], 2)
        try:
            issue_res = query_linear(create_issue_query, {
                "teamId": team["id"],
                "projectId": project_id,
                "title": t["title"],
                "description": t["description"],
                "priority": p_val,
                "estimate": t["story_points"]
            })
            issue = issue_res["issueCreate"]["issue"]
            print(f"✓ Creada en Linear: {issue['identifier']} - {issue['title']}")
        except Exception as err:
            print(f"Error creando {t['id']} en Linear: {err}")

if __name__ == "__main__":
    main()
'''
    with open(script_path, "w", encoding="utf-8") as f:
        f.write(content)
    os.chmod(script_path, 0o755)
    print(f"Generated Linear Sync Script at: {script_path}")


def create_github_issues():
    print(f"Creating GitHub Issues in {REPO} and linking to Project #{PROJECT_NUMBER}...")

    milestone_titles = {
        1: "Sprint 1: Cimientos, Ingesta Real y Lakehouse MinIO + DuckDB",
        2: "Sprint 2: Cerebro del Agente IA y Motor Anti-Alucinación",
        3: "Sprint 3: Gráficos Instantáneos y Frontend Next.js 15",
        4: "Sprint 4: Hardening, Pruebas de Carga y Entrega Final",
    }

    for i, t in enumerate(TASKS, start=1):
        labels_str = f"{t['epic']},{t['sprint']},{t['priority']},{t['points']},{t['team']}"
        milestone_title = milestone_titles.get(t["milestone"], "")

        # Usar un archivo temporal para el body para evitar problemas de escape en bash
        body_file = f"/tmp/issue_body_{t['id']}.md"
        with open(body_file, "w", encoding="utf-8") as f:
            f.write(t["description"])

        cmd = [
            "gh",
            "issue",
            "create",
            "--repo",
            REPO,
            "--title",
            t["title"],
            "--body-file",
            body_file,
            "--milestone",
            milestone_title,
            "--label",
            labels_str,
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            issue_url = result.stdout.strip()
            print(f"[{i}/{len(TASKS)}] Created {t['id']}: {issue_url}")

            # Vincular al Project #2 de GitHub
            link_cmd = [
                "gh",
                "project",
                "item-add",
                str(PROJECT_NUMBER),
                "--owner",
                PROJECT_OWNER,
                "--url",
                issue_url,
            ]
            link_res = subprocess.run(link_cmd, capture_output=True, text=True)
            if link_res.returncode == 0:
                print(f"      -> Linked to Project #{PROJECT_NUMBER}")
            else:
                print(f"      -> Warning linking to project: {link_res.stderr.strip()}")

        except subprocess.CalledProcessError as err:
            print(f"Error creating issue {t['id']}: {err.stderr}")
        finally:
            if os.path.exists(body_file):
                os.remove(body_file)

        time.sleep(0.5)


if __name__ == "__main__":
    generate_linear_csv()
    generate_linear_sync_script()
    create_github_issues()
    print("All tasks processed successfully!")
