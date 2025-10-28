#!/usr/bin/env python3
"""
Nexus Alpha Live Simple
Simplified live data application
"""
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pathlib import Path
import uvicorn
import asyncio
import json
from datetime import datetime
import logging

# Import our components
from live_data_engine import live_data_engine, LiveMarketData
from ai_engine import ai_engine, AISignal

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Nexus Alpha Live Simple",
    description="Real-time AI Trading System with Live Market Data",
    version="3.0.0"
)

# Global state
live_signals = {}
market_analysis = {}
data_status = {"status": "starting", "exchanges_connected": 0, "last_update": None}

def calculate_technical_score(market_data: LiveMarketData) -> float:
    """Calculate technical score from live data"""
    try:
        score = 50.0
        
        # Volume factor
        if market_data.volume_usdt > 10000000:
            score += 10
        elif market_data.volume_usdt < 1000000:
            score -= 10
        
        # Spread factor
        if market_data.spread < 5:
            score += 15
        elif market_data.spread < 10:
            score += 5
        elif market_data.spread > 20:
            score -= 10
        
        # Price change factor
        if market_data.change_percent_24h > 5:
            score += 10
        elif market_data.change_percent_24h < -5:
            score -= 10
        
        return max(0, min(100, score))
    except:
        return 50.0

def calculate_liquidity_edge(market_data: LiveMarketData) -> float:
    """Calculate liquidity edge from live data"""
    try:
        volume_factor = min(5, market_data.volume_usdt / 10000000)
        spread_factor = max(-2, 5 - market_data.spread / 2)
        return volume_factor + spread_factor
    except:
        return 0.0

def calculate_momentum_edge(market_data: LiveMarketData) -> float:
    """Calculate momentum edge from live data"""
    try:
        return market_data.change_percent_24h / 10
    except:
        return 0.0

def calculate_atr(market_data: LiveMarketData) -> float:
    """Calculate ATR from live data"""
    try:
        if market_data.high_24h > 0 and market_data.low_24h > 0:
            return (market_data.high_24h - market_data.low_24h) / market_data.price * 100
        return 2.0
    except:
        return 2.0

async def process_live_data():
    """Process live data with AI"""
    global live_signals, market_analysis, data_status
    
    while True:
        try:
            # Get live data
            live_data = live_data_engine.get_live_data()
            
            if not live_data:
                await asyncio.sleep(5)
                continue
            
            # Update status
            data_status["status"] = "running"
            data_status["exchanges_connected"] = len(set(data.exchange for data in live_data.values()))
            data_status["last_update"] = datetime.now().isoformat()
            
            # Process each symbol with AI
            for key, market_data in live_data.items():
                if market_data.status != "live":
                    continue
                
                # Convert to AI input format
                ai_input = {
                    'symbol': market_data.symbol,
                    'score': calculate_technical_score(market_data),
                    'spread_bps': market_data.spread,
                    'qvol_usdt': market_data.volume_usdt,
                    'atr_pct': calculate_atr(market_data),
                    'liquidity_edge': calculate_liquidity_edge(market_data),
                    'momentum_edge': calculate_momentum_edge(market_data),
                    'price': market_data.price,
                    'change_24h': market_data.change_percent_24h,
                    'volume_24h': market_data.volume_24h,
                    'high_24h': market_data.high_24h,
                    'low_24h': market_data.low_24h,
                    'bid': market_data.bid,
                    'ask': market_data.ask,
                    'timestamp': market_data.timestamp
                }
                
                # AI Analysis
                ai_signal = await ai_engine.analyze_market(ai_input)
                live_signals[key] = ai_signal
                
                # Store market analysis
                market_analysis[key] = {
                    'live_data': market_data,
                    'ai_signal': ai_signal,
                    'technical_score': ai_input['score'],
                    'timestamp': datetime.now().isoformat()
                }
            
            # Wait before next processing
            await asyncio.sleep(10)
            
        except Exception as e:
            logger.error(f"Error processing live data: {e}")
            await asyncio.sleep(30)

# Health endpoint
@app.get("/health")
async def health():
    return {
        "status": "ok",
        "message": "Nexus Alpha Live Simple is running",
        "ai_status": "ACTIVE",
        "data_status": data_status,
        "live_signals_count": len(live_signals)
    }

