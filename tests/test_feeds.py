import asyncio
import json

import pytest

from market_scanner.feeds.htx import HTXFeed


class DummyWS:
    def __init__(self):
        self.sent = []

    async def send(self, payload: str) -> None:
        self.sent.append(json.loads(payload))

    async def ping(self) -> None:  # pragma: no cover - used in production
        self.sent.append({"ping": True})


@pytest.mark.asyncio
async def test_handle_message_enqueues_event():
    feed = HTXFeed(["BTC-USDT"])
    ws = DummyWS()
    message = {
        "topic": "market.btc-usdt.trade.detail",
        "tick": {"seqNum": 1, "data": [{"price": "100", "amount": "1"}]},
    }
    await feed._handle_message(ws, json.dumps(message))
    event = await asyncio.wait_for(feed._queue.get(), timeout=0.1)
    assert event.topic == "market.btc-usdt.trade.detail"
    assert event.sequence == 1
    assert event.event_type.value == "trade"


@pytest.mark.asyncio
async def test_sequence_gap_triggers_resubscribe():
    feed = HTXFeed(["BTC-USDT"])
    ws = DummyWS()
    first = {
        "topic": "market.btc-usdt.trade.detail",
        "tick": {"seqNum": 10, "data": []},
    }
    second = {
        "topic": "market.btc-usdt.trade.detail",
        "tick": {"seqNum": 12, "data": []},
    }
    await feed._handle_message(ws, json.dumps(first))
    await feed._handle_message(ws, json.dumps(second))
    assert any(payload.get("sub") == "market.btc-usdt.trade.detail" for payload in ws.sent)


@pytest.mark.asyncio
async def test_ping_message_replies_with_pong():
    feed = HTXFeed(["BTC-USDT"])
    ws = DummyWS()
    await feed._handle_message(ws, json.dumps({"ping": 12345}))
    assert ws.sent[-1] == {"pong": 12345}
