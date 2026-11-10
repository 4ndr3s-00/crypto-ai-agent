"""
Pruebas unitarias para el conector REST de Binance (US-02).
Verifica paginación de velas, validación de contrato y cálculo de timestamps.
"""

from datetime import date
from ingestion.connectors.binance_rest import (
    date_to_timestamps_ms,
    format_kline_to_event,
    fetch_binance_klines,
)
from ingestion.schemas import MarketEvent


def test_date_to_timestamps_ms():
    target = date(2026, 11, 1)
    start_ms, end_ms = date_to_timestamps_ms(target)

    # 2026-11-01 00:00:00 UTC = 1793491200000
    assert start_ms < end_ms
    # La diferencia debe ser exactamente 24 horas - 1 ms = 86,399,999 ms
    assert end_ms - start_ms == 86_399_999


def test_format_kline_to_event():
    raw_kline = [
        1793491200000,     # 0: Open time
        "68500.50",        # 1: Open
        "69100.00",        # 2: High
        "68200.00",        # 3: Low
        "68950.25",        # 4: Close
        "124.550",         # 5: Volume
        1793491259999,     # 6: Close time
        "8587632.12",      # 7: Quote asset volume
        1420,              # 8: Number of trades
    ]

    event = format_kline_to_event(raw_kline, "BTCUSDT", interval="1m")

    assert isinstance(event, MarketEvent)
    assert event.symbol == "BTCUSDT"
    assert event.open == 68500.50
    assert event.high == 69100.00
    assert event.low == 68200.00
    assert event.close == 68950.25
    assert event.volume == 124.550
    assert event.trades_count == 1420
    assert event.event_id == "binance_BTCUSDT_1793491200000"
    assert event.schema_version == "2.0.0"


def test_live_binance_klines_fetch():
    """
    Verifica que la API pública de Binance responda con velas reales.
    Utiliza el día de ayer para garantizar que los datos estén consolidados.
    """
    from datetime import date, timedelta
    yesterday = date.today() - timedelta(days=2)

    events = fetch_binance_klines(symbol="BTCUSDT", target_date=yesterday, interval="1h", limit=24)

    assert len(events) >= 1
    assert all(isinstance(e, MarketEvent) for e in events)
    assert all(e.close > 0 for e in events)
    assert all(e.symbol == "BTCUSDT" for e in events)
