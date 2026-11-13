export type Provenance = "MINIO_LAKE" | "EXCHANGE_LIVE" | "DUCKDB_OLAP" | "ROUTER_GUARD";

export interface Candle {
  timestamp: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface ChatChart {
  symbol: string;
  interval: string;
  chart_type: "candlestick" | "line" | "volume_histogram";
  candles: Candle[];
  indicators: {
    vwap?: number;
    support_s1?: number;
    resistance_r1?: number;
    range_high_24h?: number;
    range_low_24h?: number;
    volume_total?: number;
    [key: string]: any;
  };
  source: string;
  data_source: string;
  cutoff_time?: string;
}

export interface ToolCallRecord {
  name: string;
  arguments: Record<string, any>;
  result_summary: string;
}

export interface SourceReference {
  source: string;
  title?: string;
  snippet?: string;
  kind: "tool" | "database" | "exchange" | "guardrail";
}

export interface ChatResponse {
  provider?: string;
  model?: string | null;
  answer?: string;
  reply?: string;
  chart?: ChatChart | null;
  tool_calls: ToolCallRecord[];
  sources: SourceReference[];
  latency_ms: number;
  provenance: Provenance;
}

export interface ChatRequest {
  message: string;
  conversation_id?: string;
}

export interface LiveTicker {
  symbol: string;
  price?: number;
  current_price?: number;
  price_change_percent_24h?: number;
  return_24h?: number;
  open?: number;
  high?: number;
  high_24h?: number;
  low?: number;
  low_24h?: number;
  volume_24h?: number;
  timestamp?: string;
  cutoff_time?: string;
}

export interface MarketOverview {
  assets: LiveTicker[];
  count: number;
  timestamp: string;
}

export interface HealthServices {
  binance?: string;
  ollama?: string;
  ollama_model?: string | null;
  groq_model?: string | null;
  api?: string;
  minio?: string | boolean;
  duckdb?: string | boolean;
  groq?: string;
  groq_llama?: boolean;
  ollama_local?: boolean;
}

export interface HealthResponse {
  status: "healthy" | "degraded" | "unhealthy";
  services: HealthServices;
  timestamp: string;
  version: string;
}

export interface MarketReport {
  symbol: string;
  generated_at: string;
  report_markdown: string;
  metrics: Record<string, any>;
  source: string;
}

export interface ChatMessage {
  provider?: string;
  model?: string | null;
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: string;
  chart?: ChatChart | null;
  provenance?: Provenance;
  latency_ms?: number;
  sources?: SourceReference[];
}

export interface TechnicalSummary {
  symbol: string;
  current_price: number;
  change_24h: number;
  return_24h: number;
  high_24h: number;
  low_24h: number;
  volume_24h: number;
  vwap: number;
  rsi_14: number;
  sma_20: number;
  ema_50: number;
  technical_rating: string;
  rating_score: number;
  horizons: {
    "24h": number;
    "7d": number;
    "30d": number;
    "90d": number;
    "1y": number;
  };
  high_52w: number;
  low_52w: number;
  source: string;
  data_source: string;
  timestamp: string;
}

