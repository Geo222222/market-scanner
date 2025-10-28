from __future__ import annotations

from fastapi import Header, HTTPException, status

from .config import get_settings

ADMIN_HEADER = "X-Admin-Token"


def require_admin(
    x_admin_token: str | None = Header(default=None, alias=ADMIN_HEADER),
    authorization: str | None = Header(default=None),
) -> None:
    """Ensure the request carries a valid admin token."""

    expected = get_settings().admin_api_token
    if not expected:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Admin API token is not configured",
        )

    candidate: str | None = None
    if x_admin_token:
        candidate = x_admin_token.strip()
    elif authorization:
        scheme, _, token = authorization.partition(" ")
        if scheme.lower() == "bearer":
            candidate = token.strip()

    if not candidate or candidate != expected:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid admin token",
            headers={"WWW-Authenticate": "Bearer"},
        )
