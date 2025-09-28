from datetime import datetime, timezone

from market_scanner.feeds.events import FeedEvent, FeedEventType
from market_scanner.storage.bars import Bar, build_trade_bars


def _make_event(symbol: str, price: float, amount: float, ts_ms: int) -> FeedEvent:
    payload = {"data": [{"price": price, "amount": amount, "ts": ts_ms}]}
    return FeedEvent(
        event_type=FeedEventType.TRADE,
        topic=f"market.{symbol}.trade.detail",
        symbol=symbol,
        payload=payload,
        sequence=None,
        recv_ts=datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc),
        raw=payload,
    )


def test_build_trade_bars_single_bucket():
    events = [
        _make_event("btc-usdt", 100.0, 1.0, 1_700_000_000_000),
        _make_event("btc-usdt", 101.0, 0.5, 1_700_000_000_500),
    ]
    bars = list(build_trade_bars(events, bucket_seconds=1))
    assert len(bars) == 1
    bar = bars[0]
    assert isinstance(bar, Bar)
    assert bar.open == 100.0
    assert bar.close == 101.0
    assert bar.high == 101.0
    assert bar.low == 100.0
    assert bar.volume_base == 1.5
    assert round(bar.volume_quote, 2) == round(100.0 * 1.0 + 101.0 * 0.5, 2)
    assert bar.trade_count == 2


def test_build_trade_bars_multiple_buckets():
    events = [
        _make_event("eth-usdt", 200.0, 1.0, 1_700_000_000_000),
        _make_event("eth-usdt", 201.0, 2.0, 1_700_000_000_000 + 1_000),
        _make_event("eth-usdt", 202.0, 1.5, 1_700_000_000_000 + 3_000),
    ]
    bars = list(build_trade_bars(events, bucket_seconds=2))
    assert len(bars) == 2
    first, second = bars
    assert first.ts < second.ts
    assert first.trade_count == 2
    assert second.trade_count == 1
