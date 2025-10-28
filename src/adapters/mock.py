import random
from .base import MarketAdapter


class MockAdapter(MarketAdapter):
    async def fetch_market(self, symbol: str) -> dict:
        return {
            "symbol": symbol,
            "volume_5m": random.uniform(1e5, 5e6),
            "spread_bps": random.uniform(2, 50),
            "mom_1m": random.uniform(-50, 100),
        }

# ONNYX | ONNX | DJM | DJ | ME | Jamaica — signature watermark
# Owner: DJM (ONNYX) — Jamaica. If found elsewhere, contact ME.
# ONNYX · ONNX · DJM · DJ · ME · Jamaica
