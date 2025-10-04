"""Momentum and VWAP analytics helpers."""
from __future__ import annotations

from collections import deque
from math import nan
from statistics import StatisticsError, mean, pstdev
from typing import Dict, Iterable, Sequence


def _zscore(values: Sequence[float]) -> float:
    if len(values) < 2:
        return 0.0
    try:
        sigma = pstdev(values)
    except StatisticsError:
        sigma = 0.0
    if sigma <= 1e-9:
        return 0.0
    return (values[-1] - mean(values)) / sigma


def compute_timeframe_zscores(closes: Sequence[float], window_map: Dict[str, int]) -> Dict[str, float]:
    """Return z-scores for multiple lookbacks given closing prices."""

    result: Dict[str, float] = {}
    for label, window in window_map.items():
        if len(closes) < window:
            result[label] = 0.0
            continue
        segment = closes[-window:]
        result[label] = float(_zscore(segment))
    return result


def compute_vwap_distance(ohlcv: Sequence[Dict[str, float] | Sequence[float]], fallback_close: float) -> float:
    """Compute the percentage distance between last price and rolling VWAP."""

    cumulative_price = 0.0
    cumulative_volume = 0.0
    for row in ohlcv:
        if isinstance(row, dict):
            price = float(row.get("close", fallback_close) or fallback_close)
            vol = float(row.get("volume", 0.0) or 0.0)
        else:
            if len(row) < 6:
                continue
            price = float(row[4])
            vol = float(row[5])
        cumulative_price += price * vol
        cumulative_volume += vol
    if cumulative_volume <= 0:
        return 0.0
    vwap = cumulative_price / cumulative_volume
    last_price = fallback_close
    if vwap <= 0:
        return 0.0
    return ((last_price / vwap) - 1.0) * 100.0


def compute_rsi(closes: Sequence[float], period: int = 14) -> float:
    if len(closes) <= period:
        return 50.0
    gains: deque[float] = deque(maxlen=period)
    losses: deque[float] = deque(maxlen=period)
    for prev, curr in zip(closes[-period-1:-1], closes[-period:]):
        delta = curr - prev
        if delta >= 0:
            gains.append(delta)
            losses.append(0.0)
        else:
            gains.append(0.0)
            losses.append(abs(delta))
    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def assemble_momentum_snapshot(
    closes: Sequence[float],
    ohlcv: Sequence[Dict[str, float] | Sequence[float]],
    price_velocity: float,
    fallback_close: float,
) -> Dict[str, float]:
    """Compute momentum, VWAP and oscillator metrics for the UI and scoring layer."""

    zscores = compute_timeframe_zscores(
        closes,
        {
            "z_15s": 4,
            "z_1m": 20,
            "z_5m": 60,
        },
    )
    zscores["z_15s"] = zscores.get("z_15s", 0.0) or price_velocity / 3.0
    vwap_distance = compute_vwap_distance(ohlcv, fallback_close)
    rsi = compute_rsi(closes)
    result = {
        **zscores,
        "vwap_distance": vwap_distance,
        "rsi14": rsi,
    }
    return {key: float(value) for key, value in result.items()}

