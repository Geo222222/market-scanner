from __future__ import annotations

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health():
    return {"status": "ok"}


@router.get("/healthz/details")
async def health_details():
    return {"status": "ok", "details": "Health check endpoint"}
