from market_scanner.engine.momentum import assemble_momentum_snapshot, compute_vwap_distance


def test_momentum_snapshot_contains_indicators():
    closes = [100 + i for i in range(30)]
    ohlcv = [
        {
            "close": 100 + i,
            "volume": 1000 + i * 10,
        }
        for i in range(30)
    ]
    snapshot = assemble_momentum_snapshot(closes, ohlcv, price_velocity=0.8, fallback_close=129)
    assert "z_1m" in snapshot
    assert "vwap_distance" in snapshot


def test_vwap_distance_handles_zero_volume():
    ohlcv = [{"close": 100, "volume": 0}]
    assert compute_vwap_distance(ohlcv, 100) == 0.0
