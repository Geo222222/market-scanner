"""Robust CCXT adapter with retries, timeouts, and a simple circuit breaker."""
from __future__ import annotations

import asyncio
import time
from typing import Any, Mapping

import ccxt.async_support as ccxt

from ..config import get_settings
from ..observability import record_ccxt_latency


class AdapterError(RuntimeError):
    """Raised when the market data adapter cannot fulfill a request."""


class _CircuitBreaker:
    def __init__(self, threshold: int, cooldown_s: float) -> None:
        self.threshold = max(1, threshold)
        self.cooldown_s = max(cooldown_s, 1.0)
        self.fail_count = 0
        self.blocked_until = 0.0

    def allow(self) -> bool:
        now = time.time()
        if self.blocked_until and now < self.blocked_until:
            return False
        if self.blocked_until and now >= self.blocked_until:
            self.reset()
        return True

    def record_success(self) -> None:
        self.reset()

    def record_failure(self) -> None:
        self.fail_count += 1
        if self.fail_count >= self.threshold:
            self.blocked_until = time.time() + self.cooldown_s

    def reset(self) -> None:
        self.fail_count = 0
        self.blocked_until = 0.0


class CCXTAdapter:
    """Async thin wrapper around CCXT with exponential backoff and normalization."""

    def __init__(self, exchange_id: str | None = None, **kwargs: Any) -> None:
        settings = get_settings()
        self.exchange_id = exchange_id or settings.exchange
        exchange_cls = getattr(ccxt, self.exchange_id)
        config = {
            "enableRateLimit": True,
            "timeout": int(settings.adapter_timeout_sec * 1000),
        }
        config.update(kwargs)
        self._exchange = exchange_cls(config)
        self._timeout_s = settings.adapter_timeout_sec
        self._breaker = _CircuitBreaker(settings.adapter_max_failures, settings.adapter_cooldown_sec)
        self._semaphore = asyncio.Semaphore(settings.scan_concurrency)

    async def __aenter__(self) -> "CCXTAdapter":
        return self

    async def __aexit__(self, *_exc: object) -> None:
        await self.close()

    async def close(self) -> None:
        try:
            await self._exchange.close()
        except Exception:  # pragma: no cover - best effort cleanup
            pass

    async def load_markets(self) -> Mapping[str, Any]:
        raw = await self._call("load_markets")
        return {symbol: data for symbol, data in raw.items()}

    async def fetch_ticker(self, symbol: str) -> dict[str, Any]:
        raw = await self._call("fetch_ticker", symbol)
        return {
            "symbol": raw.get("symbol", symbol),
            "bid": raw.get("bid"),
            "ask": raw.get("ask"),
            "last": raw.get("last"),
            "high": raw.get("high"),
            "low": raw.get("low"),
            "quoteVolume": raw.get("quoteVolume"),
            "baseVolume": raw.get("baseVolume"),
            "info": raw.get("info"),
            "timestamp": raw.get("timestamp"),
        }

    async def fetch_order_book(self, symbol: str, limit: int = 50) -> dict[str, Any]:
        raw = await self._call("fetch_order_book", symbol, limit)
        return {
            "symbol": symbol,
            "bids": raw.get("bids", []) or [],
            "asks": raw.get("asks", []) or [],
            "timestamp": raw.get("timestamp"),
        }

    async def fetch_ohlcv(self, symbol: str, timeframe: str, limit: int) -> list[dict[str, Any]]:
        raw = await self._call("fetch_ohlcv", symbol, timeframe, limit)
        normalized: list[dict[str, Any]] = []
        for row in raw:
            if len(row) < 5:
                continue
            normalized.append(
                {
                    "ts": row[0],
                    "open": row[1],
                    "high": row[2],
                    "low": row[3],
                    "close": row[4],
                    "volume": row[5] if len(row) > 5 else None,
                }
            )
        return normalized

    async def fetch_funding_rate(self, symbol: str) -> dict[str, Any] | None:
        if not hasattr(self._exchange, "fetch_funding_rate"):
            return None
        raw = await self._call("fetch_funding_rate", symbol)
        if raw is None:
            return None
        return {
            "symbol": raw.get("symbol", symbol),
            "fundingRate": raw.get("fundingRate") or raw.get("funding_rate"),
            "timestamp": raw.get("timestamp"),
        }

    async def fetch_open_interest(self, symbol: str) -> dict[str, Any] | None:
        if hasattr(self._exchange, "fetch_open_interest"):
            raw = await self._call("fetch_open_interest", symbol)
        elif hasattr(self._exchange, "fetch_open_interest_history"):
            history = await self._call("fetch_open_interest_history", symbol, None, 1)
            raw = history[-1] if history else None
        else:
            return None
        if raw is None:
            return None
        return {
            "symbol": raw.get("symbol", symbol),
            "openInterest": raw.get("openInterest") or raw.get("open_interest"),
            "timestamp": raw.get("timestamp") or raw.get("ts"),
        }

    async def _call(self, method: str, *args: Any, **kwargs: Any) -> Any:
        if not self._breaker.allow():
            raise AdapterError("CCXT adapter circuit open; cooling down after repeated failures.")
        backoff = 0.5
        last_exc: Exception | None = None
        for _attempt in range(3):
            try:
                func = getattr(self._exchange, method)
                async with self._semaphore:
                    with record_ccxt_latency(method):
                        result = await asyncio.wait_for(func(*args, **kwargs), timeout=self._timeout_s)
                self._breaker.record_success()
                return result
            except asyncio.TimeoutError as exc:
                last_exc = exc
            except ccxt.BaseError as exc:
                last_exc = exc
            except Exception as exc:  # pragma: no cover - defensive
                last_exc = exc
                break
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, 4.0)
        self._breaker.record_failure()
        message = f"{method} failed after retries for {args!r}."
        raise AdapterError(message) from last_exc