# Live Rankings endpoint
@app.get("/rankings")
async def live_rankings(top: int = 10, profile: str = "scalp"):
    """Live AI rankings with real market data."""
    if not live_signals:
        return {"items": [], "message": "No live data available yet", "status": "waiting"}
    
    # Sort by AI confidence and technical score
    sorted_signals = sorted(
        market_analysis.items(),
        key=lambda x: (x[1]['ai_signal'].confidence, x[1]['technical_score']),
        reverse=True
    )
    
    items = []
    for i, (key, analysis) in enumerate(sorted_signals[:top]):
        ai_signal = analysis['ai_signal']
        live_data = analysis['live_data']
        
        # Determine bias based on AI action
        if ai_signal.action == "BUY":
            bias = "Long"
        elif ai_signal.action == "SELL":
            bias = "Short"
        else:
            bias = "Neutral"
        
        # Live data flags
        flags = []
        if ai_signal.confidence > 80:
            flags.append({"name": "AI High Confidence", "active": True})
        if ai_signal.risk_level == "LOW":
            flags.append({"name": "AI Low Risk", "active": True})
        if live_data.volume_usdt > 10000000:
            flags.append({"name": "High Volume", "active": True})
        if live_data.spread < 5:
            flags.append({"name": "Tight Spread", "active": True})
        
        items.append({
            "symbol": f"{live_data.symbol} {live_data.exchange.upper()}",
            "rank": i + 1,
            "score": round(analysis['technical_score'], 1),
            "bias": bias,
            "confidence": round(ai_signal.confidence, 1),
            "liquidity_edge": round(calculate_liquidity_edge(live_data), 2),
            "momentum_edge": round(calculate_momentum_edge(live_data), 2),
            "spread_bps": round(live_data.spread, 1),
            "slip_bps": round(live_data.spread * 0.5, 1),
            "atr_pct": round(calculate_atr(live_data), 2),
            "qvol_usdt": int(live_data.volume_usdt),
            "price": round(live_data.price, 2),
            "change_24h": round(live_data.change_percent_24h, 2),
            "flags": flags,
            "ai_action": ai_signal.action,
            "ai_risk": ai_signal.risk_level,
            "ai_duration": ai_signal.expected_duration,
            "ai_reasoning": ai_signal.reasoning,
            "live_timestamp": analysis['timestamp'],
            "exchange": live_data.exchange
        })
    
    return {
        "items": items,
        "profile": profile,
        "total": len(items),
        "live_data": True,
        "data_status": data_status
    }

# Live Status endpoint
@app.get("/live/status")
async def live_status():
    """Get live data collection status."""
    return {
        "data_status": data_status,
        "exchanges": list(live_data_engine.exchanges.keys()),
        "symbols": live_data_engine.symbols,
        "live_signals_count": len(live_signals),
        "market_data_count": len(live_data_engine.market_data)
    }

# Root endpoint
@app.get("/")
async def root():
    return {
        "message": "Nexus Alpha Live Simple - Real-time AI Trading System",
        "version": "3.0.0",
        "status": "running",
        "ai_engine": "ACTIVE",
        "live_data": "ACTIVE",
        "endpoints": {
            "rankings": "/rankings",
            "live_status": "/live/status",
            "health": "/health"
        }
    }

# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize live data and AI on startup."""
    logger.info("Initializing Nexus Alpha Live Simple...")
    
    # Start live data collection in background
    asyncio.create_task(live_data_engine.start_live_data())
    
    # Start AI processing in background
    asyncio.create_task(process_live_data())
    
    logger.info("Live data and AI processing started")

if __name__ == "__main__":
    print("Nexus Alpha Live Simple - Real-time AI Trading System")
    print("=" * 60)
    print("Live Data: Real-time market data from exchanges")
    print("AI Engine: Autonomous decision making with live data")
    print("=" * 60)
    print("Starting server on http://localhost:8014")
    print("Access the live rankings at: http://localhost:8014/rankings")
    print("Press Ctrl+C to stop")
    print("=" * 60)
    
    uvicorn.run(app, host="0.0.0.0", port=8014)
