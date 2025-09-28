"""Async Redis-backed caching helpers."""
from __future__ import annotations

import json
import logging
from typing import Any, Iterable

try:
    import redis.asyncio as redis
except ImportError:  # pragma: no cover - optional dependency
    redis = None  # type: ignore

from ..config import get_settings
from ..core.metrics import SymbolSnapshot
from ..observability import record_cache_event

LOGGER = logging.getLogger(__name__)

_REDIS_CLIENT: Any = None


def _get_client() -> Any:
    global _REDIS_CLIENT
    settings = get_settings()
    if redis is None or not settings.redis_url:
        return None
    if _REDIS_CLIENT is None:
        _REDIS_CLIENT = redis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
            socket_timeout=settings.adapter_timeout_sec,
        )
    return _REDIS_CLIENT


async def cache_snapshots(snaps: Iterable[SymbolSnapshot]) -> None:
    client = _get_client()
    if client is None:
        return
    snapshots = [snap.model_dump(mode="json") for snap in snaps]
    try:
        await client.set(
            "snaps:latest",
            json.dumps(snapshots),
            ex=get_settings().redis_snapshots_ttl_sec,
        )
    except Exception as exc:  # pragma: no cover - network error path
        LOGGER.warning("Redis cache_snapshots failed: %s", exc)


async def get_latest_snapshots() -> list[SymbolSnapshot]:
    client = _get_client()
    if client is None:
        return []
    try:
        raw = await client.get("snaps:latest")
        record_cache_event("snapshots", bool(raw))
    except Exception as exc:  # pragma: no cover - network error path
        LOGGER.warning("Redis get_latest_snapshots failed: %s", exc)
        record_cache_event("snapshots", False)
        return []
    if not raw:
        return []
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return []
    snapshots: list[SymbolSnapshot] = []
    for item in data:
        try:
            snapshots.append(SymbolSnapshot.model_validate(item))
        except Exception:
            continue
    return snapshots


async def cache_rankings(profile: str, rows: list[dict[str, Any]], ts: str) -> None:
    client = _get_client()
    if client is None:
        return
    payload = {"ts": ts, "profile": profile, "rows": rows}
    try:
        await client.set(
            f"rank:{profile}",
            json.dumps(payload),
            ex=get_settings().redis_rankings_ttl_sec,
        )
    except Exception as exc:  # pragma: no cover - network error path
        LOGGER.warning("Redis cache_rankings failed: %s", exc)


async def get_rankings(profile: str) -> dict[str, Any] | None:
    client = _get_client()
    if client is None:
        return None
    key = f"rank:{profile}"
    try:
        raw = await client.get(key)
        record_cache_event("rankings", bool(raw))
    except Exception as exc:  # pragma: no cover - network error path
        LOGGER.warning("Redis get_rankings failed: %s", exc)
        record_cache_event("rankings", False)
        return None
    if not raw:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None
