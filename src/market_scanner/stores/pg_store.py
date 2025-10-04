"""Async Postgres persistence helpers using SQLAlchemy."""
from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Iterable, Sequence

from sqlalchemy import (
    JSON,
    BigInteger,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    MetaData,
    String,
    Table,
    UniqueConstraint,
    delete,
    func,
)
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from ..config import get_settings
from ..core.metrics import SymbolSnapshot
from ..feeds.events import FeedEvent
from ..storage.bars import Bar

LOGGER = logging.getLogger(__name__)

_METADATA = MetaData()

RAW_MESSAGES = Table(
    "raw_messages",
    _METADATA,
    Column("id", BigInteger, primary_key=True, autoincrement=True),
    Column("topic", String(160), nullable=False),
    Column("symbol", String(80), nullable=True, index=True),
    Column("event_type", String(32), nullable=False, index=True),
    Column("sequence", BigInteger, nullable=True),
    Column("recv_ts", DateTime(timezone=True), nullable=False, index=True),
    Column("payload", JSON, nullable=False),
    Column("raw", JSON, nullable=True),
)


def _bars_table(name: str, constraint: str) -> Table:
    return Table(
        name,
        _METADATA,
        Column("symbol", String(80), primary_key=True),
        Column("ts", DateTime(timezone=True), primary_key=True),
        Column("open", Float, nullable=False),
        Column("high", Float, nullable=False),
        Column("low", Float, nullable=False),
        Column("close", Float, nullable=False),
        Column("volume_base", Float, nullable=False),
        Column("volume_quote", Float, nullable=False),
        Column("trade_count", Integer, nullable=False),
        UniqueConstraint("symbol", "ts", name=constraint),
    )


BARS_1S = _bars_table("bars_1s", "bars_1s_symbol_ts_key")
BARS_5S = _bars_table("bars_5s", "bars_5s_symbol_ts_key")
BARS_1M_OHLC = _bars_table("bars_1m_ohlc", "bars_1m_ohlc_symbol_ts_key")

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

BAR_TABLES = {
    "1s": BARS_1S,
    "5s": BARS_5S,
    "1m": BARS_1M_OHLC,
}

USER_PROFILES = Table(
    "user_profiles",
    _METADATA,
    Column("name", String(64), primary_key=True),
    Column("weights", JSON, nullable=True),
    Column("manipulation_threshold", Float, nullable=True),
    Column("notional", Float, nullable=True),
    Column("updated_at", DateTime(timezone=True), server_default=func.now(), onupdate=func.now()),
)

WATCHLISTS = Table(
    "watchlists",
    _METADATA,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("name", String(64), unique=True, nullable=False),
    Column("created_at", DateTime(timezone=True), server_default=func.now()),
)

WATCHLIST_SYMBOLS = Table(
    "watchlist_symbols",
    _METADATA,
    Column("watchlist_id", Integer, ForeignKey("watchlists.id", ondelete="CASCADE"), primary_key=True),
    Column("symbol", String(80), primary_key=True),
    Column("position", Integer, nullable=False, default=0),
)

PROFILE_PRESETS = Table(
    "profile_presets",
    _METADATA,
    Column("name", String(64), primary_key=True),
    Column("weights", JSON, nullable=False),
    Column("created_at", DateTime(timezone=True), server_default=func.now()),
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
        return ts.replace(tzinfo=timezone.utc)
    return ts


async def insert_raw_messages(events: Sequence[FeedEvent]) -> None:
    if not events:
        return
    try:
        session = await _get_session()
    except RuntimeError as exc:
        LOGGER.warning("Postgres unavailable for insert_raw_messages: %s", exc)
        return
    rows = [
        {
            "topic": event.topic,
            "symbol": event.symbol,
            "event_type": event.event_type.value,
            "sequence": event.sequence,
            "recv_ts": _normalise_ts(event.recv_ts),
            "payload": json.loads(json.dumps(event.payload, default=str)),
            "raw": json.loads(json.dumps(event.raw, default=str)),
        }
        for event in events
    ]
    stmt = RAW_MESSAGES.insert().values(rows)
    async with session:
        await session.execute(stmt)
        await session.commit()


async def insert_timeframe_bars(timeframe: str, bars: Sequence[Bar]) -> None:
    if not bars:
        return
    table = BAR_TABLES.get(timeframe)
    if table is None:
        raise ValueError(f"Unsupported timeframe '{timeframe}'. Expected one of {list(BAR_TABLES)}")
    try:
        session = await _get_session()
    except RuntimeError as exc:
        LOGGER.warning("Postgres unavailable for insert_timeframe_bars(%s): %s", timeframe, exc)
        return
    rows = [
        {
            "symbol": bar.symbol,
            "ts": _normalise_ts(bar.ts),
            "open": float(bar.open),
            "high": float(bar.high),
            "low": float(bar.low),
            "close": float(bar.close),
            "volume_base": float(bar.volume_base),
            "volume_quote": float(bar.volume_quote),
            "trade_count": int(bar.trade_count),
        }
        for bar in bars
    ]
    stmt = insert(table).values(rows)
    update_cols = {key: stmt.excluded[key] for key in rows[0] if key not in {"symbol", "ts"}}
    async with session:
        await session.execute(
            stmt.on_conflict_do_update(index_elements=[table.c.symbol, table.c.ts], set_=update_cols)
        )
        await session.commit()


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


async def prune_expired_data(now: datetime | None = None) -> None:
    now = now or datetime.now(timezone.utc)
    try:
        session = await _get_session()
    except RuntimeError as exc:
        LOGGER.warning("Postgres unavailable for prune_expired_data: %s", exc)
        return
    settings = get_settings()
    raw_cutoff = now - timedelta(hours=settings.raw_retention_hours)
    bar_1s_cutoff = now - timedelta(hours=settings.bar_1s_retention_hours)
    bar_5s_cutoff = now - timedelta(days=settings.bar_5s_retention_days)
    bar_1m_cutoff = now - timedelta(days=settings.bar_1m_retention_days)
    statements = [
        delete(RAW_MESSAGES).where(RAW_MESSAGES.c.recv_ts < raw_cutoff),
        delete(BARS_1S).where(BARS_1S.c.ts < bar_1s_cutoff),
        delete(BARS_5S).where(BARS_5S.c.ts < bar_5s_cutoff),
        delete(BARS_1M_OHLC).where(BARS_1M_OHLC.c.ts < bar_1m_cutoff),
        delete(BARS_1M).where(BARS_1M.c.ts < bar_1m_cutoff),
    ]
    async with session:
        for stmt in statements:
            await session.execute(stmt)
        await session.commit()


__all__ = [
    "insert_raw_messages",
    "insert_timeframe_bars",
    "insert_minute_agg",
    "bulk_insert_rankings",
    "prune_expired_data",
]
