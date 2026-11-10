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
from backend.app.database.binance_live import get_live_ticker
from backend.app.database.duckdb_client import get_duckdb_client
from backend.app.database.queries import query_market_metrics, query_market_ohlcv
from backend.app.models import (
    Candle,
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
def health_check() -> HealthResponse:
    """
    Verifica el estado de salud de la API y sus dependencias (MinIO, DuckDB, Groq).
    """
    started = time.perf_counter()

    # Chequeo DuckDB + MinIO S3
    duck_status = "operational"
    minio_status = "connected"
    try:
        duck = get_duckdb_client()
        with duck.session() as conn:
            conn.execute("SELECT 1;").fetchone()
    except Exception as exc:
        logger.warning("Fallo en healthcheck de DuckDB/MinIO: %s", exc)
        duck_status = "degraded"
        minio_status = "disconnected"

    groq_status = "configured" if settings.groq_api_key else "fallback_mode"

    latency_ms = round((time.perf_counter() - started) * 1000, 2)
    return HealthResponse(
        status="healthy" if minio_status == "connected" else "degraded",
        application="crypto-ai-agent-backend",
        version="1.0.0",
        environment=settings.environment,
        services=HealthServices(
            api="operational",
            minio=minio_status,
            duckdb=duck_status,
            groq=groq_status,
        ),
        latency_ms=latency_ms,
        timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    )


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
            detail=f"Error en el procesamiento del agente: {exc}",
        ) from exc


@app.get("/api/market/ohlcv", response_model=OHLCVResponse, tags=["Mercado"])
def get_ohlcv(
    symbol: str = Query(default="BTCUSDT", description="Símbolo del par (ej. BTCUSDT)"),
    interval: str = Query(default="15m", description="Temporalidad (1m, 5m, 15m, 1h, 4h, 1d)"),
    limit: int = Query(default=96, ge=1, le=1000, description="Cantidad de velas"),
) -> OHLCVResponse:
    """
    Consulta series temporales OHLCV agregadas desde los archivos Parquet en MinIO.
    """
    res = query_market_ohlcv(symbol=symbol, interval=interval, limit=limit)
    candles = [
        Candle(
            timestamp=c["timestamp"],
            open=c["open"],
            high=c["high"],
            low=c["low"],
            close=c["close"],
            volume=c["volume"],
        )
        for c in res.get("candles", [])
    ]
    return OHLCVResponse(
        symbol=res["symbol"],
        interval=res["interval"],
        count=res["count"],
        candles=candles,
        source=res["source"],
        cutoff_time=res["cutoff_time"],
        latency_ms=res["latency_ms"],
    )


@app.get("/api/market/metrics", response_model=MetricsResponse, tags=["Mercado"])
def get_metrics(
    symbol: str = Query(default="BTCUSDT", description="Símbolo del par (ej. BTCUSDT)"),
    window: str = Query(default="24h", description="Ventana de cálculo (1h, 4h, 24h, 7d)"),
) -> MetricsResponse:
    """
    Calcula métricas financieras (VWAP, retornos, volumen acumulado, extremos) en tiempo récord.
    """
    # Intentar primero con DuckDB
    res = query_market_metrics(symbol=symbol, window=window)
    if res.get("current_price", 0.0) > 0:
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
    live = get_live_ticker(symbol=symbol)
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
            overview_data.append(ticker)
        except Exception as exc:
            logger.warning("No se pudo obtener ticker en vivo para %s: %s", sym, exc)
    return {"assets": overview_data, "count": len(overview_data), "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
