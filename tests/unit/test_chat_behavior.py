"""
Pruebas unitarias de comportamiento del Chat del Copiloto (Punto 5.B).
Valida que:
  - El activo y la temporalidad seleccionados lleguen al backend.
  - Las preguntas de seguimiento reciban el historial correspondiente.
  - No se mezcle el historial de conversaciones diferentes (aislamiento).
  - Se respeten los límites (12 turnos) y la expiración (30 minutos).
  - Limpiar el chat cree una sesión limpia.
  - Cada respuesta identifique correctamente el proveedor y modelo (Groq, Ollama, Deterministic, Router).
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, patch

from backend.app.agent.llm_service import LLMService, _history
from backend.app.config import Settings
from backend.app.models import ChatRequest, ChatResponse, ToolCallRecord
from backend.app.agent.tools import ToolResult

pytestmark = [pytest.mark.unit, pytest.mark.offline]


def make_test_settings(groq_key="", ollama_url=""):
    return Settings(
        _env_file=None,
        GROQ_API_KEY=groq_key,
        OLLAMA_BASE_URL=ollama_url,
        GROQ_MODEL="llama-3.3-70b-versatile",
        OLLAMA_MODEL="llama3.2:3b",
    )


# ------------------------------------------------------------------------------
# 1. El activo y temporalidad sugeridos llegan al backend y son respetados
# ------------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_symbol_and_interval_propagation(monkeypatch):
    # Caso 1: consulta genérica sin activo en el texto; debe adoptar el symbol e interval del request
    received_requests = []
    service = LLMService(settings=make_test_settings())

    async def mock_answer(req: ChatRequest):
        received_requests.append(req)
        return ChatResponse(
            provider="deterministic",
            model=None,
            answer="Respuesta simulada",
            asset=req.symbol,
            cutoff_time="2026-11-13T00:00:00Z",
            disclaimer="Test disclaimer",
            latency_ms=10.0,
        )

    monkeypatch.setattr(service, "_answer", mock_answer)
    req1 = ChatRequest(message="¿Cómo está el RSI y la tendencia?", symbol="SOLUSDT", interval="4h", conversation_id="conv-1")
    resp1 = await service.answer(req1)
    assert received_requests[0].symbol == "SOLUSDT"
    assert received_requests[0].interval == "4h"
    assert resp1.asset == "SOLUSDT"

    # Caso 2: consulta con activo explícito ("bitcoin") en el texto -> normaliza a BTCUSDT
    service_alias = LLMService(settings=make_test_settings())
    tr = ToolResult(
        name="query_metrics",
        arguments={"symbol": "BTCUSDT", "window": "24h"},
        payload={"current_price": 50000.0, "return_24h": 1.0, "volume_24h": 100.0, "vwap": 49500.0},
        summary="BTCUSDT · precio=$50,000 · retorno=+1.00% · VWAP=$49,500 · volumen=100.00",
    )
    monkeypatch.setattr(service_alias.tools, "execute", lambda name, args: tr)
    resp2 = await service_alias._answer(ChatRequest(message="¿Cómo se ve el precio de bitcoin?", symbol="ETHUSDT", interval="15m"))
    assert resp2.asset == "BTCUSDT"


# ------------------------------------------------------------------------------
# 2. Historial de preguntas de seguimiento y aislamiento de sesiones
# ------------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_follow_up_history_and_session_isolation(monkeypatch):
    service = LLMService(settings=make_test_settings())
    history_per_call = []

    async def fake_answer(req: ChatRequest):
        history_per_call.append((req.conversation_id, list(_history.get())))
        return ChatResponse(
            provider="deterministic",
            model=None,
            answer=f"Respuesta a {req.message}",
            cutoff_time="",
            disclaimer="",
            latency_ms=1.0,
        )

    monkeypatch.setattr(service, "_answer", fake_answer)

    # Conversación A: pregunta 1
    await service.answer(ChatRequest(message="¿Cuál es el soporte de BTC?", conversation_id="conv_A"))
    assert history_per_call[-1][0] == "conv_A"
    assert history_per_call[-1][1] == []  # Primera pregunta, historial vacío

    # Conversación A: pregunta 2 (de seguimiento)
    await service.answer(ChatRequest(message="¿Y la resistencia?", conversation_id="conv_A"))
    assert history_per_call[-1][0] == "conv_A"
    assert len(history_per_call[-1][1]) == 2
    assert history_per_call[-1][1][0]["role"] == "user"
    assert history_per_call[-1][1][0]["content"] == "¿Cuál es el soporte de BTC?"
    assert history_per_call[-1][1][1]["role"] == "assistant"

    # Conversación B: no debe recibir nada de la conversación A (aislamiento estricto)
    await service.answer(ChatRequest(message="Analiza SOL", conversation_id="conv_B"))
    assert history_per_call[-1][0] == "conv_B"
    assert history_per_call[-1][1] == []  # Historial limpio


# ------------------------------------------------------------------------------
# 3. Límites de historial (12 turnos) y expiración de inactividad
# ------------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_history_bounds_and_expiry(monkeypatch):
    service = LLMService(settings=make_test_settings())

    async def fake_answer(req: ChatRequest):
        return ChatResponse(
            provider="deterministic",
            model=None,
            answer="ok",
            cutoff_time="",
            disclaimer="",
            latency_ms=1.0,
        )

    monkeypatch.setattr(service, "_answer", fake_answer)

    # Enviar 10 preguntas sucesivas (generaría 20 mensajes sin límite)
    for i in range(10):
        await service.answer(ChatRequest(message=f"Pregunta {i}", conversation_id="bounded_conv"))

    turns = service.conversations["bounded_conv"][1]
    # Límite estricto: máximo 12 turnos (6 pares user/assistant)
    assert len(turns) <= 12

    # Simular expiración de 30 minutos (1801 segundos atrás)
    service.conversations["bounded_conv"] = (1.0, turns)  # timestamp casi cero
    seen = []

    async def check_empty_history(req: ChatRequest):
        seen.append(list(_history.get()))
        return ChatResponse(provider="deterministic", model=None, answer="ok", cutoff_time="", disclaimer="", latency_ms=0)

    monkeypatch.setattr(service, "_answer", check_empty_history)

    await service.answer(ChatRequest(message="Nueva pregunta tras expiración", conversation_id="bounded_conv"))
    assert seen[-1] == []  # El historial expirado fue purgado


# ------------------------------------------------------------------------------
# 4. Limpiar el chat inicia una conversación nueva
# ------------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_chat_reset_creates_fresh_conversation(monkeypatch):
    service = LLMService(settings=make_test_settings())
    seen = []

    async def fake_answer(req: ChatRequest):
        seen.append((req.conversation_id, list(_history.get())))
        return ChatResponse(provider="deterministic", model=None, answer="ok", cutoff_time="", disclaimer="", latency_ms=0)

    monkeypatch.setattr(service, "_answer", fake_answer)

    # Sesión original
    cid_old = "session-1"
    await service.answer(ChatRequest(message="P1", conversation_id=cid_old))
    await service.answer(ChatRequest(message="P2", conversation_id=cid_old))
    assert len(seen[-1][1]) == 2

    # Usuario presiona "Limpiar chat" en frontend -> genera nuevo randomUUID
    cid_new = "session-2"
    await service.answer(ChatRequest(message="P1 nueva", conversation_id=cid_new))
    assert seen[-1][0] == cid_new
    assert seen[-1][1] == []  # Sesión limpia sin arrastre previo


# ------------------------------------------------------------------------------
# 5. Identificación inequívoca del proveedor y modelo en cada caso
# ------------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_response_identifies_provider_and_model_router():
    """El router semántico debe responder con provider='router' y model=None."""
    service = LLMService(settings=make_test_settings())
    resp = await service.answer(ChatRequest(message="Hola", conversation_id="test-router"))
    assert resp.provider == "router"
    assert resp.model is None
    assert resp.provenance == "ROUTER_GUARD"


@pytest.mark.asyncio
async def test_response_identifies_provider_and_model_deterministic(monkeypatch):
    """El respaldo determinista debe responder con provider='deterministic' y model=None."""
    service = LLMService(settings=make_test_settings(groq_key="", ollama_url=""))

    tr = ToolResult(
        name="query_metrics",
        arguments={"symbol": "BTCUSDT", "window": "24h"},
        payload={"current_price": 65000.0, "return_24h": -2.0, "volume_24h": 500.0, "vwap": 64500.0},
        summary="BTCUSDT · precio=$65,000 · retorno=-2.00% · VWAP=$64,500 · volumen=500.00",
        source="unit_test",
        cutoff_time="2026-11-13T00:00:00Z",
    )
    monkeypatch.setattr(service.tools, "execute", lambda name, args: tr)

    resp = await service.answer(ChatRequest(message="¿Cómo está el volumen de BTC?", conversation_id="test-det"))
    assert resp.provider == "deterministic"
    assert resp.model is None
    assert "estadísticas reales calculadas" in resp.answer.lower()


@pytest.mark.asyncio
async def test_response_identifies_provider_and_model_groq(monkeypatch):
    """Groq Cloud debe identificarse como provider='groq' y model=GROQ_MODEL."""
    service = LLMService(settings=make_test_settings(groq_key="gsk_test_mock_key"))

    tr = ToolResult(
        name="query_metrics",
        arguments={"symbol": "BTCUSDT", "window": "24h"},
        payload={"current_price": 70000.0, "return_24h": 3.0, "volume_24h": 1000.0, "vwap": 69000.0},
        summary="BTCUSDT · precio=$70,000 · retorno=+3.00%",
        source="unit_test",
    )

    async def mock_run_groq(msg, sym, interval):
        return {
            "answer": "BTCUSDT sube 3.0% en 24h cotizando a $70,000 USDT con volumen de 1000 BTCUSDT.",
            "sql": "SELECT 1;",
            "tool_results": [tr],
            "tool_records": [ToolCallRecord(name=tr.name, arguments=tr.arguments, result_summary=tr.summary)],
        }

    monkeypatch.setattr(service, "_run_groq", mock_run_groq)

    resp = await service.answer(ChatRequest(message="¿Cómo está el precio de BTCUSDT en 24h?", conversation_id="test-groq"))
    assert resp.provider == "groq"
    assert resp.model == "llama-3.3-70b-versatile"


@pytest.mark.asyncio
async def test_response_identifies_provider_and_model_ollama(monkeypatch):
    """Ollama local debe identificarse como provider='ollama' y model=OLLAMA_MODEL."""
    service = LLMService(settings=make_test_settings(groq_key="", ollama_url="http://localhost:11434"))

    tr = ToolResult(
        name="query_metrics",
        arguments={"symbol": "BTCUSDT", "window": "24h"},
        payload={"current_price": 70000.0, "return_24h": 3.0, "volume_24h": 1000.0, "vwap": 69000.0},
        summary="BTCUSDT · precio=$70,000 · retorno=+3.00%",
        source="unit_test",
    )

    async def mock_run_ollama(msg, sym, interval):
        return {
            "answer": "BTCUSDT cotiza a $70,000 USDT.",
            "sql": None,
            "tool_results": [tr],
            "tool_records": [ToolCallRecord(name=tr.name, arguments=tr.arguments, result_summary=tr.summary)],
        }

    monkeypatch.setattr(service, "_run_ollama", mock_run_ollama)

    resp = await service.answer(ChatRequest(message="¿A cuánto cotiza BTC?", conversation_id="test-ollama"))
    assert resp.provider == "ollama"
    assert resp.model == "llama3.2:3b"
