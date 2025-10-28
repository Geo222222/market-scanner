from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from ..stores import settings_store
from ..security import require_admin

router = APIRouter(dependencies=[Depends(require_admin)])


class WatchlistCreatePayload(BaseModel):
    name: str = Field(..., min_length=1, max_length=64)
    symbols: Optional[list[str]] = None


class WatchlistSymbolsPayload(BaseModel):
    symbols: list[str] = Field(..., min_length=1)


@router.get("/watchlists")
async def list_watchlists():
    watchlists = await settings_store.list_watchlists()
    return [
        {
            "name": wl["name"],
            "symbols": wl["symbols"],
            "count": wl.get("count", len(wl["symbols"])),
        }
        for wl in watchlists
    ]


@router.post("/watchlists")
async def create_watchlist(payload: WatchlistCreatePayload):
    name = payload.name.strip()
    symbols = None
    if payload.symbols is not None:
        symbols = [sym.strip() for sym in payload.symbols if sym.strip()]
    result = await settings_store.upsert_watchlist(name=name, symbols=symbols)
    return result


@router.delete("/watchlists/{name}")
async def delete_watchlist(name: str):
    await settings_store.delete_watchlist(name)
    return {"ok": True}


@router.post("/watchlists/{name}/symbols")
async def add_symbol(name: str, payload: WatchlistSymbolsPayload):
    symbols = [sym.strip() for sym in payload.symbols if sym.strip()]
    if not symbols:
        raise HTTPException(status_code=422, detail="symbols must contain at least one symbol")
    # Insert symbols sequentially preserving order
    watchlist = None
    for offset, sym in enumerate(symbols):
        watchlist = await settings_store.add_symbol_to_watchlist(name, sym, position=None)
    return watchlist


@router.delete("/watchlists/{name}/symbols/{symbol}")
async def remove_symbol(name: str, symbol: str):
    watchlist = await settings_store.remove_symbol_from_watchlist(name, symbol)
    if watchlist is None:
        raise HTTPException(status_code=404, detail="Watchlist not found")
    return watchlist


@router.patch("/watchlists/{name}")
async def reorder_watchlist(name: str, payload: WatchlistSymbolsPayload):
    watchlist = await settings_store.reorder_watchlist(name, payload.symbols)
    if watchlist is None:
        raise HTTPException(status_code=404, detail="Watchlist not found")
    return watchlist

