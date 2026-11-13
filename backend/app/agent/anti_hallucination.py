"""
Módulo de Integridad Factual y Anti-Alucinación para el Agente Arca (US-10).

Verifica la concordancia numérica entre el texto emitido por el modelo
y los datos reales obtenidos por las herramientas, eliminando alucinaciones,
mocks y asegurando la inclusión obligatoria de metadatos de trazabilidad.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from backend.app.agent.tools import ToolResult
from backend.app.config import DISCLAIMER

logger = logging.getLogger("backend.anti_hallucination")

NUMBER_REGEX = re.compile(r"[-+]?\b\d+(?:[.,]\d+)?%?\b")
EMOJI_REGEX = re.compile(r"[\U00010000-\U0010ffff]", flags=re.UNICODE)


def extract_authorized_numbers(tool_results: List[ToolResult]) -> List[float]:
    """
    Extrae todos los valores numéricos válidos retornados por las herramientas de solo lectura.
    """
    numbers: List[float] = []

    def _collect(val: Any):
        if isinstance(val, (int, float)):
            numbers.append(float(val))
        elif isinstance(val, dict):
            for v in val.values():
                _collect(v)
        elif isinstance(val, list):
            for item in val:
                _collect(item)

    for tr in tool_results:
        if tr.ok and tr.payload:
            _collect(tr.payload)

    return numbers


def clean_text_artifacts(text: str) -> str:
    """
    Limpia emojis y artefactos de código markdown que degraden la presentación formal.
    """
    cleaned = text.strip()
    # Eliminar emojis estrictamente
    cleaned = EMOJI_REGEX.sub("", cleaned)
    # Eliminar bloques de código markdown innecesarios
    cleaned = re.sub(r"```(?:json|markdown|text)?\s*", "", cleaned)
    cleaned = cleaned.replace("```", "")
    # Normalizar espaciados
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned).strip()
    return cleaned


def audit_factual_consistency(
    text: str,
    tool_results: List[ToolResult],
    tolerance_pct: float = 0.001,
) -> Tuple[bool, Optional[str]]:
    """
    Verifica que las cifras financieras citadas en el texto correspondan con el payload de las herramientas.
    Si se detecta un número ficticio o fuera de rango, retorna (False, motivo).
    """
    valid = [t for t in tool_results if t.ok and t.payload]
    aliases = {"bitcoin": "BTCUSDT", "btc": "BTCUSDT", "ethereum": "ETHUSDT", "eth": "ETHUSDT", "solana": "SOLUSDT", "sol": "SOLUSDT", "bnb": "BNBUSDT"}
    numeric = r"[-+]?\d+(?:[.,]\d+)*"
    def number(raw):
        raw = raw.rstrip(".,")
        if "," in raw and "." in raw:
            return float(raw.replace(",", "") if raw.rfind(".") > raw.rfind(",") else raw.replace(".", "").replace(",", "."))
        if "," in raw:
            parts = raw.split(",")
            raw = "".join(parts) if len(parts[-1]) == 3 else raw.replace(",", ".")
        return float(raw)

    price_keys = {"current_price", "open", "high", "low", "close", "vwap", "support_level", "resistance_level"}
    for sentence in re.split(r"[\n;]|(?<=[.!?])\s+", text):
        claims = list(re.finditer(r"(?P<dollar>\$)\s*(?P<price>" + numeric + r")|(?P<value>" + numeric + r")\s*(?P<unit>%|USDT|USD|EUR|COP|BTC|ETH|SOL|BNB)", sentence, re.I))
        if not claims:
            continue
        symbols = {aliases.get(x.lower(), x.upper()) for x in re.findall(r"\b(?:BTCUSDT|ETHUSDT|SOLUSDT|BNBUSDT|bitcoin|ethereum|solana|btc|eth|sol|bnb)\b", sentence, re.I)}
        periods = set(re.findall(r"\b(?:1h|4h|24h|7d|30d)\b", sentence))
        periods.update({n + ("h" if u.lower().startswith("hora") else "d") for n, u in re.findall(r"(1|4|24|7|30)\s+(horas?|d[ií]as?)", sentence, re.I)})
        candidates = [t for t in valid if (not symbols or (t.payload.get("symbol") or t.arguments.get("symbol")) in symbols) and (not periods or (t.payload.get("window") or t.payload.get("timeframe") or t.arguments.get("window")) in periods)]
        if len(symbols) > 1:
            return False, "Comparacion numerica ambigua; se requiere una afirmacion por activo."
        for claim in claims:
            unit = (claim.group("unit") or "USDT").upper()
            value = number(claim.group("price") or claim.group("value"))
            allowed = []
            for tr in candidates:
                payload = tr.payload
                symbol = payload.get("symbol") or tr.arguments.get("symbol", "")
                if unit == "%":
                    allowed.extend(payload[k] for k in ("return_24h", "return_pct") if k in payload)
                elif unit in {"USDT", "USD"}:
                    allowed.extend(payload[k] for k in price_keys if k in payload)
                    for candle in payload.get("candles", []):
                        allowed.extend(candle[k] for k in price_keys if k in candle)
                elif symbol == unit + "USDT":
                    allowed.extend(payload[k] for k in ("volume", "volume_24h") if k in payload)
            if not any(isinstance(v, (int, float)) and abs(value-v) <= max(0.005, abs(v)*tolerance_pct) for v in allowed):
                return False, "La cifra no figura en los datos reales del activo, periodo y unidad."
    if tool_results and not valid:
        return False, "No hay datos verificados disponibles."
    return True, None


def enforce_anti_hallucination(
    raw_answer: str,
    tool_results: List[ToolResult],
    fallback_summary: str = "",
) -> str:
    """
    Pasa el texto por el auditor factual. Si falla la verificación, reemplaza
    con el resumen empírico determinista de la herramienta, asegurando 100% de factualidad.
    """
    cleaned = clean_text_artifacts(raw_answer)

    is_factual, reason = audit_factual_consistency(cleaned, tool_results)
    if not is_factual:
        logger.warning("Respuesta no factual interceptada (%s). Aplicando resumen determinista.", reason)
        if fallback_summary:
            cleaned = fallback_summary
        elif tool_results and tool_results[0].ok and tool_results[0].summary:
            cleaned = tool_results[0].summary
        else:
            cleaned = "No hay datos verificados suficientes para responder esta consulta."

    # Garantizar descargo legal si no está presente
    if DISCLAIMER not in cleaned:
        cleaned = f"{cleaned}\n\nNota: {DISCLAIMER}"

    return cleaned
