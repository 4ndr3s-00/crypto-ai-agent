"use client";

import React from "react";
import {
  Gauge,
  Activity,
  TrendingUp,
  TrendingDown,
  BarChart2,
  Calendar,
  Layers,
  ShieldCheck,
  Zap,
} from "lucide-react";
import { TechnicalSummary as TechnicalSummaryType } from "@/types";

interface TechnicalSummaryProps {
  summary: TechnicalSummaryType | null;
  loading?: boolean;
}

export function TechnicalSummary({ summary, loading = false }: TechnicalSummaryProps) {
  if (loading || !summary) {
    return (
      <div className="w-full bg-[#0d1322] border border-[#1e293b] rounded-xl p-5 animate-pulse">
        <div className="h-5 w-40 bg-[#16223b] rounded mb-4" />
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="h-32 bg-[#16223b] rounded" />
          <div className="h-32 bg-[#16223b] rounded" />
          <div className="h-32 bg-[#16223b] rounded" />
        </div>
      </div>
    );
  }

  // Calculate 24h range percentage
  const range24hSpread = summary.high_24h - summary.low_24h;
  const pct24h =
    range24hSpread > 0
      ? Math.min(100, Math.max(0, ((summary.current_price - summary.low_24h) / range24hSpread) * 100))
      : 50;

  // Calculate 52w range percentage
  const range52wSpread = summary.high_52w - summary.low_52w;
  const pct52w =
    range52wSpread > 0
      ? Math.min(100, Math.max(0, ((summary.current_price - summary.low_52w) / range52wSpread) * 100))
      : 50;

  // Determine sentiment color
  const ratingLower = summary.technical_rating.toLowerCase();
  const isBuy = ratingLower.includes("compra");
  const isSell = ratingLower.includes("venta");
  const ratingColor = isBuy
    ? "text-emerald-400 bg-emerald-500/10 border-emerald-500/30"
    : isSell
    ? "text-rose-400 bg-rose-500/10 border-rose-500/30"
    : "text-amber-400 bg-amber-500/10 border-amber-500/30";

  // Segmented scale steps
  const segments = [
    { label: "Venta Fuerte", minScore: -3, maxScore: -2, color: "bg-rose-500" },
    { label: "Venta", minScore: -1, maxScore: -1, color: "bg-rose-400" },
    { label: "Neutral", minScore: 0, maxScore: 0, color: "bg-slate-400" },
    { label: "Compra", minScore: 1, maxScore: 1, color: "bg-emerald-400" },
    { label: "Compra Fuerte", minScore: 2, maxScore: 3, color: "bg-emerald-500" },
  ];

  const getActiveSegmentIndex = () => {
    if (ratingLower.includes("fuerte") && isSell) return 0;
    if (isSell) return 1;
    if (ratingLower.includes("fuerte") && isBuy) return 4;
    if (isBuy) return 3;
    return 2;
  };

  const activeIndex = getActiveSegmentIndex();

  return (
    <div className="w-full bg-[#0d1322] border border-[#1e293b] rounded-xl p-4 lg:p-5 flex flex-col gap-5 shadow-xl">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-[#1e293b]/80 pb-3">
        <div className="flex items-center gap-2">
          <Gauge className="w-4 h-4 text-cyan-400" />
          <h2 className="text-sm font-bold text-slate-100 uppercase tracking-wider font-mono-numbers">
            Análisis Técnico & Rangos Cuantitativos
          </h2>
        </div>
        <span className="text-[11px] text-slate-400 font-mono-numbers">
          Base: Binance Spot • Actualizado en vivo
        </span>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
        {/* Consensus Gauge Column */}
        <div className="lg:col-span-5 flex flex-col justify-between p-4 bg-[#111a2e]/60 border border-[#1e293b] rounded-xl">
          <div>
            <div className="flex items-center justify-between mb-3">
              <span className="text-xs text-slate-400 font-mono-numbers">
                Consenso Técnico Global
              </span>
              <span
                className={`text-xs font-bold px-2.5 py-0.5 rounded-full border font-mono-numbers ${ratingColor}`}
              >
                {summary.technical_rating}
              </span>
            </div>

            {/* Segmented Bar */}
            <div className="space-y-1.5 my-3">
              <div className="grid grid-cols-5 gap-1 h-2 rounded overflow-hidden">
                {segments.map((seg, idx) => (
                  <div
                    key={idx}
                    className={`h-full transition-all ${
                      idx === activeIndex
                        ? `${seg.color} shadow-sm shadow-cyan-500/50`
                        : "bg-[#1d2b48] opacity-50"
                    }`}
                  />
                ))}
              </div>
              <div className="flex justify-between text-[10px] text-slate-500 font-mono-numbers">
                <span>Venta Fuerte</span>
                <span>Neutral</span>
                <span>Compra Fuerte</span>
              </div>
            </div>
          </div>

          {/* Quick Technical Signals */}
          <div className="grid grid-cols-3 gap-2 pt-3 border-t border-[#1e293b]/70 text-center font-mono-numbers">
            <div className="p-2 rounded bg-[#090e1a]/80 border border-[#1b2742]">
              <span className="text-[10px] text-slate-400 block">RSI (14)</span>
              <span
                className={`text-xs font-bold ${
                  summary.rsi_14 >= 70
                    ? "text-rose-400"
                    : summary.rsi_14 <= 30
                    ? "text-emerald-400"
                    : "text-slate-200"
                }`}
              >
                {summary.rsi_14.toFixed(1)}
              </span>
              <span className="text-[9px] text-slate-500 block">
                {summary.rsi_14 >= 70
                  ? "Sobrecompra"
                  : summary.rsi_14 <= 30
                  ? "Sobreventa"
                  : "Neutral"}
              </span>
            </div>

            <div className="p-2 rounded bg-[#090e1a]/80 border border-[#1b2742]">
              <span className="text-[10px] text-slate-400 block">SMA (20)</span>
              <span className="text-xs font-bold text-slate-200">
                ${summary.sma_20.toLocaleString(undefined, { maximumFractionDigits: 1 })}
              </span>
              <span
                className={`text-[9px] block ${
                  summary.current_price > summary.sma_20
                    ? "text-emerald-400"
                    : "text-rose-400"
                }`}
              >
                {summary.current_price > summary.sma_20 ? "Alcista (>SMA)" : "Bajista (<SMA)"}
              </span>
            </div>

            <div className="p-2 rounded bg-[#090e1a]/80 border border-[#1b2742]">
              <span className="text-[10px] text-slate-400 block">EMA (50)</span>
              <span className="text-xs font-bold text-slate-200">
                ${summary.ema_50.toLocaleString(undefined, { maximumFractionDigits: 1 })}
              </span>
              <span
                className={`text-[9px] block ${
                  summary.current_price > summary.ema_50
                    ? "text-emerald-400"
                    : "text-rose-400"
                }`}
              >
                {summary.current_price > summary.ema_50 ? "Alcista (>EMA)" : "Bajista (<EMA)"}
              </span>
            </div>
          </div>
        </div>

        {/* Range Sliders Column */}
        <div className="lg:col-span-7 flex flex-col justify-between gap-4 p-4 bg-[#111a2e]/60 border border-[#1e293b] rounded-xl">
          {/* 24h Range Slider */}
          <div className="space-y-1.5">
            <div className="flex items-center justify-between text-xs font-mono-numbers">
              <span className="text-slate-300 font-semibold flex items-center gap-1.5">
                <Activity className="w-3.5 h-3.5 text-cyan-400" />
                Rango de 24 Horas
              </span>
              <span className="text-slate-400">
                Posición actual: <strong className="text-slate-200">{pct24h.toFixed(0)}%</strong>
              </span>
            </div>

            {/* Slider track */}
            <div className="relative w-full h-2.5 bg-[#16223b] rounded-full overflow-hidden my-2">
              <div
                className="h-full bg-gradient-to-r from-rose-500 via-amber-400 to-emerald-400 rounded-full"
                style={{ width: "100%" }}
              />
            </div>

            <div className="flex justify-between items-center text-xs font-mono-numbers">
              <div>
                <span className="text-[10px] text-slate-500 block">Mínimo 24h</span>
                <span className="text-slate-200 font-semibold">
                  ${summary.low_24h.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                </span>
              </div>
              <div className="text-center">
                <span className="text-[10px] text-slate-500 block">Precio Actual</span>
                <span className="text-cyan-400 font-bold">
                  ${summary.current_price.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                </span>
              </div>
              <div className="text-right">
                <span className="text-[10px] text-slate-500 block">Máximo 24h</span>
                <span className="text-slate-200 font-semibold">
                  ${summary.high_24h.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                </span>
              </div>
            </div>
          </div>

          {/* 52-Week Range Slider */}
          <div className="space-y-1.5 pt-3 border-t border-[#1e293b]/70">
            <div className="flex items-center justify-between text-xs font-mono-numbers">
              <span className="text-slate-300 font-semibold flex items-center gap-1.5">
                <Calendar className="w-3.5 h-3.5 text-indigo-400" />
                Rango de 52 Semanas (1 Año)
              </span>
              <span className="text-slate-400">
                Posición anual: <strong className="text-slate-200">{pct52w.toFixed(0)}%</strong>
              </span>
            </div>

            {/* Slider track */}
            <div className="relative w-full h-2.5 bg-[#16223b] rounded-full overflow-hidden my-2">
              <div
                className="h-full bg-gradient-to-r from-indigo-500 via-cyan-400 to-emerald-400 rounded-full"
                style={{ width: "100%" }}
              />
            </div>

            <div className="flex justify-between items-center text-xs font-mono-numbers">
              <div>
                <span className="text-[10px] text-slate-500 block">Mínimo 52s</span>
                <span className="text-slate-200 font-semibold">
                  ${summary.low_52w.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                </span>
              </div>
              <div className="text-center">
                <span className="text-[10px] text-slate-500 block">VWAP Acumulado</span>
                <span className="text-slate-300 font-semibold">
                  ${summary.vwap.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                </span>
              </div>
              <div className="text-right">
                <span className="text-[10px] text-slate-500 block">Máximo 52s</span>
                <span className="text-slate-200 font-semibold">
                  ${summary.high_52w.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
