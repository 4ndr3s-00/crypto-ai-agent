"""
Registro de herramientas analíticas de solo lectura tipadas para Groq / Ollama (US-08).

Permite que el agente consulte datos empíricos de mercado (DuckDB sobre MinIO
o Binance en vivo) de forma aislada, sin acceso a shell ni SQL destructivo.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field, ValidationError

from backend.app.database.binance_live import (
    ExchangeUnavailable,
    get_live_klines,
    get_live_ticker,
    is_stale_cutoff,
)
from backend.app.database.queries import query_market_metrics, query_market_ohlcv

logger = logging.getLogger("backend.tools")

WINDOWS = ("1h", "4h", "24h", "7d")
INTERVALS = ("1m", "5m", "15m", "1h", "4h", "1d")
SUPPORTED_SYMBOLS = ("BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT")


class MetricsArgs(BaseModel):
    symbol: Literal["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT"] = "BTCUSDT"
    window: Literal["1h", "4h", "24h", "7d", "30d"] = "24h"


class TimeseriesArgs(BaseModel):
    symbol: Literal["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT"] = "BTCUSDT"
    interval: Literal["1m", "5m", "15m", "1h", "4h", "1d"] = "15m"
    limit: int = Field(default=96, ge=1, le=1000)


class ReportArgs(BaseModel):
    symbol: Literal["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT"] = "BTCUSDT"
    timeframe: Literal["24h", "7d", "30d"] = "24h"
    depth: Literal["summary", "detailed"] = "detailed"


TOOL_SPECS: List[Dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "query_metrics",
            "description": (
                "Calcula métricas agregadas de mercado (precio actual, retorno porcentual, "
                "volumen, VWAP y varianza) para un par y ventana temporal."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "symbol": {"type": "string", "enum": list(SUPPORTED_SYMBOLS)},
                    "window": {"type": "string", "enum": list(WINDOWS)},
                },
                "required": ["symbol", "window"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "query_timeseries",
            "description": (
                "Devuelve velas japonesas OHLCV para un activo, intervalo y límite de velas. "
                "Usar para análisis técnico, tendencias, visualización de gráficos y series temporales."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "symbol": {"type": "string", "enum": list(SUPPORTED_SYMBOLS)},
                    "interval": {"type": "string", "enum": list(INTERVALS)},
                    "limit": {"type": "integer", "minimum": 1, "maximum": 1000},
                },
                "required": ["symbol", "interval", "limit"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "generate_market_report",
            "description": (
                "Genera un informe cuantitativo completo con niveles de soporte/resistencia, "
                "diagnóstico de volatilidad, resumen de volumen y tendencia para un par."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "symbol": {"type": "string", "enum": list(SUPPORTED_SYMBOLS)},
                    "timeframe": {"type": "string", "enum": ["24h", "7d", "30d"]},
                    "depth": {"type": "string", "enum": ["summary", "detailed"]},
                },
                "required": ["symbol", "timeframe"],
                "additionalProperties": False,
            },
        },
    },
]


@dataclass
class ToolResult:
    name: str
    arguments: Dict[str, Any]
    payload: Dict[str, Any] = field(default_factory=dict)
    summary: str = ""
    source: str = ""
    cutoff_time: str = ""
    provenance: str = "DUCKDB_OLAP"
    sql: Optional[str] = None
    ok: bool = True
    error: Optional[str] = None


def _format_money(value: float) -> str:
    return f"${value:,.2f}"


class ToolRegistry:
    @property
    def specs(self) -> List[Dict[str, Any]]:
        return TOOL_SPECS

    def execute(self, name: str, arguments: Optional[Dict[str, Any]] = None) -> ToolResult:
        args = arguments or {}
        try:
            if name == "query_metrics":
                return self._metrics(MetricsArgs.model_validate(args))
            if name == "query_timeseries":
                return self._timeseries(TimeseriesArgs.model_validate(args))
            if name == "generate_market_report":
                return self._report(ReportArgs.model_validate(args))
            return ToolResult(
                name=name,
                arguments=args,
                ok=False,
                error=f"Herramienta no autorizada: {name}",
            )
        except ValidationError as exc:
            return ToolResult(
                name=name,
                arguments=args,
                ok=False,
                error=f"Argumentos inválidos: {exc.errors()}",
            )
        except Exception as exc:
            logger.error("Error al ejecutar herramienta '%s': %s", name, exc)
            return ToolResult(name=name, arguments=args, ok=False, error=str(exc))

    def _metrics(self, args: MetricsArgs) -> ToolResult:
        symbol = args.symbol
        # 1. Intentar primero con DuckDB sobre MinIO
        duck_res = query_market_metrics(symbol, window=args.window)
        cutoff = duck_res.get("cutoff_time", "")
        if duck_res.get("current_price", 0.0) > 0 and not is_stale_cutoff(cutoff):
            p = duck_res
            summary = (
                f"{symbol} · precio={_format_money(p['current_price'])} · "
                f"retorno={p['return_24h']:+.2f}% · VWAP={_format_money(p['vwap'])} · "
                f"volumen={p['volume_24h']:,.2f}"
            )
            return ToolResult(
                name="query_metrics",
                arguments=args.model_dump(),
                payload=p,
                summary=summary,
                source=p.get("source", "minio_parquet_historical"),
                cutoff_time=p.get("cutoff_time", ""),
                provenance="DUCKDB_OLAP",
                sql=(
                    f"SELECT arg_max(close, dt) AS current_price, sum(close*volume)/sum(volume) AS vwap\n"
                    f"FROM read_parquet('s3://market-lake/historical/source=binance/symbol={symbol}/*/*.parquet');"
                ),
            )

        # 2. Si no hay datos o están desactualizados en MinIO, usar Binance Live al segundo
        live = get_live_ticker(symbol, window=args.window)
        summary = (
            f"{symbol} · precio={_format_money(live['current_price'])} · "
            f"retorno={live['return_24h']:+.2f}% · VWAP={_format_money(live['vwap'])} · "
            f"volumen={live['volume_24h']:,.2f}"
        )
        return ToolResult(
            name="query_metrics",
            arguments=args.model_dump(),
            payload=live,
            summary=summary,
            source="binance_live",
            cutoff_time=live.get("cutoff_time", ""),
            provenance="EXCHANGE_LIVE",
        )

    def _timeseries(self, args: TimeseriesArgs) -> ToolResult:
        symbol = args.symbol
        duck_res = query_market_ohlcv(symbol, interval=args.interval, limit=args.limit)
        candles = duck_res.get("candles", [])
        cutoff = duck_res.get("cutoff_time", "")

        if not candles or is_stale_cutoff(cutoff):
            # Usar Binance Live si el Data Lake aún no tiene particiones o están desactualizadas
            live = get_live_klines(symbol, interval=args.interval, limit=args.limit)
            candles = live.get("candles", [])
            last = candles[-1] if candles else {}
            summary = (
                f"{symbol} (Live) · {args.interval} · {len(candles)} velas · "
                f"último cierre={_format_money(last.get('close', 0.0))}"
            )
            return ToolResult(
                name="query_timeseries",
                arguments=args.model_dump(),
                payload=live,
                summary=summary,
                source="binance_live",
                cutoff_time=live.get("cutoff_time", ""),
                provenance="EXCHANGE_LIVE",
            )

        last = candles[-1]
        summary = (
            f"{symbol} · {args.interval} · {len(candles)} velas · "
            f"último cierre={_format_money(last.get('close', 0.0))}"
        )
        return ToolResult(
            name="query_timeseries",
            arguments=args.model_dump(),
            payload=duck_res,
            summary=summary,
            source="minio_parquet_historical",
            cutoff_time=duck_res.get("cutoff_time", ""),
            provenance="DUCKDB_OLAP",
            sql=(
                f"SELECT time_bucket(INTERVAL '{args.interval}', dt), max(high), min(low), arg_max(close, dt)\n"
                f"FROM read_parquet('s3://market-lake/historical/source=binance/symbol={symbol}/*/*.parquet')\n"
                f"GROUP BY 1 ORDER BY 1 DESC LIMIT {args.limit};"
            ),
        )

    def _report(self, args: ReportArgs) -> ToolResult:
        symbol = args.symbol
        metrics = self._metrics(MetricsArgs(symbol=symbol, window=args.timeframe)).payload
        timeseries = self._timeseries(TimeseriesArgs(symbol=symbol, interval="1h", limit={"24h": 24, "7d": 168, "30d": 720}[args.timeframe])).payload
        candles = timeseries.get("candles", [])

        highs = [c["high"] for c in candles] if candles else [metrics.get("high", 0.0)]
        lows = [c["low"] for c in candles] if candles else [metrics.get("low", 0.0)]

        support = min(lows) if lows else metrics.get("low", 0.0)
        resistance = max(highs) if highs else metrics.get("high", 0.0)

        report_payload = {
            "symbol": symbol,
            "timeframe": args.timeframe,
            "current_price": metrics.get("current_price", 0.0),
            "return_pct": metrics.get("return_24h", 0.0),
            "vwap": metrics.get("vwap", 0.0),
            "volume_24h": metrics.get("volume_24h", 0.0),
            "support_level": support,
            "resistance_level": resistance,
            "volatility": metrics.get("price_variance", 0.0),
            "source": metrics.get("source", "minio_parquet_historical"),
            "cutoff_time": metrics.get("cutoff_time", ""),
        }

        summary = (
            f"Informe Cuantitativo {symbol} [{args.timeframe}]: Precio={_format_money(report_payload['current_price'])}, "
            f"Retorno={report_payload['return_pct']:+.2f}%, Soporte={_format_money(support)}, "
            f"Resistencia={_format_money(resistance)}, VWAP={_format_money(report_payload['vwap'])}"
        )

        return ToolResult(
            name="generate_market_report",
            arguments=args.model_dump(),
            payload=report_payload,
            summary=summary,
            source=report_payload["source"],
            cutoff_time=report_payload["cutoff_time"],
            provenance="DUCKDB_OLAP",
        )
