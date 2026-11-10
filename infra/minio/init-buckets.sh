#!/usr/bin/env bash
set -euo pipefail

echo "================================================================="
echo "Inicialización de MinIO Data Lake para Crypto AI Agent"
echo "================================================================="

MINIO_ENDPOINT="http://minio:9000"
BUCKET_NAME="${MINIO_BUCKET_LAKE:-market-lake}"

echo "Esperando disponibilidad del servicio MinIO en ${MINIO_ENDPOINT}..."
until mc alias set myminio "${MINIO_ENDPOINT}" "${MINIO_ROOT_USER}" "${MINIO_ROOT_PASSWORD}" > /dev/null 2>&1; do
    echo "MinIO no responde aún, reintentando en 1 segundo..."
    sleep 1
done

echo "Conectado exitosamente con MinIO."

# 1. Crear bucket principal de forma idempotente
if ! mc ls "myminio/${BUCKET_NAME}" > /dev/null 2>&1; then
    echo "Creando bucket: ${BUCKET_NAME}..."
    mc mb "myminio/${BUCKET_NAME}"
else
    echo "Bucket '${BUCKET_NAME}' ya existe."
fi

# 2. Configurar políticas IAM
echo "Configurando políticas IAM..."
if [ -f "/policies/lake-readwrite.json" ]; then
    mc admin policy create myminio lake-readwrite /policies/lake-readwrite.json || true
fi

if [ -f "/policies/lake-readonly.json" ]; then
    mc admin policy create myminio lake-readonly /policies/lake-readonly.json || true
fi

# 3. Crear usuarios de servicio y adjuntar políticas
echo "Configurando usuarios de servicio..."

# Ingesta (Read-Write)
if [ -n "${INGESTION_MINIO_USER:-}" ] && [ -n "${INGESTION_MINIO_PASSWORD:-}" ]; then
    mc admin user add myminio "${INGESTION_MINIO_USER}" "${INGESTION_MINIO_PASSWORD}" || true
    mc admin policy attach myminio lake-readwrite --user "${INGESTION_MINIO_USER}" || true
    echo "Usuario '${INGESTION_MINIO_USER}' configurado con permisos Read-Write."
fi

# Backend / DuckDB (Read-Only)
if [ -n "${API_MINIO_USER:-}" ] && [ -n "${API_MINIO_PASSWORD:-}" ]; then
    mc admin user add myminio "${API_MINIO_USER}" "${API_MINIO_PASSWORD}" || true
    mc admin policy attach myminio lake-readonly --user "${API_MINIO_USER}" || true
    echo "Usuario '${API_MINIO_USER}' configurado con permisos Read-Only."
fi

echo "================================================================="
echo "MinIO Data Lake inicializado correctamente y listo para operar."
echo "================================================================="
exit 0
