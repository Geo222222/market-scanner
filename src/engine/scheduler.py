import os
import asyncio
import time
import httpx
from typing import Sequence
from ..config import settings
from ..engine.scoring import score_symbol
from ..adapters.base import MarketAdapter
from ..adapters.mock import MockAdapter
from ..adapters.ccxt import CCXTAdapter


def make_adapter() -> MarketAdapter:
    use_ccxt = os.getenv("SCANNER_USE_CCXT", "0") == "1"
    return CCXTAdapter("htx") if use_ccxt else MockAdapter()


async def scan_once(symbols: Sequence[str]):
    adapter = make_adapter()
    t0 = time.time()
    rankings = []
    for sym in symbols:
        md = await adapter.fetch_market(sym)
        score, metrics = score_symbol(md)
        rankings.append({"symbol": sym, "score": score, "metrics": metrics})
        if score >= 85 and settings.alert_system_url:
            async with httpx.AsyncClient(timeout=5) as c:
                await c.post(
                    settings.alert_system_url,
                    json={
                        "source": "scanner",
                        "severity": "info",
                        "payload": {"symbol": sym, "score": score, **metrics},
                    },
                )
    if hasattr(adapter, "close"):
        await adapter.close()  # type: ignore[attr-defined]
    return {"duration_ms": int(1000 * (time.time() - t0)), "rankings": rankings}


async def loop(symbols: Sequence[str], interval_s: int = 10):
    while True:
        await scan_once(symbols)
        await asyncio.sleep(interval_s)

# ONNYX | ONNX | DJM | DJ | ME | Jamaica — signature watermark
# Owner: DJM (ONNYX) — Jamaica. If found elsewhere, contact ME.
# ONNYX · ONNX · DJM · DJ · ME · Jamaica
