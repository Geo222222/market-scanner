"""Background scanning loop that orchestrates data collection and scoring."""
from __future__ import annotations

import asyncio
import json
import logging
import time
from collections.abc import Sequence
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
from ..core.scoring import rank
from ..manip.detector import detect_manipulation
from ..observability import record_cycle
from ..stores.pg_store import bulk_insert_rankings, insert_minute_agg
from ..stores.redis_store import cache_rankings, cache_snapshots

LOGGER = logging.getLogger(__name__)

_MARKETS_CACHE: dict[str, Any] = {}
_MARKETS_TS: float | None = None


@dataclass(slots=True)
class SnapshotBundle:
    snapshot: SymbolSnapshot
    close: float
    manip_features: dict[str, float]


def _chunk(symbols: Sequence[str], size: int) -> list[list[str]]:
    return [list(symbols[i : i + size]) for i in range(0, len(symbols), max(1, size))]


def _is_usdt_perp(data: Mapping[str, Any]) -> bool:
    if not (data.get("swap") or data.get("contract") or data.get("type") == "swap"):
        return False
    settle = str(data.get("settle") or data.get("quote") or "").upper()
    if settle and settle != "USDT":
        return False
    linear = data.get("linear")
    if linear is False:
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
        filtered = {
            sym: data
            for sym, data in markets.items()
            if _is_usdt_perp(data)
        }
        _MARKETS_CACHE = filtered
        _MARKETS_TS = now
    active = [sym for sym, data in _MARKETS_CACHE.items() if data.get("active", True)]
    return active


def _extract_spot_reference(ticker: dict[str, Any]) -> float | None:
    info = ticker.get("info") or {}
    if isinstance(info, dict):
        for key in ("indexPrice", "index_price", "markPrice", "mark_price", "spotPrice"):
            if key in info:
                value = info[key]
                try:
                    return float(value)
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
    try:
        ticker_task = adapter.fetch_ticker(symbol)
        orderbook_task = adapter.fetch_order_book(symbol, limit=50)
        ohlcv_task = adapter.fetch_ohlcv(symbol, settings.timeframe, 200)
        ticker, orderbook, ohlcv = await asyncio.gather(ticker_task, orderbook_task, ohlcv_task)
    except AdapterError as exc:
        LOGGER.debug("Adapter mandatory fetch failed for %s: %s", symbol, exc)
        return None

    funding = None
    open_interest = None
    opt_results = await asyncio.gather(
        adapter.fetch_funding_rate(symbol),
        adapter.fetch_open_interest(symbol),
        return_exceptions=True,
    )
    if opt_results:
        fund_res, oi_res = opt_results
        if isinstance(fund_res, AdapterError):
            pass
        elif isinstance(fund_res, Exception):
            LOGGER.debug("Funding fetch error for %s: %s", symbol, fund_res)
        else:
            funding = fund_res
        if isinstance(oi_res, AdapterError):
            pass
        elif isinstance(oi_res, Exception):
            LOGGER.debug("Open interest fetch error for %s: %s", symbol, oi_res)
        else:
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
    slip = estimate_slippage_bps(orderbook, settings.notional_test, side="both")
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

    features = dict(manip_result.features or {})
    features.setdefault("volume_zscore", round(volume_z, 2))
    features.setdefault("vol_regime", round(vol_reg, 4))
    features.setdefault("velocity", round(velocity, 4))
    features.setdefault("order_flow_imbalance", round(ofi, 4))
    features.setdefault("depth_to_volume", round(depth_to_volume, 4))
    features.setdefault("latest_volume_usdt", round(bar_volume_usdt, 2))
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
    return SnapshotBundle(snapshot=snapshot, close=close_price, manip_features=features)


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
                "manip_score": snap.manip_score,
                "manip_flags": snap.manip_flags,
            }
        )
    return rows


async def run_cycle(profile: str) -> tuple[list[SnapshotBundle], list[SymbolSnapshot]]:
    settings = get_settings()
    async with CCXTAdapter() as adapter:
        symbols = await _load_symbols(adapter)
        if not symbols:
            LOGGER.warning("No active perp symbols discovered; skipping cycle.")
            return [], []
        bundles = await _collect_snapshots(adapter, symbols)
    if not bundles:
        return [], []

    bundles.sort(key=lambda b: b.snapshot.qvol_usdt, reverse=True)
    top_universe = bundles[: settings.scan_top_by_qvol]
    snapshots = [b.snapshot for b in top_universe]
    ranked = rank(snapshots, top=settings.topn_default, profile=profile)
    return top_universe, ranked


async def loop(stop_event: asyncio.Event | None = None) -> None:
    settings = get_settings()
    profile = settings.profile_default
    failure_streak = 0
    while True:
        started = time.time()
        bundles: list[SnapshotBundle] = []
        ranked: list[SymbolSnapshot] = []
        errors = 0
        try:
            bundles, ranked = await run_cycle(profile)
            failure_streak = 0
        except AdapterError as exc:
            failure_streak += 1
            errors = 1
            wait = min(settings.scan_interval_sec * (2**failure_streak), 300)
            LOGGER.warning("Scan cycle failed (%s). Backing off for %.1fs", exc, wait)
            record_cycle(0.0, 0, 0, errors)
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

        duration = time.time() - started
        record_cycle(duration, len(bundles), len(ranked), errors)

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
            "cycle_ms": round(duration * 1000, 2),
            "symbols_scanned": len(bundles),
            "ranked": len(ranked),
            "manip_flagged": flagged,
            "timestamp": ts_iso,
        }
        LOGGER.info("scan_cycle %s", json.dumps(log_payload))

        if stop_event and stop_event.is_set():
            return
        await asyncio.sleep(settings.scan_interval_sec)
