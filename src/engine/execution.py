"""Execution quality analytics derived from order book snapshots."""
from __future__ import annotations

from typing import Dict, Sequence

from ..core.metrics import estimate_slippage_bps


def queue_position_estimate(orderbook: Dict[str, Sequence[Sequence[float]]], notional: float) -> float:
    """Rudimentary queue position approximation based on top-of-book depth."""

    bids = orderbook.get("bids") or []
    if not bids:
        return 0.0
    best_price, best_amount = bids[0]
    try:
        best_price = float(best_price)
        best_amount = float(best_amount)
    except (TypeError, ValueError):
        return 0.0
    depth_notional = best_price * best_amount
    if depth_notional <= 0:
        return 0.0
    return min(1.0, notional / depth_notional)


def spread_history_update(history: list[float], current_spread: float, max_points: int = 50) -> list[float]:
    history.append(current_spread)
    if len(history) > max_points:
        history.pop(0)
    return history


def simulated_impact(orderbook: Dict[str, Sequence[Sequence[float]]], notional: float) -> float:
    """Estimate expected impact in basis points for the provided notional."""

    if notional <= 0:
        return 0.0
    return float(estimate_slippage_bps(orderbook, notional, side="buy"))
