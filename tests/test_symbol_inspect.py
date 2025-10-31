from datetime import datetime, timezone

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from market_scanner.core.metrics import SymbolSnapshot
from market_scanner.jobs.loop import SnapshotBundle
from market_scanner.routers import symbols as symbols_router


@pytest.mark.asyncio
async def test_symbol_inspect(monkeypatch):
    snapshot = SymbolSnapshot(
        symbol='BTC/USDT:USDT',
        exchange='htx',  # Required field
        qvol_usdt=80_000_000,
        spread_bps=4.0,
        top5_depth_usdt=1_200_000,
        atr_pct=1.0,
        ret_1=0.5,
        ret_15=1.5,
        slip_bps=2.4,
        funding_8h_pct=0.01,
        open_interest=10_000,
        basis_bps=5.0,
        volume_zscore=2.0,
        order_flow_imbalance=0.2,
        volatility_regime=0.4,
        price_velocity=0.3,
        anomaly_score=10.0,
        depth_to_volume_ratio=0.8,
        manip_score=5.0,
        manip_flags=['wash_trade_volume'],
        ts=datetime.now(timezone.utc),
        z_15s=0.1,
        z_1m=0.2,
        z_5m=0.3,
        vwap_distance=0.5,
        rsi14=55.0,
    )
    bundle = SnapshotBundle(
        snapshot=snapshot,
        close=30000.0,
        manip_features={},
        ticker={'last': 30000},
        orderbook={'bids': [[30000, 1]], 'asks': [[30010, 1]]},
        momentum={'z_1m': 0.2},
        micro_features={'depth_decay': 0.1},
        execution={'queue_position': 0.5},
        trades=[],
        fetch_latency_ms=12.0,
    )

    def fake_latest(symbol):
        return bundle

    async def fake_collect(symbol):
        return bundle

    async def fake_bars(symbol, timeframe='1m', limit=60):
        return [{'ts': '2025-01-01T00:00:00Z', 'close': 30000.0}]

    monkeypatch.setattr(symbols_router, 'get_latest_bundle', fake_latest)
    monkeypatch.setattr(symbols_router, 'collect_snapshot', fake_collect)
    monkeypatch.setattr(symbols_router, 'fetch_recent_bars', fake_bars)

    app = FastAPI()
    app.include_router(symbols_router.router, prefix='/symbol')

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url='http://test') as client:
        response = await client.get('/symbol/BTC/inspect')
    assert response.status_code == 200
    data = response.json()
    assert data['symbol'] == 'BTC/USDT:USDT'
    assert data['orderbook']['bids']
