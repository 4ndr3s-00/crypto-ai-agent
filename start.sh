#!/usr/bin/env bash
# ==============================================================================
# Arca Crypto AI Platform - Orquestador de Inicio Unificado
# ==============================================================================
# Levanta la infraestructura completa en orden de dependencias:
#   1. Contenedores Docker (MinIO Lakehouse S3)
#   2. Servidor Backend FastAPI (DuckDB OLAP + Agente Arca en puerto 8001)
#   3. Servidor Frontend Next.js 15 (Lightweight Charts UI en puerto 3000)
#
# Maneja apagado graceful con Ctrl+C (SIGINT/SIGTERM).
# ==============================================================================

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

# Colores de terminal para mensajes limpios
CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${CYAN}===================================================================${NC}"
echo -e "${CYAN}        MARKET COPILOT - CRYPTO AI ANALYTICS PLATFORM              ${NC}"
echo -e "${CYAN}===================================================================${NC}"

# ------------------------------------------------------------------------------
# 1. Verificar e iniciar MinIO Lakehouse (Docker)
# ------------------------------------------------------------------------------
echo -e "\n${YELLOW}[1/3] Verificando infraestructura de almacenamiento (MinIO)...${NC}"

if ! command -v docker &> /dev/null; then
    echo -e "${RED}[ERROR] Docker no está instalado en el sistema.${NC}"
    exit 1
fi

docker compose up -d minio

# Esperar a que MinIO esté respondiendo
echo -e "Esperando a que MinIO S3 responda en el puerto 9000..."
MAX_RETRIES=15
COUNTER=0
until curl -s "http://localhost:9000/minio/health/live" > /dev/null 2>&1 || [ $COUNTER -eq $MAX_RETRIES ]; do
    sleep 1
    COUNTER=$((COUNTER + 1))
done

if [ $COUNTER -eq $MAX_RETRIES ]; then
    echo -e "${YELLOW}[AVISO] MinIO tardó en responder. Continuando arranque...${NC}"
else
    echo -e "${GREEN}[OK] MinIO S3 activo y saludable en http://localhost:9000${NC}"
fi

# ------------------------------------------------------------------------------
# 2. Verificar entorno Python y Backend FastAPI
# ------------------------------------------------------------------------------
echo -e "\n${YELLOW}[2/3] Iniciando Backend FastAPI (Agente Arca + DuckDB OLAP)...${NC}"

if [ ! -d ".venv" ]; then
    echo -e "${YELLOW}No se detectó .venv. Creando entorno virtual con uv...${NC}"
    uv venv .venv
    uv pip install -e ".[dev]"
fi

# Iniciar backend en segundo plano
.venv/bin/uvicorn backend.app.main:app --host 0.0.0.0 --port 8001 --reload &
BACKEND_PID=$!

# Función de limpieza ante cierre
cleanup() {
    echo -e "\n${YELLOW}[Arca] Señal de terminación recibida. Cerrando servicios...${NC}"
    if [ -n "${BACKEND_PID:-}" ] && kill -0 "$BACKEND_PID" 2>/dev/null; then
        kill "$BACKEND_PID" 2>/dev/null || true
    fi
    if [ -n "${FRONTEND_PID:-}" ] && kill -0 "$FRONTEND_PID" 2>/dev/null; then
        kill "$FRONTEND_PID" 2>/dev/null || true
    fi
    echo -e "${GREEN}[Arca] Todos los procesos detenidos correctamente.${NC}"
    exit 0
}

trap cleanup SIGINT SIGTERM

# Esperar a que FastAPI esté listo
echo -e "Esperando disponibilidad del endpoint de salud en http://localhost:8001/health..."
COUNTER=0
MAX_RETRIES=20
until curl -s "http://localhost:8001/health" > /dev/null 2>&1 || [ $COUNTER -eq $MAX_RETRIES ]; do
    sleep 1
    COUNTER=$((COUNTER + 1))
done

if [ $COUNTER -eq $MAX_RETRIES ]; then
    echo -e "${YELLOW}[AVISO] FastAPI demoró en responder. Verificando procesos...${NC}"
else
    echo -e "${GREEN}[OK] Backend FastAPI operativo en http://localhost:8001${NC}"
fi

# ------------------------------------------------------------------------------
# 3. Verificar e iniciar Frontend Next.js 15
# ------------------------------------------------------------------------------
echo -e "\n${YELLOW}[3/3] Iniciando Frontend Next.js 15 (Lightweight Charts UI)...${NC}"

if [ ! -d "frontend/node_modules" ]; then
    echo -e "${YELLOW}Instalando dependencias de Node.js en frontend/...${NC}"
    (cd frontend && npm install)
fi

(cd frontend && npm run dev) &
FRONTEND_PID=$!

echo -e "\n${GREEN}===================================================================${NC}"
echo -e "${GREEN}             SISTEMA COMPLETO EN LÍNEA Y OPERATIVO                ${NC}"
echo -e "${GREEN}===================================================================${NC}"
echo -e "  * ${CYAN}Frontend UI:${NC}         http://localhost:3000"
echo -e "  * ${CYAN}Backend REST & Chat:${NC} http://localhost:8001"
echo -e "  * ${CYAN}Documentación Swagger:${NC}http://localhost:8001/docs"
echo -e "  * ${CYAN}MinIO S3 Console:${NC}    http://localhost:9001 (minioadmin / minioadmin)"
echo -e "-------------------------------------------------------------------"
echo -e "Presiona ${YELLOW}Ctrl+C${NC} en cualquier momento para detener todos los servicios."
echo -e "${GREEN}===================================================================${NC}\n"

# Esperar a que terminen los procesos en background
wait "$BACKEND_PID" "$FRONTEND_PID"
