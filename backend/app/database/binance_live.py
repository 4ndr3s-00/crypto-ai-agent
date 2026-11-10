"""
Cliente público de datos en vivo de Binance (US-08).

Permite consultar cotizaciones en tiempo real (ticker 24h, klines recientes)
directamente de los endpoints públicos de Binance sin requerir API keys.
Incluye caché en memoria con TTL corto (5s) para protección de rate limits.
"""

from __future__ import annotations

import logging
import os
import threading
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import httpx

logger = logging.getLogger("backend.binance_live")

BINANCE_BASE = os.getenv("BINANCE_API_BASE", "https://data-api.binance.vision")
CACHE_TTL = float(os.getenv("MARKET_CACHE_TTL_SECONDS", "5.0"))
TIMEOUT = float(os.getenv("MARKET_REQUEST_TIMEOUT_SECONDS", "8.0"))

_CACHE: Dict[str, Tuple[float, Any]] = {}
_CACHE_LOCK = threading.Lock()


class ExchangeUnavailable(RuntimeError):
    """El exchange público no respondió o devolvió un payload inválido."""


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _cache_get(key: str) -> Optional[Any]:
    now = time.monotonic()
    with _CACHE_LOCK:
        entry = _CACHE.get(key)
        if entry and now - entry[0] < CACHE_TTL:
            return entry[1]
        if entry:
            _CACHE.pop(key, None)
    return None


def _cache_set(key: str, value: Any) -> Any:
    with _CACHE_LOCK:
        _CACHE[key] = (time.monotonic(), value)
    return value


def _http_get(path: str, params: Optional[Dict[str, Any]] = None) -> Any:
    params_sorted = sorted((params or {}).items())
    cache_key = f"{path}|{params_sorted}"

    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    url = f"{BINANCE_BASE.rstrip('/')}{path}"
    try:
        with httpx.Client(timeout=TIMEOUT) as client:
            resp = client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()
    except Exception as exc:
        logger.warning("Fallo al consultar Binance Live [%s]: %s", path, exc)
        raise ExchangeUnavailable(f"Binance Live no respondió: {exc}") from exc

    return _cache_set(cache_key, data)


def get_live_ticker(symbol: str) -> Dict[str, Any]:
    """
    Obtiene métricas de las últimas 24h para un par en vivo (precio actual, retorno, volumen, extremos).
    """
    clean_symbol = symbol.strip().upper()
    data = _http_get("/api/v3/ticker/24hr", {"symbol": clean_symbol})
    if not isinstance(data, dict) or "lastPrice" not in data:
        raise ExchangeUnavailable(f"Ticker inválido devuelto por Binance para {clean_symbol}")

    current_price = float(data["lastPrice"])
    open_price = float(data["openPrice"])
    high_price = float(data["highPrice"])
    low_price = float(data["lowPrice"])
    volume = float(data["volume"])
    quote_volume = float(data["quoteVolume"])
    vwap = float(data.get("weightedAvgPrice") or current_price)
    price_change_pct = float(data.get("priceChangePercent") or 0.0)

    cutoff_time = datetime.fromtimestamp(int(data["closeTime"]) / 1000, tz=timezone.utc).isoformat().replace("+00:00", "Z")

    return {
        "symbol": clean_symbol,
        "window": "24h",
        "current_price": current_price,
        "open": open_price,
        "high": high_price,
        "low": low_price,
        "volume_24h": volume,
        "vwap": vwap,
        "price_variance": 0.0,
        "return_24h": price_change_pct,
        "source": "binance_live",
        "data_source": "exchange_live",
        "cutoff_time": cutoff_time,
        "is_live": True,
        "fetched_at": _iso_now(),
    }


def get_live_klines(symbol: str, interval: str = "15m", limit: int = 96) -> Dict[str, Any]:
    """
    Obtiene velas recientes en tiempo real para graficación instantánea.
    """
    clean_symbol = symbol.strip().upper()
    binance_interval = "1d" if interval.lower() in {"1d", "7d"} else interval
    safe_limit = max(1, min(int(limit), 1000))

    data = _http_get(
        "/api/v3/klines",
        {"symbol": clean_symbol, "interval": binance_interval, "limit": safe_limit},
    )

    if not isinstance(data, list):
        raise ExchangeUnavailable(f"Klines inválidas devueltas por Binance para {clean_symbol}")

    candles: List[Dict[str, Any]] = []
    for item in data:
        open_time = int(item[0])
        dt = datetime.fromtimestamp(open_time / 1000, tz=timezone.utc).isoformat().replace("+00:00", "Z")
        candles.append({
            "timestamp": dt,
            "open": float(item[1]),
            "high": float(item[2]),
            "low": float(item[3]),
            "close": float(item[4]),
            "volume": float(item[5]),
        })

    last_cutoff = candles[-1]["timestamp"] if candles else _iso_now()

    return {
        "symbol": clean_symbol,
        "interval": interval,
        "count": len(candles),
        "candles": candles,
        "source": "binance_live",
        "data_source": "exchange_live",
        "cutoff_time": last_cutoff,
        "is_live": True,
        "fetched_at": _iso_now(),
    }
