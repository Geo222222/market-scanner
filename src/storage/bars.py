"""Utilities for building time-bucketed bars from raw feed events."""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable, Iterator, Mapping

from ..feeds.events import FeedEvent, FeedEventType


@dataclass(slots=True)
class Bar:
    symbol: str
    ts: datetime
    open: float
    high: float
    low: float
    close: float
    volume_base: float
    volume_quote: float
    trade_count: int


def _floor_to_bucket(ts: datetime, bucket_seconds: int) -> datetime:
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    epoch = int(ts.timestamp())
    bucket = epoch - (epoch % bucket_seconds)
    return datetime.fromtimestamp(bucket, tz=timezone.utc)


def _extract_trade_fields(payload: Mapping[str, object]) -> tuple[float, float]:
    price = payload.get("price") or payload.get("tradePrice") or payload.get("p")
    amount = payload.get("amount") or payload.get("tradeVolume") or payload.get("q")
    return float(price), float(amount)


def _quote_volume(price: float, amount: float) -> float:
    return price * amount


def build_trade_bars(events: Iterable[FeedEvent], bucket_seconds: int) -> Iterator[Bar]:
    buckets: dict[tuple[str, datetime], list[Mapping[str, object]]] = defaultdict(list)
    for event in events:
        if event.event_type != FeedEventType.TRADE or not event.symbol:
            continue
        trades = event.payload.get("data") if isinstance(event.payload, Mapping) else None
        if trades is None:
            trades = [event.payload]
        for trade in trades:  # type: ignore[assignment]
            if not isinstance(trade, Mapping):
                continue
            try:
                price, amount = _extract_trade_fields(trade)
            except (TypeError, ValueError):
                continue
            ts_raw = trade.get("ts") or trade.get("created_at") or event.recv_ts.timestamp() * 1000
            ts_dt = datetime.fromtimestamp(int(ts_raw) / 1000, tz=timezone.utc)
            bucket = _floor_to_bucket(ts_dt, bucket_seconds)
            key = (event.symbol, bucket)
            buckets[key].append({"price": price, "amount": amount, "ts": ts_dt})
    for (symbol, bucket_ts), trades in sorted(buckets.items(), key=lambda item: item[0][1]):
        prices = [t["price"] for t in trades]
        amounts = [t["amount"] for t in trades]
        if not prices:
            continue
        open_price = prices[0]
        close_price = prices[-1]
        high_price = max(prices)
        low_price = min(prices)
        base_vol = sum(amounts)
        quote_vol = sum(_quote_volume(p, a) for p, a in zip(prices, amounts))
        yield Bar(
            symbol=symbol,
            ts=bucket_ts,
            open=open_price,
            high=high_price,
            low=low_price,
            close=close_price,
            volume_base=base_vol,
            volume_quote=quote_vol,
            trade_count=len(prices),
        )
