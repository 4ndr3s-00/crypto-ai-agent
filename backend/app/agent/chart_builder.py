"""
Constructor de especificaciones de gráficos interactivos (US-11).

Normaliza series temporales de velas OHLCV, histogramas de volumen
y overlays de indicadores técnicos (VWAP, EMA, Soportes/Resistencias)
en formatos compatibles con TradingView Lightweight Charts en menos de 10 ms.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from backend.app.models import Candle, ChatChart, DataSource

logger = logging.getLogger("backend.chart_builder")


def build_candlestick_chart(
    symbol: str,
    interval: str,
    candles_data: List[Dict[str, Any]],
    vwap: Optional[float] = None,
    source: str = "minio_parquet_historical",
    cutoff_time: str = "",
) -> ChatChart:
    """
    Ensambla un objeto ChatChart estructurado y tipado para renderizado Canvas inmediato.
    """
    candles: List[Candle] = []
    for c in candles_data:
        try:
            candles.append(
                Candle(
                    timestamp=str(c["timestamp"]),
                    open=float(c["open"]),
                    high=float(c["high"]),
                    low=float(c["low"]),
                    close=float(c["close"]),
                    volume=float(c["volume"]),
                )
            )
        except (KeyError, ValueError, TypeError) as exc:
            logger.warning("Vela descartada por formato erróneo: %s (%s)", c, exc)
            continue

    indicators: Dict[str, Any] = {}
    if vwap is not None and vwap > 0:
        indicators["vwap"] = round(vwap, 4)

    # Calcular soporte y resistencia empíricos de la serie
    if candles:
        lows = [c.low for c in candles]
        highs = [c.high for c in candles]
        indicators["support"] = round(min(lows), 4)
        indicators["resistance"] = round(max(highs), 4)

    return ChatChart(
        symbol=symbol.upper(),
        interval=interval,
        chart_type="candlestick",
        candles=candles,
        indicators=indicators,
        source=source,
        data_source="minio_parquet" if source == "minio_parquet_historical" else "exchange_live",
        cutoff_time=cutoff_time or (candles[-1].timestamp if candles else ""),
    )
