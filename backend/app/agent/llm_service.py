"""
Orquestador de inferencia LLM (Groq / Ollama), Function Calling y Anti-Alucinación (US-07).

Gestiona el flujo completo: Router Semántico -> Function Calling -> Fact Check -> Chart Build -> ChatResponse.
"""

from __future__ import annotations

import json
import asyncio
from contextvars import ContextVar
from collections import OrderedDict
import logging
import re
import time
from typing import Any, Dict, List, Optional

import httpx

from backend.app.agent.anti_hallucination import enforce_anti_hallucination
from backend.app.agent.prompts import SYSTEM_PROMPT
from backend.app.agent.semantic_router import RouterDecision, SemanticRouter
from backend.app.agent.tools import ToolRegistry, ToolResult
from backend.app.config import DISCLAIMER, Settings, get_settings
from backend.app.database.queries import query_market_ohlcv
from backend.app.models import (
    Candle,
    ChatChart,
    ChatRequest,
    ChatResponse,
    SourceReference,
    ToolCallRecord,
)

_window = ContextVar("market_window", default="24h")
_history = ContextVar("chat_history", default=())

logger = logging.getLogger("backend.llm_service")


class LLMService:
    def __init__(self, settings: Optional[Settings] = None, router: Optional[SemanticRouter] = None) -> None:
        self.settings = settings or get_settings()
        self.router = router or SemanticRouter()
        self.tools = ToolRegistry()
        self.conversations = OrderedDict()
        self._conversation_locks = [asyncio.Lock() for _ in range(64)]

    async def answer(self, request: ChatRequest) -> ChatResponse:
        # A bounded, expiring single-process store. Never share the legacy default ID.
        key = request.conversation_id
        if not key or key == "default":
            return await self._answer(request)
        async with self._conversation_locks[hash(key) % 64]:
            now = time.monotonic()
            for old in list(self.conversations):
                if now - self.conversations[old][0] > 1800:
                    del self.conversations[old]
            turns = self.conversations.get(key, (now, []))[1]
            token = _history.set(tuple(turns))
            try:
                response = await self._answer(request)
            finally:
                _history.reset(token)
            turns = (turns + [{"role": "user", "content": request.message},
                              {"role": "assistant", "content": response.answer[:8000]}])[-12:]
            self.conversations[key] = (time.monotonic(), turns)
            self.conversations.move_to_end(key)
            while len(self.conversations) > 256:
                self.conversations.popitem(last=False)
            return response

    async def _answer(self, request: ChatRequest) -> ChatResponse:
        started = time.perf_counter()
        message = request.message.strip()
        aliases = {"bitcoin": "BTCUSDT", "btc": "BTCUSDT", "ethereum": "ETHUSDT", "eth": "ETHUSDT", "solana": "SOLUSDT", "sol": "SOLUSDT", "bnb": "BNBUSDT"}
        mentioned = re.findall(r"\b(bitcoin|btc|ethereum|eth|solana|sol|bnb|BTCUSDT|ETHUSDT|SOLUSDT|BNBUSDT)\b", message, re.I)
        if len(mentioned) == 1:
            request = request.model_copy(update={"symbol": aliases.get(mentioned[0].lower(), mentioned[0].upper())})

        periods = re.findall(r"\b(1h|4h|24h|7d|30d)\b", message)
        window_token = periods[-1] if periods else "24h"
        _window.set(window_token)
        # 1. Enrutamiento semántico local (latencia < 5ms)
        decision = self.router.route(message)
        if decision.kind != "analytics" and decision.response:
            latency_ms = round((time.perf_counter() - started) * 1000, 2)
            return ChatResponse(
                answer=decision.response,
                reply=decision.response,
                sql=None,
                provenance="ROUTER_GUARD",
                asset=request.symbol,
                source="semantic_router",
                sources=[SourceReference(source="semantic_router", title="Filtro Semántico Local", kind="guardrail")],
                cutoff_time=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                disclaimer=DISCLAIMER,
                tool_calls=[],
                intent=decision.intent,
                chart=None,
                latency_ms=latency_ms,
            )

        # 2. Inferencia con Groq Cloud o Fallback
        provider, model = "deterministic", None
        model_result: Optional[Dict[str, Any]] = None
        if self.settings.groq_api_key:
            try:
                model_result = await self._run_groq(message, request.symbol, request.interval)
                provider, model = "groq", self.settings.groq_model
            except Exception as exc:
                logger.warning("Fallo en inferencia Groq (%s), recurriendo a Ollama/Fallback...", exc)

        if not model_result and self.settings.ollama_base_url:
            try:
                model_result = await self._run_ollama(message, request.symbol, request.interval)
                provider, model = "ollama", self.settings.ollama_model
            except Exception as exc:
                logger.warning("Fallo en inferencia Ollama (%s), usando fallback determinista...", exc)

        # 3. Fallback determinista si los modelos fallan
        if not model_result:
            model_result = await asyncio.to_thread(self._fallback_deterministic, message, request.symbol, request.interval)

        tool_results: List[ToolResult] = model_result.get("tool_results", [])
        tool_records: List[ToolCallRecord] = model_result.get("tool_records", [])
        raw_answer: str = model_result.get("answer", "")
        sql_executed: Optional[str] = model_result.get("sql")

        # 4. Auditoría Factual y Anti-Alucinación
        fallback_summary = "\n".join(tr.summary for tr in tool_results if tr.ok and tr.summary)
        final_answer = enforce_anti_hallucination(raw_answer, tool_results, fallback_summary)

        # 5. Construcción del Gráfico Financiero (Chart)
        chart = await asyncio.to_thread(self._build_chart, request.symbol, request.interval, tool_results)

        # Metadatos de linaje y corte
        cutoff_time = next(
            (tr.cutoff_time for tr in tool_results if tr.cutoff_time),
            time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        )
        provenance = next((tr.provenance for tr in tool_results if tr.provenance), "DUCKDB_OLAP")
        source = next((tr.source for tr in tool_results if tr.source), "minio_parquet_historical")

        sources = [
            SourceReference(
                source=tr.source,
                title=f"Ejecución de {tr.name}",
                snippet=tr.summary,
                kind="tool",
            )
            for tr in tool_results
        ]

        latency_ms = round((time.perf_counter() - started) * 1000, 2)

        return ChatResponse(
            provider=provider,
            model=model,
            answer=final_answer,
            reply=final_answer,
            sql=sql_executed if request.include_sql else None,
            provenance=provenance,  # type: ignore[arg-type]
            asset=request.symbol,
            source=source,
            sources=sources,
            cutoff_time=cutoff_time,
            disclaimer=DISCLAIMER,
            tool_calls=tool_records,
            intent="market_analytics",
            chart=chart,
            latency_ms=latency_ms,
        )

    async def _run_groq(self, message: str, symbol: str, interval: str) -> Dict[str, Any]:
        """
        Ejecuta el loop de Function Calling con Groq Cloud (Llama-3.3-70b-versatile).
        """
        url = f"{self.settings.groq_base_url.rstrip('/')}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.settings.groq_api_key}",
            "Content-Type": "application/json",
        }

        messages: List[Dict[str, Any]] = [
            {"role": "system", "content": SYSTEM_PROMPT},
            *_history.get(),
            {
                "role": "user",
                "content": f"Consulta de Andrés: {message}\nSímbolo sugerido: {symbol}\nTemporalidad sugerida: {interval}",
            },
        ]

        tool_results: List[ToolResult] = []
        tool_records: List[ToolCallRecord] = []

        async with httpx.AsyncClient(timeout=self.settings.groq_timeout_seconds) as client:
            for _ in range(3):
                payload = {
                    "model": self.settings.groq_model,
                    "messages": messages,
                    "tools": self.tools.specs,
                    "tool_choice": "auto",
                    "temperature": 0.1,
                    "max_tokens": 600,
                }
                resp = await client.post(url, headers=headers, json=payload)
                if resp.status_code >= 400:
                    raise RuntimeError(f"Groq API error {resp.status_code}: {resp.text[:200]}")

                data = resp.json()
                choices = data.get("choices") or []
                choice_msg = choices[0].get("message") if choices else {}
                raw_tool_calls = choice_msg.get("tool_calls") or []

                if raw_tool_calls:
                    messages.append({
                        "role": "assistant",
                        "content": choice_msg.get("content") or "",
                        "tool_calls": raw_tool_calls,
                    })

                    for call in raw_tool_calls:
                        fn = call.get("function") or {}
                        fn_name = fn.get("name") or ""
                        fn_args = fn.get("arguments") or {}
                        if isinstance(fn_args, str):
                            try:
                                fn_args = json.loads(fn_args)
                            except json.JSONDecodeError:
                                fn_args = {}

                        tr = await asyncio.to_thread(self.tools.execute, fn_name, fn_args)
                        tool_results.append(tr)
                        tool_records.append(
                            ToolCallRecord(
                                name=fn_name,
                                arguments=fn_args,
                                result_summary=tr.summary if tr.ok else (tr.error or "error"),
                            )
                        )
                        messages.append({
                            "role": "tool",
                            "tool_call_id": call.get("id"),
                            "name": fn_name,
                            "content": json.dumps(tr.payload if tr.ok else {"error": tr.error}, ensure_ascii=False, default=str),
                        })
                    continue

                content = str(choice_msg.get("content") or "").strip()
                sql = next((tr.sql for tr in tool_results if tr.sql), None)
                return {
                    "answer": content,
                    "sql": sql,
                    "tool_results": tool_results,
                    "tool_records": tool_records,
                }

        # Si agotó las iteraciones
        return {
            "answer": next((tr.summary for tr in tool_results if tr.summary), "Análisis completado."),
            "sql": next((tr.sql for tr in tool_results if tr.sql), None),
            "tool_results": tool_results,
            "tool_records": tool_records,
        }

    async def _run_ollama(self, message: str, symbol: str, interval: str) -> Dict[str, Any]:
        """
        Ejecuta la inferencia local con Ollama (llama3.2:3b u otro modelo activo).
        Inyecta contexto empírico de mercado para que el modelo razone con base real y responda
        a preguntas abiertas o analíticas con verdadero lenguaje natural.
        """
        url = f"{self.settings.ollama_base_url.rstrip('/')}/api/chat"

        tr_metrics = await asyncio.to_thread(self.tools.execute, "query_metrics", {"symbol": symbol, "window": _window.get()})
        tr_ts = await asyncio.to_thread(self.tools.execute, "query_timeseries", {"symbol": symbol, "interval": interval, "limit": 48})
        tool_results = [tr_metrics, tr_ts]

        context_prompt = (
            f"Contexto actual de mercado para {symbol} ({interval}):\n"
            f"- Métricas {_window.get()}: {tr_metrics.summary}\n"
            f"- Series recientes: {tr_ts.summary}\n\n"
            f"Instrucción: Utiliza estos datos cuantitativos reales si la pregunta lo amerita. "
            f"Si la consulta es conceptual, macroeconómica o imprevista, razona con claridad analítica en español. "
            f"No inventes datos numéricos fuera de los provistos.\n\n"
            f"Consulta del usuario: {message}"
        )

        payload = {
            "model": self.settings.ollama_model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
            *_history.get(),
                {"role": "user", "content": context_prompt},
            ],
            "stream": False,
            "options": {
                "temperature": 0.2,
                "top_p": 0.9,
            },
        }
        async with httpx.AsyncClient(timeout=35.0) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()
            answer = data.get("message", {}).get("content", "").strip()

        return {
            "answer": answer or tr_metrics.summary,
            "sql": tr_metrics.sql or tr_ts.sql,
            "tool_results": tool_results,
            "tool_records": [
                ToolCallRecord(name=tr.name, arguments=tr.arguments, result_summary=tr.summary)
                for tr in tool_results
            ],
        }

    def _fallback_deterministic(self, message: str, symbol: str, interval: str) -> Dict[str, Any]:
        """
        Respaldo determinista garantizado: ejecuta herramientas reales sin LLM.
        """
        tr_metrics = self.tools.execute("query_metrics", {"symbol": symbol, "window": _window.get()})
        tr_ts = self.tools.execute("query_timeseries", {"symbol": symbol, "interval": interval, "limit": 48})

        answer = (
            f"Aquí tienes las estadísticas reales calculadas para {symbol}:\n\n"
            f"- {tr_metrics.summary}\n"
            f"- {tr_ts.summary}\n\n"
            f"El sistema ha verificado los datos directamente contra el lago MinIO S3 y el exchange en vivo."
        )

        return {
            "answer": answer,
            "sql": tr_ts.sql or tr_metrics.sql,
            "tool_results": [tr_metrics, tr_ts],
            "tool_records": [
                ToolCallRecord(name=tr_metrics.name, arguments=tr_metrics.arguments, result_summary=tr_metrics.summary),
                ToolCallRecord(name=tr_ts.name, arguments=tr_ts.arguments, result_summary=tr_ts.summary),
            ],
        }

    def _build_chart(
        self,
        symbol: str,
        interval: str,
        tool_results: List[ToolResult],
    ) -> Optional[ChatChart]:
        """
        Construye el payload ChatChart con velas y VWAP para la interfaz interactiva.
        """
        # 1. Buscar si se ejecutó query_timeseries
        ts_result = next((tr for tr in tool_results if tr.name == "query_timeseries" and tr.ok), None)
        if ts_result:
            candles_data = ts_result.payload.get("candles", [])
            candles = [
                Candle(
                    timestamp=c["timestamp"],
                    open=c["open"],
                    high=c["high"],
                    low=c["low"],
                    close=c["close"],
                    volume=c["volume"],
                )
                for c in candles_data
            ]
            return ChatChart(
                symbol=str(ts_result.payload.get("symbol") or symbol),
                interval=str(ts_result.payload.get("interval") or interval),
                chart_type="candlestick",
                candles=candles,
                source=ts_result.source,
                cutoff_time=ts_result.cutoff_time,
            )

        # 2. Si solo se ejecutó query_metrics, consultar velas de 1h para graficar
        metrics_result = next((tr for tr in tool_results if tr.name == "query_metrics" and tr.ok), None)
        if metrics_result:
            res = query_market_ohlcv(symbol, interval="1h", limit=24)
            candles = [
                Candle(
                    timestamp=c["timestamp"],
                    open=c["open"],
                    high=c["high"],
                    low=c["low"],
                    close=c["close"],
                    volume=c["volume"],
                )
                for c in res.get("candles", [])
            ]
            if candles:
                return ChatChart(
                    symbol=symbol,
                    interval="1h",
                    chart_type="candlestick",
                    candles=candles,
                    indicators={"vwap": metrics_result.payload.get("vwap", 0.0)},
                    source=res.get("source", "minio_parquet_historical"),
                    cutoff_time=res.get("cutoff_time", ""),
                )

        return None
