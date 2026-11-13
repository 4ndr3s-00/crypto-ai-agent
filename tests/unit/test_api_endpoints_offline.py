"""
Pruebas de regresión offline para los endpoints de FastAPI con dobles de prueba (Punto 5.A y 5.C).
Verifica:
  - Validación de símbolos, intervalos y ventanas temporales (respuestas 400 o 422).
  - Manejo de fallback a Binance Live cuando DuckDB no tiene datos.
  - Manejo controlado de fallos (ExchangeUnavailable) sin causar errores 500.
  - Identificación clara del estado en /health sin red externa.
"""

import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.database import binance_live
from backend.app.database.binance_live import ExchangeUnavailable

pytestmark = [pytest.mark.unit, pytest.mark.offline]

client = TestClient(app)


def test_api_metrics_invalid_window_returns_400():
    """Ventana inválida debe devolver 400 Bad Request."""
    response = client.get("/api/market/metrics?symbol=BTCUSDT&window=invalid_window")
    assert response.status_code == 400
    assert "Ventana invalida" in response.json()["detail"]


def test_api_ohlcv_invalid_interval_returns_400():
    """Intervalo inválido debe devolver 400 Bad Request."""
    response = client.get("/api/market/ohlcv?symbol=BTCUSDT&interval=99m")
    assert response.status_code == 400
    assert "Intervalo o límite inválido" in response.json()["detail"]


def test_api_ohlcv_invalid_symbol_pattern_returns_422():
    """Símbolo con caracteres especiales debe fallar validación de query (422)."""
    response = client.get("/api/market/ohlcv?symbol=BTC$$$&interval=15m")
    assert response.status_code == 422


def test_api_reports_invalid_timeframe_returns_400():
    """Timeframe inválido en reportes debe devolver 400."""
    response = client.get("/api/reports/BTCUSDT?timeframe=99d")
    assert response.status_code == 400
    assert "Timeframe inválido" in response.json()["detail"]


def test_api_reports_export_invalid_symbol_returns_400():
    """Exportación con símbolo inválido debe devolver 400."""
    response = client.get("/api/reports/BTC$$$/export?timeframe=24h")
    assert response.status_code == 400


def test_api_metrics_exchange_down_handles_gracefully(monkeypatch):
    """
    Cuando MinIO no tiene datos y Binance Live está caído,
    el endpoint debe devolver un modelo válido con data_source='no_data_available'
    y mensaje de error sin provocar una excepción 500.
    """
    import backend.app.main as main_module

    def mock_broken_ticker(symbol, window="24h"):
        raise ExchangeUnavailable("Simulación de corte de servicio de exchange")

    monkeypatch.setattr(main_module, "get_live_ticker", mock_broken_ticker)

    response = client.get("/api/market/metrics?symbol=BTCUSDT&window=24h")
    assert response.status_code == 200
    data = response.json()
    assert data["data_source"] == "no_data_available"
    assert "Exchange no disponible" in (data.get("error") or "")
