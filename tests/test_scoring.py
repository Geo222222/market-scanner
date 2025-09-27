from datetime import datetime, timezone

import pytest

from market_scanner.core.metrics import SymbolSnapshot
from market_scanner.core.scoring import REJECT_SCORE, rank, score


@pytest.fixture
def base_ts() -> datetime:
    return datetime.now(timezone.utc)


def make_snapshot(
    symbol: str,
    qvol: float,
    spread: float,
    depth: float,
    atr: float,
    ret1: float,
    ret15: float,
    slip: float,
    funding: float | None,
    ts: datetime,
) -> SymbolSnapshot:
    return SymbolSnapshot(
        symbol=symbol,
        qvol_usdt=qvol,
        spread_bps=spread,
        top5_depth_usdt=depth,
        atr_pct=atr,
        ret_1=ret1,
        ret_15=ret15,
        slip_bps=slip,
        funding_8h_pct=funding,
        open_interest=10_000,
        basis_bps=0.0,
        ts=ts,
    )


def test_score_prefers_liquidity_and_low_costs(base_ts: datetime):
    rich = make_snapshot("RICH", 200_000_000, 2.0, 5_000_000, 1.5, 0.5, 1.2, 3.0, 0.0, base_ts)
    poor = make_snapshot("POOR", 60_000_000, 8.0, 500_000, 1.0, 0.2, 0.5, 8.0, 0.0, base_ts)
    assert score(rich, profile="scalp") > score(poor, profile="scalp")


def test_score_rejects_under_qvol(base_ts: datetime):
    thin = make_snapshot("THIN", 1_000_000, 2.0, 500_000, 1.0, 0.5, 0.5, 2.0, 0.0, base_ts)
    assert score(thin, profile="scalp") == REJECT_SCORE


def test_rank_stamps_scores(base_ts: datetime):
    snaps = [
        make_snapshot("A", 200_000_000, 2.0, 4_000_000, 1.0, 0.8, 1.2, 3.0, 0.0, base_ts),
        make_snapshot("B", 120_000_000, 3.0, 3_000_000, 0.8, 0.5, 0.9, 4.0, 0.0, base_ts),
    ]
    ranked = rank(snaps, top=2, profile="scalp")
    assert len(ranked) == 2
    assert ranked[0].score is not None
    assert ranked[0].score >= ranked[1].score
