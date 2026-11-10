"""
Pruebas unitarias para el sistema anti-alucinación y fact-checking (US-10).
"""

from backend.app.agent.anti_hallucination import (
    audit_factual_consistency,
    clean_text_artifacts,
    enforce_anti_hallucination,
)
from backend.app.agent.tools import ToolResult
from backend.app.config import DISCLAIMER


def test_clean_text_artifacts():
    dirty_text = "Bitcoin sube 🚀📈 y está en ```$68,000```\n\n\n\nExcelente."
    cleaned = clean_text_artifacts(dirty_text)

    # Verificar que no contenga emojis ni fences de código
    assert "🚀" not in cleaned
    assert "📈" not in cleaned
    assert "```" not in cleaned
    assert "$68,000" in cleaned


def test_audit_factual_consistency_match():
    tool_res = ToolResult(
        name="query_metrics",
        arguments={"symbol": "BTCUSDT", "window": "24h"},
        payload={"current_price": 68450.0, "vwap": 68200.0, "return_24h": 2.5},
        summary="BTCUSDT · precio=$68,450.00 · VWAP=$68,200.00",
        ok=True,
    )

    valid_text = "Andrés, el precio de Bitcoin es $68,450.00 y el VWAP se ubica en $68,200.00."
    is_factual, reason = audit_factual_consistency(valid_text, [tool_res])

    assert is_factual
    assert reason is None


def test_audit_factual_consistency_hallucination_detected():
    tool_res = ToolResult(
        name="query_metrics",
        arguments={"symbol": "BTCUSDT", "window": "24h"},
        payload={"current_price": 68450.0, "vwap": 68200.0},
        summary="BTCUSDT · precio=$68,450.00",
        ok=True,
    )

    # El modelo alucina un precio inventado de $95,000.00
    hallucinated_text = "Bitcoin se disparó a $95,000.00 el día de hoy."
    is_factual, reason = audit_factual_consistency(hallucinated_text, [tool_res])

    assert not is_factual
    assert reason is not None
    assert "no figura en los datos reales" in reason


def test_enforce_anti_hallucination_override():
    tool_res = ToolResult(
        name="query_metrics",
        arguments={"symbol": "BTCUSDT", "window": "24h"},
        payload={"current_price": 68450.0},
        summary="BTCUSDT · precio=$68,450.00 · verificado",
        ok=True,
    )

    hallucinated_answer = "Andrés, BTC llegó a $150,000.00 🚀."
    enforced = enforce_anti_hallucination(hallucinated_answer, [tool_res], tool_res.summary)

    # El texto alucinado debió ser sustituido por el resumen determinista verificado
    assert "$150,000" not in enforced
    assert "BTCUSDT · precio=$68,450.00 · verificado" in enforced
    assert DISCLAIMER in enforced
