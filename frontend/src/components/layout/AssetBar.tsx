"use client";

import React, { useEffect, useState } from "react";
import { TrendingUp, TrendingDown, RefreshCw } from "lucide-react";
import { LiveTicker } from "@/types";
import { apiClient } from "@/lib/apiClient";

interface AssetBarProps {
  selectedSymbol: string;
  onSelectSymbol: (symbol: string) => void;
}

export function AssetBar({ selectedSymbol, onSelectSymbol }: AssetBarProps) {
  const [tickers, setTickers] = useState<LiveTicker[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchOverview = async () => {
    try {
      const data = await apiClient.getMarketOverview();
      if (data && data.assets) {
        setTickers(data.assets);
      }
    } catch (err) {
      // Backend error or not running
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchOverview();
    const interval = setInterval(fetchOverview, 10000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="w-full bg-[#0d1322] border-b border-[#1e293b] px-4 py-2 flex items-center justify-between overflow-x-auto scrollbar-none gap-4">
      <div className="flex items-center gap-3">
        <span className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider font-mono-numbers flex-shrink-0">
          Mercados Reales:
        </span>

        {tickers.map((t) => {
          const isSelected = t.symbol === selectedSymbol;
          const isPositive = t.price_change_percent_24h >= 0;

          return (
            <button
              key={t.symbol}
              type="button"
              onClick={() => onSelectSymbol(t.symbol)}
              className={`flex items-center gap-2 px-3 py-1.5 rounded-lg border text-xs font-mono-numbers transition-all flex-shrink-0 ${
                isSelected
                  ? "bg-cyan-500/10 border-cyan-500/40 text-cyan-300 shadow-sm shadow-cyan-900/20"
                  : "bg-[#111a2e]/60 border-[#1e293b] hover:bg-[#16223b] text-slate-300"
              }`}
            >
              <span className="font-bold">{t.symbol}</span>
              <span className="text-slate-100">${t.price.toLocaleString()}</span>
              <span
                className={`flex items-center gap-0.5 font-medium ${
                  isPositive ? "text-emerald-400" : "text-rose-400"
                }`}
              >
                {isPositive ? (
                  <TrendingUp className="w-3 h-3" />
                ) : (
                  <TrendingDown className="w-3 h-3" />
                )}
                {isPositive ? "+" : ""}
                {t.price_change_percent_24h.toFixed(2)}%
              </span>
            </button>
          );
        })}

        {tickers.length === 0 && !loading && (
          <span className="text-xs text-slate-500 font-mono-numbers">
            Esperando datos de Binance Live / DuckDB...
          </span>
        )}
      </div>

      <button
        type="button"
        onClick={fetchOverview}
        className="p-1 text-slate-500 hover:text-slate-300 rounded transition-colors flex-shrink-0"
        title="Actualizar cotizaciones en vivo"
      >
        <RefreshCw className="w-3.5 h-3.5" />
      </button>
    </div>
  );
}
