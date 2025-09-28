"""Common feed event types for streaming ingestion."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Mapping, Optional


class FeedEventType(str, Enum):
    TRADE = "trade"
    ORDER_BOOK = "order_book"
    TICKER = "ticker"
    MARK_PRICE = "mark_price"
    FUNDING = "funding"
    OPEN_INTEREST = "open_interest"
    LIQUIDATION = "liquidation"
    VOLUME_24H = "volume_24h"
    HEARTBEAT = "heartbeat"
    OTHER = "other"


@dataclass(slots=True)
class FeedEvent:
    """Normalized feed message emitted by exchange adapters."""

    event_type: FeedEventType
    topic: str
    symbol: Optional[str]
    payload: Mapping[str, Any]
    sequence: Optional[int]
    recv_ts: datetime
    raw: Any


__all__ = ["FeedEventType", "FeedEvent"]
