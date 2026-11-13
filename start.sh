#!/usr/bin/env bash
# ==============================================================================
# Crypto AI Agent Platform - Orquestador de Inicio Unificado (Linux / macOS)
# ==============================================================================
# Inicia los servicios en el orden correcto de dependencias:
#   1. MinIO Data Lake (Docker S3)
#   2. Inicialización de buckets y políticas (minio-init)
#   3. Servidor Backend FastAPI (DuckDB OLAP + Agente Arca en puerto 8001)
#   4. Servidor Frontend Next.js 15 (Lightweight Charts UI en puerto 3000)
#
# Maneja apagado graceful sin tocar procesos ajenos ni destruir volúmenes.
# ==============================================================================

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

# Colores para terminal
CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${CYAN}===================================================================${NC}"
echo -e "${CYAN}        CRYPTO AI AGENT PLATFORM - ORQUESTADOR DE INICIO          ${NC}"
echo -e "${CYAN}===================================================================${NC}"

# ------------------------------------------------------------------------------
# 0. Cargar variables de entorno respetando configuración existente
# ------------------------------------------------------------------------------
if [ -f ".env" ]; then
    echo -e "${GREEN}[OK] Archivo .env detectado. Cargando variables de configuración...${NC}"
    set -a
    # shellcheck disable=SC1091
    source .env
    set +a
elif [ -f ".env.example" ]; then
    echo -e "${YELLOW}[AVISO] No se detectó .env. Creando .env a partir de .env.example...${NC}"
    cp .env.example .env
    set -a
    # shellcheck disable=SC1091
    source .env
    set +a
else
    echo -e "${YELLOW}[AVISO] No se encontró .env ni .env.example. Usando valores predeterminados.${NC}"
fi

# Variables unificadas
API_HOST="${API_HOST:-0.0.0.0}"
API_PORT="${API_PORT:-8001}"
MINIO_PORT="${MINIO_PORT:-9000}"
MINIO_CONSOLE_PORT="${MINIO_CONSOLE_PORT:-9001}"
FRONTEND_PORT="${FRONTEND_PORT:-3000}"
OLLAMA_BASE_URL="${OLLAMA_BASE_URL:-http://localhost:11434}"
OLLAMA_MODEL="${OLLAMA_MODEL:-llama3.2:3b}"
GROQ_API_KEY="${GROQ_API_KEY:-}"
GROQ_MODEL="${GROQ_MODEL:-llama-3.3-70b-versatile}"
NEXT_PUBLIC_API_URL="${NEXT_PUBLIC_API_URL:-http://localhost:${API_PORT}}"
export NEXT_PUBLIC_API_URL

# ------------------------------------------------------------------------------
# 1. Comprobar requisitos del sistema
# ------------------------------------------------------------------------------
echo -e "\n${YELLOW}[Paso 1/4] Verificando requisitos del sistema...${NC}"

# Python >= 3.11
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}[ERROR] Python 3 no está instalado en el sistema.${NC}"
    exit 1
fi

PY_VER=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
PY_MAJOR=$(python3 -c 'import sys; print(sys.version_info.major)')
PY_MINOR=$(python3 -c 'import sys; print(sys.version_info.minor)')

if [ "$PY_MAJOR" -lt 3 ] || ([ "$PY_MAJOR" -eq 3 ] && [ "$PY_MINOR" -lt 11 ]); then
    echo -e "${RED}[ERROR] Se requiere Python 3.11 o superior. Versión detectada: Python ${PY_VER}.${NC}"
    exit 1
fi
echo -e "  * Python: ${GREEN}OK (v${PY_VER})${NC}"

# Node.js y npm
if ! command -v node &> /dev/null; then
    echo -e "${RED}[ERROR] Node.js no está instalado en el sistema.${NC}"
    exit 1
fi
NODE_VER=$(node -v)
echo -e "  * Node.js: ${GREEN}OK (${NODE_VER})${NC}"

if ! command -v npm &> /dev/null; then
    echo -e "${RED}[ERROR] npm no está instalado en el sistema.${NC}"
    exit 1
