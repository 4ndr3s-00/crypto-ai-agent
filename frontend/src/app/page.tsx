"use client";

import React, { useState, useEffect } from "react";
import dynamic from "next/dynamic";
import { Header } from "@/components/layout/Header";
import { AssetBar } from "@/components/layout/AssetBar";
import { ConsoleView } from "@/components/chat/ConsoleView";
import { ReportModal } from "@/components/reports/ReportModal";
import { ChatChart, MarketReport } from "@/types";
import { apiClient } from "@/lib/apiClient";
import {
  TrendingUp,
  BarChart2,
  FileText,
  ShieldAlert,
  Layers,
  Database,
  Loader2,
  RefreshCw,
  Cpu,
} from "lucide-react";

// Dynamically import InteractiveChart with SSR disabled to prevent hydration/canvas errors
const InteractiveChart = dynamic(
  () => import("@/components/charts/InteractiveChart").then((mod) => mod.InteractiveChart),
  {
    ssr: false,
    loading: () => (
      <div className="w-full h-[400px] bg-[#0d1322] border border-[#1e293b] rounded-lg flex items-center justify-center text-xs text-slate-500 font-mono-numbers animate-pulse">
        <Loader2 className="w-5 h-5 animate-spin text-cyan-500 mr-2" />
        Inicializando lienzo de trading TradingView...
      </div>
    ),
  }
);

export default function DashboardPage() {
  const [selectedSymbol, setSelectedSymbol] = useState("BTCUSDT");
  const [selectedInterval, setSelectedInterval] = useState("15m");
  const [chartData, setChartData] = useState<ChatChart | null>(null);
  const [chartLoading, setChartLoading] = useState(true);

  const [activeReport, setActiveReport] = useState<MarketReport | null>(null);
  const [isReportModalOpen, setIsReportModalOpen] = useState(false);
  const [reportLoading, setReportLoading] = useState(false);

  // Fetch chart data when symbol or interval changes
  const loadChart = async (symbol: string, interval: string) => {
    setChartLoading(true);
    try {
      const data = await apiClient.getMarketChart(symbol, interval, 96);
      setChartData(data);
    } catch (err) {
      console.error("Error al cargar gráfico:", err);
    } finally {
      setChartLoading(false);
    }
  };

  useEffect(() => {
    loadChart(selectedSymbol, selectedInterval);
  }, [selectedSymbol, selectedInterval]);

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
        {/* Left Workbench (TradingView Chart + Quantitative Overview) */}
        <section className="lg:col-span-7 flex flex-col gap-4">
          {/* Chart Section */}
          <div className="relative">
            {chartData ? (
              <InteractiveChart
                chartData={chartData}
                height={460}
                selectedInterval={selectedInterval}
                onIntervalChange={(tf) => setSelectedInterval(tf)}
              />
            ) : (
              <div className="w-full h-[460px] bg-[#0d1322] border border-[#1e293b] rounded-lg flex items-center justify-center text-xs text-slate-400 font-mono-numbers">
                {chartLoading ? (
                  <div className="flex items-center gap-2">
                    <Loader2 className="w-5 h-5 animate-spin text-cyan-400" />
                    <span>Cargando datos OHLCV desde MinIO Parquet / DuckDB...</span>
                  </div>
                ) : (
                  <span>No hay datos de velas disponibles para {selectedSymbol}</span>
                )}
              </div>
            )}
          </div>

          {/* Quantitative Metrics Summary Strip */}
          {chartData?.indicators && (
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
              <div className="p-3 bg-[#0d1322] border border-[#1e293b] rounded-lg">
                <span className="text-[11px] text-slate-500 font-mono-numbers block">VWAP 24h</span>
                <span className="text-sm font-semibold text-cyan-400 font-mono-numbers">
                  ${chartData.indicators.vwap ? Number(chartData.indicators.vwap).toLocaleString(undefined, { minimumFractionDigits: 2 }) : "N/A"}
                </span>
              </div>

              <div className="p-3 bg-[#0d1322] border border-[#1e293b] rounded-lg">
                <span className="text-[11px] text-slate-500 font-mono-numbers block">Soporte S1</span>
                <span className="text-sm font-semibold text-emerald-400 font-mono-numbers">
                  ${chartData.indicators.support_s1 ? Number(chartData.indicators.support_s1).toLocaleString(undefined, { minimumFractionDigits: 2 }) : "N/A"}
                </span>
              </div>

              <div className="p-3 bg-[#0d1322] border border-[#1e293b] rounded-lg">
                <span className="text-[11px] text-slate-500 font-mono-numbers block">Resistencia R1</span>
                <span className="text-sm font-semibold text-rose-400 font-mono-numbers">
                  ${chartData.indicators.resistance_r1 ? Number(chartData.indicators.resistance_r1).toLocaleString(undefined, { minimumFractionDigits: 2 }) : "N/A"}
                </span>
              </div>

              <div className="p-3 bg-[#0d1322] border border-[#1e293b] rounded-lg flex items-center justify-between">
                <div>
                  <span className="text-[11px] text-slate-500 font-mono-numbers block">Reporte Cuantitativo</span>
                  <button
                    type="button"
                    onClick={() => handleOpenReport(selectedSymbol)}
                    disabled={reportLoading}
                    className="mt-0.5 text-xs font-semibold text-cyan-400 hover:text-cyan-300 underline font-mono-numbers flex items-center gap-1"
                  >
                    {reportLoading ? (
                      <Loader2 className="w-3 h-3 animate-spin" />
                    ) : (
                      <FileText className="w-3 h-3" />
                    )}
                    Ver {selectedSymbol}
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* Anti-Hallucination & Provenance Footer Notice */}
          <div className="p-3 bg-[#0d1322]/60 border border-[#1e293b] rounded-lg flex items-center justify-between text-xs font-mono-numbers text-slate-400">
            <div className="flex items-center gap-2">
              <ShieldAlert className="w-4 h-4 text-cyan-400" />
              <span>Verificación Factual Estricta: Cada dato numérico proviene de MinIO S3 y DuckDB sin simulación.</span>
            </div>
            <button
              type="button"
              onClick={() => loadChart(selectedSymbol, selectedInterval)}
              className="p-1 hover:text-slate-200 transition-colors"
              title="Recargar gráfico"
            >
              <RefreshCw className="w-3.5 h-3.5" />
            </button>
          </div>
        </section>

        {/* Right Workbench (Arca AI Conversational Console) */}
        <section className="lg:col-span-5 flex flex-col h-[650px] lg:h-auto min-h-[550px]">
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
