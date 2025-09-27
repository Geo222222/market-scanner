"""Rankings router with paging, filters, and Redis-backed snapshots."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from ..config import get_settings
from ..core.metrics import SymbolSnapshot
from ..core.scoring import REJECT_SCORE, score
from ..stores.redis_store import get_latest_snapshots, get_rankings

router = APIRouter()


class RankingQuery(BaseModel):
    top: int = Field(default_factory=lambda: get_settings().topn_default, ge=1, le=200)
    profile: str = Field(default_factory=lambda: get_settings().ranking_profile_default)
    min_qvol: float = Field(default_factory=lambda: float(get_settings().min_qvol_usdt), ge=0)
    max_spread_bps: float = Field(default_factory=lambda: float(get_settings().max_spread_bps), ge=0)
    notional: float = Field(default_factory=lambda: float(get_settings().notional_test), ge=1)
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=25, ge=1, le=100)
    include_funding: bool = True
    include_basis: bool = True


class RankingItem(BaseModel):
    symbol: str
    score: float
    qvol_usdt: float
    atr_pct: float
    spread_bps: float
    slip_bps: float
    top5_depth_usdt: float
    ret_15: float
    ret_1: float
    funding_8h_pct: float | None = None
    open_interest: float | None = None
    basis_bps: float | None = None


class RankingsResponse(BaseModel):
    ts: datetime
    profile: str
    filters: dict[str, Any]
    items: list[RankingItem]
    page: int
    page_size: int
    total: int


async def _query_params(
    top: int = Query(default=None, ge=1, le=200),
    profile: str | None = Query(default=None),
    min_qvol: float | None = Query(default=None, ge=0),
    max_spread_bps: float | None = Query(default=None, ge=0),
    notional: float | None = Query(default=None, ge=1),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    include_funding: bool = Query(default=True),
    include_basis: bool = Query(default=True),
) -> RankingQuery:
    base = RankingQuery()
    if top is not None:
        base.top = top
    if profile is not None:
        base.profile = profile
    if min_qvol is not None:
        base.min_qvol = min_qvol
    if max_spread_bps is not None:
        base.max_spread_bps = max_spread_bps
    if notional is not None:
        base.notional = notional
    base.page = page
    base.page_size = page_size
    base.include_funding = include_funding
    base.include_basis = include_basis
    return base


def _adjust_snapshot(snapshot: SymbolSnapshot, params: RankingQuery) -> SymbolSnapshot:
    settings = get_settings()
    updates: dict[str, Any] = {}
    if not params.include_funding:
        updates["funding_8h_pct"] = None
    if not params.include_basis:
        updates["basis_bps"] = None
    if params.notional != settings.notional_test and settings.notional_test > 0:
        ratio = params.notional / settings.notional_test
        updates["slip_bps"] = snapshot.slip_bps * ratio
    if updates:
        return snapshot.model_copy(update=updates)
    return snapshot


async def _load_from_cache(profile: str) -> tuple[list[SymbolSnapshot], datetime] | None:
    cached = await get_rankings(profile)
    if not cached:
        return None
    ts_raw = cached.get("ts")
    rows = cached.get("rows") or []
    if not isinstance(rows, list) or not ts_raw:
        return None
    try:
        ts = datetime.fromisoformat(ts_raw)
    except ValueError:
        ts = datetime.now(timezone.utc)
    snapshots: list[SymbolSnapshot] = []
    for row in rows:
        symbol = row.get("symbol")
        if not symbol:
            continue
        try:
            snapshots.append(
                SymbolSnapshot(
                    symbol=symbol,
                    qvol_usdt=float(row.get("qvol_usdt", 0.0)),
                    spread_bps=float(row.get("spread_bps", 0.0)),
                    top5_depth_usdt=float(row.get("top5_depth_usdt", 0.0)),
                    atr_pct=float(row.get("atr_pct", 0.0)),
                    ret_1=float(row.get("ret_1", 0.0)),
                    ret_15=float(row.get("ret_15", 0.0)),
                    slip_bps=float(row.get("slip_bps", 0.0)),
                    funding_8h_pct=row.get("funding_8h_pct"),
                    open_interest=row.get("open_interest"),
                    basis_bps=row.get("basis_bps"),
                    ts=ts,
                    score=float(row.get("score", 0.0)),
                )
            )
        except Exception:
            continue
    return snapshots, ts


async def compute_rankings(params: RankingQuery) -> tuple[list[SymbolSnapshot], datetime]:
    snapshots = await get_latest_snapshots()
    ts = max((snap.ts for snap in snapshots), default=None)
    if not snapshots:
        cached = await _load_from_cache(params.profile)
        if not cached:
            raise HTTPException(status_code=503, detail="Rankings are currently unavailable")
        snapshots, ts = cached
    ts = ts or datetime.now(timezone.utc)

    scored: list[SymbolSnapshot] = []
    for snapshot in snapshots:
        snap = _adjust_snapshot(snapshot, params)
        if snap.qvol_usdt < params.min_qvol:
            continue
        if snap.spread_bps > params.max_spread_bps:
            continue
        snap_score = score(snap, profile=params.profile)
        if snap_score <= REJECT_SCORE:
            continue
        scored.append(snap.model_copy(update={"score": snap_score}))
    scored.sort(key=lambda s: s.score or REJECT_SCORE, reverse=True)
    return scored, ts


@router.get("/", response_model=RankingsResponse)
async def get_rankings_endpoint(params: RankingQuery = Depends(_query_params)) -> RankingsResponse:
    ranked, ts = await compute_rankings(params)
    top_limit = min(params.top, len(ranked))
    limited = ranked[:top_limit]
    total = len(limited)
    start = (params.page - 1) * params.page_size
    end = start + params.page_size
    paged = limited[start:end]
    items = [
        RankingItem(
            symbol=snap.symbol,
            score=float(snap.score or 0.0),
            qvol_usdt=snap.qvol_usdt,
            atr_pct=snap.atr_pct,
            spread_bps=snap.spread_bps,
            slip_bps=snap.slip_bps,
            top5_depth_usdt=snap.top5_depth_usdt,
            ret_15=snap.ret_15,
            ret_1=snap.ret_1,
            funding_8h_pct=snap.funding_8h_pct,
            open_interest=snap.open_interest,
            basis_bps=snap.basis_bps,
        )
        for snap in paged
    ]
    filters = {
        "min_qvol": params.min_qvol,
        "max_spread_bps": params.max_spread_bps,
        "notional": params.notional,
        "include_funding": params.include_funding,
        "include_basis": params.include_basis,
    }
    return RankingsResponse(
        ts=ts,
        profile=params.profile,
        filters=filters,
        items=items,
        page=params.page,
        page_size=params.page_size,
        total=total,
    )

