"""Application-wide async broadcast utilities for streaming ranking events."""
from __future__ import annotations

import asyncio
from datetime import datetime
from typing import AsyncIterator, Dict, List

from pydantic import BaseModel


class RankingSymbolFrame(BaseModel):
    """Serializable payload for a ranked symbol in the streaming feed."""

    symbol: str
    rank: int
    rank_delta: int
    score: float
    liquidity_edge: float
    momentum_edge: float
    volatility_edge: float
    microstructure_edge: float
    anomaly_residual: float
    spread_bps: float
    slip_bps: float
    volume_zscore: float
    order_flow_imbalance: float
    volatility_regime: float
    price_velocity: float
    anomaly_score: float
    depth_to_volume_ratio: float
    manipulation_score: float | None = None
    manipulation_flags: list[str] | None = None
    stale: bool = False
    latency_ms: float | None = None
    score_components: Dict[str, float] | None = None
    execution_metrics: Dict[str, float] | None = None
    manipulation_threshold_exceeded: bool = False


class RankingFrame(BaseModel):
    """Top-level ranking frame emitted to UI consumers."""

    ts: datetime
    profile: str
    market_gauge: float
    volatility_bucket: str
    top: int
    items: List[RankingSymbolFrame]


class _Broadcast:
    """Simple asyncio fan-out broadcast for structured payloads."""

    def __init__(self) -> None:
        self._subscribers: set[asyncio.Queue[RankingFrame]] = set()
        self._lock = asyncio.Lock()
        self._last_frame: RankingFrame | None = None

    async def publish(self, payload: RankingFrame) -> None:
        self._last_frame = payload
        if not self._subscribers:
            return
        for queue in list(self._subscribers):
            try:
                queue.put_nowait(payload)
            except asyncio.QueueFull:
                # Slow consumer; drop the oldest by emptying queue before re-adding
                _drain_queue(queue)
                queue.put_nowait(payload)

    async def subscribe(self) -> AsyncIterator[RankingFrame]:
        queue: asyncio.Queue[RankingFrame] = asyncio.Queue(maxsize=2)
        async with self._lock:
            self._subscribers.add(queue)
        try:
            # Immediately deliver the last frame so new clients have state
            if self._last_frame is not None:
                queue.put_nowait(self._last_frame)
            while True:
                payload = await queue.get()
                yield payload
        finally:
            async with self._lock:
                self._subscribers.discard(queue)


def _drain_queue(queue: asyncio.Queue[RankingFrame]) -> None:
    try:
        while True:
            queue.get_nowait()
    except asyncio.QueueEmpty:
        return


_ranking_broadcast: _Broadcast | None = None


def get_ranking_broadcast() -> _Broadcast:
    global _ranking_broadcast
    if _ranking_broadcast is None:
        _ranking_broadcast = _Broadcast()
    return _ranking_broadcast

