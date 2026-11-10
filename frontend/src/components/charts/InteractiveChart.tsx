"use client";

import React, { useEffect, useRef, useState } from "react";
import {
  createChart,
  ColorType,
  CandlestickSeries,
  HistogramSeries,
  LineSeries,
  IChartApi,
  ISeriesApi,
  Time,
  UTCTimestamp,
} from "lightweight-charts";
import { ChatChart, Candle } from "@/types";
import { TrendingUp, Layers, Database, ShieldCheck, Activity } from "lucide-react";

interface InteractiveChartProps {
  chartData: ChatChart;
  height?: number;
  showControls?: boolean;
  selectedInterval?: string;
  onIntervalChange?: (interval: string) => void;
}

export function InteractiveChart({
  chartData,
  height = 400,
  showControls = true,
  selectedInterval,
  onIntervalChange,
}: InteractiveChartProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartInstanceRef = useRef<IChartApi | null>(null);

  const [activeTooltip, setActiveTooltip] = useState<{
    time: string;
    open: number;
    high: number;
    low: number;
    close: number;
    volume: number;
    changePct: number;
  } | null>(null);

  const intervals = ["1m", "5m", "15m", "1h", "4h", "1d"];

  useEffect(() => {
    if (!containerRef.current) return;

    // Clear any previous chart instances
    if (chartInstanceRef.current) {
      chartInstanceRef.current.remove();
      chartInstanceRef.current = null;
    }

    const container = containerRef.current;
    const chart = createChart(container, {
      width: container.clientWidth || 600,
      height: height,
      layout: {
        background: { type: ColorType.Solid, color: "#0d1322" },
        textColor: "#94a3b8",
        fontSize: 12,
        fontFamily: "ui-monospace, SFMono-Regular, Menlo, monospace",
      },
      grid: {
        vertLines: { color: "#1e293b", style: 1 },
        horzLines: { color: "#1e293b", style: 1 },
      },
      crosshair: {
        vertLine: {
          color: "#06b6d4",
          width: 1,
          style: 3,
          labelBackgroundColor: "#0f172a",
        },
        horzLine: {
          color: "#06b6d4",
          width: 1,
          style: 3,
          labelBackgroundColor: "#0f172a",
        },
      },
      timeScale: {
        borderColor: "#1e293b",
        timeVisible: true,
        secondsVisible: false,
      },
      rightPriceScale: {
        borderColor: "#1e293b",
        scaleMargins: {
          top: 0.1,
          bottom: 0.2,
        },
      },
    });

    chartInstanceRef.current = chart;

    // Setup Candlestick series
    const candleSeries = chart.addSeries(CandlestickSeries, {
      upColor: "#10b981",
      downColor: "#f43f5e",
      borderUpColor: "#10b981",
      borderDownColor: "#f43f5e",
      wickUpColor: "#10b981",
      wickDownColor: "#f43f5e",
    });

    // Setup Volume Histogram series overlay
    const volumeSeries = chart.addSeries(HistogramSeries, {
      priceFormat: {
        type: "volume",
      },
      priceScaleId: "volume_overlay",
    });

    chart.priceScale("volume_overlay").applyOptions({
      scaleMargins: {
        top: 0.82,
        bottom: 0,
      },
    });

    // Prepare and sanitize candle data (sort ascending, remove duplicates)
    const rawCandles = chartData.candles || [];
    const candleMap = new Map<number, Candle>();

    for (const c of rawCandles) {
      const sec = Math.floor(new Date(c.timestamp).getTime() / 1000);
      if (!isNaN(sec) && sec > 0) {
        candleMap.set(sec, c);
      }
    }

    const sortedSeconds = Array.from(candleMap.keys()).sort((a, b) => a - b);

    const formattedCandles = sortedSeconds.map((sec) => {
      const c = candleMap.get(sec)!;
      return {
        time: sec as UTCTimestamp,
        open: c.open,
        high: c.high,
        low: c.low,
        close: c.close,
      };
    });

    const formattedVolumes = sortedSeconds.map((sec) => {
      const c = candleMap.get(sec)!;
      const isUp = c.close >= c.open;
      return {
        time: sec as UTCTimestamp,
        value: c.volume,
        color: isUp ? "rgba(16, 185, 129, 0.35)" : "rgba(244, 63, 94, 0.35)",
      };
    });

    if (formattedCandles.length > 0) {
      candleSeries.setData(formattedCandles);
      volumeSeries.setData(formattedVolumes);

      // Default tooltip to last candle
      const last = formattedCandles[formattedCandles.length - 1];
      const lastVol = formattedVolumes[formattedVolumes.length - 1]?.value || 0;
      const changePct = ((last.close - last.open) / (last.open || 1)) * 100;
      setActiveTooltip({
        time: new Date((last.time as number) * 1000).toISOString().replace("T", " ").slice(0, 19) + " UTC",
        open: last.open,
        high: last.high,
        low: last.low,
        close: last.close,
        volume: lastVol,
        changePct,
      });
    }

    // Add VWAP Price Line if present
    if (chartData.indicators?.vwap && typeof chartData.indicators.vwap === "number") {
      candleSeries.createPriceLine({
        price: chartData.indicators.vwap,
        color: "#06b6d4",
        lineWidth: 2,
        lineStyle: 2,
        axisLabelVisible: true,
        title: "VWAP",
      });
    }

    // Add Support Level if present
    if (chartData.indicators?.support_s1 && typeof chartData.indicators.support_s1 === "number") {
      candleSeries.createPriceLine({
        price: chartData.indicators.support_s1,
        color: "#10b981",
        lineWidth: 1,
        lineStyle: 3,
        axisLabelVisible: true,
        title: "S1 Soporte",
      });
    }

    // Add Resistance Level if present
    if (chartData.indicators?.resistance_r1 && typeof chartData.indicators.resistance_r1 === "number") {
      candleSeries.createPriceLine({
        price: chartData.indicators.resistance_r1,
        color: "#f43f5e",
        lineWidth: 1,
        lineStyle: 3,
        axisLabelVisible: true,
        title: "R1 Resistencia",
      });
    }

    // Subscribe to crosshair move for real-time hover inspection
    chart.subscribeCrosshairMove((param) => {
      if (!param || !param.time || !param.seriesData) return;
      const data = param.seriesData.get(candleSeries) as any;
      const volData = param.seriesData.get(volumeSeries) as any;

      if (data && typeof data.close === "number") {
        const timeSec = param.time as number;
        const timeStr =
          typeof param.time === "number"
            ? new Date(timeSec * 1000).toISOString().replace("T", " ").slice(0, 19) + " UTC"
            : String(param.time);
        const changePct = ((data.close - data.open) / (data.open || 1)) * 100;
        setActiveTooltip({
          time: timeStr,
          open: data.open,
          high: data.high,
          low: data.low,
          close: data.close,
          volume: volData?.value || 0,
          changePct,
        });
      }
    });

    chart.timeScale().fitContent();

    // Resize observer
    const handleResize = () => {
      if (containerRef.current && chartInstanceRef.current) {
        chartInstanceRef.current.applyOptions({
          width: containerRef.current.clientWidth,
        });
      }
    };

    window.addEventListener("resize", handleResize);

    return () => {
      window.removeEventListener("resize", handleResize);
      if (chartInstanceRef.current) {
        chartInstanceRef.current.remove();
        chartInstanceRef.current = null;
      }
    };
  }, [chartData, height]);

  const currentInterval = selectedInterval || chartData.interval || "15m";

  return (
    <div className="w-full bg-[#0d1322] border border-[#1e293b] rounded-lg overflow-hidden flex flex-col shadow-xl">
      {/* Header Bar */}
      <div className="flex flex-wrap items-center justify-between px-4 py-2.5 border-b border-[#1e293b] bg-[#111a2e]/60 backdrop-blur-sm gap-2">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1.5 text-cyan-400 font-semibold tracking-wider text-sm font-mono-numbers">
            <TrendingUp className="w-4 h-4" />
            <span>{chartData.symbol}</span>
          </div>

          <div className="flex items-center gap-1 bg-[#1a253d] px-2 py-0.5 rounded text-xs text-slate-300 font-mono-numbers border border-[#22314e]">
            <Database className="w-3 h-3 text-cyan-400" />
            <span>{chartData.data_source || chartData.source}</span>
          </div>

          {chartData.indicators?.vwap && (
            <div className="hidden sm:flex items-center gap-1 text-xs text-cyan-400 font-mono-numbers">
              <span className="text-slate-500">VWAP:</span>
              <span>${Number(chartData.indicators.vwap).toFixed(2)}</span>
            </div>
          )}
        </div>

        {/* Interval Selector */}
        {showControls && (
          <div className="flex items-center gap-1 bg-[#090d16] p-0.5 rounded-md border border-[#1e293b]">
            {intervals.map((tf) => (
              <button
                key={tf}
                type="button"
                onClick={() => onIntervalChange?.(tf)}
                className={`px-2 py-1 rounded text-xs font-mono-numbers font-medium transition-colors ${
                  currentInterval === tf
                    ? "bg-cyan-500/20 text-cyan-300 border border-cyan-500/40"
                    : "text-slate-400 hover:text-slate-200 hover:bg-[#131c31]"
                }`}
              >
                {tf}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Tooltip / Legend Bar */}
      <div className="px-4 py-1.5 border-b border-[#1e293b]/60 bg-[#0a0f1b] flex flex-wrap items-center gap-x-4 gap-y-1 text-xs font-mono-numbers text-slate-300 min-h-[30px]">
        {activeTooltip ? (
          <>
            <span className="text-slate-500">{activeTooltip.time}</span>
            <div>
              <span className="text-slate-500">O: </span>
              <span className="text-slate-200">${activeTooltip.open.toLocaleString()}</span>
            </div>
            <div>
              <span className="text-slate-500">H: </span>
              <span className="text-slate-200">${activeTooltip.high.toLocaleString()}</span>
            </div>
            <div>
              <span className="text-slate-500">L: </span>
              <span className="text-slate-200">${activeTooltip.low.toLocaleString()}</span>
            </div>
            <div>
              <span className="text-slate-500">C: </span>
              <span className={activeTooltip.changePct >= 0 ? "text-emerald-400 font-semibold" : "text-rose-400 font-semibold"}>
                ${activeTooltip.close.toLocaleString()}
              </span>
            </div>
            <div>
              <span className="text-slate-500">Var: </span>
              <span className={activeTooltip.changePct >= 0 ? "text-emerald-400" : "text-rose-400"}>
                {activeTooltip.changePct >= 0 ? "+" : ""}
                {activeTooltip.changePct.toFixed(2)}%
              </span>
            </div>
            {activeTooltip.volume > 0 && (
              <div>
                <span className="text-slate-500">Vol: </span>
                <span className="text-slate-300">{activeTooltip.volume.toFixed(2)}</span>
              </div>
            )}
          </>
        ) : (
          <span className="text-slate-500 flex items-center gap-1.5">
            <Activity className="w-3.5 h-3.5 text-cyan-400 animate-pulse" />
            Mueve el cursor sobre las velas para inspeccionar detalles
          </span>
        )}
      </div>

      {/* Chart Canvas */}
      <div ref={containerRef} className="w-full relative" style={{ height: `${height}px` }} />
    </div>
  );
}
