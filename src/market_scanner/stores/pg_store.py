"""Async Postgres persistence helpers using SQLAlchemy."""
from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Column, DateTime, Float, MetaData, String, Table, UniqueConstraint
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from ..config import get_settings
from ..core.metrics import SymbolSnapshot

LOGGER = logging.getLogger(__name__)

_METADATA = MetaData()

BARS_1M = Table(
    "bars_1m",
    _METADATA,
    Column("symbol", String(80), primary_key=True),
    Column("ts", DateTime(timezone=True), primary_key=True),
    Column("close", Float, nullable=False),
    Column("atr_pct", Float, nullable=True),
    Column("spread_bps", Float, nullable=True),
    Column("depth_usdt", Float, nullable=True),
    Column("mom_1m", Float, nullable=True),
    Column("mom_15m", Float, nullable=True),
    Column("funding_pct", Float, nullable=True),
    Column("open_interest", Float, nullable=True),
    Column("basis_bps", Float, nullable=True),
    Column("manip_score", Float, nullable=True),
    Column("manip_flags", JSON, nullable=True),
    UniqueConstraint("symbol", "ts", name="bars_1m_symbol_ts_key"),
)

RANKINGS = Table(
    "rankings",
    _METADATA,
    Column("symbol", String(80), primary_key=True),
    Column("ts", DateTime(timezone=True), primary_key=True),
    Column("profile", String(32), primary_key=True),
    Column("score", Float, nullable=False),
    Column("manip_score", Float, nullable=True),
    Column("manip_flags", JSON, nullable=True),
    Column("inputs_json", JSON, nullable=False),
    UniqueConstraint("symbol", "ts", "profile", name="rankings_symbol_ts_profile_key"),
)

_ENGINE: AsyncEngine | None = None
_SESSION_FACTORY: sessionmaker[AsyncSession] | None = None
_SCHEMA_READY = False


async def _get_engine() -> AsyncEngine:
    global _ENGINE, _SESSION_FACTORY
    settings = get_settings()
    if not settings.postgres_url:
        raise RuntimeError("POSTGRES_URL is not configured")
    if _ENGINE is None:
        _ENGINE = create_async_engine(settings.postgres_url, echo=False, future=True)
        _SESSION_FACTORY = sessionmaker(_ENGINE, class_=AsyncSession, expire_on_commit=False)
    await _ensure_schema()
    return _ENGINE


async def _get_session() -> AsyncSession:
    await _get_engine()
    if _SESSION_FACTORY is None:  # pragma: no cover - safety
        raise RuntimeError("Session factory not initialised")
    return _SESSION_FACTORY()


async def _ensure_schema() -> None:
    global _SCHEMA_READY
    if _SCHEMA_READY or _ENGINE is None:
        if _ENGINE is None:
            return
        _SCHEMA_READY = True
        return
    async with _ENGINE.begin() as conn:  # pragma: no cover - run once
        await conn.run_sync(_METADATA.create_all)
    _SCHEMA_READY = True


def _normalise_ts(ts: datetime) -> datetime:
    if ts.tzinfo is None:
        from datetime import timezone

        return ts.replace(tzinfo=timezone.utc)
    return ts


async def insert_minute_agg(snapshot: SymbolSnapshot, close: float) -> None:
    try:
        session = await _get_session()
    except RuntimeError as exc:
        LOGGER.warning("Postgres unavailable for insert_minute_agg: %s", exc)
        return
    data = {
        "symbol": snapshot.symbol,
        "ts": _normalise_ts(snapshot.ts),
        "close": float(close),
        "atr_pct": float(snapshot.atr_pct),
        "spread_bps": float(snapshot.spread_bps),
        "depth_usdt": float(snapshot.top5_depth_usdt),
        "mom_1m": float(snapshot.ret_1),
        "mom_15m": float(snapshot.ret_15),
        "funding_pct": float(snapshot.funding_8h_pct) if snapshot.funding_8h_pct is not None else None,
        "open_interest": float(snapshot.open_interest) if snapshot.open_interest is not None else None,
        "basis_bps": float(snapshot.basis_bps) if snapshot.basis_bps is not None else None,
        "manip_score": float(snapshot.manip_score) if snapshot.manip_score is not None else None,
        "manip_flags": snapshot.manip_flags,
    }
    stmt = insert(BARS_1M).values(**data)
    update_cols = {key: stmt.excluded[key] for key in data if key not in {"symbol", "ts"}}
    async with session:
        await session.execute(
            stmt.on_conflict_do_update(index_elements=[BARS_1M.c.symbol, BARS_1M.c.ts], set_=update_cols)
        )
        await session.commit()


async def bulk_insert_rankings(ts: datetime, profile: str, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    try:
        session = await _get_session()
    except RuntimeError as exc:
        LOGGER.warning("Postgres unavailable for bulk_insert_rankings: %s", exc)
        return
    prepared = [
        {
            "symbol": row.get("symbol"),
            "ts": _normalise_ts(ts),
            "profile": profile,
            "score": float(row.get("score", 0.0) or 0.0),
            "manip_score": float(row.get("manip_score", 0.0) or 0.0) if row.get("manip_score") is not None else None,
            "manip_flags": row.get("manip_flags"),
            "inputs_json": json.loads(json.dumps(row, default=float)),
        }
        for row in rows
        if row.get("symbol")
    ]
    if not prepared:
        return
    stmt = insert(RANKINGS).values(prepared)
    update_cols = {
        "score": stmt.excluded.score,
        "manip_score": stmt.excluded.manip_score,
        "manip_flags": stmt.excluded.manip_flags,
        "inputs_json": stmt.excluded.inputs_json,
    }
    async with session:
        await session.execute(
            stmt.on_conflict_do_update(
                index_elements=[RANKINGS.c.symbol, RANKINGS.c.ts, RANKINGS.c.profile],
                set_=update_cols,
            )
        )
        await session.commit()
