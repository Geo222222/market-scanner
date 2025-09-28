import time

import pytest

from market_scanner.manip import detector


@pytest.fixture(autouse=True)
def reset_state():
    detector._STATE.clear()


def test_detects_spoofing_depth_imbalance():
    orderbook = {
        "bids": [[100.0, 500.0], [99.9, 200.0], [99.8, 150.0], [99.7, 100.0]],
        "asks": [[100.1, 5.0], [100.2, 4.0], [100.3, 3.0], [100.4, 2.0]],
    }
    ohlcv = [[0, 100.0, 101.0, 99.0, 100.5, 1000]]
    result = detector.detect_manipulation(
        symbol="TEST/USDT:USDT",
        orderbook=orderbook,
        ohlcv=ohlcv,
        close_price=100.5,
        atr_pct_val=0.5,
        ret_1=0.1,
        ret_15=0.2,
        funding_rate=0.01,
        open_interest=1_000_000.0,
        timestamp=time.time(),
    )
    assert result.score is not None and result.score > 0
    assert "spoofing_depth_imbalance" in result.flags


def test_clean_book_low_score():
    orderbook = {
        "bids": [[100.0, 50.0], [99.9, 45.0], [99.8, 40.0], [99.7, 35.0]],
        "asks": [[100.1, 52.0], [100.2, 48.0], [100.3, 44.0], [100.4, 40.0]],
    }
    ohlcv = [[0, 100.0, 100.6, 99.6, 100.2, 1000]]
    result = detector.detect_manipulation(
        symbol="CLEAN/USDT:USDT",
        orderbook=orderbook,
        ohlcv=ohlcv,
        close_price=100.2,
        atr_pct_val=0.6,
        ret_1=0.05,
        ret_15=0.1,
        funding_rate=0.0,
        open_interest=900_000.0,
        timestamp=time.time(),
    )
    assert result.flags == []
    assert result.score <= 10.0
