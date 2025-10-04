from __future__ import annotations

from fastapi import APIRouter

from ..config import get_settings
from ..core.scoring import set_profile_override, WEIGHT_PRESETS
from ..engine.runtime import set_manipulation_threshold, set_notional_override
from ..stores import settings_store

router = APIRouter()


@router.get("/settings")
async def fetch_settings():
    profile = await settings_store.get_user_profile()
    watchlists = await settings_store.list_watchlists()
    return {
        "weights": profile["weights"],
        "manipulation_threshold": profile.get("manipulation_threshold"),
        "notional": profile.get("notional"),
        "watchlists": [
            {
                "name": wl["name"],
                "symbols": wl["symbols"],
            }
            for wl in watchlists
        ],
    }


@router.post("/settings")
async def update_settings(payload: dict[str, float]):
    liquidity = float(payload.get("liquidity_weight", 0.0))
    momentum = float(payload.get("momentum_weight", 0.0))
    spread_penalty = float(payload.get("spread_penalty", 0.0))
    manip_threshold = payload.get("manipulation_threshold")
    notional = payload.get("notional")

    weights = {
        "liquidity": liquidity,
        "momentum": momentum,
        "spread": spread_penalty,
    }
    await settings_store.upsert_user_profile(
        name="default",
        weights=weights,
        manipulation_threshold=manip_threshold,
        notional=notional,
    )

    default_profile = get_settings().profile_default
    base = WEIGHT_PRESETS.get(default_profile, {})
    override = {
        "edges": {
            "liquidity": liquidity or base.get("edges", {}).get("liquidity", 0.0),
            "momentum": momentum or base.get("edges", {}).get("momentum", 0.0),
        },
        "cost": {"spread": spread_penalty or base.get("cost", {}).get("spread", 0.0)},
    }
    set_profile_override(default_profile, override)
    set_manipulation_threshold(manip_threshold)
    set_notional_override(notional)

    return {"status": "ok"}
