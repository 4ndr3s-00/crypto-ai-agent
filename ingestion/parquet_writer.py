"""
Módulo de escritura columnar Parquet hacia MinIO S3 (US-03).

Convierte lotes de MarketEvent a tablas PyArrow con compresión Snappy
y persiste las particiones de forma idempotente en MinIO.
"""

from __future__ import annotations

import io
import logging
import os
from typing import List, Optional

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError
import pyarrow as pa
import pyarrow.parquet as pq

try:
    from ingestion.schemas import MarketEvent
except ImportError:
    from schemas import MarketEvent

logger = logging.getLogger("ingestion.parquet_writer")

MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "http://localhost:9000")
MINIO_BUCKET = os.getenv("MINIO_BUCKET_LAKE", "market-lake")
MINIO_ACCESS_KEY = os.getenv("INGESTION_MINIO_USER", os.getenv("MINIO_ROOT_USER", "minioadmin"))
MINIO_SECRET_KEY = os.getenv("INGESTION_MINIO_PASSWORD", os.getenv("MINIO_ROOT_PASSWORD", "miniopassword123"))

# Esquema PyArrow explícito y tipado
ARROW_SCHEMA = pa.schema([
    pa.field("event_id", pa.string(), nullable=False),
    pa.field("source", pa.string(), nullable=False),
    pa.field("exchange", pa.string(), nullable=False),
    pa.field("symbol", pa.string(), nullable=False),
    pa.field("event_time", pa.string(), nullable=False),
    pa.field("ingestion_time", pa.string(), nullable=False),
    pa.field("open", pa.float64(), nullable=False),
    pa.field("high", pa.float64(), nullable=False),
    pa.field("low", pa.float64(), nullable=False),
    pa.field("close", pa.float64(), nullable=False),
    pa.field("volume", pa.float64(), nullable=False),
    pa.field("trades_count", pa.int64(), nullable=False),
    pa.field("interval", pa.string(), nullable=False),
    pa.field("schema_version", pa.string(), nullable=False),
])


def get_s3_client(
    endpoint_url: str = MINIO_ENDPOINT,
    access_key: str = MINIO_ACCESS_KEY,
    secret_key: str = MINIO_SECRET_KEY,
):
    """
    Crea un cliente boto3 configurado para MinIO S3 con firma v4 y reintentos.
    """
    return boto3.client(
        "s3",
        endpoint_url=endpoint_url,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        config=Config(signature_version="s3v4", connect_timeout=5, retries={"max_attempts": 3}),
        region_name="us-east-1",
    )


def events_to_parquet_bytes(events: List[MarketEvent]) -> bytes:
    """
    Convierte una lista de MarketEvent en un buffer binario Parquet comprimido con Snappy.
    """
    if not events:
        raise ValueError("No se pueden serializar una lista vacía de eventos.")

    pydict = {
        "event_id": [e.event_id for e in events],
        "source": [e.source for e in events],
        "exchange": [e.exchange for e in events],
        "symbol": [e.symbol for e in events],
        "event_time": [e.event_time for e in events],
        "ingestion_time": [e.ingestion_time for e in events],
        "open": [e.open for e in events],
        "high": [e.high for e in events],
        "low": [e.low for e in events],
        "close": [e.close for e in events],
        "volume": [e.volume for e in events],
        "trades_count": [e.trades_count for e in events],
        "interval": [e.interval for e in events],
        "schema_version": [e.schema_version for e in events],
    }

    table = pa.Table.from_pydict(pydict, schema=ARROW_SCHEMA)
    sink = io.BytesIO()
    pq.write_table(table, sink, compression="snappy", flavor="spark")
    return sink.getvalue()


def write_partition_to_minio(
    events: List[MarketEvent],
    target_date_str: str,
    symbol: str,
    bucket: str = MINIO_BUCKET,
    s3_client=None,
) -> str:
    """
    Escribe una partición diaria completa en MinIO S3.
    Ruta canónica: historical/source=binance/symbol={SYMBOL}/date={YYYY-MM-DD}/data.parquet
    """
    if not events:
        raise ValueError(f"No hay eventos para persistir en la partición {symbol} / {target_date_str}")

    client = s3_client or get_s3_client()
    parquet_bytes = events_to_parquet_bytes(events)

    s3_key = (
        f"historical/source=binance/symbol={symbol.upper()}/"
        f"date={target_date_str}/data.parquet"
    )

    client.put_object(
        Bucket=bucket,
        Key=s3_key,
        Body=parquet_bytes,
        ContentType="application/octet-stream",
    )

    logger.info(
        "Partición Parquet guardada exitosamente: s3://%s/%s (Eventos: %d, Tamaño: %d bytes)",
        bucket,
        s3_key,
        len(events),
        len(parquet_bytes),
    )
    return s3_key
