import asyncio
import pytest
from backend.app.agent.anti_hallucination import audit_factual_consistency
from backend.app.agent.tools import ToolResult
from backend.app.agent.llm_service import LLMService, _history
from backend.app.config import Settings
from backend.app.models import ChatRequest, ChatResponse
from backend.app.database import binance_live

@pytest.mark.parametrize("text,valid", [
    ("BTCUSDT sube 2.5% en 24h", True),
    ("BTCUSDT sube 8% en 24h", False),
    ("ETHUSDT sube 2.5% en 24h", False),
    ("BTCUSDT sube 2.5% en 7d", False),
    ("BTCUSDT vale 100 COP", False),
    ("BTCUSDT vale 100 USDT", True),
    ("Volumen de 10 BTC", True),
    ("Volumen de 100 BTC", False),
    ("BTCUSDT vale $10", False),
])
def test_claim_scope(text, valid):
    result = ToolResult("query_metrics", {"symbol": "BTCUSDT", "window": "24h"},
        payload={"current_price": 100, "return_24h": 2.5, "volume_24h": 10})
    assert audit_factual_consistency(text, [result])[0] is valid

@pytest.mark.parametrize("window", ["1h", "4h", "24h", "7d", "30d"])
def test_live_window(monkeypatch, window):
    calls = []
    def get(path, params):
        calls.append((path, params))
        return dict(lastPrice="100", openPrice="90", highPrice="101", lowPrice="89",
                    volume="10", quoteVolume="1000", closeTime=1700000000000)
    monkeypatch.setattr(binance_live, "_http_get", get)
    assert binance_live.get_live_ticker("BTCUSDT", window)["window"] == window
    assert calls[0][0] == ("/api/v3/ticker/24hr" if window == "24h" else "/api/v3/ticker")
    if window != "24h":
        assert calls[0][1]["windowSize"] == window

def test_memory_isolation_expiry_and_bound(monkeypatch):
    async def run():
        service = LLMService(Settings(_env_file=None))
        seen = []
        async def answer(req):
            seen.append(list(_history.get()))
            return ChatResponse(answer="ok", cutoff_time="", disclaimer="", latency_ms=0)
        monkeypatch.setattr(service, "_answer", answer)
        await service.answer(ChatRequest(message="first", conversation_id="a"))
        await service.answer(ChatRequest(message="second", conversation_id="a"))
        await service.answer(ChatRequest(message="private", conversation_id="b"))
        assert seen[1][0]["content"] == "first"
        assert seen[2] == []
        service.conversations["a"] = (0, service.conversations["a"][1])
        await service.answer(ChatRequest(message="expired", conversation_id="a"))
        assert seen[-1] == []
        for _ in range(10):
            await service.answer(ChatRequest(message="more", conversation_id="a"))
        assert len(service.conversations["a"][1]) == 12
        await service.answer(ChatRequest(message="anonymous"))
        assert seen[-1] == []
    asyncio.run(run())

def test_health_detects_independent_failures(monkeypatch):
    import backend.app.health as health
    class Response:
        def raise_for_status(self): pass
        def json(self): return {"models": [{"name": "different-model"}]}
    class Client:
        def __init__(self, **kw): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *args): pass
        async def get(self, url, **kw):
            if "ping" in url: raise RuntimeError("offline")
            return Response()
    def unavailable(*args, **kwargs): raise RuntimeError("offline")
    monkeypatch.setattr(health.httpx, "AsyncClient", Client)
    monkeypatch.setattr(health.boto3, "client", unavailable)
    result = asyncio.run(health.check_health(Settings(_env_file=None)))
    assert result.status == "degraded"
    assert result.services.duckdb == "operational"
    assert result.services.minio == "disconnected"
    assert result.services.binance == "unavailable"
    assert result.services.ollama == "model_missing"
