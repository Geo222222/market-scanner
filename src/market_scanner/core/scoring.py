"""Scoring logic for market snapshots."""
from __future__ import annotations

from math import log1p
from typing import Iterable

from ..config import get_settings
from .metrics import SymbolSnapshot

REJECT_SCORE = -1_000_000.0
# Manipulation penalties scale the final score so that high-risk symbols are deprioritized.
MANIP_PENALTY_WEIGHT = 0.4

# Weight presets are tuned for different trading styles. Each bucket maps to component weights
# (liquidity, volatility, momentum, execution cost, carry). The values were chosen so that
# liquidity and costs dominate the stack for scalp/news profiles while swing trades reward
# sustained momentum and carry edges slightly more. See docs/scoring.md for rationale.
WEIGHT_PRESETS: dict[str, dict[str, dict[str, float]]] = {
    "scalp": {
        "liq": {"qvol": 4.0, "depth": 3.5},
        "vol": {"atr": 1.2},
        "mom": {"ret_15": 1.5, "ret_1": 1.0},
        "cost": {"spread": 3.0, "slip": 2.5},
        "carry": {"funding": 0.5, "basis": 0.3},
        "structure": {"volume_z": 1.2, "ofi": 3.5, "volatility": 1.4, "velocity": 0.8, "anomaly": 0.7, "residual": 1.2},
        "edges": {"liquidity": 1.6, "momentum": 1.2, "volatility": 0.9, "micro": 1.5},
    },
    "swing": {
        "liq": {"qvol": 2.5, "depth": 2.5},
        "vol": {"atr": 1.8},
        "mom": {"ret_15": 2.2, "ret_1": 0.8},
        "cost": {"spread": 2.0, "slip": 1.5},
        "carry": {"funding": 0.8, "basis": 0.6},
        "structure": {"volume_z": 1.0, "ofi": 2.5, "volatility": 1.6, "velocity": 1.0, "anomaly": 0.6, "residual": 0.9},
        "edges": {"liquidity": 1.3, "momentum": 1.6, "volatility": 1.1, "micro": 1.1},
    },
    "news": {
        "liq": {"qvol": 3.0, "depth": 2.0},
        "vol": {"atr": 2.2},
        "mom": {"ret_15": 2.8, "ret_1": 1.5},
        "cost": {"spread": 2.2, "slip": 1.8},
        "carry": {"funding": 0.3, "basis": 0.2},
        "structure": {"volume_z": 1.5, "ofi": 2.8, "volatility": 1.2, "velocity": 1.4, "anomaly": 0.8, "residual": 1.0},
        "edges": {"liquidity": 1.4, "momentum": 1.8, "volatility": 1.2, "micro": 1.3},
    },
}


def _scale_log(value: float, divisor: float) -> float:
    return log1p(max(0.0, value) / divisor)


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def score(snapshot: SymbolSnapshot, profile: str = "scalp", include_carry: bool | None = None) -> float:
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

    carry_enabled = settings.include_carry if include_carry is None else include_carry
    carry_component = 0.0
    if carry_enabled:
        funding = snapshot.funding_8h_pct
        if funding is not None:
            carry_component += weights["carry"]["funding"] * (-funding)
        basis = snapshot.basis_bps
        if basis is not None:
            carry_component += weights["carry"]["basis"] * (-basis / 100.0)

    structure_weights = weights.get("structure")
    structure_bonus = 0.0
    structure_penalty = 0.0
    if structure_weights:
        volume_component = structure_weights.get("volume_z", 0.0) * max(-2.5, min(6.0, snapshot.volume_zscore))
        velocity_component = structure_weights.get("velocity", 0.0) * max(-5.0, min(5.0, snapshot.price_velocity))
        ofi_penalty = structure_weights.get("ofi", 0.0) * abs(snapshot.order_flow_imbalance)
        volatility_penalty = structure_weights.get("volatility", 0.0) * abs(snapshot.volatility_regime)
        anomaly_penalty = structure_weights.get("anomaly", 0.0) * (snapshot.anomaly_score / 10.0)
        residual_penalty = structure_weights.get("residual", 0.0) * max(0.0, snapshot.anomaly_residual)
        structure_bonus = volume_component + velocity_component
        structure_penalty = ofi_penalty + volatility_penalty + anomaly_penalty + residual_penalty

    edges_component = 0.0
    edges_weights = weights.get("edges")
    if edges_weights:
        edges_component = (
            edges_weights.get("liquidity", 0.0) * _clamp(snapshot.liquidity_edge, -3.0, 3.0)
            + edges_weights.get("momentum", 0.0) * _clamp(snapshot.momentum_edge, -3.0, 3.0)
            + edges_weights.get("volatility", 0.0) * _clamp(snapshot.volatility_edge, -3.0, 3.0)
            + edges_weights.get("micro", 0.0) * _clamp(snapshot.microstructure_edge, -3.0, 3.0)
        )

    raw_score = liq + vol_component + mom_component + carry_component + structure_bonus + edges_component - cost_penalty - structure_penalty

    if snapshot.manip_score is not None:
        raw_score -= snapshot.manip_score * MANIP_PENALTY_WEIGHT

    return round(raw_score, 4)


def rank(
    snaps: Iterable[SymbolSnapshot],
    top: int,
    profile: str = "scalp",
    include_carry: bool | None = None,
) -> list[SymbolSnapshot]:
    """Sort snapshots by score, return the Top-N with the computed values attached."""

    scored: list[SymbolSnapshot] = []
    for snap in snaps:
        snap_score = score(snap, profile=profile, include_carry=include_carry)
        scored.append(snap.model_copy(update={"score": snap_score}))
    scored.sort(key=lambda s: s.score or REJECT_SCORE, reverse=True)
    return scored[: max(top, 0)]
