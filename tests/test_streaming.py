import anyio
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from market_scanner.engine.streaming import RankingFrame, RankingSymbolFrame, get_ranking_broadcast
from market_scanner.routers.stream import router as stream_router


@pytest.mark.asyncio
async def test_broadcast_delivers_last_frame():
    broadcast = get_ranking_broadcast()
    frame = RankingFrame(
        ts='2025-01-01T00:00:00Z',
        profile='scalp',
        market_gauge=1.2,
        volatility_bucket='low',
        top=1,
        items=[
            RankingSymbolFrame(
                symbol='BTC/USDT:USDT',
                rank=1,
                rank_delta=0,
                score=12.34,
                liquidity_edge=1.0,
                momentum_edge=0.5,
                volatility_edge=0.1,
                microstructure_edge=0.2,
                anomaly_residual=0.0,
                spread_bps=3.4,
                slip_bps=2.1,
                volume_zscore=1.2,
                order_flow_imbalance=0.1,
                volatility_regime=0.2,
                price_velocity=0.3,
                anomaly_score=10.0,
                depth_to_volume_ratio=0.5,
            )
        ],
    )
    await broadcast.publish(frame)
    agen = broadcast.subscribe()
    event = await agen.__anext__()
    assert event.profile == 'scalp'
    await agen.aclose()


def test_websocket_stream_message(monkeypatch):
    app = FastAPI()
    app.include_router(stream_router, prefix="/stream")
    client = TestClient(app)
    broadcast = get_ranking_broadcast()

    with client.websocket_connect("/stream/rankings") as websocket:
        frame = RankingFrame(
            ts='2025-01-01T00:00:00Z',
            profile='scalp',
            market_gauge=1.0,
            volatility_bucket='low',
            top=0,
            items=[],
        )
        anyio.run(broadcast.publish, frame)
        message = websocket.receive_json()
        assert message['profile'] == 'scalp'