fi
NPM_VER=$(npm -v)
echo -e "  * npm: ${GREEN}OK (v${NPM_VER})${NC}"

# Docker y Docker Compose
if ! command -v docker &> /dev/null; then
    echo -e "${RED}[ERROR] Docker no está instalado.${NC}"
    exit 1
fi

if ! docker compose version &> /dev/null; then
    echo -e "${RED}[ERROR] El plugin 'docker compose' no está disponible.${NC}"
    exit 1
fi

if ! docker info &> /dev/null; then
    echo -e "${RED}[ERROR] El daemon de Docker no está en ejecución. Por favor inicia el servicio de Docker.${NC}"
    exit 1
fi
echo -e "  * Docker y Compose: ${GREEN}OK (daemon activo)${NC}"

# Inferencia: Groq y Ollama
echo -e "\n${YELLOW}Evaluando proveedores de inferencia de IA...${NC}"
AI_AVAILABLE=0

if [ -n "$GROQ_API_KEY" ]; then
    echo -e "  * Groq Cloud: ${GREEN}Configurado (${GROQ_MODEL})${NC}"
    AI_AVAILABLE=1
else
    echo -e "  * Groq Cloud: ${YELLOW}No configurado (GROQ_API_KEY vacía en .env)${NC}"
fi

OLLAMA_HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" --max-time 2 "${OLLAMA_BASE_URL}/api/tags" 2>/dev/null || true)
if [ "$OLLAMA_HTTP_CODE" = "200" ]; then
    OLLAMA_TAGS=$(curl -s --max-time 3 "${OLLAMA_BASE_URL}/api/tags" 2>/dev/null || true)
    if echo "$OLLAMA_TAGS" | grep -q "\"${OLLAMA_MODEL}\""; then
        echo -e "  * Ollama Local: ${GREEN}Disponible con modelo '${OLLAMA_MODEL}'${NC}"
        AI_AVAILABLE=1
    else
        echo -e "  * Ollama Local: ${YELLOW}Servicio activo pero el modelo '${OLLAMA_MODEL}' no está descargado.${NC}"
        echo -e "    ${YELLOW}Para descargarlo: ollama pull ${OLLAMA_MODEL}${NC}"
    fi
else
    echo -e "  * Ollama Local: ${YELLOW}No responde en ${OLLAMA_BASE_URL}${NC}"
fi

if [ "$AI_AVAILABLE" -eq 0 ]; then
    echo -e "  * ${YELLOW}[AVISO - MODO DEGRADADO] Ni Groq ni Ollama cuentan con modelos listos.${NC}"
    echo -e "    ${YELLOW}El sistema operará con el Respaldo Determinista cuantitativo sin IA.${NC}"
fi

# ------------------------------------------------------------------------------
# 2. Comprobar conflictos de puertos
# ------------------------------------------------------------------------------
check_port() {
    local port=$1
    if command -v ss &> /dev/null; then
        ss -tuln 2>/dev/null | grep -q ":${port} " && return 1
    elif command -v lsof &> /dev/null; then
        lsof -i ":${port}" &>/dev/null && return 1
    elif command -v netstat &> /dev/null; then
        netstat -tuln 2>/dev/null | grep -q ":${port} " && return 1
    fi
    return 0
}

# Comprobar si el puerto de MinIO está ocupado por algo que NO sea nuestro contenedor crypto-minio
if ! check_port "$MINIO_PORT"; then
    if ! docker ps --filter "name=crypto-minio" --filter "status=running" --format '{{.Names}}' | grep -q "crypto-minio"; then
        echo -e "${RED}[ERROR] El puerto ${MINIO_PORT} (MinIO) ya está ocupado por otro servicio ajeno.${NC}"
        echo -e "${RED}Por favor libera el puerto o cambia MINIO_PORT en tu archivo .env.${NC}"
        exit 1
    fi
fi

