"use client";

import React from "react";
import { TrendingUp, TrendingDown, Clock, ShieldCheck, Activity } from "lucide-react";
import { TechnicalSummary } from "@/types";

interface TradingViewHeroProps {
  summary: TechnicalSummary | null;
  selectedSymbol: string;
  onSelectHorizon?: (horizon: string) => void;
  selectedHorizon?: string;
}

export function TradingViewHero({
  summary,
  selectedSymbol,
  onSelectHorizon,
  selectedHorizon = "24h",
}: TradingViewHeroProps) {
  if (!summary || summary.symbol !== selectedSymbol) {
    return (
      <div className="w-full bg-[#0d1322] border border-[#1e293b] rounded-xl p-4 animate-pulse">
        <div className="h-6 w-48 bg-[#16223b] rounded mb-2"></div>
        <div className="h-10 w-36 bg-[#16223b] rounded"></div>
      </div>
    );
  }

  const isPositive = summary.return_24h >= 0;
  const horizons = [
    { key: "24h", label: "24 horas", value: summary.horizons["24h"] },
    { key: "7d", label: "1 semana", value: summary.horizons["7d"] },
    { key: "30d", label: "1 mes", value: summary.horizons["30d"] },
    { key: "90d", label: "3 meses", value: summary.horizons["90d"] },
    { key: "1y", label: "1 año", value: summary.horizons["1y"] },
  ];

  const getPairFullName = (sym: string) => {
    if (sym === "BTCUSDT") return "Bitcoin / TetherUS";
    if (sym === "ETHUSDT") return "Ethereum / TetherUS";
    if (sym === "SOLUSDT") return "Solana / TetherUS";
    if (sym === "BNBUSDT") return "BNB / TetherUS";
    return `${sym} Spot`;
  };

  return (
    <div className="w-full bg-[#0d1322] border border-[#1e293b] rounded-xl p-4 lg:p-5 flex flex-col gap-4 shadow-xl">
      {/* Top Title & Exchange Badges */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-full bg-amber-500/10 border border-amber-500/30 flex items-center justify-center font-bold text-xs text-amber-400 font-mono-numbers">
            {selectedSymbol.slice(0, 3)}
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-lg lg:text-xl font-bold text-slate-100 tracking-tight font-mono-numbers">
                {getPairFullName(selectedSymbol)}
              </h1>
              <span className="text-xs px-2 py-0.5 rounded bg-[#16223b] text-slate-300 border border-[#223558] font-mono-numbers">
                {selectedSymbol}
              </span>
            </div>
            <div className="flex items-center gap-2 mt-0.5 text-xs text-slate-400 font-mono-numbers">
              <span className="text-amber-400 font-semibold">BINANCE</span>
              <span>•</span>
              <span>Spot CEX</span>
              <span>•</span>
              <span className="flex items-center gap-1 text-emerald-400">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
                Mercado Abierto 24/7
              </span>
            </div>
          </div>
        </div>

        {/* Real-time Data Source Badge */}
        <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-[#111a2e] border border-[#1e293b] text-xs font-mono-numbers text-slate-400">
          <ShieldCheck className="w-3.5 h-3.5 text-cyan-400" />
          <span>Binance Spot API Real</span>
        </div>
      </div>

      {/* Center Live Price & Change */}
      <div className="flex flex-wrap items-baseline gap-4">
        <span className="text-3xl lg:text-4xl font-extrabold text-slate-100 font-mono-numbers tracking-tight">
          ${summary.current_price.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
        </span>

        <div
          className={`flex items-center gap-1.5 px-3 py-1 rounded-lg text-sm font-bold font-mono-numbers ${
            isPositive
              ? "bg-emerald-500/15 text-emerald-400 border border-emerald-500/30"
              : "bg-rose-500/15 text-rose-400 border border-rose-500/30"
          }`}
        >
          {isPositive ? <TrendingUp className="w-4 h-4" /> : <TrendingDown className="w-4 h-4" />}
          <span>
            {isPositive ? "+" : ""}
            {summary.change_24h.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          </span>
          <span>({isPositive ? "+" : ""}{summary.return_24h.toFixed(2)}%)</span>
          <span className="text-xs opacity-75 font-normal">24h</span>
        </div>
      </div>

      {/* Multi-Horizon Performance Strip (TradingView style) */}
      <div className="flex items-center gap-1.5 overflow-x-auto scrollbar-none pt-1 border-t border-[#1e293b]/70">
        <span className="text-xs text-slate-500 font-mono-numbers mr-2 hidden sm:inline flex-shrink-0">
          Rendimiento:
        </span>
        {horizons.map((h) => {
          const positive = h.value >= 0;
          const isSelected = selectedHorizon === h.key;
          return (
            <button
              key={h.key}
              type="button"
              onClick={() => onSelectHorizon?.(h.key)}
              className={`flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-mono-numbers transition-all flex-shrink-0 border ${
                isSelected
                  ? "bg-cyan-500/15 border-cyan-500/40 text-cyan-300"
                  : "bg-[#111a2e]/80 border-[#1e293b] hover:bg-[#16223b] text-slate-300"
              }`}
            >
              <span className="text-slate-400">{h.label}:</span>
              <span className={`font-semibold ${positive ? "text-emerald-400" : "text-rose-400"}`}>
                {positive ? "+" : ""}
                {h.value.toFixed(2)}%
              </span>
            </button>
          );
        })}
      </div>
    </div>
  );
}
