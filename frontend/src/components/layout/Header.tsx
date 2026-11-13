"use client";

import React, { useEffect, useState } from "react";
import { Cpu, Database, Server, Zap, Shield, FileText, CheckCircle2, AlertTriangle, XCircle } from "lucide-react";
import { HealthResponse } from "@/types";
import { apiClient } from "@/lib/apiClient";

interface HeaderProps {
  onOpenReportModal: () => void;
}

export function Header({ onOpenReportModal }: HeaderProps) {
  const [health, setHealth] = useState<HealthResponse | null>(null);

  useEffect(() => {
    const fetchHealth = async () => {
      try {
        const res = await apiClient.checkHealth();
        setHealth(res);
      } catch (err) {
        setHealth({
          status: "unhealthy",
          services: {
            api: "unavailable",
            minio: "disconnected",
            duckdb: "unavailable",
            binance: "unavailable",
            ollama: "unavailable",
            groq: "unavailable",
          },
          timestamp: new Date().toISOString(),
          version: "1.0.0",
        });
      }
    };

    fetchHealth();
    const interval = setInterval(fetchHealth, 15000);
    return () => clearInterval(interval);
  }, []);

  const getStatusIndicator = () => {
    if (!health) return { color: "bg-slate-500", text: "Conectando...", icon: null };
    if (health.status === "healthy") {
      return {
        color: "bg-emerald-500",
        text: "Sistemas Operativos",
        icon: <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />,
      };
    }
    if (health.status === "degraded") {
      return {
        color: "bg-amber-500",
        text: "Modo Degradado",
        icon: <AlertTriangle className="w-3.5 h-3.5 text-amber-400" />,
      };
    }
    return {
      color: "bg-rose-500",
      text: "Desconectado",
      icon: <XCircle className="w-3.5 h-3.5 text-rose-400" />,
    };
  };

  const status = getStatusIndicator();

  return (
    <header className="w-full bg-[#080c14] border-b border-[#1e293b] px-4 lg:px-6 py-3 flex items-center justify-between">
      {/* Brand & Identity */}
      <div className="flex items-center gap-3">
        <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-cyan-600 to-blue-700 flex items-center justify-center border border-cyan-400/40 shadow-lg shadow-cyan-900/30">
          <Cpu className="w-5 h-5 text-slate-950 font-bold" />
        </div>
        <div>
          <div className="flex items-center gap-2">
            <span className="text-base font-bold tracking-wider text-slate-100 font-mono-numbers">
              MARKET COPILOT
            </span>
            <span className="text-xs px-1.5 py-0.5 rounded bg-cyan-950/80 text-cyan-400 border border-cyan-800/50 font-mono-numbers">
              v1.0
            </span>
          </div>
          <p className="text-[11px] text-slate-400 font-mono-numbers hidden sm:block">
            Copiloto Analítico & Inteligencia Cuantitativa de Mercados en Vivo
          </p>
        </div>
      </div>

      {/* Center Services Health Matrix */}
      <div className="hidden md:flex items-center gap-4 px-3 py-1.5 rounded-lg bg-[#0d1322] border border-[#1e293b] text-xs font-mono-numbers">
        <div className="flex items-center gap-1.5">
          <div
            className={`w-2 h-2 rounded-full ${
              health?.services.minio === "connected" || health?.services.minio === true
                ? "bg-cyan-400"
                : "bg-rose-500"
            }`}
          />
          <span className="text-slate-400">MinIO S3</span>
        </div>

        <div className="w-px h-3 bg-[#1e293b]" />

        <div className="flex items-center gap-1.5">
          <div
            className={`w-2 h-2 rounded-full ${
              health?.services.duckdb === "operational" || health?.services.duckdb === true
                ? "bg-amber-400"
                : "bg-rose-500"
            }`}
          />
          <span className="text-slate-400">DuckDB OLAP</span>
        </div>

        <div className="w-px h-3 bg-[#1e293b]" />

        <div className="flex items-center gap-1.5">
          <div
            className={`w-2 h-2 rounded-full ${
              health?.services.binance === "available"
                ? "bg-emerald-400"
                : "bg-rose-500"
            }`}
          />
          <span className="text-slate-400">Binance Spot ({health?.services.binance || "sin verificar"})</span>
        </div>

        <div className="w-px h-3 bg-[#1e293b]" />

        <div className="flex items-center gap-1.5">
          <div
            className={`w-2 h-2 rounded-full ${
              health?.services.groq === "available" || health?.services.ollama === "available"
                ? "bg-emerald-400"
                : health?.services.ollama === "model_missing"
                ? "bg-amber-400"
                : "bg-amber-500"
            }`}
          />
          <span className="text-slate-400">
            {health?.services.groq === "available"
              ? `Groq: ${health?.services.groq_model}`
              : health?.services.ollama === "available"
              ? `Ollama: ${health?.services.ollama_model}`
              : health?.services.ollama === "model_missing"
              ? `Ollama: modelo ausente`
              : "Modo: Respaldo determinista"}
          </span>
        </div>
      </div>
      {/* Action & Status */}
      <div className="flex items-center gap-3">
        <button
          type="button"
          onClick={onOpenReportModal}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-[#111a2e] hover:bg-[#16223b] text-slate-200 text-xs font-mono-numbers border border-[#23355b] transition-colors"
        >
          <FileText className="w-3.5 h-3.5 text-cyan-400" />
          <span>Reporte Cuantitativo</span>
        </button>

        <div className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-[#0d1322] border border-[#1e293b] text-xs font-mono-numbers text-slate-300">
          {status.icon}
          <span className="hidden sm:inline">{status.text}</span>
        </div>
      </div>
    </header>
  );
}
