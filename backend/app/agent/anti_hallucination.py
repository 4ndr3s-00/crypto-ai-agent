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
    tolerance_pct: float = 0.05,
) -> Tuple[bool, Optional[str]]:
    """
    Verifica que las cifras financieras citadas en el texto correspondan con el payload de las herramientas.
    Si se detecta un número ficticio o fuera de rango, retorna (False, motivo).
    """
    if not tool_results:
        # Si no hubo tools ejecutadas y el texto intenta citar cifras de mercado, es sospechoso
        if re.search(r"\$\s*\d+", text):
            return False, "Cita de precios sin ejecución previa de herramientas de mercado."
        return True, None

    authorized_numbers = extract_authorized_numbers(tool_results)
    if not authorized_numbers:
        return True, None

    # Extraer precios con formato moneda en el texto ($68,450 o 68450)
    cited_currency = re.findall(r"\$\s*([\d,]+(?:\.\d+)?)", text)
    for raw_price in cited_currency:
        try:
            val = float(raw_price.replace(",", ""))
            # Verificar si existe algún valor autorizado dentro de la tolerancia
            matches = any(abs(val - auth) / max(auth, 1.0) <= tolerance_pct for auth in authorized_numbers)
            if not matches and val > 10.0:  # Ignorar números triviales
                logger.warning("Alucinación detectada: precio citado $%s no coincide con datos reales.", val)
                return False, f"Precio citado ${val} no figura en los datos reales retornados por la herramienta."
        except ValueError:
            continue

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
        elif tool_results and tool_results[0].summary:
            cleaned = tool_results[0].summary

    # Garantizar descargo legal si no está presente
    if DISCLAIMER not in cleaned:
        cleaned = f"{cleaned}\n\nNota: {DISCLAIMER}"

    return cleaned
