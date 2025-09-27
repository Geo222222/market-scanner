from __future__ import annotations

import asyncio
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates

from .config import get_settings
from .jobs.loop import loop as scanner_loop
from .routers import health, symbols, rankings, opportunities, stream

settings = get_settings()

app = FastAPI(title="Market Scanner")

app.include_router(health.router)
app.include_router(symbols.router, prefix="/symbols", tags=["symbols"])
app.include_router(rankings.router, prefix="/rankings", tags=["rankings"])
app.include_router(opportunities.router, prefix="/opportunities", tags=["opportunities"])
app.include_router(stream.router, prefix="/stream", tags=["stream"])

_templates_path = Path(__file__).resolve().parent / "templates"
templates = Jinja2Templates(directory=str(_templates_path))


@app.on_event("startup")
async def _startup() -> None:
    asyncio.create_task(scanner_loop())


@app.get("/panel", include_in_schema=False)
async def render_panel(request: Request):
    return templates.TemplateResponse(
        "panel.html",
        {
            "request": request,
            "default_profile": settings.ranking_profile_default,
            "default_top": settings.topn_default,
            "default_notional": settings.notional_test,
        },
    )
