"use client";

import React from "react";
import ReactMarkdown from "react-markdown";
import {
  Bot,
  User,
  Clock,
  Database,
  ShieldCheck,
  TrendingUp,
  Cpu,
  Layers,
} from "lucide-react";
import { ChatMessage, Provenance } from "@/types";
import { InteractiveChart } from "@/components/charts/InteractiveChart";

interface MessageItemProps {
  message: ChatMessage;
}

export function MessageItem({ message }: MessageItemProps) {
  const isAssistant = message.role === "assistant";

  const getProvenanceBadge = (prov?: Provenance) => {
    switch (prov) {
      case "MINIO_LAKE":
        return {
          label: "MinIO S3 Lake",
          className: "bg-cyan-500/10 text-cyan-400 border-cyan-500/30",
        };
      case "DUCKDB_OLAP":
        return {
          label: "DuckDB OLAP",
          className: "bg-amber-500/10 text-amber-400 border-amber-500/30",
        };
      case "EXCHANGE_LIVE":
        return {
          label: "Binance Live",
          className: "bg-emerald-500/10 text-emerald-400 border-emerald-500/30",
        };
      case "ROUTER_GUARD":
        return {
          label: "Semantic Router",
          className: "bg-purple-500/10 text-purple-400 border-purple-500/30",
        };
      default:
        return {
          label: "Verificado",
          className: "bg-slate-700/30 text-slate-400 border-slate-700/50",
        };
    }
  };

  const badge = getProvenanceBadge(message.provenance);

  return (
    <div
      className={`flex flex-col gap-2 p-4 rounded-xl border transition-all ${
        isAssistant
          ? "bg-[#0d1322] border-[#1e293b]"
          : "bg-[#111a2e]/60 border-[#22314e] ml-6 md:ml-12"
      }`}
    >
      {/* Message Header */}
      <div className="flex items-center justify-between text-xs">
        <div className="flex items-center gap-2">
          {isAssistant ? (
            <div className="flex items-center gap-1.5 text-cyan-400 font-semibold font-mono-numbers">
              <div className="p-1 rounded-md bg-cyan-500/10 border border-cyan-500/30">
                <Cpu className="w-3.5 h-3.5" />
              </div>
              <span>Copiloto {message.provider && `· ${message.model || message.provider}`}</span>
            </div>
          ) : (
            <div className="flex items-center gap-1.5 text-slate-300 font-medium font-mono-numbers">
              <div className="p-1 rounded-md bg-slate-800 border border-slate-700">
                <User className="w-3.5 h-3.5 text-slate-400" />
              </div>
              <span>Trader</span>
            </div>
          )}

          {isAssistant && message.provenance && (
            <span
              className={`px-2 py-0.5 rounded text-[10px] font-mono-numbers border ${badge.className}`}
            >
              {badge.label}
            </span>
          )}
        </div>

        <div className="flex items-center gap-3 text-slate-500 font-mono-numbers text-[11px]">
          {isAssistant && typeof message.latency_ms === "number" && (
            <span className="flex items-center gap-1">
              <Clock className="w-3 h-3 text-slate-600" />
              {message.latency_ms.toFixed(0)}ms
            </span>
          )}
          <span>{message.timestamp}</span>
        </div>
      </div>

      {/* Message Content */}
      <div className="text-sm leading-relaxed text-slate-200 prose prose-invert max-w-none prose-p:my-1.5 prose-headings:my-2 prose-headings:text-slate-100 prose-table:border prose-table:border-[#1e293b] prose-th:bg-[#111a2e] prose-th:p-1.5 prose-td:p-1.5 prose-code:text-cyan-300 prose-code:bg-[#16223b] prose-code:px-1 prose-code:py-0.5 prose-code:rounded">
        <ReactMarkdown>{message.content}</ReactMarkdown>
      </div>

      {/* Attached Financial Chart */}
      {message.chart && (
        <div className="mt-3">
          <InteractiveChart chartData={message.chart} height={320} showControls={false} />
        </div>
      )}

      {/* Citations and References */}
      {message.sources && message.sources.length > 0 && (
        <div className="mt-2 pt-2 border-t border-[#1e293b]/60 flex flex-wrap gap-2 items-center text-[11px] font-mono-numbers text-slate-400">
          <span className="text-slate-500">Fuentes auditadas:</span>
          {message.sources.map((s, idx) => (
            <div
              key={idx}
              className="flex items-center gap-1 px-2 py-0.5 rounded bg-[#111a2e] border border-[#1e293b] text-slate-300"
            >
              <Database className="w-3 h-3 text-cyan-400" />
              <span>{s.source}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
