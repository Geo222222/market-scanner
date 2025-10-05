"""HTX USDT-M WebSocket feed client."""
from __future__ import annotations

import asyncio
import gzip
import json
import logging
import time
from datetime import datetime, timezone
from typing import Any, AsyncContextManager, AsyncIterable, Awaitable, Callable, Dict, Iterable, Mapping, Optional

from websockets.client import WebSocketClientProtocol
from websockets.exceptions import ConnectionClosed

from ..config import get_settings
from .events import FeedEvent, FeedEventType

LOGGER = logging.getLogger(__name__)

WS_URL = "wss://api.hbdm.com/linear-swap-ws"

TOPIC_TEMPLATES = {
    FeedEventType.TRADE: "market.{symbol}.trade.detail",
    FeedEventType.ORDER_BOOK: "market.{symbol}.depth.size_20.high_freq",
    FeedEventType.TICKER: "market.{symbol}.detail",
    FeedEventType.MARK_PRICE: "market.{symbol}.mark_price_kline.1min",
    FeedEventType.FUNDING: "public.{symbol}.funding_rate",
    FeedEventType.OPEN_INTEREST: "public.{symbol}.open_interest",
    FeedEventType.LIQUIDATION: "public.{symbol}.liquidation_orders",
}

OPTIONAL_TOPICS = {
    FeedEventType.VOLUME_24H: "market.{symbol}.detail",
}


class HTXFeed:
    """Manage HTX WebSocket subscriptions with reconnection and gap detection."""

    def __init__(
        self,
        symbols: Iterable[str],
        *,
        websocket_factory: Optional[Callable[[str], AsyncContextManager[WebSocketClientProtocol]]] = None,
        loop: Optional[asyncio.AbstractEventLoop] = None,
    ) -> None:
        self.settings = get_settings()
        self.symbols = sorted({self._normalize_symbol(sym) for sym in symbols})
        self._websocket_factory = websocket_factory or self._default_factory
        self._loop = loop or asyncio.get_event_loop()
        self._queue: asyncio.Queue[FeedEvent] = asyncio.Queue(maxsize=10_000)
        self._stop_event = asyncio.Event()
        self._task: Optional[asyncio.Task[None]] = None
        self._last_seq: Dict[str, int] = {}
        self._backoff = 1.0

    @staticmethod
    def _normalize_symbol(symbol: str) -> str:
        return symbol.replace("/", "-").replace(":", "-").lower()

    async def start(self) -> None:
        if self._task and not self._task.done():
            return
        self._stop_event.clear()
        self._task = self._loop.create_task(self._run_forever())

    async def stop(self) -> None:
        self._stop_event.set()
        if self._task:
            await self._task

    async def events(self) -> AsyncIterable[FeedEvent]:
        while True:
            event = await self._queue.get()
            yield event

    async def _run_forever(self) -> None:
        while not self._stop_event.is_set():
            try:
                await self._connect_and_listen()
                self._backoff = 1.0
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # pragma: no cover - relies on network
                LOGGER.warning("HTX feed error: %s", exc)
                await asyncio.sleep(min(self._backoff, 30.0))
                self._backoff = min(self._backoff * 1.5, 30.0)

    async def _connect_and_listen(self) -> None:
        async with self._websocket_factory(WS_URL) as ws:
            await self._subscribe_all(ws)
            while not self._stop_event.is_set():
                try:
                    raw = await asyncio.wait_for(ws.recv(), timeout=30.0)
                except asyncio.TimeoutError:
                    await ws.ping()
                    continue
                await self._handle_message(ws, raw)

    def _default_factory(self, url: str) -> AsyncContextManager[WebSocketClientProtocol]:  # pragma: no cover - network path
        import websockets

        return websockets.connect(url, max_size=None, ping_interval=None)

    async def _subscribe_all(self, ws: WebSocketClientProtocol) -> None:
        topics: list[str] = []
        for symbol in self.symbols:
            for topic_tpl in TOPIC_TEMPLATES.values():
                topics.append(topic_tpl.format(symbol=symbol))
        payload = {
            "sub": topics,
            "id": f"scanner-{int(time.time())}",
        }
        await ws.send(json.dumps(payload))

    async def _handle_message(self, ws: WebSocketClientProtocol, raw: Any) -> None:
        message = self._decode(raw)
        if message is None:
            return
        if "ping" in message:
            await ws.send(json.dumps({"pong": message["ping"]}))
            return
        if message.get("op") == "notify" and message.get("topic") == "public.status":
            return
        topic = message.get("topic")
        if not topic:
            return
        event_type = self._topic_event_type(topic)
        tick = message.get("tick") or message.get("data") or {}
        sequence = tick.get("seqNum") or tick.get("seqnum") or message.get("seq")
        if sequence is not None:
            await self._check_sequence(topic, int(sequence), ws)
        event = FeedEvent(
            event_type=event_type,
            topic=topic,
            symbol=self._topic_symbol(topic),
            payload=tick if isinstance(tick, Mapping) else {"data": tick},
            sequence=int(sequence) if sequence is not None else None,
            recv_ts=datetime.now(timezone.utc),
            raw=message,
        )
        await self._queue.put(event)

    def _decode(self, raw: Any) -> Optional[Mapping[str, Any]]:
        if raw is None:
            return None
        if isinstance(raw, bytes):
            try:
                raw = gzip.decompress(raw).decode("utf-8")
            except OSError:
                raw = raw.decode("utf-8")
        if isinstance(raw, str):
            try:
                return json.loads(raw)
            except json.JSONDecodeError:
                LOGGER.debug("Unable to parse message: %s", raw)
                return None
        if isinstance(raw, Mapping):
            return raw
        return None

    def _topic_event_type(self, topic: str) -> FeedEventType:
        for etype, tpl in TOPIC_TEMPLATES.items():
            if tpl.split("{symbol}")[0] in topic:
                return etype
        return FeedEventType.OTHER

    def _topic_symbol(self, topic: str) -> Optional[str]:
        try:
            return topic.split(".")[1]
        except IndexError:
            return None

    async def _check_sequence(self, topic: str, sequence: int, ws: WebSocketClientProtocol) -> None:
        prev = self._last_seq.get(topic)
        self._last_seq[topic] = sequence
        if prev is None or sequence == prev + 1:
            return
        if sequence <= prev:
            return
        LOGGER.warning("Sequence gap detected on %s: prev=%s current=%s", topic, prev, sequence)
        await self._resubscribe(ws, topic)

    async def _resubscribe(self, ws: WebSocketClientProtocol, topic: str) -> None:
        payload = {"sub": topic, "id": f"resub-{int(time.time()*1000)}"}
        await ws.send(json.dumps(payload))
