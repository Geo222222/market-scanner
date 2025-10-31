from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from .config import get_settings
from .logging_config import configure_production_logging
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
    trading,
    backtesting,
    dashboard,
    signal_history,
    level2,
    ml_status,
)

# Configure production-grade logging (suppresses WebSocket debug spam)
configure_production_logging(log_level="INFO", enable_file_logging=False)

settings = get_settings()

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    asyncio.create_task(scanner_loop())
    yield
    # Shutdown
    pass

app = FastAPI(title="Nexus Alpha", description="The Intelligent Trading Ecosystem", lifespan=lifespan)

static_dir = Path(__file__).resolve().parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

# ============================================================================
# Security Headers Middleware - CRITICAL FIX
# ============================================================================
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses."""
    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        
        # Prevent MIME type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"
        
        # Prevent clickjacking
        response.headers["X-Frame-Options"] = "DENY"
        
        # Enable XSS protection
        response.headers["X-XSS-Protection"] = "1; mode=block"
        
        # Content Security Policy (strict)
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'wasm-unsafe-eval' https://cdn.tailwindcss.com https://unpkg.com https://cdn.jsdelivr.net https://cdn.plot.ly; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "img-src 'self' data: https:; "
            "connect-src 'self' https:; "
            "font-src 'self' https://fonts.gstatic.com; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self'"
        )
        
        # Referrer policy
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # Permissions policy (formerly Feature-Policy)
        response.headers["Permissions-Policy"] = (
            "geolocation=(), "
            "microphone=(), "
            "camera=(), "
            "payment=()"
        )
        
        return response

# Add security middleware BEFORE CORS
app.add_middleware(SecurityHeadersMiddleware)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(panel_router.router)
app.include_router(control.router)
app.include_router(symbols.router, prefix="/symbols", tags=["symbols"])
app.include_router(rankings.router, prefix="/rankings", tags=["rankings"])
app.include_router(opportunities.router, prefix="/opportunities", tags=["opportunities"])
app.include_router(trading.router, prefix="/trading", tags=["trading"])
app.include_router(backtesting.router, prefix="/backtesting", tags=["backtesting"])
app.include_router(dashboard.router, tags=["dashboard"])
app.include_router(signal_history.router, prefix="/api/signals", tags=["signal-history"])
app.include_router(level2.router, prefix="/api", tags=["level2"])
app.include_router(ml_status.router, prefix="/api", tags=["ml"])
app.include_router(settings_routes.router, tags=["settings"])
app.include_router(watchlists.router, tags=["watchlists"])
app.include_router(profiles.router, tags=["profiles"])
app.include_router(stream.router, prefix="/stream", tags=["stream"])


if settings.metrics_enabled:
    @app.get("/metrics", include_in_schema=False)
    async def metrics_endpoint() -> Response:
        return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)





