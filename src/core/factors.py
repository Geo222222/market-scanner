"""Cross-sectional factor enrichment for symbol snapshots."""
from __future__ import annotations

from math import log1p
from statistics import StatisticsError, mean, pstdev
from typing import Iterable, Sequence

from .metrics import SymbolSnapshot


def _zscore(values: Sequence[float]) -> list[float]:
    """Return z-scores with graceful fallback for flat distributions."""

    if len(values) < 2:
        return [0.0 for _ in values]
    try:
        mu = mean(values)
    except StatisticsError:
        mu = 0.0
    try:
        sigma = pstdev(values)
    except StatisticsError:
        sigma = 0.0
    if sigma <= 1e-9:
        return [0.0 for _ in values]
    return [(value - mu) / sigma for value in values]


def _liquidity_inputs(snaps: Iterable[SymbolSnapshot]) -> list[float]:
    metrics: list[float] = []
    for snap in snaps:
        depth_component = log1p(max(snap.top5_depth_usdt, 0.0))
        volume_component = log1p(max(snap.qvol_usdt, 0.0))
        resilience_component = log1p(max(snap.depth_to_volume_ratio, 0.0) + 1.0)
        spread_component = log1p(max(snap.spread_bps, 0.01))
        slip_component = log1p(max(snap.slip_bps, 0.01))
        metrics.append(depth_component + volume_component + resilience_component - spread_component - slip_component)
    return metrics


def _momentum_inputs(snaps: Iterable[SymbolSnapshot]) -> list[float]:
    metrics: list[float] = []
    for snap in snaps:
        # Weight medium-horizon momentum (ret_15) more heavily per intraday trend-following literature.
        metrics.append((snap.ret_15 * 0.7) + (snap.ret_1 * 0.3))
    return metrics


def _volatility_inputs(snaps: Iterable[SymbolSnapshot]) -> list[float]:
    scores: list[float] = []
    for snap in snaps:
        atr_component = max(snap.atr_pct, 0.0)
        regime_component = max(0.0, 1.0 + snap.volatility_regime)
        scores.append(atr_component * regime_component)
    return scores


def _microstructure_penalty(snaps: Iterable[SymbolSnapshot]) -> list[float]:
    penalties: list[float] = []
    for snap in snaps:
        imbalance_penalty = abs(snap.order_flow_imbalance) * 40.0
        anomaly_penalty = max(0.0, snap.anomaly_score)
        velocity_penalty = abs(snap.price_velocity) * 2.0
        volume_penalty = max(0.0, snap.volume_zscore) * 5.0
        manip_penalty = snap.manip_score or 0.0
        penalties.append(imbalance_penalty + anomaly_penalty + velocity_penalty + volume_penalty + manip_penalty)
    return penalties


def _anomaly_residuals(snaps: Iterable[SymbolSnapshot]) -> list[float]:
    residuals: list[float] = []
    for snap in snaps:
        residuals.append(max(0.0, snap.anomaly_score) + (snap.manip_score or 0.0))
    return residuals


def enrich_cross_sectional(snaps: Sequence[SymbolSnapshot]) -> list[SymbolSnapshot]:
    """Attach cross-sectional factor edges to each snapshot.

    The scoring signals follow microstructure research (Hasbrouck, 2007; Easley & O'Hara, 2012) by
    rewarding depth-resilient order books, persistent momentum, and orderly flow while penalizing
    anomalous prints. The resulting z-scores are clipped per snapshot to stabilise downstream weights.
    """

    snaps_list = list(snaps)
    if len(snaps_list) < 3:
        return list(snaps_list)

    liquidity = _zscore(_liquidity_inputs(snaps_list))
    momentum = _zscore(_momentum_inputs(snaps_list))
    volatility = _zscore(_volatility_inputs(snaps_list))
    micro_penalty = _zscore(_microstructure_penalty(snaps_list))
    anomaly = _zscore(_anomaly_residuals(snaps_list))

    enriched: list[SymbolSnapshot] = []
    for snap, liq, mom, vol, micro, residual in zip(
        snaps_list,
        liquidity,
        momentum,
        volatility,
        micro_penalty,
        anomaly,
    ):
        enriched.append(
            snap.model_copy(
                update={
                    "liquidity_edge": round(liq, 4),
                    "momentum_edge": round(mom, 4),
                    "volatility_edge": round(vol, 4),
                    "microstructure_edge": round(-micro, 4),  # invert penalty so higher is healthier
                    "anomaly_residual": round(residual, 4),
                }
            )
        )
    return enriched
