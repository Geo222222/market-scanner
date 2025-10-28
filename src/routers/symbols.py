from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from ..jobs.loop import collect_snapshot, get_latest_bundle, get_spread_history
from ..stores.analytics_store import fetch_recent_bars
from ..core.scoring import score_with_breakdown

router = APIRouter()


@router.get("/")
async def list_symbols():
    return {"status": "ok"}


def _compact_orderbook(book: dict) -> dict:
    return {
        "bids": (book.get("bids") or [])[:10],
        "asks": (book.get("asks") or [])[:10],
    }


def _aggregate_bars(bars: list[dict], window: int) -> list[dict]:
    aggregated: list[dict] = []
    chunk: list[dict] = []
    for row in bars:
        chunk.append(row)
        if len(chunk) == window:
            aggregated.append(_collapse_chunk(chunk))
            chunk = []
    if chunk:
        aggregated.append(_collapse_chunk(chunk))
    return aggregated


def _collapse_chunk(chunk: list[dict]) -> dict:
    if not chunk:
        return {}
    open_ = chunk[0].get("open", chunk[0].get("close"))
    close = chunk[-1].get("close")
    high = max(row.get("high", row.get("close", 0.0)) for row in chunk)
    low = min(row.get("low", row.get("close", 0.0)) for row in chunk)
    volume_quote = sum(row.get("volume_quote", 0.0) or 0.0 for row in chunk)
    return {
        "ts": chunk[-1].get("ts"),
        "open": open_,
        "close": close,
        "high": high,
        "low": low,
        "volume_quote": volume_quote,
    }


@router.get("/{symbol}/inspect")
async def inspect_symbol(symbol: str, mode: str | None = Query(default=None)):
    bundle = get_latest_bundle(symbol)
    if bundle is None:
        bundle = await collect_snapshot(symbol)
    if bundle is None:
        raise HTTPException(status_code=404, detail="symbol not found")

    snapshot = bundle.snapshot
    score, breakdown = score_with_breakdown(snapshot)

    if mode == "card":
        return {
            "symbol": snapshot.symbol,
            "score": score,
            "liquidity_edge": snapshot.liquidity_edge,
            "momentum_edge": snapshot.momentum_edge,
        }

    bars_1m = await fetch_recent_bars(symbol, "1m", limit=200)
    bars_5m = _aggregate_bars(bars_1m, window=5)
    bars_15m = _aggregate_bars(bars_1m, window=15)

    response = {
        "symbol": snapshot.symbol,
        "score": score,
        "snapshot": snapshot.model_dump(mode="json"),
        "orderbook": _compact_orderbook(bundle.orderbook),
        "momentum": bundle.momentum,
        "micro": bundle.micro_features,
        "metrics": {**bundle.execution, **breakdown},
        "manip_features": bundle.manip_features,
        "bars_1m": bars_1m,
        "bars_5m": bars_5m,
        "bars_15m": bars_15m,
        "trades": (bundle.trades or [])[-50:],
        "spread_history": get_spread_history(symbol),
    }
    return response
