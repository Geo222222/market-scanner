"""Background scanning loop that orchestrates data collection, scoring, and streaming."""
from __future__ import annotations

import asyncio
import json
import logging
import time
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Mapping, Optional

from ..adapters.ccxt_adapter import AdapterError, CCXTAdapter
from ..config import get_settings
from ..data_integrity import is_strict_mode, is_permissive_mode, log_data_error
from ..core.metrics import (
    SymbolSnapshot,
    atr_pct,
    basis_bp,
    closes_from_ohlcv,
    estimate_slippage_bps,
    funding_8h_pct,
    latest_volume_usdt,
    order_flow_imbalance,
    price_velocity,
    pump_dump_score,
    quote_volume_usdt,
    returns,
    spread_bps,
    top5_depth_usdt,
    volume_zscore,
    volatility_regime,
)
from ..core.factors import enrich_cross_sectional
from ..core.scoring import rank, score_with_breakdown
from ..engine.alerts import get_signal_bus
from ..engine.execution import queue_position_estimate, simulated_impact, spread_history_update
from ..engine.microstructure import compute_microstructure_features
from ..engine.momentum import assemble_momentum_snapshot
from ..engine.runtime import get_manipulation_threshold, get_notional_override
from ..engine.streaming import RankingFrame, RankingSymbolFrame, get_ranking_broadcast
from ..manip.detector import detect_manipulation
from ..observability import record_cycle
from ..stores.pg_store import bulk_insert_rankings, insert_minute_agg
from ..stores.redis_store import cache_rankings, cache_snapshots
from ..engines.ai_engine_enhanced import EnhancedAIEngine

LOGGER = logging.getLogger(__name__)

_MARKETS_CACHE: dict[str, Any] = {}
_MARKETS_TS: float | None = None
_LATEST_BUNDLES: dict[str, "SnapshotBundle"] = {}
_PREVIOUS_RANKS: dict[str, int] = {}
_SPREAD_HISTORY: dict[str, list[float]] = defaultdict(list)

# Initialize AI engine for autonomous analysis
_AI_ENGINE = EnhancedAIEngine()

# Initialize pause event to unpaused (set = unpaused, clear = paused)
_PAUSE_EVENT = asyncio.Event()
_PAUSE_EVENT.set()

_FORCE_EVENT = asyncio.Event()

_HEALTH_STATE: dict[str, Any] = {
    "last_cycle_ms": 0.0,
    "last_success": None,
    "last_error": None,
    "failure_streak": 0,
    "cycle_count": 0,
    "backoff_sec": 0.0,
    "adapter": {
        "exchange": get_settings().exchange,
        "state": "idle",
        "fail_count": 0,
        "cooldown_remaining": 0.0,
        "threshold": get_settings().adapter_max_failures,
    },
    "target_cycle_ms": get_settings().scan_interval_sec * 1000,
    "sla": {
        "warn": get_settings().scan_sla_warn_multiplier,
        "critical": get_settings().scan_sla_critical_multiplier,
    },
    "cycle_history_ms": [],
    "control": {},
    "symbols": {},
}

_CONTROL_AUDIT: deque[dict[str, Any]] = deque(maxlen=200)
_CONTROL_STATE: dict[str, Any] = {
    "paused": False,
    "breaker": {
        "manual_state": "closed",
        "last_reason": None,
        "updated_at": None,
    },
}

def _snapshot_control_state() -> dict[str, Any]:
    return {
        "paused": _CONTROL_STATE.get("paused", False),
        "breaker": dict(_CONTROL_STATE.get("breaker", {})),
        "audit": list(_CONTROL_AUDIT)[-20:],
    }


def get_control_state() -> dict[str, Any]:
    return json.loads(json.dumps(_snapshot_control_state()))


def _log_control_event(action: str, actor: str, detail: Optional[dict[str, Any]] = None) -> None:
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "action": action,
        "actor": actor,
        "detail": detail or {},
    }
    _CONTROL_AUDIT.append(entry)
    _HEALTH_STATE["control"] = _snapshot_control_state()


_HEALTH_STATE["control"] = _snapshot_control_state()


async def request_force_scan(actor: str = "system", reason: Optional[str] = None) -> dict[str, Any]:
    if not _PAUSE_EVENT.is_set():
        return {"queued": False, "reason": "paused"}
    _FORCE_EVENT.set()
    _log_control_event("force_scan_requested", actor, {"reason": reason})
    return {"queued": True}


async def pause_scanner(actor: str = "system", reason: Optional[str] = None) -> dict[str, Any]:
    if not _PAUSE_EVENT.is_set():
        return {"paused": True}
    _PAUSE_EVENT.clear()
    _CONTROL_STATE["paused"] = True
    _log_control_event("paused", actor, {"reason": reason})
    return {"paused": True}


