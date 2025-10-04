"""Pure analytics functions and data models for market snapshots."""
from __future__ import annotations

from datetime import datetime
from math import log1p, log
from statistics import StatisticsError, mean, median, pstdev
from typing import Iterable, Mapping, Sequence

from pydantic import BaseModel, Field


class SymbolSnapshot(BaseModel):
    """Immutable view of the metrics used for scoring a tradable symbol."""

    symbol: str = Field(..., description="Symbol identifier (exchange format).")
    qvol_usdt: float = Field(..., description="24h quote volume in USDT.")
    spread_bps: float = Field(..., description="Current bid/ask spread in basis points.")
    top5_depth_usdt: float = Field(..., description="Aggregated book depth across top 5 levels on both sides.")
    atr_pct: float = Field(..., description="Average true range expressed as percent of price.")
    ret_1: float = Field(..., description="1-period momentum return (percent).")
    ret_15: float = Field(..., description="15-period momentum return (percent).")
    slip_bps: float = Field(..., description="Estimated worst-case slippage for the configured notional.")
    funding_8h_pct: float | None = Field(None, description="Funding rate expressed per 8h period in percent.")
    open_interest: float | None = Field(None, description="Open interest for the contract, if available.")
    basis_bps: float | None = Field(None, description="Basis between perp and spot markets in basis points.")
    volume_zscore: float = Field(0.0, description="Z-score of the latest volume relative to a trailing baseline.")
    order_flow_imbalance: float = Field(0.0, description="Normalized order-flow imbalance across the top book levels (-1 to 1).")
    volatility_regime: float = Field(0.0, description="Short/long realized volatility ratio minus one.")
    price_velocity: float = Field(0.0, description="Recent price velocity expressed as percent change per bar.")
    anomaly_score: float = Field(0.0, description="Composite anomaly score capturing pump-and-dump or wash-trading signatures.")
    depth_to_volume_ratio: float = Field(0.0, description="Top-5 book depth divided by the latest bar quote volume.")
    liquidity_edge: float = Field(0.0, description="Cross-sectional liquidity edge (z-score), positive means deeper and tighter than peers.")
    momentum_edge: float = Field(0.0, description="Cross-sectional momentum edge (z-score) from intraday returns.")
    volatility_edge: float = Field(0.0, description="Cross-sectional volatility regime edge (z-score).")
    microstructure_edge: float = Field(0.0, description="Cross-sectional microstructure health edge (z-score).")
    anomaly_residual: float = Field(0.0, description="Residual anomaly pressure vs peers (positive implies more suspicious flow).")
    manip_score: float | None = Field(None, description="Heuristic manipulation risk score (0-100).")
    manip_flags: list[str] | None = Field(None, description="List of triggered manipulation signals.")
    ts: datetime = Field(..., description="Timestamp when the snapshot was computed.")
    score: float | None = Field(None, description="Computed ranking score (assigned downstream).")

    model_config = {
        "frozen": True,
        "arbitrary_types_allowed": False,
    }


