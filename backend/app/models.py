"""
Contratos y modelos Pydantic v2 para la Serving API, Chat y Gráficos (US-06).

Define tipado estricto para las interacciones con el Agente de IA,
estructuras de gráficos financieros y métricas de mercado sin mocks.
"""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional
from pydantic import AliasChoices, BaseModel, ConfigDict, Field

Provenance = Literal["MINIO_LAKE", "EXCHANGE_LIVE", "DUCKDB_OLAP", "ROUTER_GUARD"]
SourceKind = Literal["tool", "database", "exchange", "guardrail"]
DataSource = Literal["postgres_reconciled", "minio_parquet", "exchange_live", "no_data_available"]


class Candle(BaseModel):
    model_config = ConfigDict(frozen=True)

    timestamp: str = Field(description="Fecha y hora en formato ISO 8601 UTC")
    open: float = Field(description="Precio de apertura")
    high: float = Field(description="Precio máximo")
    low: float = Field(description="Precio mínimo")
    close: float = Field(description="Precio de cierre")
    volume: float = Field(description="Volumen negociado")


class ChatChart(BaseModel):
    model_config = ConfigDict(frozen=True)

    symbol: str
    interval: str
    chart_type: Literal["candlestick", "line", "volume_histogram"] = "candlestick"
    candles: List[Candle] = Field(default_factory=list)
    indicators: Dict[str, Any] = Field(default_factory=dict)
    source: str = "minio_parquet_historical"
    data_source: DataSource = "minio_parquet"
    cutoff_time: str = ""


class ToolCallRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    arguments: Dict[str, Any]
    result_summary: str


class SourceReference(BaseModel):
    model_config = ConfigDict(frozen=True)

    source: str
    title: Optional[str] = None
    snippet: Optional[str] = None
    kind: SourceKind = "tool"


class ChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message: str = Field(
        min_length=1,
        max_length=4000,
        validation_alias=AliasChoices("message", "query"),
        description="Consulta del usuario en lenguaje natural",
    )
    symbol: str = Field(default="BTCUSDT", description="Símbolo sugerido por el contexto")
    interval: str = Field(default="15m", description="Temporalidad sugerida para el análisis")
    include_sql: bool = Field(default=True, description="Incluir sentencias analíticas ejecutadas")


class ChatResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    answer: str = Field(description="Respuesta analítica en texto plano y profesional")
    reply: Optional[str] = Field(default=None, description="Respuesta analítica duplicada para clientes frontend")
    sql: Optional[str] = Field(default=None, description="Consulta SQL ejecutada en DuckDB si aplica")
    provenance: Provenance = "DUCKDB_OLAP"
    asset: Optional[str] = None
    source: Optional[str] = None
    sources: List[SourceReference] = Field(default_factory=list)
    cutoff_time: str
    disclaimer: str
    tool_calls: List[ToolCallRecord] = Field(default_factory=list)
    intent: Optional[str] = None
    chart: Optional[ChatChart] = None
    latency_ms: float


class MetricsResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    symbol: str
    window: str
    current_price: float
    open: float
    high: float
    low: float
    return_24h: float
    volume_24h: float
    vwap: float
    price_variance: float
    source: str
    data_source: DataSource = "minio_parquet"
    cutoff_time: str
    latency_ms: float
    error: Optional[str] = None


class OHLCVResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    symbol: str
    interval: str
    count: int
    candles: List[Candle]
    source: str
    cutoff_time: str
    latency_ms: float
    error: Optional[str] = None


class HealthServices(BaseModel):
    api: str
    minio: str
    duckdb: str
    groq: str


class HealthResponse(BaseModel):
    status: str
    application: str
    version: str
    environment: str
    services: HealthServices
    latency_ms: float
    timestamp: str
