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


def get_live_ticker(symbol: str, window: str = "24h") -> Dict[str, Any]:
    """
    Obtiene métricas de las últimas 24h para un par en vivo (precio actual, retorno, volumen, extremos).
    """
    clean_symbol = symbol.strip().upper()
    if window not in {"1h", "4h", "24h", "7d", "30d"}:
        raise ValueError("Invalid window")
    endpoint = "/api/v3/ticker/24hr" if window == "24h" else "/api/v3/ticker"
    params = {"symbol": clean_symbol}
    if window != "24h":
        params["windowSize"] = window
    data = _http_get(endpoint, params)
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
        "window": window,
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


def is_stale_cutoff(cutoff_iso: str, max_age_seconds: float = 900) -> bool:
    """
    Retorna True si la marca de tiempo tiene más de max_age_seconds de antigüedad o es inválida.
    Permite detectar automáticamente cuándo los datos en disco o lakehouse están atrasados.
    """
    if not cutoff_iso or not isinstance(cutoff_iso, str):
        return True
    try:
        clean = cutoff_iso.replace("Z", "+00:00")
        dt = datetime.fromisoformat(clean)
        now = datetime.now(timezone.utc)
        return abs((now - dt).total_seconds()) > max_age_seconds
    except Exception:
        return True


def get_technical_summary(symbol: str) -> Dict[str, Any]:
    """
    Calcula el resumen técnico estilo TradingView para el par:
    - Cotización en tiempo real y rangos de 24 horas
    - RSI (14 periodos)
    - Medias móviles SMA (20) y EMA (50)
    - Termómetro/consenso técnico ("Compra fuerte", "Compra", "Neutral", "Venta", "Venta fuerte")
    - Rendimiento en múltiples horizontes (24h, 7d, 30d, 90d, 1y)
    - Rango de 52 semanas
    """
    clean_symbol = symbol.strip().upper()
    ticker = get_live_ticker(clean_symbol)
    current_price = ticker["current_price"]

    # Consultar klines diarias para horizontes de rendimiento y medias móviles
    daily_klines = get_live_klines(clean_symbol, interval="1d", limit=365)
    candles = daily_klines.get("candles", [])

    horizons = {
        "24h": round(ticker["return_24h"], 2),
        "7d": 0.0,
        "30d": 0.0,
        "90d": 0.0,
        "1y": 0.0,
    }

    closes = [c["close"] for c in candles]
    if len(closes) >= 7:
        c7 = closes[-7]
        horizons["7d"] = round(((current_price - c7) / c7) * 100, 2)
    if len(closes) >= 30:
        c30 = closes[-30]
        horizons["30d"] = round(((current_price - c30) / c30) * 100, 2)
    if len(closes) >= 90:
        c90 = closes[-90]
        horizons["90d"] = round(((current_price - c90) / c90) * 100, 2)
    if len(closes) >= 365:
        c365 = closes[-365]
        horizons["1y"] = round(((current_price - c365) / c365) * 100, 2)
    elif len(closes) > 0:
        c_old = closes[0]
        horizons["1y"] = round(((current_price - c_old) / c_old) * 100, 2)

    # Rango 52 semanas
    high_52w = max([c["high"] for c in candles]) if candles else ticker["high"]
    low_52w = min([c["low"] for c in candles]) if candles else ticker["low"]

    # RSI 14 sobre velas de 1h
    klines_1h = get_live_klines(clean_symbol, interval="1h", limit=40)
    c1h = [c["close"] for c in klines_1h.get("candles", [])]

    rsi = 50.0
    if len(c1h) >= 15:
        deltas = [c1h[i] - c1h[i - 1] for i in range(1, len(c1h))]
        gains = [d for d in deltas[-14:] if d > 0]
        losses = [-d for d in deltas[-14:] if d < 0]
        avg_gain = sum(gains) / 14 if gains else 0.0
        avg_loss = sum(losses) / 14 if losses else 0.00001
        rs = avg_gain / avg_loss
        rsi = round(100 - (100 / (1 + rs)), 2)

    # SMA 20 y EMA 50
    sma_20 = round(sum(closes[-20:]) / len(closes[-20:]), 2) if len(closes) >= 20 else current_price

    ema_50 = sma_20
    if len(closes) >= 50:
        k = 2 / (50 + 1)
        ema = closes[-50]
        for c in closes[-49:]:
            ema = (c * k) + (ema * (1 - k))
        ema_50 = round(ema, 2)

    # Consenso técnico cuantitativo
    score = 0
    if current_price > sma_20:
        score += 1
    else:
        score -= 1

    if current_price > ema_50:
        score += 1
    else:
        score -= 1

    if rsi > 55:
        score += 1
    elif rsi < 45:
        score -= 1

    if rsi >= 70:
        rating = "Venta (Sobrecompra)"
    elif rsi <= 30:
        rating = "Compra (Sobreventa)"
    elif score >= 2:
        rating = "Compra fuerte"
    elif score == 1:
        rating = "Compra"
    elif score <= -2:
        rating = "Venta fuerte"
    elif score == -1:
        rating = "Venta"
    else:
        rating = "Neutral"

    return {
        "symbol": clean_symbol,
        "current_price": current_price,
        "change_24h": round(current_price - ticker["open"], 2),
        "return_24h": round(ticker["return_24h"], 2),
        "high_24h": ticker["high"],
        "low_24h": ticker["low"],
        "volume_24h": ticker["volume_24h"],
        "vwap": ticker["vwap"],
        "rsi_14": rsi,
        "sma_20": sma_20,
        "ema_50": ema_50,
        "technical_rating": rating,
        "rating_score": score,
        "horizons": horizons,
        "high_52w": high_52w,
        "low_52w": low_52w,
        "source": "binance_live",
        "data_source": "exchange_live",
        "timestamp": _iso_now(),
    }

