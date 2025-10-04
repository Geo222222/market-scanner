"""Scoring logic for market snapshots with breakdown support."""
from __future__ import annotations

from copy import deepcopy
from math import log1p
from typing import Dict, Iterable, Tuple

from ..config import get_settings
from .metrics import SymbolSnapshot

REJECT_SCORE = -1_000_000.0
MANIP_PENALTY_WEIGHT = 0.4

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

_PROFILE_OVERRIDES: dict[str, dict[str, dict[str, float]]] = {}


def _scale_log(value: float, divisor: float) -> float:
    return log1p(max(0.0, value) / divisor)


def _resolve_weights(profile: str) -> dict[str, dict[str, float]]:
    base = deepcopy(WEIGHT_PRESETS.get(profile) or {})
    override = _PROFILE_OVERRIDES.get(profile)
    if not override:
        return base
    for section, section_weights in override.items():
        base.setdefault(section, {})
        base[section].update(section_weights)
    return base


def set_profile_override(profile: str, weights: dict[str, dict[str, float]]) -> None:
    """Override preset weights for hot-reloadable profiles."""

    _PROFILE_OVERRIDES[profile] = deepcopy(weights)


def score_with_breakdown(
    snapshot: SymbolSnapshot,
    profile: str = "scalp",
    include_carry: bool | None = None,
) -> Tuple[float, Dict[str, float]]:
    settings = get_settings()
    weights = _resolve_weights(profile)
    if not weights:
        raise ValueError(f"Unknown profile '{profile}'. Available: {', '.join(sorted(WEIGHT_PRESETS))}")

    if snapshot.qvol_usdt < settings.min_qvol_usdt or snapshot.spread_bps > settings.max_spread_bps:
        return REJECT_SCORE, {}

    liquidity_component = (
        weights.get("liq", {}).get("qvol", 0.0) * _scale_log(snapshot.qvol_usdt, 1_000_000.0)
        + weights.get("liq", {}).get("depth", 0.0) * _scale_log(snapshot.top5_depth_usdt, 100_000.0)
    )

    volatility_component = weights.get("vol", {}).get("atr", 0.0) * snapshot.atr_pct

    momentum_weights = weights.get("mom", {})
    volatility_regime = snapshot.volatility_regime
    momentum_scale = 0.7 if volatility_regime > 1.0 else 1.0
    momentum_component = momentum_scale * (
        momentum_weights.get("ret_15", 0.0) * snapshot.ret_15
        + momentum_weights.get("ret_1", 0.0) * snapshot.ret_1
    )

    cost_penalty = (
        weights.get("cost", {}).get("spread", 0.0) * snapshot.spread_bps
        + weights.get("cost", {}).get("slip", 0.0) * snapshot.slip_bps
    )

    carry_enabled = settings.include_carry if include_carry is None else include_carry
    carry_component = 0.0
    if carry_enabled:
        if snapshot.funding_8h_pct is not None:
            carry_component += weights.get("carry", {}).get("funding", 0.0) * (-snapshot.funding_8h_pct)
        if snapshot.basis_bps is not None:
            carry_component += weights.get("carry", {}).get("basis", 0.0) * (-snapshot.basis_bps / 100.0)

    structure_weights = weights.get("structure", {})
    structure_bonus = (
        structure_weights.get("volume_z", 0.0) * max(-2.5, min(6.0, snapshot.volume_zscore))
        + structure_weights.get("velocity", 0.0) * max(-5.0, min(5.0, snapshot.price_velocity))
    )
    structure_penalty = (
        structure_weights.get("ofi", 0.0) * abs(snapshot.order_flow_imbalance)
        + structure_weights.get("volatility", 0.0) * abs(snapshot.volatility_regime)
        + structure_weights.get("anomaly", 0.0) * (snapshot.anomaly_score / 10.0)
        + structure_weights.get("residual", 0.0) * max(0.0, snapshot.anomaly_residual)
    )

    edges_weights = weights.get("edges", {})
    edges_component = (
        edges_weights.get("liquidity", 0.0) * max(-3.0, min(3.0, snapshot.liquidity_edge))
        + edges_weights.get("momentum", 0.0) * max(-3.0, min(3.0, snapshot.momentum_edge))
        + edges_weights.get("volatility", 0.0) * max(-3.0, min(3.0, snapshot.volatility_edge))
        + edges_weights.get("micro", 0.0) * max(-3.0, min(3.0, snapshot.microstructure_edge))
    )

    total = (
        liquidity_component
        + volatility_component
        + momentum_component
        + carry_component
        + structure_bonus
        + edges_component
        - cost_penalty
        - structure_penalty
    )

    if snapshot.manip_score is not None:
        total -= snapshot.manip_score * MANIP_PENALTY_WEIGHT

    breakdown = {
        "liquidity": liquidity_component,
        "volatility": volatility_component,
        "momentum": momentum_component,
        "carry": carry_component,
        "structure_bonus": structure_bonus,
        "structure_penalty": structure_penalty,
        "edges": edges_component,
        "cost": cost_penalty,
        "manip_penalty": snapshot.manip_score * MANIP_PENALTY_WEIGHT if snapshot.manip_score is not None else 0.0,
        "momentum_scale": momentum_scale,
    }

    return round(total, 4), breakdown


def score(snapshot: SymbolSnapshot, profile: str = "scalp", include_carry: bool | None = None) -> float:
    value, _ = score_with_breakdown(snapshot, profile=profile, include_carry=include_carry)
    return value


def rank(
    snaps: Iterable[SymbolSnapshot],
    top: int,
    profile: str = "scalp",
    include_carry: bool | None = None,
) -> list[SymbolSnapshot]:
    scored: list[SymbolSnapshot] = []
    for snap in snaps:
        snap_score, _ = score_with_breakdown(snap, profile=profile, include_carry=include_carry)
        scored.append(snap.model_copy(update={"score": snap_score}))
    scored.sort(key=lambda s: s.score or REJECT_SCORE, reverse=True)
    return scored[: max(top, 0)]


__all__ = [
    "REJECT_SCORE",
    "score",
    "score_with_breakdown",
    "rank",
    "set_profile_override",
]


