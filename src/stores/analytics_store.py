"""Read models for charting and analytics panels.""" 
from __future__ import annotations

from typing import Any, List

from sqlalchemy import desc, select

from .pg_store import BAR_TABLES, _get_session


async def fetch_recent_bars(symbol: str, timeframe: str = "1m", limit: int = 60) -> List[dict[str, Any]]:
    table = BAR_TABLES.get(timeframe)
    if table is None:
        return []
    session = await _get_session()
    stmt = select(table).where(table.c.symbol == symbol).order_by(desc(table.c.ts)).limit(limit)
    result = await session.execute(stmt)
    rows = [dict(row._mapping) for row in result.fetchall()]
    rows.reverse()
    return rows
