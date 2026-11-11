"""
Router semántico local y filtro de dominio para el Agente Arca (US-09).

Clasifica intenciones comunes (saludos, despedidas, agradecimientos, identidad)
y bloquea consultas fuera de dominio en menos de 5 ms sin consumir tokens de inferencia.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

ANALYTICS_PATTERN = re.compile(
    r"\b("
    r"precio|precios|cotizaci[oó]n|cu[aá]nto vale|cierre|apertura|m[aá]ximo|m[ií]nimo|"
    r"volumen|retorno|rendimiento|variaci[oó]n|subi[oó]|baj[oó]|alcista|bajista|"
    r"vwap|media|volatilidad|gr[aá]fico|gr[aá]fica|chart|vela|velas|candle|ohlcv|"
    r"reporte|informe|resumen|tendencia|an[aá]lisis|soporte|resistencia|"
    r"btc|bitcoin|eth|ethereum|sol|solana|bnb|binance|usdt|cripto|crypto|"
    r"mercado|par|temporalidad|1m|5m|15m|1h|4h|1d|7d|24h"
    r")\b",
    re.IGNORECASE,
)

OUT_OF_SCOPE_PATTERN = re.compile(
    r"\b("
    r"receta|cocinar|pizza|torta|capital de|presidente|pol[ií]tica|f[uú]tbol|gol|"
    r"canci[oó]n|pel[ií]cula|actor|clima en|tiempo en|poema|chiste|historia de roma|"
    r"m[eé]dico|s[ií]ntoma|diagn[oó]stico|abogado|demanda"
    r")\b",
    re.IGNORECASE,
)

GREETING_PATTERN = re.compile(
    r"^(hola|buenos d[ií]as|buenas tardes|buenas noches|qu[eé] tal|hello|hi|hey)(\s+(arca|amigo|equipo|asistente))?[\s.?!]*$",
    re.IGNORECASE,
)

FAREWELL_PATTERN = re.compile(
    r"^(adi[oó]s|hasta luego|chao|nos vemos|bye|goodbye)(\s+(arca|amigo|equipo))?[\s.?!]*$",
    re.IGNORECASE,
)

THANKS_PATTERN = re.compile(
    r"^(gracias|muchas gracias|mil gracias|thank you|thanks)[\s.?!]*$",
    re.IGNORECASE,
)

IDENTITY_PATTERN = re.compile(
    r"\b(qui[eé]n eres|c[oó]mo te llamas|cu[aá]l es tu nombre|qu[eé] haces|tu rol)\b",
    re.IGNORECASE,
)

GREETING_RESPONSE = (
    "Hola. Soy Market Copilot, tu asistente analítico de inteligencia de mercados cripto. "
    "Estoy conectado en tiempo real al lago de datos MinIO y a Binance para consultar "
    "cotizaciones en vivo, series OHLCV, VWAP y generar diagnósticos técnicos. ¿Qué activo o indicador deseas evaluar?"
)

FAREWELL_RESPONSE = (
    "Hasta pronto. Quedo a disposición cuando requieras nuevos diagnósticos técnicos, gráficos o reportes de mercado."
)

THANKS_RESPONSE = (
    "Con gusto. Aquí estaré para cualquier consulta cuantitativa sobre activos financieros."
)

IDENTITY_RESPONSE = (
    "Soy Market Copilot, el asistente analítico de inteligencia de mercado para esta plataforma. "
    "Cuento con conexión directa al lakehouse MinIO S3 (Parquet) y feeds en vivo de Binance, asistido por un motor "
    "OLAP DuckDB y modelos de lenguaje locales para entregarte análisis precisos y diagramas interactivos en segundos."
)

OUT_OF_SCOPE_RESPONSE = (
    "Mi alcance está estrictamente delimitado al análisis cuantitativo del mercado crypto, "
    "series temporales OHLCV, métricas de volatilidad y reportes financieros del sistema. "
    "No dispongo de información sobre temas ajenos a este dominio."
)


@dataclass(frozen=True)
class RouterDecision:
    kind: str  # "analytics", "greeting", "farewell", "thanks", "identity", "out_of_scope"
    intent: str
    response: Optional[str] = None
    score: float = 1.0

    @classmethod
    def analytics(cls) -> RouterDecision:
        return cls(kind="analytics", intent="market_analytics", response=None, score=1.0)


class SemanticRouter:
    """
    Enrutador semántico de reglas y patrones vectorizados locales de latencia cero.
    """

    def route(self, message: str) -> RouterDecision:
        text = message.strip()

        # 1. Saludos
        if GREETING_PATTERN.match(text):
            return RouterDecision(kind="greeting", intent="greeting", response=GREETING_RESPONSE)

        # 2. Despedidas
        if FAREWELL_PATTERN.match(text):
            return RouterDecision(kind="farewell", intent="farewell", response=FAREWELL_RESPONSE)

        # 3. Agradecimientos
        if THANKS_PATTERN.match(text):
            return RouterDecision(kind="thanks", intent="thanks", response=THANKS_RESPONSE)

        # 4. Identidad
        if IDENTITY_PATTERN.search(text):
            return RouterDecision(kind="identity", intent="identity", response=IDENTITY_RESPONSE)

        # 5. Consultas analíticas de mercado explícitas
        if ANALYTICS_PATTERN.search(text):
            return RouterDecision.analytics()

        # 6. Consultas fuera de dominio
        if OUT_OF_SCOPE_PATTERN.search(text):
            return RouterDecision(kind="out_of_scope", intent="out_of_scope", response=OUT_OF_SCOPE_RESPONSE)

        # Por defecto, si menciona números o preguntas cortas, dar paso a la inferencia analítica
        return RouterDecision.analytics()
