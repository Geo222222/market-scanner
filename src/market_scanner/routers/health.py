from __future__ import annotations

from fastapi import APIRouter

from ..jobs.loop import get_health_state

router = APIRouter()


@router.get("/health")
async def health():
    return {"status": "ok"}


@router.get("/healthz/details")
async def health_details():
    return get_health_state()
