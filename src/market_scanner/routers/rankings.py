"""Rankings router with paging, filters, and Redis-backed snapshots."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from ..config import get_settings
from ..core.metrics import SymbolSnapshot
from ..core.scoring import REJECT_SCORE, score
from ..stores.redis_store import get_latest_snapshots, get_rankings
from ..engines.ai_engine_enhanced import EnhancedAIEngine
from ._helpers import format_flag_objects
from ..data_integrity import (
    is_strict_mode,
    is_permissive_mode,
    exchange_tracker,
    validate_data_source
)

router = APIRouter()

# Initialize AI engine
ai_engine = EnhancedAIEngine()


def generate_ai_analysis(snapshot: SymbolSnapshot) -> dict:
    """Generate AI analysis for a symbol snapshot"""
    try:
        # Prepare market data for AI analysis
        market_data = {
            'symbol': snapshot.symbol,
            'price': snapshot.price if hasattr(snapshot, 'price') else 0.0,
            'volume': snapshot.qvol_usdt,
            'change_24h': snapshot.ret_1 * 100 if snapshot.ret_1 else 0.0,
            'spread': snapshot.spread_bps,
            'volatility': snapshot.atr_pct,
            'liquidity_edge': snapshot.liquidity_edge,
            'momentum_edge': snapshot.momentum_edge,
            'score': snapshot.score
        }
        
        # Generate AI signal
        ai_signal = ai_engine.analyze_market_data_enhanced(market_data)
        
        # Determine bias and action based on score and edges
        if snapshot.score > 0.6:
            bias = "Long"
            action = "BUY"
        elif snapshot.score < -0.6:
            bias = "Short" 
            action = "SELL"
        else:
            bias = "Neutral"
            action = "HOLD"
        
        # Calculate confidence based on score and edges
        confidence = min(abs(snapshot.score) * 100, 95) if snapshot.score != 0 else 50
        
        # Generate price targets using enhanced AI
        price_target, stop_loss = ai_engine._calculate_enhanced_targets(
            market_data['price'], 
            action, 
            confidence, 
            snapshot.atr_pct, 
            market_data
        )
        
        # Generate AI insight
        ai_insight = ai_engine._generate_ai_insight(
            {'pattern_name': 'AI_ANALYSIS', 'description': 'AI-enhanced market analysis'},
            {'opportunity': snapshot.manip_score > 0.7 if snapshot.manip_score else False, 'price_diff_pct': 0.0}
        )
        
        return {
            'price_target': price_target,
            'stop_loss': stop_loss,
            'ai_confidence': confidence,
            'ai_insight': ai_insight,
            'pattern_detected': 'AI_PATTERN',
            'arbitrage_opportunity': snapshot.manip_score > 0.7 if snapshot.manip_score else False,
            'bias': bias,
            'action': action
        }
        
    except Exception as e:
        # Fallback values if AI analysis fails
        import logging
        logging.getLogger(__name__).error(f"AI analysis failed for {snapshot.symbol}: {e}", exc_info=True)
        return {
            'price_target': None,
            'stop_loss': None,
            'ai_confidence': 50.0,
            'ai_insight': 'AI analysis temporarily unavailable',
            'pattern_detected': 'N/A',
            'arbitrage_opportunity': False,
            'bias': 'Neutral',
            'action': 'HOLD'
        }


class RankingQuery(BaseModel):
    top: int = Field(default_factory=lambda: get_settings().topn_default, ge=1, le=200)
    profile: str = Field(default_factory=lambda: get_settings().profile_default)
    min_qvol: float = Field(default_factory=lambda: float(get_settings().min_qvol_usdt), ge=0)
    max_spread_bps: float = Field(default_factory=lambda: float(get_settings().max_spread_bps), ge=0)
    notional: float = Field(default_factory=lambda: float(get_settings().notional_test), ge=1)
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=25, ge=1, le=100)
    include_funding: bool = True
    include_basis: bool = True
    include_carry: bool = True
    max_manip_score: float | None = Field(default=None, ge=0, le=100)
    min_manip_score: float | None = Field(default=None, ge=0, le=100)
    exclude_flags: List[str] = Field(default_factory=list)


class RankingItem(BaseModel):
    """Single ranking row - REQUIRED: exchange field must never be null/empty/defaulted"""
    rank: int = Field(..., description="Ranking position")
    symbol: str = Field(..., description="Trading pair symbol")
    exchange: str = Field(..., description="Exchange name - REQUIRED, never null")
    score: float = Field(..., description="Ranking score")
    bias: str = Field(default="Neutral", description="Trading bias: Long, Short, or Neutral")
    confidence: float = Field(default=50.0, ge=0.0, le=100.0, description="Confidence score 0-100")
    liquidity: float = Field(default=0.0, description="Liquidity metric (liquidity_edge)")
    momentum: float = Field(default=0.0, description="Momentum metric (momentum_edge)")
    spread_bps: float = Field(..., description="Spread in basis points")
    ai_insight: str | None = Field(None, description="AI-generated insight")
    ts: str = Field(..., description="ISO8601 timestamp")

    # Additional fields for compatibility
    qvol_usdt: float | None = None
    atr_pct: float | None = None
    slip_bps: float | None = None
    top5_depth_usdt: float | None = None
    ret_15: float | None = None
    ret15: float | None = None
    ret_1: float | None = None
    ret1: float | None = None
    funding_8h_pct: float | None = None
    open_interest: float | None = None
    basis_bps: float | None = None
    volume_zscore: float | None = None
    order_flow_imbalance: float | None = None
    volatility_regime: float | None = None
    price_velocity: float | None = None
    anomaly_score: float | None = None
    depth_to_volume_ratio: float | None = None
    liquidity_edge: float | None = None
    momentum_edge: float | None = None
    volatility_edge: float | None = None
    microstructure_edge: float | None = None
    anomaly_residual: float | None = None
    manip_score: float | None = None
    manip_flags: list[str] | None = None
    flags: list[dict[str, bool]] = Field(default_factory=list)
    price_target: float | None = None
    stop_loss: float | None = None
    ai_confidence: float | None = None
    pattern_detected: str | None = None
    arbitrage_opportunity: bool = False
    action: str = "HOLD"


class RankingsResponse(BaseModel):
    """Rankings API response with degradation tracking"""
    mode: str = Field(default="live", description="Operating mode")
    degraded: bool = Field(default=False, description="True if partial availability")
    asof: str = Field(..., description="ISO8601 timestamp of data")
    exchanges_ok: List[str] = Field(default_factory=list, description="List of working exchanges")
    rows: list[RankingItem] = Field(default_factory=list, description="Ranking rows")
    error: Optional[str] = Field(None, description="Error code if complete failure")
    detail: Optional[str] = Field(None, description="Error detail message")

    # Legacy fields for backward compatibility
    ts: datetime | None = None
    profile: str | None = None
    filters: dict[str, Any] | None = None
    items: list[RankingItem] | None = None
    page: int | None = None
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
    include_carry: bool = Query(default=True),
    max_manip_score: float | None = Query(default=None, ge=0, le=100),
    min_manip: float | None = Query(default=None, ge=0, le=100),
    exclude_flags: Optional[list[str]] = Query(default=None),
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
    base.include_carry = include_carry
    if max_manip_score is not None:
        base.max_manip_score = max_manip_score
    if min_manip is not None:
        base.min_manip_score = min_manip
    if exclude_flags:
        base.exclude_flags = sorted({flag for flag in exclude_flags if flag})
    return base


def _adjust_snapshot(snapshot: SymbolSnapshot, params: RankingQuery) -> SymbolSnapshot:
    settings = get_settings()
    updates: dict[str, Any] = {}
    if not params.include_funding or not params.include_carry:
        updates["funding_8h_pct"] = None
    if not params.include_basis or not params.include_carry:
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
                    volume_zscore=float(row.get("volume_zscore", 0.0)),
                    order_flow_imbalance=float(row.get("order_flow_imbalance", row.get("imbalance", 0.0))),
                    volatility_regime=float(row.get("volatility_regime", 0.0)),
                    price_velocity=float(row.get("price_velocity", 0.0)),
                    anomaly_score=float(row.get("anomaly_score", 0.0)),
                    depth_to_volume_ratio=float(row.get("depth_to_volume_ratio", row.get("depth_to_volume", 0.0))),
                    liquidity_edge=float(row.get("liquidity_edge", 0.0)),
                    momentum_edge=float(row.get("momentum_edge", 0.0)),
                    volatility_edge=float(row.get("volatility_edge", 0.0)),
                    microstructure_edge=float(row.get("microstructure_edge", 0.0)),
                    anomaly_residual=float(row.get("anomaly_residual", 0.0)),
                    manip_score=row.get("manip_score"),
                    manip_flags=row.get("manip_flags"),
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
        if params.exclude_flags and snapshot.manip_flags:
            if any(flag in params.exclude_flags for flag in snapshot.manip_flags):
                continue
        if (
            params.min_manip_score is not None
            and (snapshot.manip_score is None or snapshot.manip_score < params.min_manip_score)
        ):
            continue
        if (
            params.max_manip_score is not None
            and snapshot.manip_score is not None
            and snapshot.manip_score > params.max_manip_score
        ):
            continue
        snap = _adjust_snapshot(snapshot, params)
        if snap.qvol_usdt < params.min_qvol:
            continue
        if snap.spread_bps > params.max_spread_bps:
            continue
        snap_score = score(snap, profile=params.profile, include_carry=params.include_carry)
        if snap_score <= REJECT_SCORE:
            continue
        scored.append(snap.model_copy(update={"score": snap_score}))
    scored.sort(key=lambda s: s.score or REJECT_SCORE, reverse=True)
    return scored, ts


@router.get("/", response_model=RankingsResponse)
async def get_rankings_endpoint(params: RankingQuery = Depends(_query_params)) -> RankingsResponse:
    ranked, ts = await compute_rankings(params)

    # Filter out rows with missing exchange field (strict mode enforcement)
    original_count = len(ranked)
    valid_rows = []
    dropped_count = 0

    for snap in ranked:
        # REQUIRED: exchange field must never be null/empty/defaulted
        if not hasattr(snap, 'exchange') or not snap.exchange or snap.exchange == "":
            dropped_count += 1
            if is_strict_mode():
                # In strict mode: drop the entire row
                continue

        # In strict mode: also drop rows from mock sources
        if is_strict_mode() and hasattr(snap, 'exchange'):
            if not validate_data_source(snap.exchange):
                dropped_count += 1
                continue

        valid_rows.append(snap)

    # Determine degraded state
    degraded = dropped_count > 0

    # Get working exchanges
    exchanges_ok = exchange_tracker.get_working_exchanges()

    # Pagination
    top_limit = min(params.top, len(valid_rows))
    limited = valid_rows[:top_limit]
    start = (params.page - 1) * params.page_size
    end = start + params.page_size
    paged = limited[start:end]

    # Build ranking items
    items = []
    for rank_idx, snap in enumerate(paged, start=start+1):
        # Generate AI analysis for each signal
        ai_analysis = generate_ai_analysis(snap)

        items.append(RankingItem(
            rank=rank_idx,
            symbol=snap.symbol,
            exchange=snap.exchange,  # REQUIRED field
            score=float(snap.score or 0.0),
            bias=ai_analysis['bias'],
            confidence=ai_analysis['ai_confidence'],
            liquidity=snap.liquidity_edge or 0.0,
            momentum=snap.momentum_edge or 0.0,
            spread_bps=snap.spread_bps,
            ai_insight=ai_analysis['ai_insight'],
            ts=snap.ts.isoformat(),

            # Additional fields for compatibility
            qvol_usdt=snap.qvol_usdt,
            atr_pct=snap.atr_pct,
            slip_bps=snap.slip_bps,
            top5_depth_usdt=snap.top5_depth_usdt,
            ret_15=snap.ret_15,
            ret15=snap.ret_15,
            ret_1=snap.ret_1,
            ret1=snap.ret_1,
            funding_8h_pct=snap.funding_8h_pct,
            open_interest=snap.open_interest,
            basis_bps=snap.basis_bps,
            volume_zscore=snap.volume_zscore,
            order_flow_imbalance=snap.order_flow_imbalance,
            volatility_regime=snap.volatility_regime,
            price_velocity=snap.price_velocity,
            anomaly_score=snap.anomaly_score,
            depth_to_volume_ratio=snap.depth_to_volume_ratio,
            liquidity_edge=snap.liquidity_edge,
            momentum_edge=snap.momentum_edge,
            volatility_edge=snap.volatility_edge,
            microstructure_edge=snap.microstructure_edge,
            anomaly_residual=snap.anomaly_residual,
            manip_score=snap.manip_score,
            manip_flags=snap.manip_flags,
            flags=format_flag_objects(snap.manip_flags),
            price_target=ai_analysis['price_target'],
            stop_loss=ai_analysis['stop_loss'],
            ai_confidence=ai_analysis['ai_confidence'],
            pattern_detected=ai_analysis['pattern_detected'],
            arbitrage_opportunity=ai_analysis['arbitrage_opportunity'],
            action=ai_analysis['action']
        ))
    filters = {
        "min_qvol": params.min_qvol,
        "max_spread_bps": params.max_spread_bps,
        "notional": params.notional,
        "include_funding": params.include_funding,
        "include_basis": params.include_basis,
        "include_carry": params.include_carry,
        "max_manip_score": params.max_manip_score,
        "min_manip_score": params.min_manip_score,
        "exclude_flags": params.exclude_flags,
    }

    # Build response with new data contract
    return RankingsResponse(
        mode="live",
        degraded=degraded,
        asof=ts.isoformat(),
        exchanges_ok=exchanges_ok,
        rows=items,
        error=None,
        detail=f"Dropped {dropped_count} rows due to missing exchange field" if dropped_count > 0 else None,

        # Legacy fields for backward compatibility
        ts=ts,
        profile=params.profile,
        filters=filters,
        items=items,
        page=params.page,
    )











