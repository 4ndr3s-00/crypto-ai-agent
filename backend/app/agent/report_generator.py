"""
Motor de generación de reportes financieros cuantitativos ejecutivos (US-12).

Calcula indicadores técnicos de soporte/resistencia, VWAP, dispersión de volatilidad
y produce informes estructurados en Markdown limpio listos para exportación.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from backend.app.config import DISCLAIMER
from backend.app.database.binance_live import get_live_ticker, get_live_klines, is_stale_cutoff
from backend.app.database.queries import query_market_metrics, query_market_ohlcv

logger = logging.getLogger("backend.report_generator")


def _format_curr(val: float) -> str:
    return f"${val:,.2f}"


def generate_executive_report(
    symbol: str,
    timeframe: str = "24h",
    depth: str = "detailed",
) -> Dict[str, Any]:
    """
    Genera un informe financiero ejecutivo respaldado empíricamente por MinIO y Binance.
    """
    clean_sym = symbol.strip().upper()

    # 1. Obtener métricas
    metrics = query_market_metrics(clean_sym, window=timeframe)
    if metrics.get("current_price", 0.0) <= 0 or is_stale_cutoff(metrics.get("cutoff_time", "")):
        metrics = get_live_ticker(clean_sym, window=timeframe)

    # 2. Obtener serie temporal para cálculo de niveles
    limit = 168 if timeframe == "7d" else 30 if timeframe == "30d" else 24
    interval = "1d" if timeframe == "30d" else "1h"
    ts = query_market_ohlcv(clean_sym, interval=interval, limit=limit)
    if not ts.get("candles") or is_stale_cutoff(ts.get("cutoff_time", "")):
        ts = get_live_klines(clean_sym, interval=interval, limit=limit)
    candles = ts.get("candles", [])

    current_price = metrics.get("current_price", 0.0)
    open_price = metrics.get("open", current_price)
    high_price = metrics.get("high", current_price)
    low_price = metrics.get("low", current_price)
    vwap = metrics.get("vwap", current_price)
    volume_24h = metrics.get("volume_24h", 0.0)
    return_pct = metrics.get("return_24h", 0.0)
    volatility = metrics.get("price_variance", 0.0)

    # Calcular soportes y resistencias
    if candles:
        lows = [c["low"] for c in candles]
        highs = [c["high"] for c in candles]
        support_1 = min(lows)
        resistance_1 = max(highs)
        range_pct = ((resistance_1 - support_1) / max(support_1, 1.0)) * 100
    else:
        support_1 = low_price
        resistance_1 = high_price
        range_pct = ((high_price - low_price) / max(low_price, 1.0)) * 100

    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    cutoff_time = metrics.get("cutoff_time") or now_iso
    source_layer = metrics.get("source", "minio_parquet_historical")

    trend_diag = "Alcista" if return_pct > 0.5 else "Bajista" if return_pct < -0.5 else "Consolidación Neutral"

    # Redacción del reporte en Markdown limpio (sin emojis)
    markdown_content = f"""# Reporte Financiero Cuantitativo: {clean_sym}
**Fecha de Emisión:** {now_iso}  
**Ventana Temporal Analizada:** {timeframe}  
**Fuente de Datos:** {source_layer}  
**Corte Temporal de Datos:** {cutoff_time}  

---

## 1. Resumen Ejecutivo
El activo **{clean_sym}** cotiza actualmente a **{_format_curr(current_price)}**, registrando una variación de **{return_pct:+.2f}%** en la ventana de **{timeframe}**.
- **Precio de Apertura de Ventana:** {_format_curr(open_price)}
- **Rango Operativo:** {_format_curr(low_price)} — {_format_curr(high_price)}
- **Diagnóstico de Tendencia Local:** {trend_diag}

---

## 2. Dinámica de Precios y Niveles Técnicos Clave
- **Precio Promedio Ponderado por Volumen (VWAP):** {_format_curr(vwap)}
  * Posición respecto a VWAP: {"Cotizando por encima del VWAP (sesgo comprador)" if current_price >= vwap else "Cotizando por debajo del VWAP (sesgo vendedor)"}.
- **Nivel de Soporte Primario:** {_format_curr(support_1)}
- **Nivel de Resistencia Primaria:** {_format_curr(resistance_1)}
- **Amplitud del Rango Extremo:** {range_pct:.2f}%

---

## 3. Perfil de Volumen y Volatilidad
- **Volumen Total Acumulado:** {volume_24h:,.2f} {clean_sym.replace('USDT', '')}
- **Desviación Estándar de Cierre:** {_format_curr(volatility)}
- **Evaluación de Riesgo:** {"Volatilidad contenida" if range_pct < 4.0 else "Alta volatilidad registrada en el periodo"}.

---

## 4. Trazabilidad y Descargo de Responsabilidad
- **ID de Auditoría:** `REP_{clean_sym}_{int(datetime.now(timezone.utc).timestamp())}`
- **Entorno de Verificación:** Plataforma Arca / DuckDB OLAP sobre MinIO Data Lake.
- **Nota Legal:** {DISCLAIMER}
"""

    return {
        "symbol": clean_sym,
        "timeframe": timeframe,
        "depth": depth,
        "current_price": current_price,
        "return_pct": return_pct,
        "vwap": vwap,
        "support_level": support_1,
        "resistance_level": resistance_1,
        "volume": volume_24h,
        "volatility": volatility,
        "source": source_layer,
        "cutoff_time": cutoff_time,
        "markdown": markdown_content.strip(),
        "generated_at": now_iso,
    }
