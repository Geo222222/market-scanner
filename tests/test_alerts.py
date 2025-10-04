import asyncio
import pytest

from market_scanner.engine.alerts import AlertRule, SignalBus


@pytest.mark.asyncio
async def test_alert_rule_matches_and_queues(monkeypatch):
    bus = SignalBus()
    bus._settings.redis_url = None  # avoid redis dependency
    bus.register_rule(AlertRule(name='top-signal', expression='score > 10'))
    await bus.publish_if_matched({
        'symbol': 'BTC/USDT:USDT',
        'rank': 1,
        'score': 12.5,
        'liquidity_edge': 1.0,
        'momentum_edge': 0.5,
        'volatility_edge': 0.1,
        'microstructure_edge': 0.2,
        'anomaly_residual': 0.0,
    })
    payload = bus._queue.get_nowait()
    assert payload['symbol'] == 'BTC/USDT:USDT'
