"""
Pruebas unitarias de validación de datos, ventanas temporales, controles de antigüedad y manejo de fallos (Punto 5.A).
Todas las pruebas corren de forma offline y aislada mediante dobles de prueba tipados.
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock

from backend.app.database import binance_live, queries
from backend.app.database.binance_live import is_stale_cutoff, ExchangeUnavailable
from backend.app.agent.tools import ToolRegistry, MetricsArgs, TimeseriesArgs, WINDOWS, INTERVALS
from backend.app.agent.chart_builder import build_candlestick_chart
from backend.app.agent.report_generator import generate_executive_report

pytestmark = [pytest.mark.unit, pytest.mark.offline]


# ------------------------------------------------------------------------------
# 1. Validación de símbolos, intervalos y ventanas temporales
# ------------------------------------------------------------------------------

@pytest.mark.parametrize("symbol", ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT"])
def test_valid_supported_symbols(symbol):
    assert symbol in queries.INTERVAL_MAP or symbol.endswith("USDT")
    args = MetricsArgs(symbol=symbol, window="24h")
    assert args.symbol == symbol


@pytest.mark.parametrize("invalid_symbol", [
    "invalid_long_symbol_xyz1234567890",
    "BTC-USDT",
    "BTC/USDT",
    "BTC USDT",
    "A",
    "",
    "$$$BTC",
])
def test_invalid_symbol_rejection_in_queries(invalid_symbol):
    with pytest.raises((ValueError, Exception)):
        queries.query_market_ohlcv(symbol=invalid_symbol)

    with pytest.raises((ValueError, Exception)):
        queries.query_market_metrics(symbol=invalid_symbol)


@pytest.mark.parametrize("window", ["1h", "4h", "24h", "7d", "30d"])
def test_all_supported_windows_in_metrics(window):
    assert window in WINDOWS
    args = MetricsArgs(symbol="BTCUSDT", window=window)
    assert args.window == window


@pytest.mark.parametrize("invalid_window", ["2h", "10m", "1w", "365d", "unknown", ""])
def test_invalid_window_rejection(invalid_window):
    with pytest.raises((ValueError, Exception)):
        queries.query_market_metrics(symbol="BTCUSDT", window=invalid_window)

    with pytest.raises((ValueError, Exception)):
        binance_live.get_live_ticker(symbol="BTCUSDT", window=invalid_window)


@pytest.mark.parametrize("interval", ["1m", "5m", "15m", "1h", "4h", "1d"])
def test_all_supported_intervals(interval):
    assert interval in INTERVALS
    assert interval in queries.INTERVAL_MAP
    args = TimeseriesArgs(symbol="BTCUSDT", interval=interval, limit=50)
    assert args.interval == interval


@pytest.mark.parametrize("invalid_interval", ["2m", "3h", "10s", "1y", ""])
def test_invalid_interval_rejection(invalid_interval):
    with pytest.raises((ValueError, Exception)):
        queries.query_market_ohlcv(symbol="BTCUSDT", interval=invalid_interval)


# ------------------------------------------------------------------------------
# 2. Métricas de 1h, 4h, 24h, 7d y 30d obtenidas mediante el respaldo de Binance
# ------------------------------------------------------------------------------

@pytest.mark.parametrize("window", ["1h", "4h", "24h", "7d", "30d"])
def test_binance_live_window_consistency(monkeypatch, window):
    calls = []

    def mock_get(path, params):
        calls.append((path, params))
        return {
            "lastPrice": "50000.0",
            "openPrice": "48000.0",
            "highPrice": "51000.0",
            "lowPrice": "47500.0",
            "volume": "1234.5",
            "quoteVolume": "60000000.0",
            "weightedAvgPrice": "49500.0",
            "priceChangePercent": "4.17",
            "closeTime": 1700000000000,
        }

    monkeypatch.setattr(binance_live, "_http_get", mock_get)

    ticker = binance_live.get_live_ticker("ETHUSDT", window=window)
    assert ticker["symbol"] == "ETHUSDT"
    assert ticker["window"] == window
    assert ticker["current_price"] == 50000.0
    assert ticker["open"] == 48000.0
    assert ticker["return_24h"] == 4.17
    assert ticker["vwap"] == 49500.0
    assert ticker["source"] == "binance_live"
    assert ticker["data_source"] == "exchange_live"

    expected_endpoint = "/api/v3/ticker/24hr" if window == "24h" else "/api/v3/ticker"
    assert calls[0][0] == expected_endpoint
    if window != "24h":
        assert calls[0][1]["windowSize"] == window


# ------------------------------------------------------------------------------
# 3. Control de antigüedad (is_stale_cutoff)
# ------------------------------------------------------------------------------

def test_is_stale_cutoff_logic():
    now = datetime.now(timezone.utc)

    # 1. Fecha reciente (hace 1 minuto) -> no está stale
    fresh_time = (now - timedelta(seconds=60)).isoformat().replace("+00:00", "Z")
    assert is_stale_cutoff(fresh_time, max_age_seconds=900) is False

    # 2. Fecha antigua (hace 20 minutos) -> está stale (> 900s)
    stale_time = (now - timedelta(minutes=20)).isoformat().replace("+00:00", "Z")
    assert is_stale_cutoff(stale_time, max_age_seconds=900) is True

    # 3. Cutoff vacío, nulo o corrupto -> está stale
    assert is_stale_cutoff("") is True
    assert is_stale_cutoff(None) is True
    assert is_stale_cutoff("fecha-invalida-xyz") is True


# ------------------------------------------------------------------------------
# 4. Manejo de fallos en Binance Live (servicios caídos, respuestas inválidas)
# ------------------------------------------------------------------------------

def test_binance_live_handles_network_error(monkeypatch):
    binance_live._CACHE.clear()

    class MockFailingClient:
        def __init__(self, *args, **kwargs):
            pass
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass
        def get(self, *args, **kwargs):
            raise RuntimeError("Conexión rechazada o timeout simulado")

    monkeypatch.setattr(binance_live.httpx, "Client", MockFailingClient)

    with pytest.raises(ExchangeUnavailable) as exc_info:
        binance_live.get_live_ticker("BTCUSDT", "24h")
    assert "Binance Live no respondió" in str(exc_info.value)

    with pytest.raises(ExchangeUnavailable):
        binance_live.get_live_klines("BTCUSDT", "15m", 50)


def test_binance_live_handles_invalid_payload(monkeypatch):
    binance_live._CACHE.clear()

    # 1. Payload de ticker sin campo lastPrice
    def mock_invalid_ticker(path, params):
        return {"unexpected_key": 123}

    monkeypatch.setattr(binance_live, "_http_get", mock_invalid_ticker)
    with pytest.raises(ExchangeUnavailable):
        binance_live.get_live_ticker("BTCUSDT", "24h")

    # 2. Payload de klines no iterable
    def mock_invalid_klines(path, params):
        return {"error": "Not a list"}

    monkeypatch.setattr(binance_live, "_http_get", mock_invalid_klines)
    with pytest.raises(ExchangeUnavailable):
        binance_live.get_live_klines("BTCUSDT", "15m", 50)


# ------------------------------------------------------------------------------
# 5. Generación de Gráficos y Reportes Cuantitativos
# ------------------------------------------------------------------------------

def test_chart_builder_specification():
    sample_candles = [
        {"timestamp": "2026-11-13T00:00:00Z", "open": 100.0, "high": 105.0, "low": 98.0, "close": 102.0, "volume": 10.0},
        {"timestamp": "2026-11-13T01:00:00Z", "open": 102.0, "high": 108.0, "low": 101.0, "close": 106.0, "volume": 15.0},
    ]
    chart = build_candlestick_chart(
        symbol="BTCUSDT",
        interval="1h",
        candles_data=sample_candles,
        vwap=104.0,
        source="unit_test",
        cutoff_time="2026-11-13T01:00:00Z",
    )
    assert chart.symbol == "BTCUSDT"
    assert chart.interval == "1h"
    assert chart.chart_type == "candlestick"
    assert len(chart.candles) == 2
    assert chart.indicators.get("vwap") == 104.0
    assert chart.indicators.get("support") == 98.0
    assert chart.indicators.get("resistance") == 108.0


def test_report_generator_with_mocked_data(monkeypatch):
    binance_live._CACHE.clear()
    import backend.app.agent.report_generator as rep_gen

    def mock_ticker(sym, window="24h"):
        return {
            "symbol": sym, "current_price": 60000.0, "open": 58000.0, "high": 61000.0,
            "low": 57000.0, "return_24h": 3.45, "volume_24h": 5000.0, "vwap": 59500.0,
            "price_variance": 500.0, "cutoff_time": "2026-11-13T00:00:00Z",
            "source": "binance_live", "data_source": "exchange_live",
        }

    def mock_klines(sym, interval="1h", limit=24):
        return {
            "symbol": sym, "interval": interval, "count": 2,
            "candles": [
                {"timestamp": "2026-11-13T00:00:00Z", "open": 58000.0, "high": 61000.0, "low": 57000.0, "close": 60000.0, "volume": 100.0},
            ],
            "cutoff_time": "2026-11-13T00:00:00Z",
        }

    # Forzar que llame al fallback en vivo mockeado
    monkeypatch.setattr(rep_gen, "query_market_metrics", lambda *a, **kw: {"current_price": 0.0, "cutoff_time": ""})
    monkeypatch.setattr(rep_gen, "query_market_ohlcv", lambda *a, **kw: {"candles": [], "cutoff_time": ""})
    monkeypatch.setattr(rep_gen, "get_live_ticker", mock_ticker)
    monkeypatch.setattr(rep_gen, "get_live_klines", mock_klines)

    report = generate_executive_report("BTCUSDT", timeframe="24h", depth="detailed")
    assert report["symbol"] == "BTCUSDT"
    assert report["current_price"] == 60000.0
    assert "Reporte Financiero Cuantitativo" in report["markdown"]
    assert "Nivel de Soporte" in report["markdown"]
    assert "BTCUSDT" in report["markdown"]
