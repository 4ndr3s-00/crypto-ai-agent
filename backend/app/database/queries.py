"""
Consultas analíticas OLAP de alta velocidad con DuckDB sobre MinIO (US-05).

Calcula series de tiempo OHLCV re-muestreadas, VWAP, retornos acumulados,
volatilidad y rangos máximos/mínimos en milisegundos directamente
sobre los archivos Parquet en S3.
"""

from __future__ import annotations

import logging
import time
import re
from typing import Any, Dict, List, Optional

from backend.app.database.duckdb_client import get_duckdb_client, MINIO_BUCKET

logger = logging.getLogger("backend.queries")

INTERVAL_MAP = {
    "1m": "INTERVAL '1 minute'",
    "5m": "INTERVAL '5 minutes'",
    "15m": "INTERVAL '15 minutes'",
    "1h": "INTERVAL '1 hour'",
    "4h": "INTERVAL '4 hours'",
    "1d": "INTERVAL '1 day'",
    "1D": "INTERVAL '1 day'",
    "7d": "INTERVAL '7 days'",
    "7D": "INTERVAL '7 days'",
}


def query_market_ohlcv(
    symbol: str,
    interval: str = "15m",
    limit: int = 96,
    bucket: str = MINIO_BUCKET,
) -> Dict[str, Any]:
    """
    Agrega y re-muestrea velas de 1 minuto a la temporalidad deseada usando DuckDB.
    """
    started = time.perf_counter()
    clean_symbol = symbol.strip().upper()
    if not re.fullmatch(r"[A-Z0-9]{2,20}", clean_symbol):
        raise ValueError("Símbolo inválido")
    parquet_glob = f"s3://{bucket}/historical/source=binance/symbol={clean_symbol}/*/*.parquet"

    duck = get_duckdb_client()

    if interval not in INTERVAL_MAP or not 1 <= limit <= 1000:
        raise ValueError("Intervalo o límite inválido")
    bucket_interval = INTERVAL_MAP[interval]

    query = f"""
    WITH raw_candles AS (
        SELECT
            strptime(event_time, '%Y-%m-%dT%H:%M:%S.%fZ') AS dt,
            open,
            high,
            low,
            close,
            volume
        FROM read_parquet('{parquet_glob}')
    ),
    aggregated AS (
        SELECT
            time_bucket({bucket_interval}, dt) AS bucket_time,
            arg_min(open, dt) AS open,
            max(high) AS high,
            min(low) AS low,
            arg_max(close, dt) AS close,
            sum(volume) AS volume
        FROM raw_candles
        GROUP BY 1
        ORDER BY 1 DESC
        LIMIT {limit}
    )
    SELECT
        strftime(bucket_time, '%Y-%m-%dT%H:%M:%SZ') AS timestamp,
        round(open, 4) AS open,
        round(high, 4) AS high,
        round(low, 4) AS low,
        round(close, 4) AS close,
        round(volume, 4) AS volume
    FROM aggregated
    ORDER BY bucket_time ASC;
    """

    try:
        with duck.session() as conn:
            rows = conn.execute(query).fetchall()
    except Exception as exc:
        logger.warning("No se pudieron consultar velas en DuckDB para %s: %s", clean_symbol, exc)
        return {
            "symbol": clean_symbol,
            "interval": interval,
            "candles": [],
            "count": 0,
            "source": "minio_parquet_historical",
            "data_source": "no_data_available",
            "cutoff_time": "",
            "latency_ms": round((time.perf_counter() - started) * 1000, 2),
        }

    candles = [
        {
            "timestamp": r[0],
            "open": float(r[1]),
            "high": float(r[2]),
            "low": float(r[3]),
            "close": float(r[4]),
            "volume": float(r[5]),
        }
        for r in rows
    ]

    last_time = candles[-1]["timestamp"] if candles else ""
    latency_ms = round((time.perf_counter() - started) * 1000, 2)

    return {
        "symbol": clean_symbol,
        "interval": interval,
        "candles": candles,
        "count": len(candles),
        "source": "minio_parquet_historical",
        "data_source": "postgres_reconciled" if candles else "no_data_available",
        "cutoff_time": last_time,
        "latency_ms": latency_ms,
    }


def query_market_metrics(
    symbol: str,
    window: str = "24h",
    bucket: str = MINIO_BUCKET,
) -> Dict[str, Any]:
    """
    Calcula métricas agregadas instantáneas (VWAP, Retorno %, Volatilidad, Extremos) con DuckDB.
    """
    started = time.perf_counter()
    clean_symbol = symbol.strip().upper()
    if not re.fullmatch(r"[A-Z0-9]{2,20}", clean_symbol):
        raise ValueError("Símbolo inválido")
    parquet_glob = f"s3://{bucket}/historical/source=binance/symbol={clean_symbol}/*/*.parquet"

    duck = get_duckdb_client()

    windows = {"1h": 1, "4h": 4, "24h": 24, "7d": 168, "30d": 720}
    if window not in windows:
        raise ValueError("Ventana invalida")
    hours = windows[window]
    query = f"""
    WITH raw_candles AS (
        SELECT
            strptime(event_time, '%Y-%m-%dT%H:%M:%S.%fZ') AS dt,
            open,
            high,
            low,
            close,
            volume
        FROM read_parquet('{parquet_glob}')
    ),
    summary AS (
        SELECT
            arg_max(close, dt) AS current_price,
            arg_min(open, dt) AS open_price,
            max(high) AS high,
            min(low) AS low,
            sum(volume) AS total_volume,
            sum(close * volume) / NULLIF(sum(volume), 0) AS vwap,
            stddev(close) AS price_stddev,
            max(dt) AS max_time
        FROM raw_candles
        WHERE dt >= current_timestamp - INTERVAL '{hours} hours'
    )
    SELECT
        round(current_price, 4),
        round(open_price, 4),
        round(high, 4),
        round(low, 4),
        round(total_volume, 4),
        round(vwap, 4),
        round(COALESCE(price_stddev, 0), 4),
        round(((current_price - open_price) / NULLIF(open_price, 0)) * 100, 2) AS return_pct,
        strftime(max_time, '%Y-%m-%dT%H:%M:%SZ') AS cutoff_time
    FROM summary;
    """

    try:
        with duck.session() as conn:
            row = conn.execute(query).fetchone()
    except Exception as exc:
        logger.warning("No se pudieron calcular métricas en DuckDB para %s: %s", clean_symbol, exc)
        row = None

    latency_ms = round((time.perf_counter() - started) * 1000, 2)

    if not row or row[0] is None:
        return {
            "symbol": clean_symbol,
            "window": window,
            "current_price": 0.0,
            "open": 0.0,
            "high": 0.0,
            "low": 0.0,
            "volume_24h": 0.0,
            "vwap": 0.0,
            "price_variance": 0.0,
            "return_24h": 0.0,
            "source": "minio_parquet_historical",
            "data_source": "no_data_available",
            "cutoff_time": "",
            "latency_ms": latency_ms,
        }

    return {
        "symbol": clean_symbol,
        "window": window,
        "current_price": float(row[0]),
        "open": float(row[1]),
        "high": float(row[2]),
        "low": float(row[3]),
        "volume_24h": float(row[4]),
        "vwap": float(row[5]) if row[5] is not None else float(row[0]),
        "price_variance": float(row[6]),
        "return_24h": float(row[7]) if row[7] is not None else 0.0,
        "source": "minio_parquet_historical",
        "data_source": "postgres_reconciled",
        "cutoff_time": str(row[8]),
        "latency_ms": latency_ms,
    }
