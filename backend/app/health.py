"""Independent bounded probes; availability does not imply inference succeeded."""
import asyncio
import time
import boto3
import duckdb
import httpx
from botocore.config import Config
from backend.app.models import HealthResponse, HealthServices

async def check_health(settings):
    started = time.perf_counter()
    async def probe(url, headers=None):
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                response = await client.get(url, headers=headers)
                response.raise_for_status()
                return response.json()
        except Exception:
            return None

    def storage():
        try:
            client = boto3.client("s3", endpoint_url=settings.minio_endpoint,
                aws_access_key_id=settings.api_minio_user,
                aws_secret_access_key=settings.api_minio_password,
                config=Config(connect_timeout=2, read_timeout=2, retries={"max_attempts": 0}))
            client.list_objects_v2(Bucket=settings.minio_bucket, MaxKeys=1)
            return "connected"
        except Exception:
            return "disconnected"

    def database():
        try:
            with duckdb.connect(":memory:") as conn:
                conn.execute("SELECT 1").fetchone()
            return "operational"
        except Exception:
            return "unavailable"

    minio, duck, binance, ollama, groq = await asyncio.gather(
        asyncio.to_thread(storage), asyncio.to_thread(database),
        probe(settings.binance_api_base.rstrip("/") + "/api/v3/ping"),
        probe(settings.ollama_base_url.rstrip("/") + "/api/tags"),
        probe(settings.groq_base_url.rstrip("/") + "/models", {"Authorization": "Bearer " + settings.groq_api_key})
            if settings.groq_api_key else asyncio.sleep(0, result=None))
    names = {m.get("name") for m in (ollama or {}).get("models", [])}
    local = "available" if settings.ollama_model in names else "model_missing" if ollama is not None else "unavailable"
    cloud = "available" if any(m.get("id") == settings.groq_model for m in (groq or {}).get("data", [])) else "unavailable" if settings.groq_api_key else "not_configured"
    return HealthResponse(status="healthy" if minio == "connected" and duck == "operational" and binance is not None and (local == "available" or cloud == "available") else "degraded",
        application="crypto-ai-agent-backend", version="1.0.0", environment=settings.environment,
        services=HealthServices(api="operational", minio=minio, duckdb=duck,
            binance="available" if binance is not None else "unavailable", ollama=local, groq=cloud,
            ollama_model=settings.ollama_model, groq_model=settings.groq_model),
        latency_ms=round((time.perf_counter()-started)*1000, 2),
        timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
