"""
Conector REST para la extracción de datos históricos de Binance (US-02).

Extrae velas históricas (klines) de mercado desde la API pública de Binance,
normaliza cada observación al contrato canónico MarketEvent y valida
su conformidad con Pydantic v2 antes de la persistencia en MinIO.
"""

from __future__ import annotations

import logging
import os
import time
from datetime import date, datetime, time as dtime, timezone
from typing import Any, List, Optional, Tuple

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

try:
    from ingestion.schemas import MarketEvent
except ImportError:
    from schemas import MarketEvent

logger = logging.getLogger("ingestion.binance_rest")

BINANCE_API_BASE = os.getenv("BINANCE_API_BASE", "https://data-api.binance.vision")
DEFAULT_SYMBOLS = os.getenv("DEFAULT_SYMBOLS", "BTCUSDT,ETHUSDT,SOLUSDT").split(",")
DEFAULT_INTERVAL = "1m"
SCHEMA_VERSION = "2.0.0"


def get_http_session(retries: int = 3, backoff_factor: float = 0.5) -> requests.Session:
    """
    Retorna una sesión HTTP configurada con reintentos automáticos para códigos 429, 500, 502, 503, 504.
    """
    session = requests.Session()
    retry_strategy = Retry(
        total=retries,
        backoff_factor=backoff_factor,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


def date_to_timestamps_ms(target_date: date) -> Tuple[int, int]:
    """
    Convierte una fecha calendario en marcas de tiempo Unix (milisegundos UTC)
    para el inicio (00:00:00.000) y el final (23:59:59.999) del día.
    """
    start_dt = datetime.combine(target_date, dtime.min, tzinfo=timezone.utc)
    end_dt = datetime.combine(target_date, dtime.max, tzinfo=timezone.utc)
    start_ms = int(start_dt.timestamp() * 1000)
    end_ms = int(end_dt.timestamp() * 1000)
    return start_ms, end_ms


def format_kline_to_event(
    kline: list,
    symbol: str,
    interval: str = DEFAULT_INTERVAL,
) -> MarketEvent:
    """
    Transforma una vela cruda de la API de Binance al contrato canónico MarketEvent.

    Estructura de la respuesta kline de Binance:
    [
        0: Open time (ms),
        1: Open price,
        2: High price,
        3: Low price,
        4: Close price,
        5: Volume,
        6: Close time,
        7: Quote asset volume,
        8: Number of trades,
        ...
    ]
    """
    open_time_ms = int(kline[0])
    open_price = float(kline[1])
    high_price = float(kline[2])
    low_price = float(kline[3])
    close_price = float(kline[4])
    volume = float(kline[5])
    trades_count = int(kline[8]) if len(kline) > 8 else 0

    event_dt = datetime.fromtimestamp(open_time_ms / 1000, tz=timezone.utc)
    ingestion_dt = datetime.now(timezone.utc)

    # Identificador determinístico: evita duplicados si la ingesta se reintenta
    event_id = f"binance_{symbol}_{open_time_ms}"

    return MarketEvent(
        event_id=event_id,
        source="binance_rest",
        exchange="binance",
        symbol=symbol,
        event_time=event_dt.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z",
        ingestion_time=ingestion_dt.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z",
        open=open_price,
        high=high_price,
        low=low_price,
        close=close_price,
        volume=volume,
        trades_count=trades_count,
        interval=interval,
        schema_version=SCHEMA_VERSION,
    )


def fetch_binance_klines(
    symbol: str,
    target_date: date,
    interval: str = DEFAULT_INTERVAL,
    limit: int = 1000,
    session: Optional[requests.Session] = None,
) -> List[MarketEvent]:
    """
    Descarga todas las velas de un símbolo para una fecha completa desde Binance REST API.

    Un día en intervalo de 1 minuto consta de 1440 observaciones. Como el límite
    máximo por petición es de 1000 elementos, se ejecutan iteraciones paginadas
    cubriendo el rango exacto desde las 00:00:00 hasta las 23:59:59 UTC.
    """
    start_ms, end_ms = date_to_timestamps_ms(target_date)
    http = session or get_http_session()
    events: List[MarketEvent] = []

    current_start = start_ms
    endpoint = f"{BINANCE_API_BASE}/api/v3/klines"

    logger.info("Iniciando descarga Binance para %s, fecha %s", symbol, target_date.isoformat())

    while current_start <= end_ms:
        params = {
            "symbol": symbol.upper(),
            "interval": interval,
            "startTime": current_start,
            "endTime": end_ms,
            "limit": limit,
        }

        try:
            response = http.get(endpoint, params=params, timeout=12)
            response.raise_for_status()
            data = response.json()
        except requests.RequestException as err:
            logger.error("Error al consultar Binance para %s en %s: %s", symbol, target_date, err)
            raise RuntimeError(f"Error en Binance REST API: {err}") from err

        if not data:
            break

        for item in data:
            event = format_kline_to_event(item, symbol, interval)
            events.append(event)

        # Avanzar el inicio al siguiente milisegundo tras la última vela recibida
        last_close_time = int(data[-1][6])
        if last_close_time >= end_ms or len(data) < limit:
            break
        current_start = last_close_time + 1

        # Respetar rate limits de la API pública
        time.sleep(0.05)

    logger.info(
        "Descarga completada para %s [%s]: total observaciones = %d",
        symbol,
        target_date.isoformat(),
        len(events),
    )
    return events


def extract_daily_market_data(
    target_date: date,
    symbols: Optional[List[str]] = None,
    interval: str = DEFAULT_INTERVAL,
) -> List[MarketEvent]:
    """
    Extrae los eventos históricos del día para la lista de símbolos configurada.
    """
    target_symbols = symbols or DEFAULT_SYMBOLS
    all_events: List[MarketEvent] = []

    session = get_http_session()
    for symbol in target_symbols:
        clean_symbol = symbol.strip().upper()
        if not clean_symbol:
            continue
        symbol_events = fetch_binance_klines(
            symbol=clean_symbol,
            target_date=target_date,
            interval=interval,
            session=session,
        )
        all_events.extend(symbol_events)

    return all_events
