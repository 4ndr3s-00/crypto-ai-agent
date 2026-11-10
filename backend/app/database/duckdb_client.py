"""
Cliente y pool de conexiones DuckDB con soporte S3/MinIO httpfs (US-04).

Permite ejecutar consultas OLAP vectorizadas directamente sobre archivos
Apache Parquet persistidos en MinIO con latencia inferior a 50 ms,
sin levantar clústeres pesados de Spark ni motores relacionales intermedios.
"""

from __future__ import annotations

import logging
import os
import threading
from contextlib import contextmanager
from typing import Generator

import duckdb

logger = logging.getLogger("backend.duckdb_client")

# Configuración MinIO / S3
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "http://localhost:9000").replace("http://", "").replace("https://", "")
MINIO_ACCESS_KEY = os.getenv("API_MINIO_USER", os.getenv("MINIO_ROOT_USER", "minioadmin"))
MINIO_SECRET_KEY = os.getenv("API_MINIO_PASSWORD", os.getenv("MINIO_ROOT_PASSWORD", "miniopassword123"))
MINIO_BUCKET = os.getenv("MINIO_BUCKET_LAKE", "market-lake")

_LOCAL_LOCK = threading.Lock()


class DuckDBClient:
    """
    Gestor de conexiones DuckDB optimizado para consultas analíticas sobre S3.
    """

    def __init__(
        self,
        endpoint: str = MINIO_ENDPOINT,
        access_key: str = MINIO_ACCESS_KEY,
        secret_key: str = MINIO_SECRET_KEY,
        bucket: str = MINIO_BUCKET,
    ) -> None:
        self.endpoint = endpoint
        self.access_key = access_key
        self.secret_key = secret_key
        self.bucket = bucket
        self._initialized = False

    def get_connection(self) -> duckdb.DuckDBPyConnection:
        """
        Crea y configura una conexión DuckDB en memoria con la extensión httpfs.
        """
        conn = duckdb.connect(":memory:")
        try:
            conn.execute("INSTALL httpfs; LOAD httpfs;")
            conn.execute(f"SET s3_endpoint='{self.endpoint}';")
            conn.execute("SET s3_use_ssl=false;")
            conn.execute("SET s3_url_style='path';")
            conn.execute(f"SET s3_access_key_id='{self.access_key}';")
            conn.execute(f"SET s3_secret_access_key='{self.secret_key}';")
        except Exception as exc:
            logger.error("Error al configurar httpfs en DuckDB: %s", exc)
            raise RuntimeError(f"Fallo inicializando DuckDB httpfs: {exc}") from exc
        return conn

    @contextmanager
    def session(self) -> Generator[duckdb.DuckDBPyConnection, None, None]:
        """
        Context manager para adquirir y cerrar de forma segura conexiones DuckDB.
        """
        conn = self.get_connection()
        try:
            yield conn
        finally:
            conn.close()


# Instancia singleton predeterminada
_DEFAULT_CLIENT: DuckDBClient | None = None


def get_duckdb_client() -> DuckDBClient:
    global _DEFAULT_CLIENT
    with _LOCAL_LOCK:
        if _DEFAULT_CLIENT is None:
            _DEFAULT_CLIENT = DuckDBClient()
        return _DEFAULT_CLIENT
