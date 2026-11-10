# Crypto AI Agent Platform

> **Plataforma Analítica de Mercado Crypto con Agente de IA, Inferencia Ultrarrápida (Groq/Ollama), DuckDB sobre MinIO Parquet, Sistema Anti-Alucinación y Generación Instantánea de Gráficos Financieros.**

---

## 1. Visión General del Proyecto

Esta plataforma sustituye la sobrecarga y el gigantismo de la infraestructura distribuida tradicional (Spark, Kafka, Airflow, Atlas) por una **Arquitectura Lean de Alto Rendimiento**:

- **Lago de Datos (MinIO S3):** Almacenamiento duradero de series temporales particionadas en formato columnar **Apache Parquet**.
- **Motor Analítico OLAP Embebido (DuckDB):** Consultas analíticas SQL vectorizadas ejecutadas en C++ directamente sobre archivos Parquet en MinIO con latencias inferiores a **40 milisegundos**.
- **Inferencia de IA Subsegundo (Groq):** Modelo `llama-3.3-70b-versatile` orquestando Function Calling con respuesta en menos de **800 milisegundos** y fallback a Ollama local (`qwen2.5-coder`).
- **Sistema Anti-Alucinación Estricto (Zero-Mock):** Las respuestas se fundamentan exclusivamente en datos reales de mercado. Prohibición total de datos simulados y citas obligatorias de corte temporal (`cutoff_time`), fuente (`source`) y linaje (`provenance`).
- **Visualización Instantánea:** Generación de especificaciones de gráficos interactivos de velas japonesas OHLCV y volumen con **TradingView Lightweight Charts** en menos de **2 segundos** end-to-end.
- **Frontend Financiero Moderno:** Construido con **Next.js 15**, **React 19**, **Tailwind CSS v4** y **Lucide Icons** (prohibición estricta de emojis en la interfaz).

---

## 2. Gestión del Proyecto y Backlog del Equipo

El proyecto cuenta con un backlog exhaustivo dividido en 4 Sprints, documentado con Criterios de Aceptación BDD y tareas técnicas paso a paso:

- **GitHub Project Board:** [Crypto AI Agent Platform #2](https://github.com/users/4ndr3s-00/projects/2)
- **Repositorio:** [4ndr3s-00/crypto-ai-agent](https://github.com/4ndr3s-00/crypto-ai-agent)
- **Linear Sync / Importación:**
  - Archivo CSV para importación directa en 1 clic: `linear_tasks_import.csv` (en la raíz).
  - Script de sincronización automática vía API GraphQL: `sync_to_linear.py`.

---

## 3. Resumen de Sprints y Metas

| Sprint | Meta Principal | Épicas Clave | Historias |
| :--- | :--- | :--- | :--- |
| **Sprint 1: Cimientos y Lakehouse** | Ingesta real de Binance, almacenamiento Parquet en MinIO y motor DuckDB OLAP. | Épica 1, 2, 3 | US-01 a US-05 |
| **Sprint 2: Agente y Anti-Alucinación** | Orquestación Groq/Ollama, herramientas tipadas, router semántico y guardrails factuales. | Épica 4, 5 | US-06 a US-10 |
| **Sprint 3: Gráficos y Frontend** | Generador de gráficos en milisegundos, reportes ejecutivos y UI Next.js 15 sin emojis. | Épica 6, 7, 8 | US-11 a US-14 |
| **Sprint 4: Hardening y Entrega** | Testing automatizado, auditoría sin mocks, benchmark de latencia p95 < 2s y manual final. | Épica 9 | US-15 a US-16 |

---

## 4. Distribución del Equipo de Desarrollo

- **Andrés Blanco:** Big Data Architect & OLAP Lead (DuckDB sobre MinIO Parquet, optimización de queries analíticas).
- **Andrés Teherán:** DevOps, Ingesta & Data Pipelines Lead (Docker Compose, MinIO S3, Parquet Writer y CI/CD).
- **Sebastián:** AI Engineer & LLM Specialist (Orquestación Groq/Ollama, herramientas tipadas y router semántico).
- **Camilo:** Frontend Lead & Data Visualization (Next.js 15, TradingView Lightweight Charts y diseño UI).
- **Diego:** Quantitative Analyst & Reports Lead (Motor de métricas financieras, niveles técnicos y anti-alucinación).
- **Samuel Benavidez:** Realtime Ingestion & Exchange Connectors (Conectores REST/WebSocket Binance y validación de esquemas).
- **Samuel Roncancio:** QA & Testing Automation Engineer (Suites pytest, tests de concurrencia y validación zero-mock).

---

## 5. Arquitectura del Repositorio

```
crypto-ai-agent/
├── docker-compose.yml          # MinIO Data Lake + inicializador automático
├── linear_tasks_import.csv     # Exportación exhaustiva para importación en Linear
├── sync_to_linear.py           # Sincronizador automático con Linear GraphQL API
├── generate_tasks.py           # Generador reproducible de backlog e issues
├── README.md
│
├── ingestion/                  # Extracción de Binance y conversión Parquet
│   ├── connectors/             # Conector Binance REST con paginación
│   ├── schemas.py              # Esquemas canónicos Pydantic v2
│   └── parquet_writer.py       # Escritor columnar hacia MinIO
│
├── backend/                    # API FastAPI + Agente de IA
│   ├── app/
│   │   ├── main.py             # Endpoints FastAPI y SSE
│   │   ├── config.py           # Settings Pydantic v2
│   │   ├── models.py           # Contratos Chat, Chart y Report
│   │   ├── database/           # Cliente DuckDB (httpfs) y Binance Live
│   │   └── agent/              # Inferencia Groq/Ollama, Tools, Router y Anti-Alucinación
│
├── frontend/                   # UI Next.js 15 + React 19 + Tailwind v4
│   └── src/
│       ├── components/chat/    # Consola interactiva y trazabilidad
│       ├── components/charts/  # TradingView Lightweight Charts
│       └── components/reports/ # Visor y exportador de informes ejecutivos
│
└── tests/                      # Suite de pruebas unitarias, integración y carga
```

---

## 6. Puesta en Marcha Rápida (Entorno Fish Shell)

```fish
# 1. Clonar e ingresar al repositorio
cd ~/Projects/crypto-ai-agent

# 2. Configurar entorno
cp .env.example .env

# 3. Levantar MinIO
docker compose up -d

# 4. Sincronizar tareas con Linear (si dispones de API Key)
set -x LINEAR_API_KEY "lin_api_tu_token_aqui"
python3 sync_to_linear.py
```
