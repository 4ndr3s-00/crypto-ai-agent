import {
  ChatRequest,
  ChatResponse,
  ChatChart,
  HealthResponse,
  MarketOverview,
  MarketReport,
} from "@/types";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001";

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = "ApiError";
  }
}

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let errMsg = `Error ${res.status}: ${res.statusText}`;
    try {
      const errJson = await res.json();
      if (errJson.detail) {
        errMsg = typeof errJson.detail === "string" ? errJson.detail : JSON.stringify(errJson.detail);
      }
    } catch {
      // no json response
    }
    throw new ApiError(res.status, errMsg);
  }
  return res.json() as Promise<T>;
}

export const apiClient = {
  baseUrl: API_BASE_URL,

  async checkHealth(): Promise<HealthResponse> {
    const res = await fetch(`${API_BASE_URL}/health`, { cache: "no-store" });
    return handleResponse<HealthResponse>(res);
  },

  async getMarketOverview(): Promise<MarketOverview> {
    const res = await fetch(`${API_BASE_URL}/api/market/overview`, { cache: "no-store" });
    return handleResponse<MarketOverview>(res);
  },

  async getMarketChart(
    symbol = "BTCUSDT",
    interval = "15m",
    limit = 96
  ): Promise<ChatChart> {
    const params = new URLSearchParams({
      symbol,
      interval,
      limit: limit.toString(),
    });
    const res = await fetch(`${API_BASE_URL}/api/market/chart?${params.toString()}`, {
      cache: "no-store",
    });
    return handleResponse<ChatChart>(res);
  },

  async getMarketReport(symbol = "BTCUSDT"): Promise<MarketReport> {
    const res = await fetch(`${API_BASE_URL}/api/reports/${symbol}`, {
      cache: "no-store",
    });
    return handleResponse<MarketReport>(res);
  },

  getReportExportUrl(symbol = "BTCUSDT"): string {
    return `${API_BASE_URL}/api/reports/${symbol}/export`;
  },

  async sendChatMessage(
    message: string,
    conversationId = "default"
  ): Promise<ChatResponse> {
    const res = await fetch(`${API_BASE_URL}/api/chat`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        message,
        conversation_id: conversationId,
      }),
    });
    return handleResponse<ChatResponse>(res);
  },
};
