import math

import pytest

from market_scanner.core.metrics import (
    atr_pct,
    estimate_slippage_bps,
    funding_8h_pct,
    quote_volume_usdt,
    returns,
    spread_bps,
    top5_depth_usdt,
)


def test_quote_volume_prefers_quote():
    ticker = {"quoteVolume": "1250000"}
    assert quote_volume_usdt(ticker) == pytest.approx(1_250_000)


def test_quote_volume_fallback_to_base_and_last():
    ticker = {"baseVolume": 100, "last": 250}
    assert quote_volume_usdt(ticker) == pytest.approx(25_000)


def test_spread_bps():
    assert spread_bps(99, 101) == pytest.approx(((101 - 99) / 100) * 10_000)


def test_top5_depth_usdt():
    ob = {"bids": [[100, 2], [99, 1]], "asks": [[101, 3], [102, 1]]}
    assert top5_depth_usdt(ob) == pytest.approx((100 * 2) + (99 * 1) + (101 * 3) + (102 * 1))


def test_atr_pct():
    ohlcv = [[0, 100, 110, 95, 105, 0], [1, 105, 112, 100, 108, 0]]
    value = atr_pct(ohlcv, period=2)
    assert value > 0


def test_returns():
    closes = [100, 110, 121]
    metrics = returns(closes, lookback=2)
    assert metrics["ret_1"] == pytest.approx(10.0)
    assert metrics["ret_15"] == pytest.approx(21.0)


def test_estimate_slippage_bps_handles_depth():
    orderbook = {"bids": [[100, 5]], "asks": [[101, 5]]}
    # Notional of 200 can be filled entirely from top level
    slippage = estimate_slippage_bps(orderbook, 200, side="buy")
    assert slippage >= 0
    assert slippage < 10_000


def test_funding_conversion():
    assert funding_8h_pct(0.0005) == pytest.approx(0.05)
