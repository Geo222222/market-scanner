from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ..jobs.loop import (
    get_control_state,
    pause_scanner,
    request_force_scan,
    resume_scanner,
    set_manual_breaker,
)

router = APIRouter(prefix="/control", tags=["control"])


class ControlPayload(BaseModel):
    reason: str | None = Field(default=None, max_length=200)
    actor: str | None = Field(default="api", max_length=64)


class BreakerPayload(ControlPayload):
    state: str = Field(..., pattern="^(open|closed)$")


@router.get("/state")
async def control_state() -> dict[str, object]:
    return get_control_state()


@router.post("/force-scan")
async def force_scan(payload: ControlPayload) -> dict[str, object]:
    result = await request_force_scan(actor=payload.actor or "api", reason=payload.reason)
    if not result.get("queued"):
        raise HTTPException(status_code=409, detail=result.get("reason", "Unable to queue force scan"))
    return result


@router.post("/pause")
async def pause(payload: ControlPayload) -> dict[str, object]:
    return await pause_scanner(actor=payload.actor or "api", reason=payload.reason)


@router.post("/resume")
async def resume(payload: ControlPayload) -> dict[str, object]:
    return await resume_scanner(actor=payload.actor or "api", reason=payload.reason)


@router.post("/breaker")
async def breaker(payload: BreakerPayload) -> dict[str, object]:
    try:
        return set_manual_breaker(payload.state, actor=payload.actor or "api", reason=payload.reason)
    except ValueError as exc:  # pragma: no cover - validation guard
        raise HTTPException(status_code=422, detail=str(exc)) from exc
