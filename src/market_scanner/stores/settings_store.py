"""Persistence helpers for user settings and watchlists."""
from __future__ import annotations

from collections.abc import Iterable
from typing import Any, Dict, List, Optional

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert as pg_insert

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
    manipulation_threshold: Optional[float],
    notional: Optional[float],
    *,
    session: Optional[AsyncSession] = None,
) -> None:
    own_session = session is None
    if own_session:
        session = await _get_session()

    stmt = pg_insert(USER_PROFILES).values(
        name=name,
        weights=weights,
        manipulation_threshold=manipulation_threshold,
        notional=notional,
    )
    excluded = getattr(stmt, "excluded", None)
    if excluded is not None:
        update_cols = {
            "weights": excluded.weights,
            "manipulation_threshold": excluded.manipulation_threshold,
            "notional": excluded.notional,
        }
    else:  # pragma: no cover - safety for dialects without excluded support
        update_cols = {
            "weights": weights,
            "manipulation_threshold": manipulation_threshold,
            "notional": notional,
        }
    upsert_stmt = stmt.on_conflict_do_update(
        index_elements=[USER_PROFILES.c.name],
        set_=update_cols,
    )
    await session.execute(upsert_stmt)

    if own_session:
        await session.commit()
    else:  # allow callers to manage their transaction lifecycle
        await session.flush()


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
        symbols = symbols_result.fetchall()
        watchlists.append(
            {
                "id": row.id,
                "name": row.name,
                "count": len(symbols),
                "symbols": [sym[0] for sym in symbols],
            }
        )
    return watchlists


async def upsert_watchlist(name: str, symbols: List[str] | None = None) -> Dict[str, Any]:
    session = await _get_session()
    stmt = pg_insert(WATCHLISTS).values(name=name)
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
            await session.execute(pg_insert(WATCHLIST_SYMBOLS).values(values))
    await session.commit()
    return {"id": watchlist_id, "name": name, "symbols": symbols or []}


async def delete_watchlist(name: str) -> None:
    session = await _get_session()
    watchlist = await session.execute(select(WATCHLISTS.c.id).where(WATCHLISTS.c.name == name))
    row = watchlist.fetchone()
    if not row:
        return
    watchlist_id = row.id
    await session.execute(delete(WATCHLIST_SYMBOLS).where(WATCHLIST_SYMBOLS.c.watchlist_id == watchlist_id))
    await session.execute(delete(WATCHLISTS).where(WATCHLISTS.c.id == watchlist_id))
    await session.commit()


async def add_symbol_to_watchlist(name: str, symbol: str, position: Optional[int] = None) -> Dict[str, Any]:
    session = await _get_session()
    wl_row = await session.execute(select(WATCHLISTS).where(WATCHLISTS.c.name == name))
    row = wl_row.fetchone()
    if not row:
        result = await session.execute(
            pg_insert(WATCHLISTS)
            .values(name=name)
            .returning(WATCHLISTS.c.id, WATCHLISTS.c.name)
        )
        row = result.fetchone()
    watchlist_id = row.id

    current_symbols_result = await session.execute(
        select(WATCHLIST_SYMBOLS.c.symbol, WATCHLIST_SYMBOLS.c.position)
        .where(WATCHLIST_SYMBOLS.c.watchlist_id == watchlist_id)
        .order_by(WATCHLIST_SYMBOLS.c.position)
    )
    current_symbols = [(sym, pos) for sym, pos in current_symbols_result.fetchall()]
    if any(existing_symbol == symbol for existing_symbol, _ in current_symbols):
        await session.commit()
        return {
            "id": watchlist_id,
            "name": row.name,
            "symbols": [sym for sym, _ in current_symbols],
        }

    if position is None or position < 0 or position > len(current_symbols):
        position = len(current_symbols)

    # shift positions for symbols after the insertion point
    await session.execute(
        update(WATCHLIST_SYMBOLS)
        .where(
            WATCHLIST_SYMBOLS.c.watchlist_id == watchlist_id,
            WATCHLIST_SYMBOLS.c.position >= position,
        )
        .values(position=WATCHLIST_SYMBOLS.c.position + 1)
    )

    await session.execute(
        pg_insert(WATCHLIST_SYMBOLS).values(
            watchlist_id=watchlist_id,
            symbol=symbol,
            position=position,
        )
    )

    await session.commit()

    return await get_watchlist(name)