async def resume_scanner(actor: str = "system", reason: Optional[str] = None) -> dict[str, Any]:
    if _PAUSE_EVENT.is_set():
        return {"paused": False}
    _PAUSE_EVENT.set()
    _CONTROL_STATE["paused"] = False
    _log_control_event("resumed", actor, {"reason": reason})
    return {"paused": False}


def set_manual_breaker(state: str, actor: str = "system", reason: Optional[str] = None) -> dict[str, Any]:
    state = state.lower()
    if state not in {"open", "closed"}:
        raise ValueError("Breaker state must be 'open' or 'closed'")
    _CONTROL_STATE["breaker"] = {
        "manual_state": state,
        "last_reason": reason,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    _log_control_event("breaker_" + state, actor, {"reason": reason})
    return _CONTROL_STATE["breaker"]


@dataclass
class SnapshotBundle:
    snapshot: SymbolSnapshot
    close: float
    manip_features: dict[str, float]
    ticker: dict[str, Any]
    orderbook: dict[str, Any]
    momentum: dict[str, float]
    micro_features: dict[str, Any]
    execution: dict[str, float]
    trades: list[dict[str, Any]]
    fetch_latency_ms: float


def _chunk(symbols: list[str], size: int) -> list[list[str]]:
    return [symbols[i : i + size] for i in range(0, len(symbols), max(1, size))]


def _is_usdt_perp(data: Mapping[str, Any]) -> bool:
    if not (data.get("swap") or data.get("contract") or data.get("type") == "swap"):
        return False
    settle = str(data.get("settle") or data.get("quote") or "").upper()
    if settle and settle != "USDT":
        return False
    if data.get("linear") is False:
        return False
    contract_type = str(data.get("info", {}).get("contractType", "")).lower()
    if contract_type and "swap" not in contract_type:
        return False
    return True


async def _load_symbols(adapter: CCXTAdapter) -> list[str]:
    global _MARKETS_CACHE, _MARKETS_TS
    settings = get_settings()
    LOGGER.info(f"DEBUG: settings.symbols = {settings.symbols}")
    allow_list = [sym.strip() for sym in settings.symbols if str(sym).strip()]
    LOGGER.info(f"DEBUG: allow_list = {allow_list}")
    if allow_list:
        return allow_list

    now = time.time()
    if not _MARKETS_CACHE or _MARKETS_TS is None or now - _MARKETS_TS > settings.markets_cache_ttl_sec:
        LOGGER.info("DEBUG: Loading markets from exchange...")
        markets = await adapter.load_markets()
        filtered = {sym: data for sym, data in markets.items() if _is_usdt_perp(data)}
        _MARKETS_CACHE = filtered
        _MARKETS_TS = now
        LOGGER.info(f"DEBUG: Loaded {len(_MARKETS_CACHE)} USDT perp markets")
    result = [sym for sym, data in _MARKETS_CACHE.items() if data.get("active", True)]
    LOGGER.info(f"DEBUG: Returning {len(result)} active symbols")
    return result


def _extract_spot_reference(ticker: Mapping[str, Any]) -> float | None:
    info = ticker.get("info") or {}
    if isinstance(info, Mapping):
        for key in ("indexPrice", "index_price", "markPrice", "mark_price", "spotPrice"):
            if key in info:
                try:
                    return float(info[key])
                except (TypeError, ValueError):
                    continue
    if "indexPrice" in ticker:
        try:
            return float(ticker["indexPrice"])
        except (TypeError, ValueError):
            return None
    return None


async def _build_snapshot(adapter: CCXTAdapter, symbol: str) -> SnapshotBundle | None:
    settings = get_settings()
    notional = get_notional_override() or settings.notional_test
    fetch_started = time.perf_counter()
    try:
        LOGGER.debug(f"Fetching data for {symbol}...")
        ticker_task = adapter.fetch_ticker(symbol)
        orderbook_task = adapter.fetch_order_book(symbol, limit=50)
        ohlcv_task = adapter.fetch_ohlcv(symbol, settings.timeframe, 200)
        ticker, orderbook, ohlcv = await asyncio.gather(ticker_task, orderbook_task, ohlcv_task)
        LOGGER.debug(f"✅ Successfully fetched data for {symbol}")
    except AdapterError as exc:
        LOGGER.error(f"❌ Adapter fetch failed for {symbol}: {exc}")
        return None
    except Exception as exc:
        LOGGER.error(f"❌ Unexpected fetch error for {symbol}: {exc}")
        return None
    fetch_latency_ms = (time.perf_counter() - fetch_started) * 1000

    trades: list[dict[str, Any]] = []
    try:
        trades = await adapter.fetch_trades(symbol, limit=200)
    except AdapterError as exc:  # pragma: no cover - depends on exchange
        LOGGER.debug("Trades fetch failed for %s: %s", symbol, exc)
    except Exception as exc:  # pragma: no cover - defensive
        LOGGER.debug("Unexpected trades fetch failure for %s: %s", symbol, exc)

    funding = None
    open_interest = None
    fund_res, oi_res = await asyncio.gather(
        adapter.fetch_funding_rate(symbol),
        adapter.fetch_open_interest(symbol),
        return_exceptions=True,
    )
    if not isinstance(fund_res, Exception):
        funding = fund_res
    if not isinstance(oi_res, Exception):
        open_interest = oi_res

    bid = ticker.get("bid") or (orderbook.get("bids") or [[None]])[0][0]
    ask = ticker.get("ask") or (orderbook.get("asks") or [[None]])[0][0]
    qvol = quote_volume_usdt(ticker)
    depth = top5_depth_usdt(orderbook)
    
    # AI-Enhanced metrics calculation
    ai_metrics = _calculate_ai_enhanced_metrics({
        'ohlcv': ohlcv,
        'orderbook': orderbook,
        'ticker': ticker,
        'trades': trades,
        'closes': closes_from_ohlcv(ohlcv)
    }, _AI_ENGINE)
    
    atr = ai_metrics['atr_pct']
    closes = closes_from_ohlcv(ohlcv)
    close_price = closes[-1] if closes else float(ticker.get("last") or 0.0)
    bar_volume_usdt = latest_volume_usdt(ohlcv, close_price)
    depth_to_volume = (depth / bar_volume_usdt) if bar_volume_usdt > 0 else 0.0
    momentum = returns(closes, lookback=15)
    slip = estimate_slippage_bps(orderbook, notional, side="both")
    funding_pct = funding_8h_pct((funding or {}).get("fundingRate") if funding else None)

    oi_value = None
    if open_interest:
        try:
            oi_value = float(open_interest.get("openInterest"))
        except (TypeError, ValueError):
            oi_value = None
    basis = basis_bp(ticker.get("last"), _extract_spot_reference(ticker))
    volume_z = ai_metrics['volume_zscore']
    vol_reg = ai_metrics['volatility_regime']
    velocity = ai_metrics['price_velocity']
    ofi = ai_metrics['order_flow_imbalance']
    pump_score = ai_metrics['pump_dump_score']
    ts = datetime.now(timezone.utc)

    manip_result = detect_manipulation(
        symbol=symbol,
        orderbook=orderbook,
        ohlcv=ohlcv,
        close_price=close_price,
        atr_pct_val=atr,
        ret_1=momentum["ret_1"],
        ret_15=momentum["ret_15"],
        funding_rate=funding_pct,
        open_interest=oi_value,
        timestamp=ts.timestamp(),
    )

    snapshot = SymbolSnapshot(
        symbol=symbol,
        exchange=adapter.exchange_id,  # REQUIRED: Exchange name from adapter
        qvol_usdt=qvol,
        spread_bps=ai_metrics['spread_bps'],
        top5_depth_usdt=depth,
        atr_pct=atr,
        ret_1=momentum["ret_1"],
        ret_15=momentum["ret_15"],
        slip_bps=slip,
        funding_8h_pct=funding_pct,
        open_interest=oi_value,
        basis_bps=basis,
        volume_zscore=volume_z,
        order_flow_imbalance=ofi,
        volatility_regime=vol_reg,
        price_velocity=velocity,
        anomaly_score=pump_score,
        depth_to_volume_ratio=depth_to_volume,
        manip_score=manip_result.score,
        manip_flags=manip_result.flags or None,
        ts=ts,
    )

    momentum_metrics = assemble_momentum_snapshot(closes, ohlcv, velocity, close_price)
    snapshot = snapshot.model_copy(
        update={
            "z_15s": momentum_metrics.get("z_15s", 0.0),
            "z_1m": momentum_metrics.get("z_1m", 0.0),
            "z_5m": momentum_metrics.get("z_5m", 0.0),
            "vwap_distance": momentum_metrics.get("vwap_distance", 0.0),
            "rsi14": momentum_metrics.get("rsi14", 50.0),
        }
    )

    micro_features, micro_telemetry = compute_microstructure_features(
        symbol,
        snapshot,
        notional,
    )

    execution_metrics = {
        "queue_position": queue_position_estimate(orderbook, notional),
        "simulated_impact_bps": simulated_impact(orderbook, notional),
    }

    _SPREAD_HISTORY[symbol] = spread_history_update(_SPREAD_HISTORY[symbol], ai_metrics['spread_bps'])

    bundle = SnapshotBundle(
        snapshot=snapshot,
        close=close_price,
        manip_features=manip_result.features,
        ticker=ticker,
        orderbook=orderbook,
        momentum=momentum_metrics,
        micro_features={
            "depth_decay": micro_features.depth_decay,
            "trade_imbalance": micro_features.trade_imbalance,
            "spoof_unwind": micro_features.spoof_unwind,
            "passive_absorption": micro_features.passive_absorption,
            "pump_signature": micro_features.pump_signature,
            "dump_signature": micro_features.dump_signature,
            "volatility_bucket": micro_features.volatility_bucket,
            **micro_telemetry,
        },
        execution=execution_metrics,
        trades=trades,
        fetch_latency_ms=fetch_latency_ms,
    )
    return bundle


async def _collect_snapshots(adapter: CCXTAdapter, symbols: list[str]) -> list[SnapshotBundle]:
    settings = get_settings()
    bundles: list[SnapshotBundle] = []
    for chunk in _chunk(symbols, settings.scan_concurrency):
        tasks = [_build_snapshot(adapter, sym) for sym in chunk]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for sym, res in zip(chunk, results):
            if isinstance(res, Exception):
                LOGGER.debug("Snapshot exception for %s: %s", sym, res)
                continue
            if res is None:
                continue
            bundles.append(res)
    if bundles:
        enriched = enrich_cross_sectional([bundle.snapshot for bundle in bundles])
        for bundle, snap in zip(bundles, enriched):
            bundle.snapshot = snap
    return bundles


def _build_ranking_rows(bundles: list[SnapshotBundle]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for bundle in bundles:
        snap = bundle.snapshot
        # Generate AI analysis for each snapshot
        ai_analysis = _generate_ai_analysis(snap)
        
        rows.append(
            {
                "symbol": snap.symbol,
                "score": snap.score,
                "qvol_usdt": snap.qvol_usdt,
                "atr_pct": snap.atr_pct,
                "spread_bps": snap.spread_bps,
                "slip_bps": snap.slip_bps,
                "top5_depth_usdt": snap.top5_depth_usdt,
                "ret_15": snap.ret_15,
                "ret_1": snap.ret_1,
                "funding_8h_pct": snap.funding_8h_pct,
                "open_interest": snap.open_interest,
                "basis_bps": snap.basis_bps,
                "volume_zscore": snap.volume_zscore,
                "order_flow_imbalance": snap.order_flow_imbalance,
                "volatility_regime": snap.volatility_regime,
                "price_velocity": snap.price_velocity,
                "anomaly_score": snap.anomaly_score,
                "depth_to_volume_ratio": snap.depth_to_volume_ratio,
                "liquidity_edge": snap.liquidity_edge,
                "momentum_edge": snap.momentum_edge,
                "volatility_edge": snap.volatility_edge,
                "microstructure_edge": snap.microstructure_edge,
                "anomaly_residual": snap.anomaly_residual,
                "z_15s": snap.z_15s,
                "z_1m": snap.z_1m,
                "z_5m": snap.z_5m,
                "vwap_distance": snap.vwap_distance,
                "rsi14": snap.rsi14,
                "manip_score": snap.manip_score,
                "manip_flags": snap.manip_flags,
                # Real-time price data
                "price": bundle.close,
                # AI-generated fields
                "price_target": ai_analysis.get('price_target'),
                "stop_loss": ai_analysis.get('stop_loss'),
                "ai_confidence": ai_analysis.get('ai_confidence'),
                "ai_insight": ai_analysis.get('ai_insight'),
                "pattern_detected": ai_analysis.get('pattern_detected'),
                "arbitrage_opportunity": ai_analysis.get('arbitrage_opportunity'),
                "bias": ai_analysis.get('bias'),
                "action": ai_analysis.get('action'),
                "confidence": ai_analysis.get('ai_confidence'),
                "change_24h": snap.ret_1 * 100 if snap.ret_1 else 0.0,
            }
        )
    return rows

def _generate_ai_analysis(snapshot: SymbolSnapshot) -> dict:
    """Generate AI analysis for a symbol snapshot"""
    try:
        market_data = {
            'symbol': snapshot.symbol,
            'price': snapshot.qvol_usdt / 1000000 if snapshot.qvol_usdt > 0 else 50000,  # Estimate price from volume
            'volume': snapshot.qvol_usdt,
            'change_24h': snapshot.ret_1 * 100 if snapshot.ret_1 else 0.0,
            'spread': snapshot.spread_bps,
            'volatility': snapshot.atr_pct,
            'liquidity_edge': snapshot.liquidity_edge,
            'momentum_edge': snapshot.momentum_edge,
            'score': snapshot.score,
            'rsi': snapshot.rsi14,
            'atr_pct': snapshot.atr_pct,
            'ret_1': snapshot.ret_1,
            'ret_15': snapshot.ret_15,
            'avg_volume': snapshot.qvol_usdt * 0.8,  # Estimate average volume
            'high_24h': snapshot.qvol_usdt / 1000000 * 1.02 if snapshot.qvol_usdt > 0 else 50000,
            'low_24h': snapshot.qvol_usdt / 1000000 * 0.98 if snapshot.qvol_usdt > 0 else 50000,
        }
        
        # Generate AI signal
        ai_signal = _AI_ENGINE.analyze_market_data_enhanced(market_data)
        
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
        
        confidence = min(abs(snapshot.score) * 100, 95) if snapshot.score != 0 else 50
        
        # Calculate price targets using AI engine
        price_target, stop_loss = _AI_ENGINE._calculate_enhanced_targets(
            market_data['price'], 
            action, 
            confidence, 
            snapshot.atr_pct, 
            market_data
        )
        
        # Generate AI insight
        ai_insight = _AI_ENGINE._generate_ai_insight(
            {'pattern_name': ai_signal.pattern_detected}, 
            snapshot.manip_score > 0.5 if snapshot.manip_score else False
        )
        
        return {
            'price_target': price_target,
            'stop_loss': stop_loss,
            'ai_confidence': confidence,
            'ai_insight': ai_insight,
            'pattern_detected': ai_signal.pattern_detected,
            'arbitrage_opportunity': ai_signal.arbitrage_opportunity,
            'bias': bias,
            'action': action
        }
        
    except Exception as e:
        LOGGER.warning(f"AI analysis failed for {snapshot.symbol}: {e}")
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

async def _generate_level2_analysis(bundles: list[SnapshotBundle]) -> None:
    """Generate Level 2 analysis for top symbols"""
    try:
        # In strict mode, skip Level 2 analysis if we don't have real data
        if is_strict_mode():
            LOGGER.info("STRICT MODE: Skipping Level 2 analysis (no real orderbook data available)")
            return

        # Only generate mock Level 2 data in permissive mode
        if is_permissive_mode():
            for bundle in bundles:
                symbol = bundle.snapshot.symbol

                # Generate mock Level 2 data (only in permissive mode)
                level2_data = _generate_mock_level2_data(symbol, bundle.snapshot)

                # Analyze with AI engine
                analysis = _AI_ENGINE.analyze_level2_data(level2_data)

                # Cache Level 2 analysis (you can implement caching as needed)
                LOGGER.debug(f"PERMISSIVE MODE: Level 2 analysis for {symbol}: {analysis.get('confidence', 0):.2f} confidence")

    except Exception as e:
        LOGGER.warning(f"Level 2 analysis failed: {e}")

async def _collect_training_data(bundles: list[SnapshotBundle]) -> None:
    """Collect data for ML training"""
    try:
        for bundle in bundles:
            training_sample = {
                'symbol': bundle.snapshot.symbol,
                'timestamp': bundle.snapshot.ts.isoformat(),
                'price': bundle.close,
                'volume': bundle.snapshot.qvol_usdt,
                'spread': bundle.snapshot.spread_bps,
                'volatility': bundle.snapshot.atr_pct,
                'momentum': bundle.snapshot.ret_1,
                'liquidity': bundle.snapshot.liquidity_edge,
                'score': bundle.snapshot.score,
                'rsi': bundle.snapshot.rsi14,
                'atr_pct': bundle.snapshot.atr_pct,
                'ret_1': bundle.snapshot.ret_1,
                'ret_15': bundle.snapshot.ret_15,
                'funding_rate': bundle.snapshot.funding_8h_pct,
                'open_interest': bundle.snapshot.open_interest,
                'pattern_detected': getattr(bundle.snapshot, 'pattern_detected', 'N/A'),
                'action': getattr(bundle.snapshot, 'action', 'HOLD'),
                'avg_volume': bundle.snapshot.qvol_usdt * 0.8,  # Estimate
                'high_24h': bundle.close * 1.02,  # Estimate
                'low_24h': bundle.close * 0.98,  # Estimate
            }
            
            # Add to AI engine learning data
            _AI_ENGINE.add_training_sample(training_sample)
            
    except Exception as e:
        LOGGER.warning(f"Training data collection failed: {e}")

def _generate_mock_level2_data(symbol: str, snapshot: SymbolSnapshot) -> "Level2Data":
    """Generate mock Level 2 data for analysis"""
    from ..engines.ai_engine_enhanced import Level2Data
    import random
    
    # Base price estimation
    base_price = snapshot.qvol_usdt / 1000000 if snapshot.qvol_usdt > 0 else 50000
    spread = base_price * 0.0001  # 0.01% spread
    mid_price = base_price
    
    # Generate bids (buy orders)
    bids = []
    for i in range(15):
        price = mid_price - (i + 1) * spread * random.uniform(0.8, 1.2)
        volume = random.uniform(50, 2000)
        bids.append((price, volume))
    
    # Generate asks (sell orders)
    asks = []
    for i in range(15):
        price = mid_price + (i + 1) * spread * random.uniform(0.8, 1.2)
        volume = random.uniform(50, 2000)
        asks.append((price, volume))
    
    # Calculate derived metrics
    bid_volumes = [bid[1] for bid in bids]
    ask_volumes = [ask[1] for ask in asks]
    total_bid_volume = sum(bid_volumes)
    total_ask_volume = sum(ask_volumes)
    
    volume_imbalance = (total_bid_volume - total_ask_volume) / (total_bid_volume + total_ask_volume) if (total_bid_volume + total_ask_volume) > 0 else 0
    
    return Level2Data(
        symbol=symbol,
        timestamp=datetime.now(timezone.utc),
        bids=bids,
        asks=asks,
        spread=spread,
        mid_price=mid_price,
        volume_imbalance=volume_imbalance,
        order_flow_pressure=random.uniform(-1, 1),
        market_maker_activity=random.uniform(0, 1)
    )

def _calculate_ai_enhanced_metrics(market_data: dict, ai_engine: EnhancedAIEngine) -> dict:
    """Calculate all metrics using AI-enhanced algorithms"""
    try:
        ohlcv = market_data['ohlcv']
        orderbook = market_data['orderbook']
        ticker = market_data['ticker']
        trades = market_data.get('trades', [])
        
        # AI-Enhanced ATR calculation
        atr_ai = ai_engine._calculate_ai_atr(ohlcv)
        
        # AI-Enhanced spread analysis
        spread_ai = ai_engine._calculate_ai_spread(orderbook, ticker)
        
        # AI-Enhanced volume analysis
        volume_ai = ai_engine._calculate_ai_volume_metrics(ohlcv, ticker)
        
        # AI-Enhanced volatility regime detection
        volatility_ai = ai_engine._detect_volatility_pattern(ohlcv)
        
        # AI-Enhanced order flow analysis
        order_flow_ai = ai_engine._analyze_ai_order_flow(orderbook, trades)
        
        # AI-Enhanced pump/dump detection
        # Convert volatility regime string to numeric value
        vol_regime_value = 0.0
        if volatility_ai['regime'] == 'high_volatility':
            vol_regime_value = 2.0
        elif volatility_ai['regime'] == 'low_volatility':
            vol_regime_value = -2.0
        
        pump_dump_ai = ai_engine._detect_ai_pump_dump({
            'ret_15': market_data.get('ret_15', 0),
            'ret_1': market_data.get('ret_1', 0),
            'volume_zscore': volume_ai['zscore'],
            'volatility_regime': vol_regime_value
        })
        
        return {
            'atr_pct': atr_ai,
            'spread_bps': spread_ai,
            'volume_zscore': volume_ai['zscore'],
            'volatility_regime': vol_regime_value,
            'order_flow_imbalance': order_flow_ai['imbalance'],
            'price_velocity': order_flow_ai['velocity'],
            'pump_dump_score': pump_dump_ai,
            'ai_confidence': {
                'atr': volatility_ai['confidence'],
                'spread': 0.8,  # Default confidence for spread
                'volume': volume_ai['confidence'],
                'order_flow': order_flow_ai['confidence']
            }
        }
        
    except Exception as e:
        LOGGER.warning(f"AI-enhanced metrics calculation failed: {e}")
        # Fallback to traditional calculations
        return {
            'atr_pct': atr_pct(market_data['ohlcv']),
            'spread_bps': spread_bps(
                ticker.get("bid") or (orderbook.get("bids") or [[None]])[0][0],
                ticker.get("ask") or (orderbook.get("asks") or [[None]])[0][0]
            ),
            'volume_zscore': volume_zscore(market_data['ohlcv']),
            'volatility_regime': volatility_regime(market_data['closes']),
            'order_flow_imbalance': order_flow_imbalance(orderbook),
            'price_velocity': price_velocity(market_data['closes']),
            'pump_dump_score': 0.0,
            'ai_confidence': {'atr': 0.5, 'spread': 0.5, 'volume': 0.5, 'order_flow': 0.5}
        }

async def run_cycle(profile: str) -> tuple[list[SnapshotBundle], list[SymbolSnapshot], dict[str, Any]]:
    settings = get_settings()
    adapter_state: dict[str, Any] = _HEALTH_STATE.get("adapter", {})
    async with CCXTAdapter() as adapter:
        symbols = await _load_symbols(adapter)
        adapter_state = adapter.snapshot_state()
        if not symbols:
            LOGGER.warning("No active perp symbols discovered; skipping cycle.")
            return [], [], adapter_state
        bundles = await _collect_snapshots(adapter, symbols)
        adapter_state = adapter.snapshot_state()
    if not bundles:
        return [], [], adapter_state

    bundles.sort(key=lambda b: b.snapshot.qvol_usdt, reverse=True)
    top_universe = bundles[: settings.scan_top_by_qvol]
    snapshots = [b.snapshot for b in top_universe]
    ranked = rank(snapshots, top=settings.topn_default, profile=profile)
    return top_universe, ranked, adapter_state


async def loop(stop_event: asyncio.Event | None = None) -> None:
    settings = get_settings()
    profile = settings.profile_default
    failure_streak = 0
    broadcast = get_ranking_broadcast()
    signal_bus = get_signal_bus()

    while True:
        await _PAUSE_EVENT.wait()
        started = time.perf_counter()
        bundles: list[SnapshotBundle] = []
        ranked: list[SymbolSnapshot] = []
        errors = 0
        adapter_state: dict[str, Any] | None = None

        if _CONTROL_STATE.get("breaker", {}).get("manual_state") == "open":
            _HEALTH_STATE.update(
                {
                    "last_error": _CONTROL_STATE.get("breaker", {}).get("last_reason")
                    or "Manual circuit breaker open",
                    "failure_streak": failure_streak,
                    "cycle_count": _HEALTH_STATE.get("cycle_count", 0),
                    "control": _snapshot_control_state(),
                }
            )
            if stop_event and stop_event.is_set():
                return
            try:
                await asyncio.wait_for(_FORCE_EVENT.wait(), timeout=settings.scan_interval_sec)
                _FORCE_EVENT.clear()
            except asyncio.TimeoutError:
                pass
            continue
        try:
            bundles, ranked, adapter_state = await run_cycle(profile)
            failure_streak = 0
            _HEALTH_STATE["backoff_sec"] = 0.0
        except AdapterError as exc:
            failure_streak += 1
            errors = 1
            wait = min(settings.scan_interval_sec * (2**failure_streak), 300)
            LOGGER.warning("Scan cycle failed (%s). Backing off for %.1fs", exc, wait)
            record_cycle(0.0, 0, 0, errors)
            _HEALTH_STATE.update({
                "last_error": str(exc),
                "failure_streak": failure_streak,
                "backoff_sec": wait,
                "cycle_count": _HEALTH_STATE.get("cycle_count", 0),
                "control": _snapshot_control_state(),
            })
            await asyncio.sleep(wait)
            if stop_event and stop_event.is_set():
                return
            continue
        except Exception as exc:  # pragma: no cover - defensive
            failure_streak += 1
            errors = 1
            wait = min(settings.scan_interval_sec * (2**failure_streak), 300)
            LOGGER.exception("Unexpected scan error: %s", exc)
            record_cycle(0.0, 0, 0, errors)
            _HEALTH_STATE.update({
                "last_error": str(exc),
                "failure_streak": failure_streak,
                "backoff_sec": wait,
                "cycle_count": _HEALTH_STATE.get("cycle_count", 0),
                "control": _snapshot_control_state(),
            })
            await asyncio.sleep(wait)
            if stop_event and stop_event.is_set():
                return
            continue

        ts_dt = datetime.now(timezone.utc)
        ts_iso = ts_dt.isoformat()
        await cache_snapshots([bundle.snapshot for bundle in bundles])
        rows = _build_ranking_rows(bundles)
        await cache_rankings(profile, rows, ts_iso)
        
        # Generate Level 2 analysis for top symbols
        await _generate_level2_analysis(bundles[:5])  # Top 5 symbols
        
        # Collect training data for ML models
        await _collect_training_data(bundles)

        for bundle in bundles:
            try:
                await insert_minute_agg(bundle.snapshot, bundle.close)
            except Exception as exc:  # pragma: no cover - persistence issues
                LOGGER.warning("insert_minute_agg failed for %s: %s", bundle.snapshot.symbol, exc)
        try:
            await bulk_insert_rankings(ts_dt, profile, rows)
        except Exception as exc:  # pragma: no cover - persistence issues
            LOGGER.warning("bulk_insert_rankings failed: %s", exc)

        duration = (time.perf_counter() - started) * 1000
        record_cycle(duration / 1000, len(bundles), len(ranked), errors)

        history = _HEALTH_STATE.get("cycle_history_ms")
        if isinstance(history, list):
            history.append(duration)
            if len(history) > 120:
                del history[: len(history) - 120]

        market_gauge = sum(bundle.snapshot.atr_pct for bundle in bundles) / max(len(bundles), 1)
        volatility_bucket = "low"
        if market_gauge > 3:
            volatility_bucket = "high"
        elif market_gauge > 1.5:
            volatility_bucket = "medium"

        bundle_map = {bundle.snapshot.symbol: bundle for bundle in bundles}
        for bundle in bundles:
            _LATEST_BUNDLES[bundle.snapshot.symbol] = bundle

        manipulation_threshold = get_manipulation_threshold()
        items: list[RankingSymbolFrame] = []
        for rank_index, snap in enumerate(ranked, start=1):
            prev_rank = _PREVIOUS_RANKS.get(snap.symbol, rank_index)
            rank_delta = prev_rank - rank_index
            _PREVIOUS_RANKS[snap.symbol] = rank_index
            bundle = bundle_map.get(snap.symbol)
            breakdown = score_with_breakdown(snap, profile=profile)[1]
            stale = (ts_dt - snap.ts).total_seconds() > settings.scan_interval_sec * 2
            latency_ms = bundle.fetch_latency_ms if bundle else None
            execution_metrics = bundle.execution if bundle else {}
            items.append(
                RankingSymbolFrame(
                    symbol=snap.symbol,
                    rank=rank_index,
                    rank_delta=rank_delta,
                    score=float(snap.score or 0.0),
                    liquidity_edge=snap.liquidity_edge,
                    momentum_edge=snap.momentum_edge,
                    volatility_edge=snap.volatility_edge,
                    microstructure_edge=snap.microstructure_edge,
                    anomaly_residual=snap.anomaly_residual,
                    spread_bps=snap.spread_bps,
                    slip_bps=snap.slip_bps,
                    volume_zscore=snap.volume_zscore,
                    order_flow_imbalance=snap.order_flow_imbalance,
                    volatility_regime=snap.volatility_regime,
                    price_velocity=snap.price_velocity,
                    anomaly_score=snap.anomaly_score,
                    depth_to_volume_ratio=snap.depth_to_volume_ratio,
                    manipulation_score=snap.manip_score,
                    manipulation_flags=snap.manip_flags,
                    stale=stale,
                    latency_ms=latency_ms,
                    score_components=breakdown,
                    execution_metrics=execution_metrics,
                    manipulation_threshold_exceeded=(
                        manipulation_threshold is not None and (snap.manip_score or 0.0) >= manipulation_threshold
                    ),
                )
            )
            signal_payload = {
                "symbol": snap.symbol,
                "rank": rank_index,
                "score": snap.score,
                "liquidity_edge": snap.liquidity_edge,
                "momentum_edge": snap.momentum_edge,
                "volatility_edge": snap.volatility_edge,
                "microstructure_edge": snap.microstructure_edge,
                "anomaly_residual": snap.anomaly_residual,
            }
            await signal_bus.publish_if_matched(signal_payload)

        frame = RankingFrame(
            ts=ts_dt,
            profile=profile,
            market_gauge=market_gauge,
            volatility_bucket=volatility_bucket,
            top=len(items),
            items=items,
        )
        await broadcast.publish(frame)

        flagged = [
            {
                "symbol": b.snapshot.symbol,
                "score": b.snapshot.manip_score,
                "flags": b.snapshot.manip_flags,
                "features": b.manip_features,
            }
            for b in bundles
            if b.snapshot.manip_flags
        ]
        log_payload = {
            "cycle_ms": round(duration, 2),
            "symbols_scanned": len(bundles),
            "ranked": len(ranked),
            "manip_flagged": flagged,
            "timestamp": ts_iso,
        }
        LOGGER.info("scan_cycle %s", json.dumps(log_payload))

        _HEALTH_STATE.update(
            {
                "last_cycle_ms": duration,
                "last_success": ts_iso,
                "last_error": None if not errors else _HEALTH_STATE.get("last_error"),
                "failure_streak": failure_streak,
                "cycle_count": _HEALTH_STATE.get("cycle_count", 0) + 1,
                "backoff_sec": _HEALTH_STATE.get("backoff_sec", 0.0),
                "adapter": adapter_state or _HEALTH_STATE.get("adapter"),
                "control": _snapshot_control_state(),
                "symbols": {
                    bundle.snapshot.symbol: {
                        "latency_ms": bundle.fetch_latency_ms,
                        "stale": (ts_dt - bundle.snapshot.ts).total_seconds(),
                        "last_seen": bundle.snapshot.ts.isoformat(),
                        "volatility_bucket": bundle.micro_features.get("volatility_bucket") if bundle.micro_features else None,
                    }
                    for bundle in bundles
                },
            }
        )

        if not _PAUSE_EVENT.is_set():
            continue

        if stop_event and stop_event.is_set():
            return

        elapsed_sec = duration / 1000.0
        sleep_remaining = max(settings.scan_interval_sec - elapsed_sec, 0.0)
        if sleep_remaining <= 0:
            continue
        try:
            await asyncio.wait_for(_FORCE_EVENT.wait(), timeout=sleep_remaining)
            _FORCE_EVENT.clear()
        except asyncio.TimeoutError:
            pass


def get_latest_bundle(symbol: str) -> SnapshotBundle | None:
    return _LATEST_BUNDLES.get(symbol)


def get_health_state() -> dict[str, Any]:
    return json.loads(json.dumps(_HEALTH_STATE))


async def collect_snapshot(symbol: str) -> SnapshotBundle | None:
    async with CCXTAdapter() as adapter:
        return await _build_snapshot(adapter, symbol)


def get_spread_history(symbol: str) -> list[float]:
    return list(_SPREAD_HISTORY.get(symbol, []))


__all__ = [
    "loop",
    "run_cycle",
    "get_latest_bundle",
    "get_health_state",
    "collect_snapshot",
    "get_spread_history",
    "request_force_scan",
    "pause_scanner",
    "resume_scanner",
    "set_manual_breaker",
    "get_control_state",
]




