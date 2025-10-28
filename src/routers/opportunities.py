"""Backward-compatible import shim for the opportunities router."""
from __future__ import annotations

from .opps import router  # re-export for legacy imports

__all__ = ["router"]
