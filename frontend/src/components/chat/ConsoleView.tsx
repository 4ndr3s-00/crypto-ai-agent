"use client";

import React, { useState, useRef, useEffect } from "react";
import { Send, Terminal, Loader2, Sparkles, ArrowRight, RefreshCw, AlertCircle } from "lucide-react";
import { ChatMessage, ChatResponse } from "@/types";
import { apiClient } from "@/lib/apiClient";
import { MessageItem } from "./MessageItem";

interface ConsoleViewProps {
  onOpenReport?: (symbol: string) => void;
  onSelectSymbol?: (symbol: string) => void;
}

export function ConsoleView({ onOpenReport, onSelectSymbol }: ConsoleViewProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: "initial-welcome",
      role: "assistant",
      content:
        "Sistemas en línea. Soy tu **Copiloto Analítico de Mercados**.\n\nEstoy conectado en tiempo real a los feeds en vivo de **Binance** y al data lakehouse en **MinIO S3**. DuckDB y el motor de IA local **Ollama (llama3.2:3b)** están activos para análisis cuantitativo, proyecciones técnicas y consultas de mercado con verificación factual estricta.\n\n¿Qué activo o indicador deseas examinar hoy?",
      timestamp: "Sistema Listo",
      provenance: "ROUTER_GUARD",
      latency_ms: 0,
    },
  ]);

  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const scrollRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, loading]);

  const handleSubmit = async (textToSend?: string) => {
    const query = (textToSend || input).trim();
    if (!query || loading) return;

    setError(null);
    setInput("");

    const userMessage: ChatMessage = {
      id: "user-" + Date.now(),
      role: "user",
      content: query,
      timestamp: new Date().toLocaleTimeString(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setLoading(true);

    try {
      const response: ChatResponse = await apiClient.sendChatMessage(query);

      const assistantMessage: ChatMessage = {
        id: "arca-" + Date.now(),
        role: "assistant",
        content: response.answer || response.reply || "Sin respuesta del agente.",
        timestamp: new Date().toLocaleTimeString(),
        chart: response.chart,
        provenance: response.provenance,
        latency_ms: response.latency_ms,
        sources: response.sources,
      };

      setMessages((prev) => [...prev, assistantMessage]);

      // If user queried about a symbol and got a chart, update selected symbol
      if (response.chart?.symbol) {
        onSelectSymbol?.(response.chart.symbol);
      }
    } catch (err: any) {
      setError(err.message || "Error al conectar con el servidor del backend");
      const errorMessage: ChatMessage = {
        id: "err-" + Date.now(),
        role: "assistant",
        content: `**Error de conexión con el backend:** ${err.message || "Fallo inesperado"}.\n\nVerifica que el servicio FastAPI en el puerto 8001 esté activo.`,
        timestamp: new Date().toLocaleTimeString(),
        provenance: "ROUTER_GUARD",
        latency_ms: 0,
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setLoading(false);
    }
  };

  const suggestions = [
    "Analiza el VWAP y niveles de soporte para BTCUSDT",
    "Muestra el gráfico de ETHUSDT en temporalidad 15m",
    "¿Cuál es el volumen y volatilidad de BTC en las últimas 24h?",
    "Genera el reporte cuantitativo completo de BTCUSDT",
  ];

  return (
    <div className="flex flex-col h-full bg-[#090d16] border border-[#1e293b] rounded-xl overflow-hidden shadow-2xl">
      {/* Console Top Bar */}
      <div className="flex items-center justify-between px-4 py-3 bg-[#0d1322] border-b border-[#1e293b]">
        <div className="flex items-center gap-2">
          <div className="w-2.5 h-2.5 rounded-full bg-cyan-500 animate-pulse" />
          <span className="text-xs font-semibold text-slate-200 tracking-wider uppercase font-mono-numbers">
            Market Copilot Core
          </span>
          <span className="text-[11px] text-slate-500 font-mono-numbers">
            (DuckDB + MinIO S3 + Ollama llama3.2:3b)
          </span>
        </div>

        <button
          type="button"
          onClick={() => {
            setMessages([
              {
                id: "initial-welcome",
                role: "assistant",
                content: "Sesión reiniciada. ¿Qué activo o métrica deseas analizar?",
                timestamp: "Reinicio",
                provenance: "ROUTER_GUARD",
              },
            ]);
            setError(null);
          }}
          className="p-1 text-slate-400 hover:text-slate-200 hover:bg-[#16223b] rounded transition-colors"
          title="Reiniciar conversación"
        >
          <RefreshCw className="w-3.5 h-3.5" />
        </button>
      </div>

      {/* Message Feed */}
      <div
        ref={scrollRef}
        className="flex-1 overflow-y-auto p-4 space-y-4 scroll-smooth"
      >
        {messages.map((msg) => (
          <MessageItem key={msg.id} message={msg} />
        ))}

        {loading && (
          <div className="flex items-center gap-3 p-4 bg-[#0d1322] border border-[#1e293b] rounded-xl text-xs font-mono-numbers text-cyan-400 animate-pulse">
            <Loader2 className="w-4 h-4 animate-spin text-cyan-400" />
            <span>Consultando DuckDB OLAP / Ollama llama3.2:3b y verificando factualidad...</span>
          </div>
        )}

        {error && (
          <div className="flex items-center gap-2 p-3 bg-rose-500/10 border border-rose-500/30 rounded-lg text-xs text-rose-300 font-mono-numbers">
            <AlertCircle className="w-4 h-4 text-rose-400 flex-shrink-0" />
            <span>{error}</span>
          </div>
        )}
      </div>

      {/* Suggestion Chips */}
      <div className="px-4 py-2 border-t border-[#1e293b]/70 bg-[#0d1322]/80 flex items-center gap-2 overflow-x-auto scrollbar-none">
        <span className="text-[11px] text-slate-500 font-mono-numbers flex items-center gap-1 flex-shrink-0">
          <Sparkles className="w-3 h-3 text-cyan-400" />
          Sugerencias:
        </span>
        {suggestions.map((sug, i) => (
          <button
            key={i}
            type="button"
            disabled={loading}
            onClick={() => handleSubmit(sug)}
            className="flex-shrink-0 text-[11px] font-mono-numbers px-2.5 py-1 rounded bg-[#131c31] hover:bg-[#1c2946] text-slate-300 hover:text-cyan-300 border border-[#202f50] transition-colors"
          >
            {sug}
          </button>
        ))}
      </div>

      {/* Input Prompt Bar */}
      <form
        onSubmit={(e) => {
          e.preventDefault();
          handleSubmit();
        }}
        className="p-3 bg-[#0d1322] border-t border-[#1e293b] flex items-center gap-2"
      >
        <div className="relative flex-1">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Pregunta al Copiloto sobre métricas, VWAP, tendencias, RSI o gráficos..."
            disabled={loading}
            className="w-full bg-[#111a2e] border border-[#23355b] focus:border-cyan-500 text-slate-100 placeholder-slate-500 text-sm rounded-lg px-4 py-2.5 outline-none transition-colors font-mono-numbers disabled:opacity-50"
          />
        </div>

        <button
          type="submit"
          disabled={!input.trim() || loading}
          className="flex items-center justify-center p-2.5 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-slate-950 font-semibold disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
        >
          {loading ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <Send className="w-4 h-4" />
          )}
        </button>
      </form>
    </div>
  );
}