async def remove_symbol_from_watchlist(name: str, symbol: str) -> Dict[str, Any] | None:
    session = await _get_session()
    wl_row = await session.execute(select(WATCHLISTS).where(WATCHLISTS.c.name == name))
    row = wl_row.fetchone()
    if not row:
        return None
    watchlist_id = row.id

    await session.execute(
        delete(WATCHLIST_SYMBOLS)
        .where(
            WATCHLIST_SYMBOLS.c.watchlist_id == watchlist_id,
            WATCHLIST_SYMBOLS.c.symbol == symbol,
        )
    )

    await _reindex_watchlist(session, watchlist_id)
    await session.commit()
    return await get_watchlist(name)


async def reorder_watchlist(name: str, symbols: Iterable[str]) -> Dict[str, Any] | None:
    session = await _get_session()
    wl_row = await session.execute(select(WATCHLISTS).where(WATCHLISTS.c.name == name))
    row = wl_row.fetchone()
    if not row:
        return None
    watchlist_id = row.id

    unique_symbols: list[str] = []
    seen = set()
    for symbol in symbols:
        text = str(symbol).strip()
        if not text or text in seen:
            continue
        seen.add(text)
        unique_symbols.append(text)

    if unique_symbols:
        await session.execute(
            delete(WATCHLIST_SYMBOLS)
            .where(WATCHLIST_SYMBOLS.c.watchlist_id == watchlist_id)
            .where(~WATCHLIST_SYMBOLS.c.symbol.in_(unique_symbols))
        )
    else:
        await session.execute(delete(WATCHLIST_SYMBOLS).where(WATCHLIST_SYMBOLS.c.watchlist_id == watchlist_id))

    for position, sym in enumerate(unique_symbols):
        result = await session.execute(
            update(WATCHLIST_SYMBOLS)
            .where(
                WATCHLIST_SYMBOLS.c.watchlist_id == watchlist_id,
                WATCHLIST_SYMBOLS.c.symbol == sym,
            )
            .values(position=position)
        )
        if result.rowcount == 0:
            await session.execute(
                pg_insert(WATCHLIST_SYMBOLS).values(
                    watchlist_id=watchlist_id,
                    symbol=sym,
                    position=position,
                )
            )

    await session.commit()
    return await get_watchlist(name)


async def get_watchlist(name: str) -> Dict[str, Any] | None:
    session = await _get_session()
    wl_result = await session.execute(select(WATCHLISTS).where(WATCHLISTS.c.name == name))
    row = wl_result.fetchone()
    if not row:
        return None
    watchlist_id = row.id
    symbols_res = await session.execute(
        select(WATCHLIST_SYMBOLS.c.symbol)
        .where(WATCHLIST_SYMBOLS.c.watchlist_id == watchlist_id)
        .order_by(WATCHLIST_SYMBOLS.c.position)
    )
    symbols = [sym[0] for sym in symbols_res.fetchall()]
    return {"id": watchlist_id, "name": row.name, "symbols": symbols}


async def _reindex_watchlist(session: AsyncSession, watchlist_id: int) -> None:
    rows = await session.execute(
        select(WATCHLIST_SYMBOLS.c.symbol)
        .where(WATCHLIST_SYMBOLS.c.watchlist_id == watchlist_id)
        .order_by(WATCHLIST_SYMBOLS.c.position)
    )
    symbols = [sym[0] for sym in rows.fetchall()]
    for idx, sym in enumerate(symbols):
        await session.execute(
            update(WATCHLIST_SYMBOLS)
            .where(
                WATCHLIST_SYMBOLS.c.watchlist_id == watchlist_id,
                WATCHLIST_SYMBOLS.c.symbol == sym,
            )
            .values(position=idx)
        )


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
    stmt = pg_insert(PROFILE_PRESETS).values(name=name, weights=weights)
    update_cols = {"weights": stmt.excluded.weights}
    await session.execute(
        stmt.on_conflict_do_update(index_elements=[PROFILE_PRESETS.c.name], set_=update_cols)
    )
    await session.commit()
