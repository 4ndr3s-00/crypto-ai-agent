"""
Pruebas de integración de la Serving API FastAPI y Chat con Arca (US-06 y US-07).
"""

from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)


def test_api_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in {"healthy", "degraded"}
    assert data["application"] == "crypto-ai-agent-backend"
    assert "duckdb" in data["services"]
    assert "minio" in data["services"]


def test_api_market_ohlcv_endpoint():
    response = client.get("/api/market/ohlcv?symbol=BTCUSDT&interval=1h&limit=24")
    assert response.status_code == 200
    data = response.json()
    assert data["symbol"] == "BTCUSDT"
    assert data["interval"] == "1h"
    assert data["count"] > 0
    assert len(data["candles"]) == data["count"]


def test_api_market_metrics_endpoint():
    response = client.get("/api/market/metrics?symbol=BTCUSDT&window=24h")
    assert response.status_code == 200
    data = response.json()
    assert data["symbol"] == "BTCUSDT"
    assert data["current_price"] > 0
    assert data["cutoff_time"] != ""


def test_api_chat_greeting_router():
    """
    Verifica que saludos se resuelvan de inmediato por el router local sin error.
    """
    response = client.post("/api/chat", json={"message": "Hola Arca"})
    assert response.status_code == 200
    data = response.json()
    assert "Arca" in data["answer"]
    assert data["provenance"] == "ROUTER_GUARD"
    assert data["latency_ms"] < 100.0


def test_api_chat_analytics_fallback():
    """
    Verifica que una consulta analítica ejecute las herramientas y retorne gráficos y métricas.
    """
    response = client.post("/api/chat", json={"message": "¿Cómo está el precio y volumen de BTC?", "symbol": "BTCUSDT"})
    assert response.status_code == 200
    data = response.json()
    assert len(data["answer"]) > 10
    assert data["chart"] is not None
    assert data["chart"]["symbol"] == "BTCUSDT"
    assert len(data["chart"]["candles"]) > 0
    assert len(data["tool_calls"]) > 0
