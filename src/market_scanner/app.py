import asyncio
from fastapi import FastAPI
from .routers import health, symbols, rankings, opportunities, stream
from .config import settings
from .engine.scheduler import loop


app = FastAPI(title="Market Scanner")

app.include_router(health.router)
app.include_router(symbols.router, prefix="/symbols", tags=["symbols"])
app.include_router(rankings.router, prefix="/rankings", tags=["rankings"])
app.include_router(opportunities.router, prefix="/opportunities", tags=["opportunities"])
app.include_router(stream.router, prefix="/stream", tags=["stream"])


@app.on_event("startup")
async def _startup():
    # Start background scanning (mock or CCXT depending on env)
    asyncio.create_task(loop(settings.symbols, settings.scan_interval_s))

# ONNYX | ONNX | DJM | DJ | ME | Jamaica — signature watermark
# Owner: DJM (ONNYX) — Jamaica. If found elsewhere, contact ME.
# ONNYX · ONNX · DJM · DJ · ME · Jamaica
