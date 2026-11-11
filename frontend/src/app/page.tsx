"use client";

import React, { useState, useEffect, useCallback } from "react";
import dynamic from "next/dynamic";
import { Header } from "@/components/layout/Header";
import { AssetBar } from "@/components/layout/AssetBar";
import { ConsoleView } from "@/components/chat/ConsoleView";
import { ReportModal } from "@/components/reports/ReportModal";
import { TradingViewHero } from "@/components/market/TradingViewHero";
import { TechnicalSummary } from "@/components/market/TechnicalSummary";
import { ChatChart, MarketReport, TechnicalSummary as TechnicalSummaryType } from "@/types";
import { apiClient } from "@/lib/apiClient";
import {
  ShieldAlert,
  Loader2,
  RefreshCw,
} from "lucide-react";

// Dynamically import InteractiveChart with SSR disabled to prevent hydration/canvas errors
const InteractiveChart = dynamic(
  () => import("@/components/charts/InteractiveChart").then((mod) => mod.InteractiveChart),
  {
    ssr: false,
    loading: () => (
      <div className="w-full h-[460px] bg-[#0d1322] border border-[#1e293b] rounded-xl flex items-center justify-center text-xs text-slate-500 font-mono-numbers animate-pulse">
        <Loader2 className="w-5 h-5 animate-spin text-cyan-500 mr-2" />
        Inicializando lienzo de trading TradingView...
      </div>
    ),
  }
);

