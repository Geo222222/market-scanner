from __future__ import annotations

from datetime import datetime, timezone
from fastapi import APIRouter

from ..data_integrity import (
    exchange_tracker,
    get_fallback_policy,
    HealthResponse
)

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health():
    """
    Health endpoint with exchange status tracking.

    Returns:
        - mode: Operating mode (live)
        - live_data_ok: True if at least one exchange is working
        - degraded: True if any exchange is down
        - exchanges: Per-exchange health status
        - asof: ISO8601 timestamp
    """
    exchanges = exchange_tracker.get_all_health()
    live_data_ok = exchange_tracker.has_any_working()
    degraded = exchange_tracker.is_degraded()

    return HealthResponse(
        mode=get_fallback_policy().value,
        live_data_ok=live_data_ok,
        degraded=degraded,
        exchanges=exchanges,
        asof=datetime.now(timezone.utc).isoformat()
    )


@router.get("/healthz/details")
async def health_details():
    """Legacy health check endpoint for backward compatibility."""
    return {"status": "ok", "details": "Health check endpoint"}
