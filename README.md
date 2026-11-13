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

## 6. Arranque y Despliegue Unificado (Linux y Windows)

La plataforma cuenta con orquestadores automatizados que levantan la infraestructura completa en el orden estricto de dependencias:
1. **MinIO Data Lake (Docker S3)** en puerto `9000` (Consola: `9001`).
2. **Inicializador `minio-init`** creando buckets (`market-lake`) y políticas de acceso.
3. **Backend FastAPI (DuckDB + Agente Arca)** en puerto `8001`.
4. **Frontend Next.js 15 (Lightweight Charts UI)** en puerto `3000`.

### Requisitos Previos

| Herramienta | Versión Mínima | Propósito |
| :--- | :--- | :--- |
| **Python** | `>= 3.11` | Backend FastAPI, motor DuckDB y orquestador del agente. |
| **Node.js** | `>= 18.x` (LTS recomendado) | Servidor de desarrollo y build de Next.js 15. |
| **npm** | `>= 9.x` | Gestor de paquetes de Node.js para el frontend. |
| **Docker & Compose** | Docker 20+ con plugin Compose v2 | Contenedores MinIO S3 y minio-init. |
| **Ollama** *(Opcional)* | `>= 0.3.0` | Inferencia local alternativa (`llama3.2:3b` o `qwen2.5-coder:7b`). |

---

### Configuración de Entorno (.env)

Copia el archivo de ejemplo para generar tu archivo `.env` local:

```bash
# Linux / macOS
cp .env.example .env

# Windows (PowerShell)
Copy-Item .env.example .env
```

> [!NOTE]
> Los orquestadores `start.sh` y `start.ps1` crean automáticamente `.env` a partir de `.env.example` si no existe, y **nunca sobrescriben** un `.env` existente ni exponen credenciales.

#### Puertos y URLs Unificados

- **Frontend Next.js:** `http://localhost:3000`
- **Backend FastAPI:** `http://localhost:8001` (Docs Swagger en `http://localhost:8001/docs`)
- **MinIO S3 API:** `http://localhost:9000`
- **MinIO Console:** `http://localhost:9001` (Usuario: `minioadmin` / Clave: `miniopassword123`)

---

### Instrucciones de Arranque

#### En Linux / macOS

```bash
# Otorgar permisos de ejecución si es necesario
chmod +x start.sh

# Iniciar plataforma completa
./start.sh

# O mediante Makefile:
make run
```

#### En Windows (PowerShell)

Abre una terminal de PowerShell (versión 5.1 o PowerShell 7+) en la raíz del proyecto y ejecuta:

```powershell
.\start.ps1
```

> [!TIP]
> Si PowerShell restringe la ejecución de scripts locales, habilítala temporalmente en la sesión actual con:
> `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`

---

### Apagado Limpio y Seguro

Presiona **`Ctrl + C`** en la consola donde se ejecuta el script.
- Los orquestadores capturan la señal y terminan **únicamente los procesos de Backend y Frontend iniciados por la sesión**.
- **No se detienen procesos ajenos** ni se eliminan volúmenes ni datos persistentes de MinIO.
- Para detener manualmente los contenedores de MinIO: `docker compose down` (o `make down`).

---

### Modos de Inferencia y Modo Degradado

El sistema implementa una jerarquía estricta de inferencia:
1. **Groq Cloud (Prioridad 1):** Requiere `GROQ_API_KEY` en `.env`. Inferencia sub-segundo con `llama-3.3-70b-versatile`.
2. **Ollama Local (Prioridad 2):** Se activa automáticamente si Groq no está disponible y Ollama responde en `OLLAMA_BASE_URL` con el modelo configurado (`OLLAMA_MODEL`).
3. **Respaldo Determinista (Prioridad 3 / Modo Degradado):** Si ni Groq ni Ollama están disponibles, el sistema opera en modo degradado pero **100% funcional**: ejecuta Function Calling determinista, cálculos de métricas y gráficos directamente sobre DuckDB y Binance Live.

---

### Solución de Problemas Comunes

- **Conflicto de Puertos (`8001`, `3000`, `9000`):**
  Los scripts detectan puertos ocupados antes de iniciar. Si un puerto está en uso por otra aplicación, edita `API_PORT`, `FRONTEND_PORT` o `MINIO_PORT` en `.env`.
- **Docker daemon no responde:**
  Verifica que Docker Engine o Docker Desktop esté en ejecución (`docker info`).
- **Ollama indica `model_missing` en `/health`:**
  Ejecuta `ollama pull llama3.2:3b` para descargar el modelo local correspondiente.
- **MinIO reporta `disconnected`:**
  Asegúrate de que no haya otro servicio ocupando el puerto `9000`. Ejecuta `docker compose ps` para revisar el contenedor `crypto-minio`.

---

## 7. Pruebas Automatizadas

El proyecto cuenta con una suite integral dividida en pruebas offline y pruebas con servicios externos:

```bash
# 1. Ejecutar suite completa (unitarias + integración):
make test
# O directamente:
.venv/bin/pytest tests/ -v

# 2. Ejecutar únicamente pruebas offline (sin red ni dependencias externas):
make test-offline
# O directamente:
.venv/bin/pytest -m offline -v

# 3. Comprobación de tipos y linting del frontend:
make frontend-lint
cd frontend && npx tsc --noEmit

# 4. Build de producción del frontend:
make frontend-build
```

---

## 8. Arquitectura de Fiabilidad y Zero-Mock

- Las respuestas del chat exponen `provider` y `model`; `/health` audita disponibilidad independiente de servicios (Binance, MinIO, DuckDB, Ollama, Groq).
- Aislamiento estricto de memoria en chat: 6 turnos de historial, 30 minutos de expiración de inactividad, máximo 256 sesiones en memoria.
- Barrera anti-alucinación numérica con validación factual de precios, porcentajes, unidades y ventanas temporales (`1h`, `4h`, `24h`, `7d`, `30d`).
- El frontend descarta respuestas fuera de orden al cambiar de activo, asegurando que nunca se muestren métricas ni gráficos del activo anterior.
