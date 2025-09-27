"""Scoring logic for market snapshots."""
from __future__ import annotations

from math import log1p
from typing import Iterable

from ..config import get_settings
from .metrics import SymbolSnapshot

REJECT_SCORE = -1_000_000.0

WEIGHT_PRESETS: dict[str, dict[str, dict[str, float]]] = {
    "scalp": {
        "liq": {"qvol": 4.0, "depth": 3.5},
        "vol": {"atr": 1.2},
        "mom": {"ret_15": 1.5, "ret_1": 1.0},
        "cost": {"spread": 3.0, "slip": 2.5},
        "carry": {"funding": 0.5, "basis": 0.3},
    },
    "swing": {
        "liq": {"qvol": 2.5, "depth": 2.5},
        "vol": {"atr": 1.8},
        "mom": {"ret_15": 2.2, "ret_1": 0.8},
        "cost": {"spread": 2.0, "slip": 1.5},
        "carry": {"funding": 0.8, "basis": 0.6},
    },
    "news": {
        "liq": {"qvol": 3.0, "depth": 2.0},
        "vol": {"atr": 2.2},
        "mom": {"ret_15": 2.8, "ret_1": 1.5},
        "cost": {"spread": 2.2, "slip": 1.8},
        "carry": {"funding": 0.3, "basis": 0.2},
    },
}


def _scale_log(value: float, divisor: float) -> float:
    return log1p(max(0.0, value) / divisor)


def score(snapshot: SymbolSnapshot, profile: str = "scalp") -> float:
    """Return a weighted score for a snapshot under the requested profile."""

    settings = get_settings()
    weights = WEIGHT_PRESETS.get(profile)
    if weights is None:
        raise ValueError(f"Unknown profile '{profile}'. Available: {', '.join(sorted(WEIGHT_PRESETS))}")

    if snapshot.qvol_usdt < settings.min_qvol_usdt:
        return REJECT_SCORE
    if snapshot.spread_bps > settings.max_spread_bps:
        return REJECT_SCORE

    liq = (
        weights["liq"]["qvol"] * _scale_log(snapshot.qvol_usdt, 1_000_000.0)
        + weights["liq"]["depth"] * _scale_log(snapshot.top5_depth_usdt, 100_000.0)
    )

    vol_component = weights["vol"]["atr"] * snapshot.atr_pct
    mom_component = (
        weights["mom"]["ret_15"] * snapshot.ret_15
        + weights["mom"]["ret_1"] * snapshot.ret_1
    )

    cost_penalty = (
        weights["cost"]["spread"] * snapshot.spread_bps
        + weights["cost"]["slip"] * snapshot.slip_bps
    )

    carry_component = 0.0
    funding = snapshot.funding_8h_pct
    if funding is not None:
        carry_component += weights["carry"]["funding"] * (-funding)
    basis = snapshot.basis_bps
    if basis is not None:
        carry_component += weights["carry"]["basis"] * (-basis / 100.0)

    raw_score = liq + vol_component + mom_component + carry_component - cost_penalty
    return round(raw_score, 4)


def rank(snaps: Iterable[SymbolSnapshot], top: int, profile: str = "scalp") -> list[SymbolSnapshot]:
    """Sort snapshots by score, return the Top-N with the computed values attached."""

    scored: list[SymbolSnapshot] = []
    for snap in snaps:
        snap_score = score(snap, profile=profile)
        scored.append(snap.model_copy(update={"score": snap_score}))
    scored.sort(key=lambda s: s.score or REJECT_SCORE, reverse=True)
    return scored[: max(top, 0)]
