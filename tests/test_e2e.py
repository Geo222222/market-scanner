from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from market_scanner.core.metrics import SymbolSnapshot


@pytest.fixture
def client(monkeypatch):
    from market_scanner import app as app_module

    async def fake_loop(*_args, **_kwargs):  # pragma: no cover - test stub
        return None

    monkeypatch.setattr(app_module, "scanner_loop", fake_loop)

    sample_ts = datetime.now(timezone.utc)

    snapshots = [
        SymbolSnapshot(
            symbol="AAA/USDT:USDT",
            qvol_usdt=80_000_000,
            spread_bps=2.0,
            top5_depth_usdt=4_000_000,
            atr_pct=1.2,
            ret_1=0.6,
            ret_15=1.5,
            slip_bps=3.0,
            funding_8h_pct=0.02,
            open_interest=1_500_000,
            basis_bps=5.0,
            manip_score=5.0,
            manip_flags=["liquidity_wall"],
            ts=sample_ts,
            score=72.5,
        ),
        SymbolSnapshot(
            symbol="BBB/USDT:USDT",
            qvol_usdt=60_000_000,
            spread_bps=3.2,
            top5_depth_usdt=3_500_000,
            atr_pct=0.9,
            ret_1=0.3,
            ret_15=1.0,
            slip_bps=4.5,
            funding_8h_pct=-0.01,
            open_interest=1_200_000,
            basis_bps=-3.0,
            manip_score=20.0,
            manip_flags=["scam_wick"],
            ts=sample_ts,
            score=58.0,
        ),
    ]

    async def fake_compute_rankings(_params):
        return snapshots, sample_ts

    monkeypatch.setattr("market_scanner.routers.rankings.compute_rankings", fake_compute_rankings)
    monkeypatch.setattr("market_scanner.routers.opps.compute_rankings", fake_compute_rankings)

    return TestClient(app_module.app)


def test_health_endpoint(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_rankings_endpoint(client):
    resp = client.get("/rankings")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["items"]) == 2
    scores = [item["score"] for item in data["items"]]
    assert scores == sorted(scores, reverse=True)
    assert data["items"][0]["manip_flags"]


def test_opportunities_endpoint(client):
    resp = client.get("/opportunities")
    assert resp.status_code == 200
    data = resp.json()
    assert data["items"]
    assert all("confidence" in item for item in data["items"])
