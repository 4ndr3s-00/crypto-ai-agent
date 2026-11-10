"""
Esquemas Pydantic v2 para el contrato de eventos de mercado e ingesta.
Garantiza tipado estricto, serialización rápida y cero datos simulados.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional
from pydantic import BaseModel, ConfigDict, Field


class MarketEvent(BaseModel):
    """
    Contrato canónico para un evento u observación de mercado (vela de 1 minuto).
    """
    model_config = ConfigDict(extra="forbid", frozen=True)

    event_id: str = Field(description="Identificador único determinista (ej. binance_BTCUSDT_1700000000000)")
    source: str = Field(default="binance_rest", description="Origen de la extracción")
    exchange: str = Field(default="binance", description="Exchange de origen")
    symbol: str = Field(description="Par de negociación (ej. BTCUSDT)")
    event_time: str = Field(description="Marca de tiempo UTC del evento (ISO 8601)")
    ingestion_time: str = Field(description="Marca de tiempo UTC de la ingesta (ISO 8601)")
    open: float = Field(gt=0, description="Precio de apertura")
    high: float = Field(gt=0, description="Precio máximo")
    low: float = Field(gt=0, description="Precio mínimo")
    close: float = Field(gt=0, description="Precio de cierre")
    volume: float = Field(ge=0, description="Volumen negociado")
    trades_count: int = Field(ge=0, default=0, description="Número de transacciones en la vela")
    interval: str = Field(default="1m", description="Temporalidad de la observación")
    schema_version: str = Field(default="2.0.0", description="Versión del contrato de datos")


class KlineCandle(BaseModel):
    """
    Estructura ligera de vela para visualización en gráficos y cálculos analíticos.
    """
    model_config = ConfigDict(frozen=True)

    timestamp: str
    open: float
    high: float
    low: float
    close: float
    volume: float


class DailyIngestionResult(BaseModel):
    """
    Resultado resumido del lote de ingesta diaria.
    """
    symbol: str
    target_date: str
    total_events: int
    first_event_time: Optional[str] = None
    last_event_time: Optional[str] = None
    success: bool
    parquet_path: Optional[str] = None
    error: Optional[str] = None
