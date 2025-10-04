import math

from market_scanner.core.metrics import (
    closes_from_ohlcv,
    order_flow_imbalance,
    price_velocity,
    pump_dump_score,
    volume_zscore,
    volatility_regime,
)
from market_scanner.manip.detector import detect_manipulation


def _sample_ohlcv(bars: int = 80, base_price: float = 100.0) -> list[list[float]]:
    data: list[list[float]] = []
    for idx in range(bars):
        price = base_price * (1 + 0.001 * idx)
        if idx >= bars - 5:
            swing = 0.01 * (idx - (bars - 5) + 1)
            close = price * (1 + swing)
            high = close * 1.01
            low = close * (1 - min(0.02, swing))
        else:
            high = price * 1.002
            low = price * 0.998
            close = price * (1 + 0.0002)
        volume = 1_000 + idx * 50
        if idx == bars - 1:
            volume *= 4  # spike on the last bar
        data.append([idx, price, high, low, close, volume])
    return data


def test_volume_and_volatility_metrics_detect_anomalies():
    ohlcv = _sample_ohlcv()
    vz = volume_zscore(ohlcv)
    assert vz > 2.0  # final bar volume spike registers

    closes = closes_from_ohlcv(ohlcv)
    vol_regime = volatility_regime(closes)
    assert vol_regime > 0.0  # short vol higher than long vol due to recent move

    velocity = price_velocity(closes)
    assert abs(velocity) > 0

    pump_score = pump_dump_score(ret_15=6.0, ret_1=-2.0, volume_z=vz, vol_regime=vol_regime)
    assert pump_score > 20


def test_detect_manipulation_emits_new_features():
    ohlcv = _sample_ohlcv()
    orderbook = {
        "bids": [[100.0, 1.5], [99.9, 0.8], [99.8, 0.6]],
        "asks": [[100.1, 0.4], [100.2, 0.3], [100.3, 0.2]],
    }
    result = detect_manipulation(
        symbol="TEST/USDT:USDT",
        orderbook=orderbook,
        ohlcv=ohlcv,
        close_price=ohlcv[-1][4],
        atr_pct_val=0.35,
        ret_1=-2.5,
        ret_15=7.0,
        funding_rate=0.01,
        open_interest=1_200.0,
        timestamp=1_700_000_000.0,
    )

    assert "volume_zscore" in result.features
    assert "pump_dump_score" in result.features
    assert result.features["volume_zscore"] > 0
    assert any(flag in {"post_surge_reversal", "wash_trade_volume"} for flag in result.flags)
