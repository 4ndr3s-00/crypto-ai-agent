"""
Configuración centralizada con Pydantic Settings v2 (US-06).

Carga variables de entorno para MinIO S3, Binance API, Groq Cloud,
Ollama local y parámetros del servidor FastAPI.
"""

from __future__ import annotations

import os
from functools import lru_cache
from typing import Tuple

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

DISCLAIMER = (
    "Información exclusivamente referencial con fines analíticos. "
    "No constituye asesoramiento financiero ni recomendación de inversión."
)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Entorno del servidor
    environment: str = Field(default="production", alias="ENVIRONMENT")
    api_host: str = Field(default="0.0.0.0", alias="API_HOST")
    api_port: int = Field(default=8001, alias="API_PORT")
    cors_origins: str = Field(
        default="http://localhost:3000,http://127.0.0.1:3000",
        alias="CORS_ORIGINS",
    )

    # MinIO / Lakehouse S3
    minio_endpoint: str = Field(default="http://localhost:9000", alias="MINIO_ENDPOINT")
    minio_bucket: str = Field(default="market-lake", alias="MINIO_BUCKET_LAKE")
    api_minio_user: str = Field(default="api_service", alias="API_MINIO_USER")
    api_minio_password: str = Field(default="api_secure_pass123", alias="API_MINIO_PASSWORD")

    # Ingesta y Exchange
    binance_api_base: str = Field(default="https://data-api.binance.vision", alias="BINANCE_API_BASE")
    default_symbols: str = Field(default="BTCUSDT,ETHUSDT,SOLUSDT,BNBUSDT", alias="DEFAULT_SYMBOLS")
    market_cache_ttl_seconds: float = Field(default=5.0, alias="MARKET_CACHE_TTL_SECONDS")
    market_request_timeout_seconds: float = Field(default=10.0, alias="MARKET_REQUEST_TIMEOUT_SECONDS")

    # Groq Cloud
    groq_api_key: str = Field(default="", alias="GROQ_API_KEY")
    groq_base_url: str = Field(default="https://api.groq.com/openai/v1", alias="GROQ_BASE_URL")
    groq_model: str = Field(default="llama-3.3-70b-versatile", alias="GROQ_MODEL")
    groq_timeout_seconds: float = Field(default=15.0, alias="GROQ_TIMEOUT_SECONDS")

    # Ollama Local Fallback
    ollama_base_url: str = Field(default="http://localhost:11434", alias="OLLAMA_BASE_URL")
    ollama_model: str = Field(default="qwen2.5-coder:7b", alias="OLLAMA_MODEL")
    ollama_embedding_model: str = Field(default="bge-m3", alias="OLLAMA_EMBEDDING_MODEL")

    # Router Semántico y Anti-Alucinación
    semantic_router_enabled: bool = Field(default=True, alias="SEMANTIC_ROUTER_ENABLED")
    semantic_router_threshold: float = Field(default=0.68, alias="SEMANTIC_ROUTER_THRESHOLD")

    @property
    def cors_origins_list(self) -> Tuple[str, ...]:
        return tuple(origin.strip() for origin in self.cors_origins.split(",") if origin.strip())

    @property
    def symbols_list(self) -> Tuple[str, ...]:
        return tuple(sym.strip().upper() for sym in self.default_symbols.split(",") if sym.strip())


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
