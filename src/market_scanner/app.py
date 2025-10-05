from __future__ import annotations

import asyncio
import logging

from fastapi import FastAPI
from fastapi.responses import Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from .config import get_settings
from .jobs.loop import loop as scanner_loop
from .routers import (
    control,
    health,
    symbols,
    rankings,
    opportunities,
    stream,
    settings as settings_routes,
    watchlists,
    profiles,
    panel as panel_router,
)

logging.basicConfig(level=logging.INFO, format="%(message)s")

settings = get_settings()

app = FastAPI(title="Market Scanner")

app.include_router(health.router)
app.include_router(panel_router.router)
app.include_router(control.router)
app.include_router(symbols.router, prefix="/symbols", tags=["symbols"])
app.include_router(rankings.router, prefix="/rankings", tags=["rankings"])
app.include_router(opportunities.router, prefix="/opportunities", tags=["opportunities"])
app.include_router(settings_routes.router, tags=["settings"])
app.include_router(watchlists.router, tags=["watchlists"])
app.include_router(profiles.router, tags=["profiles"])
app.include_router(stream.router, prefix="/stream", tags=["stream"])

@app.on_event("startup")
async def _startup() -> None:
    asyncio.create_task(scanner_loop())


if settings.metrics_enabled:
    @app.get("/metrics", include_in_schema=False)
    async def metrics_endpoint() -> Response:
        return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

