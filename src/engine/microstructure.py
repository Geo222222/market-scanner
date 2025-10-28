"""Microstructure analytics and heuristic flag computation."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Tuple

from ..core.metrics import SymbolSnapshot


@dataclass(slots=True)
class MicrostructureState:
    last_imbalance: float = 0.0
    last_depth: float = 0.0
    last_volume_z: float = 0.0
    last_velocity: float = 0.0


@dataclass(slots=True)
class MicrostructureFeatures:
    depth_decay: float
    trade_imbalance: float
    spoof_unwind: bool
    passive_absorption: bool
    pump_signature: bool
    dump_signature: bool
    volatility_bucket: str


_STATE: Dict[str, MicrostructureState] = {}


def _volatility_bucket(snapshot: SymbolSnapshot) -> str:
    vr = snapshot.volatility_regime
    if vr < 0.2:
        return "low"
    if vr < 0.8:
        return "medium"
    return "high"


def compute_microstructure_features(
    symbol: str,
    snapshot: SymbolSnapshot,
    depth_notional: float,
) -> Tuple[MicrostructureFeatures, Dict[str, float]]:
    """Derive microstructure heuristics for the given snapshot.

    Returns the features along with raw numeric metrics for telemetry.
    """

    state = _STATE.get(symbol) or MicrostructureState()
    imbalance = snapshot.order_flow_imbalance
    depth = snapshot.top5_depth_usdt
    vol_z = snapshot.volume_zscore
    velocity = snapshot.price_velocity

    depth_decay = (state.last_depth - depth) / state.last_depth if state.last_depth > 0 else 0.0
    trade_imbalance = imbalance * max(vol_z, 1.0)

    spoof_unwind = state.last_imbalance > 0.6 and imbalance < -0.2 and depth_decay > 0.25
    passive_absorption = abs(imbalance) < 0.2 and vol_z > 3.5 and abs(velocity) < 0.2
    pump_signature = snapshot.ret_15 > 3.0 and velocity > 0.8 and vol_z > 2.5
    dump_signature = snapshot.ret_15 < -3.0 and velocity < -0.8 and vol_z > 2.5

    features = MicrostructureFeatures(
        depth_decay=depth_decay,
        trade_imbalance=trade_imbalance,
        spoof_unwind=spoof_unwind,
        passive_absorption=passive_absorption,
        pump_signature=pump_signature,
        dump_signature=dump_signature,
        volatility_bucket=_volatility_bucket(snapshot),
    )

    telemetry = {
        "imbalance": imbalance,
        "depth": depth,
        "depth_to_notional": depth / depth_notional if depth_notional else 0.0,
        "depth_decay": depth_decay,
        "volume_zscore": vol_z,
        "velocity": velocity,
        "trade_imbalance": trade_imbalance,
    }

    state.last_imbalance = imbalance
    state.last_depth = depth
    state.last_volume_z = vol_z
    state.last_velocity = velocity
    _STATE[symbol] = state
    return features, telemetry


