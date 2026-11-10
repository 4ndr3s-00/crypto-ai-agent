"""
Pruebas unitarias para el registro de herramientas tipadas del agente (US-08).
"""

from backend.app.agent.tools import ToolRegistry, ToolResult


def test_tool_registry_specs():
    registry = ToolRegistry()
    specs = registry.specs
    names = [s["function"]["name"] for s in specs]

    assert "query_metrics" in names
    assert "query_timeseries" in names
    assert "generate_market_report" in names


def test_tool_registry_unauthorized_call():
    registry = ToolRegistry()
    res = registry.execute("drop_database", {"all": True})

    assert not res.ok
    assert "no autorizada" in res.error.lower()


def test_tool_metrics_execution():
    registry = ToolRegistry()
    res = registry.execute("query_metrics", {"symbol": "BTCUSDT", "window": "24h"})

    assert isinstance(res, ToolResult)
    assert res.ok
    assert res.name == "query_metrics"
    assert res.payload["symbol"] == "BTCUSDT"
    assert res.payload["current_price"] > 0
    assert "BTCUSDT" in res.summary


def test_tool_timeseries_execution():
    registry = ToolRegistry()
    res = registry.execute("query_timeseries", {"symbol": "BTCUSDT", "interval": "1h", "limit": 10})

    assert isinstance(res, ToolResult)
    assert res.ok
    assert res.name == "query_timeseries"
    assert len(res.payload["candles"]) > 0


def test_tool_report_execution():
    registry = ToolRegistry()
    res = registry.execute("generate_market_report", {"symbol": "BTCUSDT", "timeframe": "24h"})

    assert isinstance(res, ToolResult)
    assert res.ok
    assert res.name == "generate_market_report"
    assert "support_level" in res.payload
    assert "resistance_level" in res.payload
    assert res.payload["support_level"] > 0
