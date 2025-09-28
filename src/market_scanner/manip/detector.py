"""Manipulation detection heuristics and lightweight scoring."""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Optional, Sequence

from pydantic import BaseModel, Field

from ..config import get_settings


@dataclass
class _State:
    last_price: Optional[float] = None
    last_oi: Optional[float] = None
    last_ts: Optional[float] = None


_STATE: Dict[str, _State] = {}


class ManipulationResult(BaseModel):
    """Output of the manipulation detector."""

    score: float | None = Field(default=None, description="Manipulation risk score in [0, 100].")
    flags: List[str] = Field(default_factory=list, description="Triggered manipulation flags.")
    features: Dict[str, float] = Field(default_factory=dict, description="Intermediate feature values for observability.")

    model_config = {
        "frozen": True,
    }


def _order_notional(level: Sequence[float]) -> float:
    try:
        price, qty = level
        return float(price) * float(qty)
    except (TypeError, ValueError):
        return 0.0


def _top_depth(orderbook: Mapping[str, Sequence[Sequence[float]]], depth: int = 5) -> tuple[float, float, float, float]:
    bids = orderbook.get("bids") or []
    asks = orderbook.get("asks") or []
    bid_total = sum(_order_notional(level) for level in bids[:depth])
    ask_total = sum(_order_notional(level) for level in asks[:depth])
    top_bid = _order_notional(bids[0]) if bids else 0.0
    top_ask = _order_notional(asks[0]) if asks else 0.0
    return bid_total, ask_total, top_bid, top_ask


def _wick_ratio(ohlcv: Sequence[Mapping[str, Any] | Sequence[Any]], atr_pct: float) -> float:
    if not ohlcv:
        return 0.0
    last = ohlcv[-1]
    try:
        high = float(last["high"]) if isinstance(last, Mapping) else float(last[2])
        low = float(last["low"]) if isinstance(last, Mapping) else float(last[3])
        close = float(last["close"]) if isinstance(last, Mapping) else float(last[4])
    except (KeyError, ValueError, TypeError, IndexError):
        return 0.0
    if close <= 0:
        return 0.0
    candle_range_pct = abs(high - low) / close * 100.0
    baseline = max(atr_pct, 0.1)
    return candle_range_pct / baseline


def _update_state(symbol: str, price: Optional[float], open_interest: Optional[float], timestamp: Optional[float]) -> _State:
    state = _STATE.get(symbol) or _State()
    _STATE[symbol] = _State(last_price=price, last_oi=open_interest, last_ts=timestamp)
    return state


def detect_manipulation(
    symbol: str,
    orderbook: Mapping[str, Sequence[Sequence[float]]],
    ohlcv: Sequence[Mapping[str, Any] | Sequence[Any]],
    close_price: float,
    atr_pct_val: float,
    ret_1: float,
    ret_15: float,
    funding_rate: Optional[float],
    open_interest: Optional[float],
    timestamp: Optional[float],
) -> ManipulationResult:
    """Return a manipulation score based on heuristics and lightweight ML features."""

    settings = get_settings()
    bid_total, ask_total, top_bid, top_ask = _top_depth(orderbook)
    total_depth = bid_total + ask_total
    imbalance = 0.0
    if total_depth > 0:
        imbalance = (bid_total - ask_total) / total_depth
    wall_notional = max(top_bid, top_ask)
    wall_ratio = 0.0
    if total_depth > 0:
        wall_ratio = wall_notional / total_depth

    vacuum_ratio = 0.0
    if settings.notional_test > 0:
        vacuum_ratio = total_depth / (settings.notional_test * 2)

    wick_ratio = _wick_ratio(ohlcv, atr_pct_val)

    prev_state = _update_state(symbol, close_price, open_interest, timestamp)
    oi_delta = 0.0
    if open_interest is not None and prev_state.last_oi:
        if prev_state.last_oi > 0:
            oi_delta = (open_interest - prev_state.last_oi) / prev_state.last_oi

    flags: List[str] = []
    severity = {
        "spoofing_depth_imbalance": 25,
        "liquidity_wall": 20,
        "liquidity_vacuum": 15,
        "scam_wick": 20,
        "oi_price_divergence": 15,
        "funding_price_divergence": 10,
    }

    if abs(imbalance) > 0.65 and wall_notional > settings.notional_test * 1.5:
        flags.append("spoofing_depth_imbalance")
    if wall_ratio > 0.55 and wall_notional > settings.notional_test:
        flags.append("liquidity_wall")
    if total_depth < settings.notional_test * 1.5:
        flags.append("liquidity_vacuum")
    if wick_ratio > 3.0 and atr_pct_val > 0.2:
        flags.append("scam_wick")
    if oi_delta > 0.05 and ret_15 < -0.8:
        flags.append("oi_price_divergence")
    if funding_rate is not None:
        if (funding_rate > 0 and ret_1 < -0.25) or (funding_rate < 0 and ret_1 > 0.25):
            flags.append("funding_price_divergence")

    imbalance_feature = max(0.0, abs(imbalance) - 0.2)
    wall_feature = max(0.0, wall_ratio - 0.3)
    wick_feature = max(0.0, min(wick_ratio, 6.0) - 2.0)
    oi_feature = max(0.0, oi_delta - 0.03)
    funding_feature = max(0.0, abs(funding_rate) - 0.05) if funding_rate is not None else 0.0
    vacuum_feature = max(0.0, 1.0 - vacuum_ratio)

    linear = (
        -2.5
        + 3.2 * imbalance_feature
        + 2.1 * wall_feature
        + 1.4 * wick_feature
        + 1.8 * oi_feature
        + 0.9 * funding_feature
        + 1.2 * vacuum_feature
    )
    prob = 1.0 / (1.0 + math.exp(-linear))
    score_ml = prob * 100.0

    score_rule = sum(severity.get(flag, 10) for flag in flags)
    score = max(score_rule, score_ml)
    score = max(0.0, min(100.0, score))

    result_flags = sorted(set(flags))
    result_score = round(score, 2) if result_flags or score > 5 else 0.0
    if result_score == 0.0 and not result_flags:
        result_score = 0.0

    return ManipulationResult(
        score=result_score,
        flags=result_flags,
        features={
            "imbalance": round(imbalance, 4),
            "wall_ratio": round(wall_ratio, 4),
            "total_depth": round(total_depth, 2),
            "wick_ratio": round(wick_ratio, 4),
            "oi_delta": round(oi_delta, 4),
            "funding": round(funding_rate or 0.0, 6) if funding_rate is not None else 0.0,
        },
    )
