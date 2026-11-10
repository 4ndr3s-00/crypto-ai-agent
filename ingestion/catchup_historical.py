"""
Catch-up histórico real de mercado hacia MinIO (US-03).

Detecta qué particiones diarias faltan en el Data Lake (MinIO)
y descarga desde Binance REST los días faltantes para consolidar
la serie de tiempo en formato Parquet columnar sin intervención manual.
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from datetime import date, timedelta
from typing import List, Optional

from ingestion.connectors.binance_rest import fetch_binance_klines, DEFAULT_SYMBOLS
from ingestion.parquet_writer import (
    get_s3_client,
    write_partition_to_minio,
    MINIO_BUCKET,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("catchup")


def list_existing_dates_in_minio(symbol: str, s3_client=None, bucket: str = MINIO_BUCKET) -> List[date]:
    """
    Lista todas las fechas ya presentes en MinIO para un símbolo determinado.
    """
    client = s3_client or get_s3_client()
    prefix = f"historical/source=binance/symbol={symbol.upper()}/date="

    paginator = client.get_paginator("list_objects_v2")
    existing_dates: List[date] = []

    try:
        for page in paginator.paginate(Bucket=bucket, Prefix=prefix, Delimiter="/"):
            for common_prefix in page.get("CommonPrefixes", []):
                raw = common_prefix.get("Prefix", "").rsplit("date=", 1)[-1].rstrip("/")
                try:
                    existing_dates.append(date.fromisoformat(raw))
                except ValueError:
                    continue
    except Exception as exc:
        logger.warning("No se pudieron listar particiones existentes en MinIO: %s", exc)

    return sorted(existing_dates)


def run_catchup(
    symbols: Optional[List[str]] = None,
    days: int = 14,
    force: bool = False,
) -> dict[str, int]:
    """
    Ejecuta la reconciliación y extracción de los últimos N días hasta ayer.
    """
    target_symbols = symbols or DEFAULT_SYMBOLS
    yesterday = date.today() - timedelta(days=1)
    start_date = yesterday - timedelta(days=days - 1)

    s3 = get_s3_client()
    summary = {}

    for sym in target_symbols:
        symbol = sym.strip().upper()
        if not symbol:
            continue

        existing = set(list_existing_dates_in_minio(symbol, s3_client=s3)) if not force else set()
        missing = [start_date + timedelta(days=i) for i in range(days) if (start_date + timedelta(days=i)) not in existing]

        logger.info(
            "[%s] Verificando historial (%d días solicitados): faltan %d particiones.",
            symbol,
            days,
            len(missing),
        )

        ingested_count = 0
        for target_date in missing:
            try:
                events = fetch_binance_klines(symbol=symbol, target_date=target_date, interval="1m")
                if events:
                    write_partition_to_minio(
                        events=events,
                        target_date_str=target_date.isoformat(),
                        symbol=symbol,
                        s3_client=s3,
                    )
                    ingested_count += 1
                else:
                    logger.warning("No se recibieron eventos para %s en %s", symbol, target_date)
            except Exception as exc:
                logger.error("Error al procesar %s en %s: %s", symbol, target_date, exc)

        summary[symbol] = ingested_count
        logger.info("[%s] Ingesta finalizada: %d particiones cargadas a MinIO.", symbol, ingested_count)

    return summary


def main():
    parser = argparse.ArgumentParser(description="Catchup de mercado crypto hacia MinIO S3.")
    parser.add_argument("--symbols", type=str, default="BTCUSDT,ETHUSDT,SOLUSDT", help="Símbolos separados por coma")
    parser.add_argument("--days", type=int, default=7, help="Número de días históricos a asegurar")
    parser.add_argument("--force", action="store_true", help="Forzar re-ingesta aunque ya existan particiones")

    args = parser.parse_args()
    symbols_list = [s.strip() for s in args.symbols.split(",") if s.strip()]

    print(f"Iniciando catchup para: {symbols_list} ({args.days} días)...")
    results = run_catchup(symbols=symbols_list, days=args.days, force=args.force)
    print(f"Resumen de Ingesta: {results}")


if __name__ == "__main__":
    main()