if ! check_port "$API_PORT"; then
    echo -e "${RED}[ERROR] El puerto ${API_PORT} (Backend FastAPI) ya está ocupado por otro proceso.${NC}"
    echo -e "${RED}Por favor libera el puerto o cambia API_PORT en tu archivo .env.${NC}"
    exit 1
fi

if ! check_port "$FRONTEND_PORT"; then
    echo -e "${RED}[ERROR] El puerto ${FRONTEND_PORT} (Frontend Next.js) ya está ocupado por otro proceso.${NC}"
    echo -e "${RED}Por favor libera el puerto o cambia FRONTEND_PORT en tu archivo .env.${NC}"
    exit 1
fi

# ------------------------------------------------------------------------------
# 3. Iniciar MinIO Data Lake y ejecutar minio-init
# ------------------------------------------------------------------------------
echo -e "\n${YELLOW}[Paso 2/4] Iniciando MinIO Data Lake e inicializador...${NC}"
docker compose up -d minio

echo -e "Esperando a que MinIO S3 responda en http://localhost:${MINIO_PORT}/minio/health/live..."
MAX_RETRIES=20
COUNTER=0
MINIO_OK=0
while [ $COUNTER -lt $MAX_RETRIES ]; do
    if curl -s "http://localhost:${MINIO_PORT}/minio/health/live" > /dev/null 2>&1; then
        MINIO_OK=1
        break
    fi
    sleep 1
    COUNTER=$((COUNTER + 1))
done

if [ "$MINIO_OK" -eq 1 ]; then
    echo -e "${GREEN}[OK] MinIO S3 activo y saludable en http://localhost:${MINIO_PORT}${NC}"
else
    echo -e "${RED}[ERROR] MinIO no respondió tras ${MAX_RETRIES} segundos. Abortando inicio.${NC}"
    exit 1
fi

# Ejecutar inicialización de buckets y permisos
echo -e "Inicializando buckets y políticas con minio-init..."
docker compose up minio-init

# ------------------------------------------------------------------------------
# 4. Iniciar Backend FastAPI
# ------------------------------------------------------------------------------
echo -e "\n${YELLOW}[Paso 3/4] Iniciando Backend FastAPI (DuckDB + Agente Arca)...${NC}"

if [ ! -d ".venv" ]; then
    echo -e "${YELLOW}Creando entorno virtual Python (.venv)...${NC}"
    if command -v uv &> /dev/null; then
        uv venv .venv
        uv pip install -e ".[dev]"
    else
        python3 -m venv .venv
        .venv/bin/pip install --upgrade pip
        .venv/bin/pip install -e ".[dev]"
    fi
fi

# Validar uvicorn en .venv
if [ ! -f ".venv/bin/uvicorn" ]; then
    echo -e "${YELLOW}Instalando dependencias faltantes en .venv...${NC}"
    .venv/bin/pip install -e ".[dev]"
fi

.venv/bin/uvicorn backend.app.main:app --host "$API_HOST" --port "$API_PORT" --reload &
BACKEND_PID=$!

# Control de terminación segura (limpia SOLO los procesos iniciados por este script)
CLEANED=0
cleanup() {
    if [ "$CLEANED" -eq 1 ]; then
        return
    fi
    CLEANED=1
    echo -e "\n${YELLOW}[Apagado] Deteniendo procesos iniciados por el orquestador...${NC}"
    if [ -n "${BACKEND_PID:-}" ] && kill -0 "$BACKEND_PID" 2>/dev/null; then
        echo -e "  * Deteniendo Backend (PID $BACKEND_PID)..."
        kill "$BACKEND_PID" 2>/dev/null || true
    fi
    if [ -n "${FRONTEND_PID:-}" ] && kill -0 "$FRONTEND_PID" 2>/dev/null; then
        echo -e "  * Deteniendo Frontend (PID $FRONTEND_PID)..."
        kill "$FRONTEND_PID" 2>/dev/null || true
    fi
    echo -e "${GREEN}[OK] Procesos detenidos correctamente. (Los volúmenes y contenedores no fueron destruidos).${NC}"
    exit 0
}

