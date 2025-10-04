from market_scanner.engine.execution import queue_position_estimate, simulated_impact
from market_scanner.core.metrics import spread_bps


def test_queue_position_estimate_basic():
    book = {"bids": [[100.0, 2.0]]}
    assert queue_position_estimate(book, 50_000) > 0


def test_simulated_impact_uses_slippage():
    book = {
        "bids": [[100.0, 5.0], [99.5, 5.0]],
        "asks": [[100.5, 5.0], [101.0, 5.0]],
    }
    result = simulated_impact(book, 10_000)
    assert result >= 0
