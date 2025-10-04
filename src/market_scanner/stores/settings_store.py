"""Persistence helpers for user settings and watchlists."""
from __future__ import annotations

from typing import Any, Dict, List

from sqlalchemy import select, delete
from sqlalchemy.dialects.postgresql import insert

from .pg_store import (
    USER_PROFILES,
    WATCHLISTS,
    WATCHLIST_SYMBOLS,
    PROFILE_PRESETS,
    _get_session,
)


async def get_user_profile(name: str = "default") -> Dict[str, Any]:
    session = await _get_session()
    result = await session.execute(select(USER_PROFILES).where(USER_PROFILES.c.name == name))
    row = result.fetchone()
    if not row:
        return {
            "name": name,
            "weights": {"liquidity": 0.0, "momentum": 0.0, "spread": 0.0},
            "manipulation_threshold": 0.0,
            "notional": None,
        }
    return {
        "name": row.name,
        "weights": row.weights or {},
        "manipulation_threshold": row.manipulation_threshold or 0.0,
        "notional": row.notional,
    }


async def upsert_user_profile(
    name: str,
    weights: Dict[str, float],
    manipulation_threshold: float | None,
    notional: float | None,
) -> None:
    session = await _get_session()
    stmt = insert(USER_PROFILES).values(
        name=name,
        weights=weights,
        manipulation_threshold=manipulation_threshold,
        notional=notional,
    )
    update_cols = {
        "weights": stmt.excluded.weights,
        "manipulation_threshold": stmt.excluded.manipulation_threshold,
        "notional": stmt.excluded.notional,
    }
    await session.execute(stmt.on_conflict_do_update(index_elements=[USER_PROFILES.c.name], set_=update_cols))
    await session.commit()


async def list_watchlists() -> List[Dict[str, Any]]:
    session = await _get_session()
    result = await session.execute(select(WATCHLISTS))
    watchlists = []
    for row in result.fetchall():
        symbols_result = await session.execute(
            select(WATCHLIST_SYMBOLS.c.symbol)
            .where(WATCHLIST_SYMBOLS.c.watchlist_id == row.id)
            .order_by(WATCHLIST_SYMBOLS.c.position)
        )
        watchlists.append(
            {
                "id": row.id,
                "name": row.name,
                "symbols": [sym[0] for sym in symbols_result.fetchall()],
            }
        )
    return watchlists


async def upsert_watchlist(name: str, symbols: List[str] | None = None) -> Dict[str, Any]:
    session = await _get_session()
    stmt = insert(WATCHLISTS).values(name=name)
    result = await session.execute(
        stmt.on_conflict_do_update(index_elements=[WATCHLISTS.c.name], set_={"name": stmt.excluded.name})
        .returning(WATCHLISTS.c.id, WATCHLISTS.c.name)
    )
    watchlist_row = result.fetchone()
    watchlist_id = watchlist_row.id
    if symbols is not None:
        await session.execute(delete(WATCHLIST_SYMBOLS).where(WATCHLIST_SYMBOLS.c.watchlist_id == watchlist_id))
        values = [
            {
                "watchlist_id": watchlist_id,
                "symbol": symbol,
                "position": idx,
            }
            for idx, symbol in enumerate(symbols)
        ]
        if values:
            await session.execute(insert(WATCHLIST_SYMBOLS).values(values))
    await session.commit()
    return {"id": watchlist_id, "name": name, "symbols": symbols or []}


async def list_profile_presets() -> List[str]:
    session = await _get_session()
    result = await session.execute(select(PROFILE_PRESETS.c.name))
    return [row.name for row in result.fetchall()]


async def get_profile_preset(name: str) -> Dict[str, Any] | None:
    session = await _get_session()
    result = await session.execute(select(PROFILE_PRESETS).where(PROFILE_PRESETS.c.name == name))
    row = result.fetchone()
    if not row:
        return None
    return {"name": row.name, "weights": row.weights}


async def save_profile_preset(name: str, weights: Dict[str, Dict[str, float]]) -> None:
    session = await _get_session()
    stmt = insert(PROFILE_PRESETS).values(name=name, weights=weights)
    update_cols = {"weights": stmt.excluded.weights}
    await session.execute(
        stmt.on_conflict_do_update(index_elements=[PROFILE_PRESETS.c.name], set_=update_cols)
    )
    await session.commit()