trap cleanup SIGINT SIGTERM EXIT

echo -e "Esperando disponibilidad del backend en http://localhost:${API_PORT}/health..."
MAX_RETRIES=25
COUNTER=0
API_OK=0
while [ $COUNTER -lt $MAX_RETRIES ]; do
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:${API_PORT}/health" 2>/dev/null || true)
    if [ "$HTTP_CODE" = "200" ]; then
        API_OK=1
        break
    fi
    sleep 1
    COUNTER=$((COUNTER + 1))
done

if [ "$API_OK" -eq 1 ]; then
    HEALTH_DATA=$(curl -s "http://localhost:${API_PORT}/health" 2>/dev/null || true)
    HEALTH_STATUS=$(python3 -c "import json, sys; print(json.loads('''$HEALTH_DATA''').get('status', 'unknown'))" 2>/dev/null || echo "ok")
    echo -e "${GREEN}[OK] Backend FastAPI operativo en http://localhost:${API_PORT} (Estado: ${HEALTH_STATUS})${NC}"
else
    echo -e "${RED}[ERROR] Backend FastAPI no respondió en el tiempo límite en el puerto ${API_PORT}.${NC}"
    exit 1
fi

# ------------------------------------------------------------------------------
# 5. Iniciar Frontend Next.js 15
# ------------------------------------------------------------------------------
echo -e "\n${YELLOW}[Paso 4/4] Iniciando Frontend Next.js 15...${NC}"

if [ ! -d "frontend/node_modules" ]; then
    echo -e "${YELLOW}Instalando dependencias de Node.js en frontend/...${NC}"
    (cd frontend && npm install)
fi

(cd frontend && NEXT_PUBLIC_API_URL="$NEXT_PUBLIC_API_URL" npm run dev -- -p "$FRONTEND_PORT") &
FRONTEND_PID=$!

echo -e "Esperando disponibilidad del frontend en http://localhost:${FRONTEND_PORT}..."
MAX_RETRIES=30
COUNTER=0
FRONTEND_OK=0
while [ $COUNTER -lt $MAX_RETRIES ]; do
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:${FRONTEND_PORT}" 2>/dev/null || true)
    if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "304" ]; then
        FRONTEND_OK=1
        break
    fi
    sleep 1
    COUNTER=$((COUNTER + 1))
done

if [ "$FRONTEND_OK" -eq 1 ]; then
    echo -e "${GREEN}[OK] Frontend Next.js 15 activo en http://localhost:${FRONTEND_PORT}${NC}"
else
    echo -e "${RED}[ERROR] Frontend no respondió en el puerto ${FRONTEND_PORT} tras ${MAX_RETRIES}s.${NC}"
    exit 1
fi

echo -e "\n${GREEN}===================================================================${NC}"
echo -e "${GREEN}             SISTEMA COMPLETO EN LÍNEA Y VERIFICADO               ${NC}"
echo -e "${GREEN}===================================================================${NC}"
echo -e "  * ${CYAN}Frontend UI:${NC}            http://localhost:${FRONTEND_PORT}"
echo -e "  * ${CYAN}Backend REST & Chat:${NC}    http://localhost:${API_PORT}"
echo -e "  * ${CYAN}Documentación Swagger:${NC}  http://localhost:${API_PORT}/docs"
echo -e "  * ${CYAN}Salud del Sistema:${NC}      http://localhost:${API_PORT}/health"
echo -e "  * ${CYAN}MinIO S3 API:${NC}           http://localhost:${MINIO_PORT}"
echo -e "  * ${CYAN}MinIO S3 Console:${NC}       http://localhost:${MINIO_CONSOLE_PORT} (minioadmin / miniopassword123)"
echo -e "-------------------------------------------------------------------"
echo -e "Presiona ${YELLOW}Ctrl+C${NC} para detener los servicios de forma limpia."
echo -e "${GREEN}===================================================================${NC}\n"

# Esperar a los procesos en background sin salir
wait "$BACKEND_PID" "$FRONTEND_PID"
