"""
Pruebas unitarias para el subsistema de Salud / Diagnóstico (/health) (Punto 5.C).
Valida que:
  - Se distinga el estado independiente de Binance, MinIO, DuckDB, Ollama y Groq.
  - Se distinga un servicio accesible de un modelo realmente disponible (ej. Ollama 'model_missing').
  - Groq no configurado devuelva 'not_configured'.
  - El estado global sea 'healthy' solo cuando los servicios críticos y al menos un LLM están operativos, y 'degraded' en caso contrario.
"""

import asyncio
import pytest
from unittest.mock import MagicMock

import backend.app.health as health
from backend.app.config import Settings

pytestmark = [pytest.mark.unit, pytest.mark.offline]


class MockResponse:
    def __init__(self, data, status_code=200):
        self._data = data
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP Error {self.status_code}")

    def json(self):
        return self._data


def create_mock_client(probe_map):
    class MockAsyncClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def get(self, url, headers=None, **kwargs):
            for pattern, outcome in probe_map.items():
                if pattern in url:
                    if isinstance(outcome, Exception):
                        raise outcome
                    return MockResponse(outcome)
            return MockResponse({})

    return MockAsyncClient


@pytest.mark.asyncio
async def test_health_all_services_healthy(monkeypatch):
    """Todos los servicios y modelos disponibles -> healthy."""
    settings = Settings(
        _env_file=None,
        GROQ_API_KEY="test_key",
        GROQ_MODEL="llama-3.3-70b-versatile",
        OLLAMA_MODEL="llama3.2:3b",
    )

    probe_map = {
        "/api/v3/ping": {},
        "/api/tags": {"models": [{"name": "llama3.2:3b"}]},
        "/models": {"data": [{"id": "llama-3.3-70b-versatile"}]},
    }

    monkeypatch.setattr(health.httpx, "AsyncClient", create_mock_client(probe_map))

    mock_s3 = MagicMock()
    monkeypatch.setattr(health.boto3, "client", lambda *args, **kwargs: mock_s3)

    res = await health.check_health(settings)
    assert res.status == "healthy"
    assert res.services.api == "operational"
    assert res.services.minio == "connected"
    assert res.services.duckdb == "operational"
    assert res.services.binance == "available"
    assert res.services.ollama == "available"
    assert res.services.groq == "available"


@pytest.mark.asyncio
async def test_health_ollama_model_missing(monkeypatch):
    """Ollama responde HTTP 200 pero no tiene el modelo configurado -> 'model_missing'."""
    settings = Settings(
        _env_file=None,
        GROQ_API_KEY="",  # Groq no configurado
        OLLAMA_MODEL="llama3.2:3b",
    )

    probe_map = {
        "/api/v3/ping": {},
        "/api/tags": {"models": [{"name": "mistral:7b"}, {"name": "qwen2.5:latest"}]},  # No está llama3.2:3b
    }

    monkeypatch.setattr(health.httpx, "AsyncClient", create_mock_client(probe_map))
    mock_s3 = MagicMock()
    monkeypatch.setattr(health.boto3, "client", lambda *args, **kwargs: mock_s3)

    res = await health.check_health(settings)
    assert res.status == "degraded"
    assert res.services.ollama == "model_missing"
    assert res.services.groq == "not_configured"


@pytest.mark.asyncio
async def test_health_groq_unavailable_and_ollama_unavailable(monkeypatch):
    """Groq con API key pero endpoint caído, Ollama offline -> ambos unavailable."""
    settings = Settings(
        _env_file=None,
        GROQ_API_KEY="invalid_or_expired_key",
        OLLAMA_MODEL="llama3.2:3b",
    )

    probe_map = {
        "/api/v3/ping": {},
        "/api/tags": RuntimeError("Ollama daemon unreachable"),
        "/models": RuntimeError("Groq API 401 Unauthorized"),
    }

    monkeypatch.setattr(health.httpx, "AsyncClient", create_mock_client(probe_map))
    mock_s3 = MagicMock()
    monkeypatch.setattr(health.boto3, "client", lambda *args, **kwargs: mock_s3)

    res = await health.check_health(settings)
    assert res.status == "degraded"
    assert res.services.ollama == "unavailable"
    assert res.services.groq == "unavailable"


@pytest.mark.asyncio
async def test_health_minio_disconnected(monkeypatch):
    """MinIO caído -> minio='disconnected' y status='degraded'."""
    settings = Settings(
        _env_file=None,
        GROQ_API_KEY="",
        OLLAMA_MODEL="llama3.2:3b",
    )

    probe_map = {
        "/api/v3/ping": {},
        "/api/tags": {"models": [{"name": "llama3.2:3b"}]},
    }

    monkeypatch.setattr(health.httpx, "AsyncClient", create_mock_client(probe_map))

    def mock_broken_s3(*args, **kwargs):
        raise ConnectionRefusedError("MinIO port 9000 unreachable")

    monkeypatch.setattr(health.boto3, "client", mock_broken_s3)

    res = await health.check_health(settings)
    assert res.services.minio == "disconnected"
    assert res.status == "degraded"


@pytest.mark.asyncio
async def test_health_binance_offline(monkeypatch):
    """Binance no responde al ping -> binance='unavailable' y status='degraded'."""
    settings = Settings(
        _env_file=None,
        GROQ_API_KEY="",
        OLLAMA_MODEL="llama3.2:3b",
    )

    probe_map = {
        "/api/v3/ping": RuntimeError("Binance API timeout"),
        "/api/tags": {"models": [{"name": "llama3.2:3b"}]},
    }

    monkeypatch.setattr(health.httpx, "AsyncClient", create_mock_client(probe_map))
    mock_s3 = MagicMock()
    monkeypatch.setattr(health.boto3, "client", lambda *args, **kwargs: mock_s3)

    res = await health.check_health(settings)
    assert res.services.binance == "unavailable"
    assert res.status == "degraded"
