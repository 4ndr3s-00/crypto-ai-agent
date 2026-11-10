"use client";

import React, { useState } from "react";
import ReactMarkdown from "react-markdown";
import { FileText, Download, Copy, Check, X, ShieldCheck, Database, Calendar } from "lucide-react";
import { MarketReport } from "@/types";
import { apiClient } from "@/lib/apiClient";

interface ReportModalProps {
  report: MarketReport | null;
  isOpen: boolean;
  onClose: () => void;
}

export function ReportModal({ report, isOpen, onClose }: ReportModalProps) {
  const [copied, setCopied] = useState(false);

  if (!isOpen || !report) return null;

  const handleCopy = () => {
    navigator.clipboard.writeText(report.report_markdown);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const exportUrl = apiClient.getReportExportUrl(report.symbol);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-fadeIn">
      <div className="relative w-full max-w-4xl max-h-[90vh] bg-[#0d1322] border border-[#1e293b] rounded-xl shadow-2xl flex flex-col overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-[#1e293b] bg-[#111a2e]">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-cyan-500/10 border border-cyan-500/20 rounded-lg text-cyan-400">
              <FileText className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base font-semibold text-slate-100 flex items-center gap-2 font-mono-numbers">
                Reporte Cuantitativo de Mercado: {report.symbol}
              </h2>
              <div className="flex items-center gap-3 text-xs text-slate-400 mt-0.5 font-mono-numbers">
                <span className="flex items-center gap-1">
                  <Calendar className="w-3.5 h-3.5 text-slate-500" />
                  {new Date(report.generated_at).toLocaleString()}
                </span>
                <span className="flex items-center gap-1">
                  <Database className="w-3.5 h-3.5 text-cyan-500" />
                  {report.source}
                </span>
                <span className="flex items-center gap-1 text-emerald-400">
                  <ShieldCheck className="w-3.5 h-3.5" />
                  Auditado Factualmente
                </span>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={handleCopy}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-mono-numbers rounded-lg bg-[#16223b] hover:bg-[#1e293b] text-slate-200 border border-[#23355b] transition-colors"
            >
              {copied ? (
                <>
                  <Check className="w-3.5 h-3.5 text-emerald-400" />
                  <span>Copiado</span>
                </>
              ) : (
                <>
                  <Copy className="w-3.5 h-3.5 text-slate-400" />
                  <span>Copiar MD</span>
                </>
              )}
            </button>

            <a
              href={exportUrl}
              download={`reporte_${report.symbol}.md`}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-mono-numbers rounded-lg bg-cyan-600 hover:bg-cyan-500 text-slate-950 font-semibold transition-colors"
            >
              <Download className="w-3.5 h-3.5" />
              <span>Descargar</span>
            </a>

            <button
              type="button"
              onClick={onClose}
              className="p-1.5 text-slate-400 hover:text-slate-100 rounded-lg hover:bg-[#16223b] transition-colors ml-1"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Content Body */}
        <div className="flex-1 overflow-y-auto p-6 space-y-4 text-slate-200 text-sm leading-relaxed">
          <div className="prose prose-invert max-w-none prose-headings:text-slate-100 prose-headings:font-semibold prose-a:text-cyan-400 prose-table:border-collapse prose-th:border prose-th:border-[#1e293b] prose-th:bg-[#111a2e] prose-th:p-2 prose-td:border prose-td:border-[#1e293b] prose-td:p-2 prose-code:text-cyan-300 prose-code:bg-[#111a2e] prose-code:px-1 prose-code:py-0.5 prose-code:rounded">
            <ReactMarkdown>{report.report_markdown}</ReactMarkdown>
          </div>
        </div>

        {/* Footer */}
        <div className="px-6 py-3 border-t border-[#1e293b] bg-[#0a0f1b] flex items-center justify-between text-xs text-slate-500 font-mono-numbers">
          <span>Generado determinísticamente con DuckDB OLAP + MinIO Data Lake</span>
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-1.5 bg-[#16223b] hover:bg-[#1e293b] text-slate-300 rounded text-xs transition-colors"
          >
            Cerrar
          </button>
        </div>
      </div>
    </div>
  );
}
