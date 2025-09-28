"""Prometheus metrics and observability helpers for the market scanner."""
from __future__ import annotations

import time
from contextlib import contextmanager
from typing import Optional

from prometheus_client import Counter, Gauge, Histogram

from .config import get_settings

_SETTINGS = get_settings()
_ENABLED = _SETTINGS.metrics_enabled

_SCAN_DURATION = Histogram(
    "scanner_cycle_duration_seconds",
    "Duration of a full market scan cycle.",
    buckets=(1, 2, 3, 5, 8, 13, 21, 34, 55, 89),
)
_SCAN_SYMBOLS = Gauge(
    "scanner_symbols_scanned",
    "Number of symbols processed in the latest cycle.",
)
_SCAN_RANKED = Gauge(
    "scanner_symbols_ranked",
    "Number of symbols ranked in the latest cycle.",
)
_SCAN_ERRORS = Counter(
    "scanner_cycle_errors_total",
    "Total number of scan cycle failures.",
)
_REDIS_CACHE_HITS = Counter(
    "scanner_cache_hits_total", "Number of successful cache hits.", ["cache"],
)
_REDIS_CACHE_MISSES = Counter(
    "scanner_cache_misses_total", "Number of cache misses.", ["cache"],
)
_CCXT_CALL_LATENCY = Histogram(
    "scanner_ccxt_call_latency_seconds",
    "Latency of CCXT adapter calls by method.",
    labelnames=("method",),
    buckets=(0.05, 0.1, 0.2, 0.3, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0, 5.0),
)


def record_cycle(duration: float, scanned: int, ranked: int, errors: int) -> None:
    if not _ENABLED:
        return
    _SCAN_DURATION.observe(max(duration, 0.0))
    _SCAN_SYMBOLS.set(scanned)
    _SCAN_RANKED.set(ranked)
    if errors:
        _SCAN_ERRORS.inc(errors)


def record_cache_event(cache: str, hit: bool) -> None:
    if not _ENABLED:
        return
    if hit:
        _REDIS_CACHE_HITS.labels(cache=cache).inc()
    else:
        _REDIS_CACHE_MISSES.labels(cache=cache).inc()


@contextmanager
def record_ccxt_latency(method: str):
    if not _ENABLED:
        yield
        return
    start = time.perf_counter()
    try:
        yield
    finally:
        elapsed = time.perf_counter() - start
        _CCXT_CALL_LATENCY.labels(method=method).observe(max(elapsed, 0.0))
