from __future__ import annotations

from typing import Iterable


def format_flag_objects(flags: Iterable[str] | None) -> list[dict[str, bool]]:
    """Return UI-friendly flag objects from raw flag names."""

    if not flags:
        return []
    formatted: list[dict[str, bool]] = []
    seen: set[str] = set()
    for flag in flags:
        if not flag:
            continue
        key = str(flag).strip()
        if not key or key.lower() in seen:
            continue
        seen.add(key.lower())
        formatted.append({"name": key, "active": True})
    return formatted
