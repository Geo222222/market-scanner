from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from ..config import get_settings
from ..core.scoring import set_profile_override
from ..stores import settings_store

router = APIRouter()


@router.get("/profiles")
async def list_profiles():
    presets = await settings_store.list_profile_presets()
    return {"presets": presets}


@router.post("/profiles")
async def save_profile(payload: dict[str, object]):
    name = str(payload.get("name", "")).strip()
    weights = payload.get("weights")
    if not name or not isinstance(weights, dict):
        raise HTTPException(status_code=422, detail="name and weights required")
    await settings_store.save_profile_preset(name, weights)
    return {"status": "ok"}


@router.post("/profiles/apply")
async def apply_profile(name: str = Query(..., description="Profile preset name")):
    preset = await settings_store.get_profile_preset(name)
    if not preset:
        raise HTTPException(status_code=404, detail="profile not found")
    default_profile = get_settings().profile_default
    set_profile_override(default_profile, preset["weights"])
    return {"status": "applied", "profile": name}
