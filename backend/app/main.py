"""
Servidor FastAPI para la Plataforma Crypto AI Agent (US-06).

Expone endpoints REST y chat interactivo con el Agente Arca,
consultas analíticas DuckDB sobre MinIO y métricas en vivo.
"""

from __future__ import annotations

import logging
import time
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.app.agent.llm_service import LLMService
from backend.app.config import get_settings
from backend.app.database.binance_live import (
    get_live_klines,
    get_live_ticker,
    get_technical_summary,
    is_stale_cutoff,
)
from backend.app.database.duckdb_client import get_duckdb_client
from backend.app.database.queries import query_market_metrics, query_market_ohlcv
from backend.app.models import (
    Candle,
    ChatChart,
    ChatRequest,
    ChatResponse,
    HealthResponse,
    HealthServices,
    MetricsResponse,
    OHLCVResponse,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("backend.main")

settings = get_settings()

app = FastAPI(
    title="Crypto AI Agent Platform - Serving API",
    version="1.0.0",
    description="API analítica de mercado crypto impulsada por el Agente Arca, DuckDB y MinIO.",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configuración CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_origins_list),
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# Inicializar servicios
llm_service = LLMService(settings=settings)


@app.get("/health", response_model=HealthResponse, tags=["Sistema"])
async def health_check() -> HealthResponse:
    from backend.app.health import check_health
    return await check_health(settings)


@app.post("/api/chat", response_model=ChatResponse, tags=["Agente Arca"])
async def chat_endpoint(request: ChatRequest) -> ChatResponse:
    """
    Canal de interacción en lenguaje natural con el Agente Arca.
    Ejecuta Function Calling, consultas DuckDB sobre MinIO, fact-checking y construcción de gráficos.
    """
    try:
        response = await llm_service.answer(request)
        return response
    except Exception as exc:
        logger.error("Error no controlado en chat_endpoint: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No se pudo procesar la consulta. Inténtalo de nuevo.",
        ) from exc


@app.get("/api/market/ohlcv", response_model=OHLCVResponse, tags=["Mercado"])
def get_ohlcv(
    symbol: str = Query(default="BTCUSDT", pattern=r"^[A-Z0-9]{2,20}$", description="Símbolo del par (ej. BTCUSDT)"),
    interval: str = Query(default="15m", description="Temporalidad (1m, 5m, 15m, 1h, 4h, 1d)"),
    limit: int = Query(default=96, ge=1, le=1000, description="Cantidad de velas"),
) -> OHLCVResponse:
    """
    Consulta series temporales OHLCV agregadas desde DuckDB/MinIO o Binance Live en tiempo real.
    """
    res = query_market_ohlcv(symbol=symbol, interval=interval, limit=limit)
    cutoff = res.get("cutoff_time", "")
    candles_data = res.get("candles", [])

    if not candles_data or is_stale_cutoff(cutoff):
        live = get_live_klines(symbol=symbol, interval=interval, limit=limit)
        candles_data = live.get("candles", [])
        res["source"] = live.get("source", "binance_live")
        res["cutoff_time"] = live.get("cutoff_time", "")
        res["count"] = len(candles_data)
        res["latency_ms"] = 0.0

    candles = [
        Candle(
            timestamp=c["timestamp"],
            open=c["open"],
            high=c["high"],
            low=c["low"],
            close=c["close"],
            volume=c["volume"],
        )
        for c in candles_data
    ]
    return OHLCVResponse(
        symbol=res["symbol"],
        interval=res["interval"],
        count=len(candles),
        candles=candles,
        source=res["source"],
        cutoff_time=res["cutoff_time"],
        latency_ms=res["latency_ms"],
    )


@app.get("/api/market/metrics", response_model=MetricsResponse, tags=["Mercado"])
def get_metrics(
    symbol: str = Query(default="BTCUSDT", pattern=r"^[A-Z0-9]{2,20}$", description="Símbolo del par (ej. BTCUSDT)"),
    window: str = Query(default="24h", description="Ventana de cálculo (1h, 4h, 24h, 7d)"),
) -> MetricsResponse:
    """
    Calcula métricas financieras (VWAP, retornos, volumen acumulado, extremos) en tiempo récord.
    """
    res = query_market_metrics(symbol=symbol, window=window)
    cutoff = res.get("cutoff_time", "")
    if res.get("current_price", 0.0) > 0 and not is_stale_cutoff(cutoff):
        return MetricsResponse(
            symbol=res["symbol"],
            window=res["window"],
            current_price=res["current_price"],
            open=res["open"],
            high=res["high"],
            low=res["low"],
            return_24h=res["return_24h"],
            volume_24h=res["volume_24h"],
            vwap=res["vwap"],
            price_variance=res["price_variance"],
            source=res["source"],
            data_source=res["data_source"],
            cutoff_time=res["cutoff_time"],
            latency_ms=res["latency_ms"],
        )

    # Fallback a Binance Live si el lago aún no tiene esa fecha
    live = get_live_ticker(symbol=symbol, window=window)
    return MetricsResponse(
        symbol=live["symbol"],
        window=live["window"],
        current_price=live["current_price"],
        open=live["open"],
        high=live["high"],
        low=live["low"],
        return_24h=live["return_24h"],
        volume_24h=live["volume_24h"],
        vwap=live["vwap"],
        price_variance=live["price_variance"],
        source=live["source"],
        data_source=live["data_source"],
        cutoff_time=live["cutoff_time"],
        latency_ms=0.0,
    )


@app.get("/api/market/overview", tags=["Mercado"])
def get_overview():
    """
    Retorna un resumen de mercado para los principales activos.
    """
    symbols = settings.symbols_list
    overview_data = []
    for sym in symbols:
        try:
            ticker = get_live_ticker(sym)
            ticker["price"] = ticker.get("current_price", 0.0)
            ticker["price_change_percent_24h"] = ticker.get("return_24h", 0.0)
            ticker["high_24h"] = ticker.get("high", 0.0)
            ticker["low_24h"] = ticker.get("low", 0.0)
            overview_data.append(ticker)
        except Exception as exc:
            logger.warning("No se pudo obtener ticker en vivo para %s: %s", sym, exc)
    return {"assets": overview_data, "count": len(overview_data), "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}


@app.get("/api/market/chart", response_model=ChatChart, tags=["Mercado"])
def get_chart_spec(
    symbol: str = Query(default="BTCUSDT", pattern=r"^[A-Z0-9]{2,20}$", description="Símbolo del par (ej. BTCUSDT)"),
    interval: str = Query(default="15m", description="Temporalidad (1m, 5m, 15m, 1h, 4h, 1d)"),
    limit: int = Query(default=96, ge=1, le=1000, description="Cantidad de velas"),
) -> ChatChart:
    """
    Retorna la especificación completa del gráfico financiero con soporte de velas japonesas y VWAP.
    """
    from backend.app.agent.chart_builder import build_candlestick_chart
    from backend.app.database.binance_live import get_live_klines

    res = query_market_ohlcv(symbol=symbol, interval=interval, limit=limit)
    candles = res.get("candles", [])
    cutoff = res.get("cutoff_time", "")
    source = res.get("source", "minio_parquet_historical")

    if not candles or is_stale_cutoff(cutoff):
        live = get_live_klines(symbol=symbol, interval=interval, limit=limit)
        candles = live.get("candles", [])
        source = live.get("source", "binance_live")
        cutoff = live.get("cutoff_time", "")

    metrics = query_market_metrics(symbol=symbol, window="24h")
    vwap = metrics.get("vwap")
    if not vwap or is_stale_cutoff(metrics.get("cutoff_time", "")):
        live_ticker = get_live_ticker(symbol=symbol)
        vwap = live_ticker.get("vwap")

    return build_candlestick_chart(
        symbol=symbol,
        interval=interval,
        candles_data=candles,
        vwap=vwap,
        source=source,
        cutoff_time=cutoff,
    )


@app.get("/api/market/technical-summary", tags=["Mercado"])
def get_technical_summary_endpoint(
    symbol: str = Query(default="BTCUSDT", pattern=r"^[A-Z0-9]{2,20}$", description="Símbolo del par (ej. BTCUSDT)"),
):
    """
    Retorna el resumen técnico completo estilo TradingView (RSI 14, SMA 20, EMA 50, termómetro y horizontes de retorno).
    """
    return get_technical_summary(symbol=symbol)


@app.get("/api/reports/{symbol}", tags=["Reportes"])
def get_report(
    symbol: str,
    timeframe: str = Query(default="24h", description="Ventana de tiempo (24h, 7d, 30d)"),
    depth: str = Query(default="detailed", description="Profundidad (summary, detailed)"),
):
    """
    Genera un informe financiero cuantitativo completo para un activo.
    """
    from backend.app.agent.report_generator import generate_executive_report
    return generate_executive_report(symbol=symbol, timeframe=timeframe, depth=depth)


@app.get("/api/reports/{symbol}/export", tags=["Reportes"])
def export_report_markdown(
    symbol: str,
    timeframe: str = Query(default="24h", description="Ventana de tiempo (24h, 7d, 30d)"),
):
    """
    Descarga el reporte cuantitativo en formato Markdown (.md) limpio.
    """
    from fastapi.responses import Response
    from backend.app.agent.report_generator import generate_executive_report

    report = generate_executive_report(symbol=symbol, timeframe=timeframe)
    filename = f"reporte_{symbol.upper()}_{timeframe}.md"

    return Response(
        content=report["markdown"],
        media_type="text/markdown",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )

