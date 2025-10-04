from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ..stores import settings_store

router = APIRouter()


@router.get("/watchlists")
async def list_watchlists():
    watchlists = await settings_store.list_watchlists()
    return [
        {
            "name": wl["name"],
            "symbols": wl["symbols"],
        }
        for wl in watchlists
    ]


@router.post("/watchlists")
async def create_watchlist(payload: dict[str, object]):
    name = str(payload.get("name", "")).strip()
    if not name:
        raise HTTPException(status_code=422, detail="Watchlist name is required")
    symbols = payload.get("symbols")
    if symbols is not None:
        if not isinstance(symbols, list):
            raise HTTPException(status_code=422, detail="symbols must be a list")
        symbols = [str(sym).strip() for sym in symbols if str(sym).strip()]
    result = await settings_store.upsert_watchlist(name=name, symbols=symbols)
    return result