def _to_float(value: object, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def quote_volume_usdt(ticker: Mapping[str, object]) -> float:
    """Return the best available quote volume figure in USDT."""

    primary_keys = ("quoteVolume", "quoteVolume24h", "v")
    for key in primary_keys:
        if key in ticker and ticker[key] not in (None, ""):
            vol = _to_float(ticker[key])
            if vol > 0:
                return vol
    base_volume = _to_float(ticker.get("baseVolume"))
    last_price = _to_float(ticker.get("last"), default=0.0)
    if base_volume > 0 and last_price > 0:
        return base_volume * last_price
    info = ticker.get("info")
    if isinstance(info, Mapping):
        for key in ("quoteVolume", "quote_volume", "turnover"):
            if key in info:
                vol = _to_float(info[key])
                if vol > 0:
                    return vol
    return 0.0


def spread_bps(best_bid: float | None, best_ask: float | None) -> float:
    """Compute the mid-market spread in basis points."""

    bid = _to_float(best_bid, default=0.0)
    ask = _to_float(best_ask, default=0.0)
    if bid <= 0 or ask <= 0 or ask <= bid:
        return 10_000.0
    mid = (bid + ask) / 2
    return abs((ask - bid) / mid) * 10_000


def top5_depth_usdt(orderbook: Mapping[str, Sequence[Sequence[float]]]) -> float:
    """Sum the notional liquidity in the top five levels for bids and asks."""

    total = 0.0
    for side in ("bids", "asks"):
        levels = orderbook.get(side) or []
        for price, amount in list(levels)[:5]:
            price_f = _to_float(price)
            amount_f = _to_float(amount)
            total += price_f * amount_f
    return total


def _extract_ohlcv_value(row: Sequence[float] | Mapping[str, float], index: int, key: str) -> float:
    if isinstance(row, Mapping):
        return _to_float(row.get(key))
    if len(row) > index:
        return _to_float(row[index])
    return 0.0


def atr_pct(ohlcv: Sequence[Sequence[float] | Mapping[str, float]], period: int = 50) -> float:
    """Compute average true range as a percentage of the last close."""

    if not ohlcv:
        return 0.0
    highs = [_extract_ohlcv_value(row, 2, "high") for row in ohlcv]
    lows = [_extract_ohlcv_value(row, 3, "low") for row in ohlcv]
    closes = [_extract_ohlcv_value(row, 4, "close") for row in ohlcv]
    if not highs or not lows or not closes:
        return 0.0
    trs: list[float] = []
    prev_close = closes[0]
    for high, low, close in zip(highs, lows, closes):
        range_hl = high - low
        range_hc = abs(high - prev_close)
        range_lc = abs(low - prev_close)
        trs.append(max(range_hl, range_hc, range_lc))
        prev_close = close
    if not trs:
        return 0.0
    window = trs[-period:]
    atr = mean(window)
    last_close = closes[-1]
    if last_close <= 0:
        return 0.0
    return (atr / last_close) * 100.0


def returns(closes: Iterable[float], lookback: int = 15) -> dict[str, float]:
    """Calculate trailing returns in percent for 1 and N (lookback) periods."""

    closes_list = [c for c in (_to_float(val) for val in closes) if c > 0]
    if len(closes_list) < 2:
        return {"ret_1": 0.0, "ret_15": 0.0}
    last = closes_list[-1]
    prev = closes_list[-2]
    ret_1 = ((last / prev) - 1.0) * 100.0 if prev else 0.0
    if len(closes_list) > lookback:
        base = closes_list[-lookback - 1]
        ret_15 = ((last / base) - 1.0) * 100.0 if base else 0.0
    else:
        ret_15 = ret_1
    return {"ret_1": ret_1, "ret_15": ret_15}


def _walk_levels(levels: Sequence[Sequence[float]], notional: float) -> tuple[float, float]:
    remaining = notional
    filled_quote = 0.0
    filled_base = 0.0
    for price, amount in levels:
        price_f = _to_float(price)
        amount_f = _to_float(amount)
        if price_f <= 0 or amount_f <= 0:
            continue
        level_quote = price_f * amount_f
        take_quote = min(level_quote, remaining)
        if take_quote <= 0:
            continue
        filled_quote += take_quote
        filled_base += take_quote / price_f
        remaining -= take_quote
        if remaining <= 1e-6:
            break
    return filled_quote, filled_base


def estimate_slippage_bps(
    orderbook: Mapping[str, Sequence[Sequence[float]]],
    notional: float,
    side: str = "both",
) -> float:
    """Estimate slippage in basis points for the provided notional."""

    bids = orderbook.get("bids") or []
    asks = orderbook.get("asks") or []
    best_bid = bids[0][0] if bids else None
    best_ask = asks[0][0] if asks else None
    if notional <= 0 or best_bid is None or best_ask is None:
        return 10_000.0
    mid = (_to_float(best_bid) + _to_float(best_ask)) / 2
    if mid <= 0:
        return 10_000.0

    def _slip(levels: Sequence[Sequence[float]], is_buy: bool) -> float:
        filled_quote, filled_base = _walk_levels(levels, notional)
        if filled_quote < notional * 0.999 or filled_base <= 0:
            return 10_000.0
        avg_price = filled_quote / filled_base
        if avg_price <= 0:
            return 10_000.0
        diff = (avg_price - mid) if is_buy else (mid - avg_price)
        return abs(diff / mid) * 10_000

    side_lower = side.lower()
    slips = []
    if side_lower in ("buy", "both"):
        slips.append(_slip(asks, True))
    if side_lower in ("sell", "both"):
        slips.append(_slip(bids, False))
    if not slips:
        slips.append(_slip(asks if asks else bids, True))
    return max(slips)


def basis_bp(perp_price: float | None, spot_price: float | None) -> float | None:
    """Return basis in basis points if both prices are provided."""

    perp = _to_float(perp_price, default=0.0)
    spot = _to_float(spot_price, default=0.0)
    if perp <= 0 or spot <= 0:
        return None
    return ((perp / spot) - 1.0) * 10_000


def funding_8h_pct(raw_rate: float | None) -> float | None:
    """Convert a raw funding rate to an 8h percent figure."""

    rate = _to_float(raw_rate, default=0.0)
    if rate == 0.0:
        return None
    return rate * 100.0


def closes_from_ohlcv(ohlcv: Sequence[Sequence[float] | Mapping[str, float]]) -> list[float]:
    """Extract closing prices from OHLCV rows."""

    closes: list[float] = []
    for row in ohlcv:
        if isinstance(row, Mapping) and "close" in row:
            try:
                closes.append(float(row["close"]))
                continue
            except (TypeError, ValueError):
                pass
        try:
            if len(row) > 4:
                closes.append(float(row[4]))
        except (TypeError, ValueError):
            continue
    return closes


def latest_volume_usdt(
    ohlcv: Sequence[Sequence[float] | Mapping[str, float]],
    fallback_price: float,
) -> float:
    """Return the most recent bar volume converted to quote notionals."""

    price = max(_to_float(fallback_price), 0.0)
    for row in reversed(ohlcv):
        volume = _extract_ohlcv_value(row, 5, "volume")
        if volume > 0:
            close = _extract_ohlcv_value(row, 4, "close") or price
            if close <= 0:
                close = price if price > 0 else 0.0
            return max(volume * close, 0.0)
    return 0.0


def order_flow_imbalance(orderbook: Mapping[str, Sequence[Sequence[float]]], depth: int = 10) -> float:
    """Return normalized order-flow imbalance using notional amounts."""

    bids = orderbook.get("bids") or []
    asks = orderbook.get("asks") or []
    bid_notional = sum(_to_float(price) * _to_float(amount) for price, amount in bids[:depth])
    ask_notional = sum(_to_float(price) * _to_float(amount) for price, amount in asks[:depth])
    total = bid_notional + ask_notional
    if total <= 0:
        return 0.0
    return (bid_notional - ask_notional) / total


def volume_zscore(ohlcv: Sequence[Sequence[float] | Mapping[str, float]], lookback: int = 60) -> float:
    """Compute a rolling z-score for the latest volume."""

    if lookback <= 1:
        return 0.0
    volumes: list[float] = []
    for row in ohlcv:
        vol = _extract_ohlcv_value(row, 5, "volume")
        if vol <= 0 and isinstance(row, Mapping):
            for key in ("quoteVolume", "baseVolume", "volume"):
                if key in row:
                    vol = _to_float(row[key])
                    if vol > 0:
                        break
        if vol > 0:
            volumes.append(vol)
    if len(volumes) < 10:
        return 0.0
    window = volumes[-lookback:]
    if len(window) < 2:
        return 0.0
    try:
        sigma = pstdev(window)
    except StatisticsError:
        sigma = 0.0
    if sigma <= 1e-6:
        return 0.0
    center = median(window)
    z = (window[-1] - center) / sigma
    return max(-10.0, min(10.0, z))


def volatility_regime(closes: Sequence[float], short_window: int = 20, long_window: int = 60) -> float:
    """Return the short/long realized volatility ratio minus one."""

    prices = [value for value in closes if value and value > 0]
    if len(prices) <= long_window:
        return 0.0
    log_returns: list[float] = []
    for prev, curr in zip(prices, prices[1:]):
        if prev > 0 and curr > 0:
            log_returns.append(log(curr / prev))
    if len(log_returns) < long_window or long_window <= 1:
        return 0.0
    try:
        short_sigma = pstdev(log_returns[-short_window:])
        long_sigma = pstdev(log_returns[-long_window:])
    except StatisticsError:
        return 0.0
    if long_sigma <= 1e-9:
        return 0.0
    ratio = short_sigma / long_sigma
    return max(-1.0, min(5.0, ratio - 1.0))


def price_velocity(closes: Sequence[float], window: int = 5) -> float:
    """Return normalized price velocity (% change per bar)."""

    prices = [value for value in closes if value and value > 0]
    if len(prices) <= window:
        return 0.0
    start = prices[-window-1]
    end = prices[-1]
    if start <= 0:
        return 0.0
    velocity = ((end / start) - 1.0) * (100.0 / window)
    return max(-10.0, min(10.0, velocity))


def pump_dump_score(ret_15: float, ret_1: float, volume_z: float, vol_regime: float) -> float:
    """Composite anomaly score highlighting pump-and-dump style behaviour."""

    surge = max(0.0, ret_15)
    reversal = max(0.0, -ret_1)
    volume_component = max(0.0, abs(volume_z) - 1.5)
    volatility_component = max(0.0, vol_regime)
    raw = (surge * 1.2) + (reversal * 1.6) + (volume_component * 6.0) + (volatility_component * 8.0)
    return max(0.0, min(100.0, raw))
