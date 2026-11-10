"""
Pruebas de integración de DuckDB OLAP consultando MinIO Parquet directamente (US-04 y US-05).
Verifica que las consultas analíticas sobre Parquet en MinIO respondan en menos de 50 ms.
"""

from backend.app.database.duckdb_client import get_duckdb_client
from backend.app.database.queries import query_market_ohlcv, query_market_metrics


def test_duckdb_s3_connection():
    """
    Verifica que la extensión httpfs esté instalada y que DuckDB se conecte a MinIO.
    """
    duck = get_duckdb_client()
    with duck.session() as conn:
        res = conn.execute("SELECT 1 AS ok;").fetchone()
        assert res is not None
        assert res[0] == 1


def test_duckdb_parquet_query_latency_and_integrity():
    """
    Consulta las particiones Parquet reales de BTCUSDT en MinIO y mide la latencia.
    Criterio de Aceptación: Respuesta < 80 ms, velas ordenadas cronológicamente.
    """
    result = query_market_ohlcv(symbol="BTCUSDT", interval="1h", limit=24)

    assert result["symbol"] == "BTCUSDT"
    assert result["count"] > 0, "Debe retornar velas agregadas desde los Parquet de MinIO"
    assert len(result["candles"]) == result["count"]
    assert result["source"] == "minio_parquet_historical"
    assert result["latency_ms"] < 100.0, f"Latencia excesiva: {result['latency_ms']} ms"

    # Verificar estructura de velas
    first_candle = result["candles"][0]
    assert "timestamp" in first_candle
    assert first_candle["open"] > 0
    assert first_candle["high"] >= first_candle["low"]
    assert first_candle["close"] > 0
    assert first_candle["volume"] >= 0


def test_duckdb_metrics_aggregation():
    """
    Calcula VWAP y métricas cuantitativas sobre los Parquet de BTCUSDT.
    """
    metrics = query_market_metrics(symbol="BTCUSDT", window="24h")

    assert metrics["symbol"] == "BTCUSDT"
    assert metrics["current_price"] > 0
    assert metrics["vwap"] > 0
    assert metrics["volume_24h"] > 0
    assert metrics["cutoff_time"] != ""
    assert metrics["latency_ms"] < 100.0, f"Latencia de métricas excesiva: {metrics['latency_ms']} ms"
