"""Opportunities router providing heuristic trade ideas."""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field

from ._helpers import format_flag_objects
from .rankings import RankingQuery, compute_rankings

router = APIRouter()


class OpportunityQuery(BaseModel):
    profile: str = Field(default="scalp")
    top: int = Field(default=12, ge=1, le=100)
    symbol: str | None = Field(default=None, min_length=1, max_length=64)
    notional: float = Field(default=10_000, ge=1)
    include_funding: bool = True
    include_basis: bool = True
    include_carry: bool = True
    max_manip_score: float | None = Field(default=None, ge=0, le=100)
    min_manip_score: float | None = Field(default=None, ge=0, le=100)
    exclude_flags: list[str] = Field(default_factory=list)


class OpportunityItem(BaseModel):
    symbol: str
    score: float
    side_bias: Literal["long", "short", "neutral"]
    entry_zone: dict[str, float | str]
    stop_suggestion: float
    tp_levels: list[float]
    confidence: int
    spread_bps: float
    slip_bps: float
    atr_pct: float
    qvol_usdt: float
    ret_15: float
    ret15: float
    ret_1: float
    ret1: float
    funding_8h_pct: float | None = None
    basis_bps: float | None = None
    manip_score: float | None
    manip_flags: list[str] | None
    flags: list[dict[str, bool]] = Field(default_factory=list)
    ts: datetime


class OpportunityResponse(BaseModel):
    ts: datetime
    profile: str
    notional: float
    items: list[OpportunityItem]
    card: OpportunityItem | None = None


async def _query_params(
    profile: str = Query(default="scalp"),
    top: int = Query(default=12, ge=1, le=100),
    symbol: str | None = Query(default=None),
    notional: float = Query(default=10_000, ge=1),
    include_funding: bool = Query(default=True),
    include_basis: bool = Query(default=True),
    include_carry: bool = Query(default=True),
    max_manip_score: float | None = Query(default=None, ge=0, le=100),
    min_manip: float | None = Query(default=None, ge=0, le=100),
    exclude_flags: list[str] | None = Query(default=None),
) -> OpportunityQuery:
    normalized_symbol = symbol.strip().upper() if symbol else None
    filtered_flags = sorted({flag.strip() for flag in exclude_flags if flag}) if exclude_flags else []
    return OpportunityQuery(
        profile=profile,
        top=top,
        symbol=normalized_symbol,
        notional=notional,
        include_funding=include_funding,
        include_basis=include_basis,
        include_carry=include_carry,
        max_manip_score=max_manip_score,
        min_manip_score=min_manip,
        exclude_flags=[flag for flag in filtered_flags if flag],
    )


def _derive_side(snapshot_score: float, ret_1: float, ret_15: float, funding: float | None) -> Literal["long", "short", "neutral"]:
    long_bias = ret_1 > 0 and ret_15 > 0
    short_bias = ret_1 < 0 and ret_15 < 0
    if snapshot_score < 0:
        return "neutral"
    if long_bias and (funding is None or funding <= 0.05):
        return "long"
    if short_bias and (funding is None or funding >= -0.05):
        return "short"
    return "neutral"


def _entry_zone(bias: str, atr_pct: float) -> dict[str, float | str]:
    window = round(min(max(atr_pct * 0.35, 0.1), 2.5), 3)
    if bias == "long":
        return {"type": "pullback", "pct": window}
    if bias == "short":
        return {"type": "fade", "pct": window}
    return {"type": "breakout", "pct": round(window / 2, 3)}


def _stop_pct(atr_pct: float, spread_bps: float) -> float:
    cushion = spread_bps / 100.0
    return round(max(atr_pct * 1.2, cushion + atr_pct * 0.5), 3)


def _tp_levels(atr_pct: float) -> list[float]:
    base = max(atr_pct, 0.1)
    levels = [round(base * factor, 3) for factor in (0.5, 1.0, 1.5)]
    return levels


def _confidence(score_val: float, spread_bps: float, slip_bps: float, manip_score: float | None, anomaly_score: float, ofi_abs: float) -> int:
    base = max(0.0, min(100.0, (score_val / 2) + 50))
    cost_penalty = min(40.0, spread_bps + slip_bps)
    manip_penalty = min(50.0, (manip_score or 0.0) * 0.6)
    structure_penalty = min(30.0, anomaly_score * 0.5 + ofi_abs * 50.0)
    confidence = base - cost_penalty - manip_penalty - structure_penalty
    return int(max(0.0, min(100.0, confidence)))


@router.get("/", response_model=OpportunityResponse)
async def get_opportunities(params: OpportunityQuery = Depends(_query_params)) -> OpportunityResponse:
    ranking_params = RankingQuery(
        top=params.top,
        profile=params.profile,
        notional=params.notional,
        include_funding=params.include_funding,
        include_basis=params.include_basis,
        include_carry=params.include_carry,
        max_manip_score=params.max_manip_score,
        min_manip_score=params.min_manip_score,
        exclude_flags=params.exclude_flags,
        page=1,
        page_size=params.top,
    )
    ranked, ts = await compute_rankings(ranking_params)
    symbol_key = params.symbol.upper() if params.symbol else None

    def build_item(snap) -> OpportunityItem:
        score_val = float(snap.score or 0.0)
        bias = _derive_side(score_val, snap.ret_1, snap.ret_15, snap.funding_8h_pct)
        entry = _entry_zone(bias, snap.atr_pct)
        stop = _stop_pct(snap.atr_pct, snap.spread_bps)
        tps = _tp_levels(snap.atr_pct)
        confidence = _confidence(
            score_val,
            snap.spread_bps,
            snap.slip_bps,
            snap.manip_score,
            snap.anomaly_score,
            abs(snap.order_flow_imbalance),
        )
        return OpportunityItem(
            symbol=snap.symbol,
            score=score_val,
            side_bias=bias,
            entry_zone=entry,
            stop_suggestion=stop,
            tp_levels=tps,
            confidence=confidence,
            spread_bps=snap.spread_bps,
            slip_bps=snap.slip_bps,
            atr_pct=snap.atr_pct,
            qvol_usdt=snap.qvol_usdt,
            ret_15=snap.ret_15,
            ret15=snap.ret_15,
            ret_1=snap.ret_1,
            ret1=snap.ret_1,
            funding_8h_pct=snap.funding_8h_pct,
            basis_bps=snap.basis_bps,
            manip_score=snap.manip_score,
            manip_flags=snap.manip_flags,
            flags=format_flag_objects(snap.manip_flags),
            ts=snap.ts,
        )

    limited = ranked[: params.top]
    items: list[OpportunityItem] = []
    card_item: OpportunityItem | None = None
    for snap in limited:
        item = build_item(snap)
        items.append(item)
        if symbol_key and snap.symbol.upper() == symbol_key:
            card_item = item
    if symbol_key and card_item is None:
        for snap in ranked:
            if snap.symbol.upper() == symbol_key:
                card_item = build_item(snap)
                break
    return OpportunityResponse(
        ts=ts,
        profile=params.profile,
        notional=params.notional,
        items=items,
        card=card_item,
    )









