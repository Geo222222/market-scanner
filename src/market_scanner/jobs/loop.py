"""Background scanning loop that orchestrates data collection, scoring, and streaming."""
from __future__ import annotations

import asyncio
import json
import logging
import time
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Mapping

from ..adapters.ccxt_adapter import AdapterError, CCXTAdapter
from ..config import get_settings
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
from ..engine.runtime import get_notional_override, get_manipulation_threshold
from ..engine.streaming import RankingFrame, RankingSymbolFrame, get_ranking_broadcast
from ..manip.detector import detect_manipulation
from ..observability import record_cycle
from ..stores.pg_store import bulk_insert_rankings, insert_minute_agg
from ..stores.redis_store import cache_rankings, cache_snapshots

LOGGER = logging.getLogger(__name__)

_MARKETS_CACHE: dict[str, Any] = {}
_MARKETS_TS: float | None = None
_LATEST_BUNDLES: dict[str, "SnapshotBundle"] = {}
_PREVIOUS_RANKS: dict[str, int] = {}
_SPREAD_HISTORY: dict[str, list[float]] = defaultdict(list)

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
    "symbols": {},
}


@dataclass(slots=True)
class SnapshotBundle:
    snapshot: SymbolSnapshot
    close: float
    manip_features: dict[str, float]
    ticker: dict[str, Any]
    orderbook: dict[str, Any]
    momentum: dict[str, float]
    micro_features: dict[str, Any]
    execution: dict[str, float]
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
    now = time.time()
    if not _MARKETS_CACHE or _MARKETS_TS is None or now - _MARKETS_TS > settings.markets_cache_ttl_sec:
        markets = await adapter.load_markets()
        filtered = {sym: data for sym, data in markets.items() if _is_usdt_perp(data)}
        _MARKETS_CACHE = filtered
        _MARKETS_TS = now
    return [sym for sym, data in _MARKETS_CACHE.items() if data.get("active", True)]


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
        ticker_task = adapter.fetch_ticker(symbol)
        orderbook_task = adapter.fetch_order_book(symbol, limit=50)
        ohlcv_task = adapter.fetch_ohlcv(symbol, settings.timeframe, 200)
        ticker, orderbook, ohlcv = await asyncio.gather(ticker_task, orderbook_task, ohlcv_task)
    except AdapterError as exc:
        LOGGER.debug("Adapter mandatory fetch failed for %s: %s", symbol, exc)
        return None
    fetch_latency_ms = (time.perf_counter() - fetch_started) * 1000

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
    spread = spread_bps(bid, ask)
    depth = top5_depth_usdt(orderbook)
    atr = atr_pct(ohlcv)
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
    volume_z = volume_zscore(ohlcv)
    vol_reg = volatility_regime(closes)
    velocity = price_velocity(closes)
    ofi = order_flow_imbalance(orderbook)
    pump_score = pump_dump_score(momentum["ret_15"], momentum["ret_1"], volume_z, vol_reg)
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
        qvol_usdt=qvol,
        spread_bps=spread,
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

    SPREAD_HISTORY[symbol] = spread_history_update(SPREAD_HISTORY[symbol], spread)

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


def _build_ranking_rows(snaps: list[SymbolSnapshot]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for snap in snaps:
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
            }
        )
    return rows


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
        started = time.perf_counter()
        bundles: list[SnapshotBundle] = []
        ranked: list[SymbolSnapshot] = []
        errors = 0
        adapter_state: dict[str, Any] | None = None
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
            })
            await asyncio.sleep(wait)
            if stop_event and stop_event.is_set():
                return
            continue

        ts_dt = datetime.now(timezone.utc)
        ts_iso = ts_dt.isoformat()
        await cache_snapshots([bundle.snapshot for bundle in bundles])
        rows = _build_ranking_rows(ranked)
        await cache_rankings(profile, rows, ts_iso)

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

        if stop_event and stop_event.is_set():
            return
        await asyncio.sleep(settings.scan_interval_sec)


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
]




