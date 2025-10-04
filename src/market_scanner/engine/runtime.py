"""Runtime overrides applied from user settings."""
from __future__ import annotations

from typing import Dict

_runtime_state: Dict[str, float] = {}


def set_notional_override(value: float | None) -> None:
    if value is None:
        _runtime_state.pop('notional', None)
    else:
        _runtime_state['notional'] = float(value)


def get_notional_override() -> float | None:
    return _runtime_state.get('notional')


def set_manipulation_threshold(value: float | None) -> None:
    if value is None:
        _runtime_state.pop('manip_thresh', None)
    else:
        _runtime_state['manip_thresh'] = float(value)


def get_manipulation_threshold() -> float | None:
    return _runtime_state.get('manip_thresh')