export default function DashboardPage() {
  const [selectedSymbol, setSelectedSymbol] = useState("BTCUSDT");
  const [selectedInterval, setSelectedInterval] = useState("15m");
  const [selectedHorizon, setSelectedHorizon] = useState("24h");
  
  const [chartData, setChartData] = useState<ChatChart | null>(null);
  const [chartLoading, setChartLoading] = useState(true);

  const [technicalSummary, setTechnicalSummary] = useState<TechnicalSummaryType | null>(null);
  const [summaryLoading, setSummaryLoading] = useState(true);

  const [activeReport, setActiveReport] = useState<MarketReport | null>(null);
  const [isReportModalOpen, setIsReportModalOpen] = useState(false);
  const [reportLoading, setReportLoading] = useState(false);

  // Fetch chart data
  const loadChart = useCallback(async (symbol: string, interval: string) => {
    setChartLoading(true);
    try {
      const data = await apiClient.getMarketChart(symbol, interval, 96);
      setChartData(data);
    } catch (err) {
      console.error("Error al cargar gráfico:", err);
    } finally {
      setChartLoading(false);
    }
  }, []);

  // Fetch technical summary
  const loadTechnicalSummary = useCallback(async (symbol: string) => {
    setSummaryLoading(true);
    try {
      const summary = await apiClient.getTechnicalSummary(symbol);
      setTechnicalSummary(summary);
    } catch (err) {
      console.error("Error al cargar resumen técnico:", err);
    } finally {
      setSummaryLoading(false);
    }
  }, []);

  // Sync data when symbol or interval changes
  useEffect(() => {
    loadChart(selectedSymbol, selectedInterval);
    loadTechnicalSummary(selectedSymbol);
  }, [selectedSymbol, selectedInterval, loadChart, loadTechnicalSummary]);

  // Periodic refresh every 30 seconds for live market tickers
  useEffect(() => {
    const timer = setInterval(() => {
      loadTechnicalSummary(selectedSymbol);
    }, 30000);
    return () => clearInterval(timer);
  }, [selectedSymbol, loadTechnicalSummary]);

  const handleSelectHorizon = (horizon: string) => {
    setSelectedHorizon(horizon);
    if (horizon === "24h") setSelectedInterval("15m");
    else if (horizon === "7d") setSelectedInterval("1h");
    else if (horizon === "30d") setSelectedInterval("4h");
    else if (horizon === "90d" || horizon === "1y") setSelectedInterval("1d");
  };

  const handleOpenReport = async (symbol?: string) => {
    const sym = symbol || selectedSymbol;
    setReportLoading(true);
    try {
      const report = await apiClient.getMarketReport(sym);
      setActiveReport(report);
      setIsReportModalOpen(true);
    } catch (err) {
      console.error("Error al obtener reporte cuantitativo:", err);
    } finally {
      setReportLoading(false);
    }
  };

  const handleManualRefresh = () => {
    loadChart(selectedSymbol, selectedInterval);
    loadTechnicalSummary(selectedSymbol);
  };

  return (
    <div className="min-h-screen flex flex-col bg-[#080c14] text-slate-100">
      {/* System Header */}
      <Header onOpenReportModal={() => handleOpenReport()} />

      {/* Real Market Asset Bar */}
      <AssetBar
        selectedSymbol={selectedSymbol}
        onSelectSymbol={(sym) => setSelectedSymbol(sym)}
      />

      {/* Main Workspace Grid */}
      <main className="flex-1 p-3 lg:p-4 grid grid-cols-1 lg:grid-cols-12 gap-4 max-w-[1920px] w-full mx-auto">
        {/* Left Workbench (TradingView Hero + Interactive Chart + Technical Summary) */}
        <section className="lg:col-span-7 flex flex-col gap-4">
          {/* TradingView Hero (Live Price, 24h Change Pill, Horizon Strip, Exchange Badges) */}
          <TradingViewHero
            summary={technicalSummary}
            selectedSymbol={selectedSymbol}
            selectedHorizon={selectedHorizon}
            onSelectHorizon={handleSelectHorizon}
          />

          {/* Interactive TradingView Candlestick Chart */}
          <div className="relative">
            {chartData ? (
              <InteractiveChart
                chartData={chartData}
                height={460}
                selectedInterval={selectedInterval}
                onIntervalChange={(tf) => setSelectedInterval(tf)}
              />
            ) : (
              <div className="w-full h-[460px] bg-[#0d1322] border border-[#1e293b] rounded-xl flex items-center justify-center text-xs text-slate-400 font-mono-numbers">
                {chartLoading ? (
                  <div className="flex items-center gap-2">
                    <Loader2 className="w-5 h-5 animate-spin text-cyan-400" />
                    <span>Cargando datos OHLCV desde Binance Spot / MinIO S3...</span>
                  </div>
                ) : (
                  <span>No hay datos de velas disponibles para {selectedSymbol}</span>
                )}
              </div>
            )}
          </div>

          {/* Technical Summary (Consensus Gauge, 24h & 52w Range Sliders, RSI, SMA, EMA) */}
          <TechnicalSummary
            summary={technicalSummary}
            loading={summaryLoading}
          />

          {/* Anti-Hallucination & Provenance Footer Notice */}
          <div className="p-3 bg-[#0d1322]/60 border border-[#1e293b] rounded-xl flex items-center justify-between text-xs font-mono-numbers text-slate-400">
            <div className="flex items-center gap-2">
              <ShieldAlert className="w-4 h-4 text-cyan-400" />
              <span>Verificación Factual Estricta: Cotizaciones en tiempo real reconciliadas con Binance Spot y MinIO S3.</span>
            </div>
            <button
              type="button"
              onClick={handleManualRefresh}
              className="p-1 hover:text-slate-200 transition-colors"
              title="Recargar gráfico y métricas"
            >
              <RefreshCw className="w-3.5 h-3.5" />
            </button>
          </div>
        </section>

        {/* Right Workbench (Market Copilot Conversational Console) */}
        <section className="lg:col-span-5 flex flex-col h-[700px] lg:h-auto min-h-[550px]">
          <ConsoleView
            onOpenReport={(sym) => handleOpenReport(sym)}
            onSelectSymbol={(sym) => setSelectedSymbol(sym)}
          />
        </section>
      </main>

      {/* Quantitative Report Modal */}
      <ReportModal
        report={activeReport}
        isOpen={isReportModalOpen}
        onClose={() => setIsReportModalOpen(false)}
      />
    </div>
  );
}
