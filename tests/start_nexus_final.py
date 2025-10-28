#!/usr/bin/env python3
"""
Nexus Alpha - Final Working Version
"""
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pathlib import Path
import uvicorn
import random

# Create FastAPI app
app = FastAPI(
    title="Nexus Alpha",
    description="The Intelligent Signal Intelligence Platform",
    version="1.0.0"
)

# Health endpoint
@app.get("/health")
async def health():
    return {"status": "ok", "message": "Nexus Alpha is running"}

# Dashboard endpoint
@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard():
    """Serve the Nexus Alpha Signal Intelligence Dashboard."""
    template_path = Path(__file__).parent / "src" / "templates" / "nexus-dashboard.html"
    
    if not template_path.exists():
        raise HTTPException(status_code=404, detail="Dashboard not found")
    
    with open(template_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    return HTMLResponse(content=content)

# Panel endpoint
@app.get("/panel", response_class=HTMLResponse)
async def panel():
    """Serve the Command Center Panel."""
    template_path = Path(__file__).parent / "src" / "templates" / "panel.html"
    
    if not template_path.exists():
        raise HTTPException(status_code=404, detail="Panel not found")
    
    with open(template_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    return HTMLResponse(content=content)

# Trading dashboard endpoint
@app.get("/trading/dashboard", response_class=HTMLResponse)
async def trading_dashboard():
    """Serve the Trading Dashboard."""
    template_path = Path(__file__).parent / "src" / "templates" / "trading.html"
    
    if not template_path.exists():
        raise HTTPException(status_code=404, detail="Trading dashboard not found")
    
    with open(template_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    return HTMLResponse(content=content)

# Mock rankings endpoint
@app.get("/rankings")
async def rankings(top: int = 10, profile: str = "scalp"):
    """Mock rankings endpoint for testing."""
    mock_symbols = [
        "BTC/USDT:USDT", "ETH/USDT:USDT", "BNB/USDT:USDT", 
        "ADA/USDT:USDT", "SOL/USDT:USDT", "XRP/USDT:USDT",
        "DOT/USDT:USDT", "DOGE/USDT:USDT", "AVAX/USDT:USDT", "MATIC/USDT:USDT"
    ]
    
    items = []
    for i, symbol in enumerate(mock_symbols[:top]):
        items.append({
            "symbol": symbol,
            "rank": i + 1,
            "score": round(random.uniform(20, 80), 2),
            "bias": random.choice(["Long", "Short", "Neutral"]),
            "confidence": random.randint(60, 95),
            "liquidity_edge": round(random.uniform(-2, 5), 2),
            "momentum_edge": round(random.uniform(-3, 4), 2),
            "spread_bps": round(random.uniform(2, 15), 1),
            "slip_bps": round(random.uniform(1, 8), 1),
            "atr_pct": round(random.uniform(0.5, 3.0), 2),
            "qvol_usdt": random.randint(1000000, 50000000),
            "flags": [
                {"name": "High Volume", "active": random.choice([True, False])},
                {"name": "Low Spread", "active": random.choice([True, False])}
            ]
        })
    
    return {"items": items, "profile": profile, "total": len(items)}

# Mock opportunities endpoint
@app.get("/opportunities")
async def opportunities(symbol: str = None, profile: str = "scalp", top: int = 5):
    """Mock opportunities endpoint for testing."""
    if symbol:
        return {
            "symbol": symbol,
            "score": round(random.uniform(30, 85), 2),
            "bias": random.choice(["Long", "Short", "Neutral"]),
            "confidence": random.randint(70, 95),
            "liquidity_edge": round(random.uniform(-1, 4), 2),
            "momentum_edge": round(random.uniform(-2, 3), 2),
            "spread_bps": round(random.uniform(3, 12), 1),
            "slip_bps": round(random.uniform(1, 6), 1),
            "atr_pct": round(random.uniform(0.8, 2.5), 2),
            "qvol_usdt": random.randint(2000000, 30000000),
            "price": round(random.uniform(20000, 70000), 2),
            "flags": [
                {"name": "High Confidence", "active": True},
                {"name": "Low Risk", "active": random.choice([True, False])}
            ]
        }
    else:
        return await rankings(top=top, profile=profile)

# Root endpoint
@app.get("/")
async def root():
    return {
        "message": "Nexus Alpha - Signal Intelligence Platform",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "dashboard": "/dashboard",
            "panel": "/panel", 
            "trading": "/trading/dashboard",
            "rankings": "/rankings",
            "opportunities": "/opportunities",
            "health": "/health"
        }
    }

if __name__ == "__main__":
    print("Nexus Alpha - Signal Intelligence Platform")
    print("=" * 50)
    print("Starting server on http://localhost:8011")
    print("Access the dashboard at: http://localhost:8011/dashboard")
    print("Press Ctrl+C to stop")
    print("=" * 50)
    
    uvicorn.run(app, host="0.0.0.0", port=8011)
