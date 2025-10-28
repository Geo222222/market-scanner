#!/usr/bin/env python3
"""
Nexus Alpha Live Data Application
Real-time AI trading system with live market data
"""
from fastapi import FastAPI, HTTPException, BackgroundTasks
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
    title="Nexus Alpha Live",
    description="Real-time AI Trading System with Live Market Data",
    version="3.0.0"
)

# Global state
live_signals = {}
market_analysis = {}
ai_insights = {}
data_status = {"status": "starting", "exchanges_connected": 0, "last_update": None}

async def start_live_data_collection():
    """Start live data collection in background"""
    global data_status
    try:
        logger.info("Starting live data collection...")
        await live_data_engine.start_live_data()
    except Exception as e:
        logger.error(f"Error in live data collection: {e}")
        data_status["status"] = "error"
        data_status["error"] = str(e)

async def process_live_data_with_ai():
    """Process live data with AI engine"""
    global live_signals, market_analysis, ai_insights, data_status
    
    while True:
        try:
            # Get live data
            live_data = live_data_engine.get_live_data()
            
            if not live_data:
                await asyncio.sleep(5)
                continue
            
            # Update status
            data_status["status"] = "running"
            data_status["exchanges_connected"] = len(set(data.exchange for data in live_data_engine.market_data.values()))
            data_status["last_update"] = datetime.now().isoformat()
            
            # Process each symbol with AI
            for key, market_data in live_data.items():
                if market_data.status != "live":
                    continue
                
                # Convert to AI input format
                ai_input = {
                    'symbol': market_data.symbol,
                    'score': _calculate_technical_score(market_data),
                    'spread_bps': market_data.spread,
                    'qvol_usdt': market_data.volume_usdt,
                    'atr_pct': _calculate_atr(market_data),
                    'liquidity_edge': _calculate_liquidity_edge(market_data),
                    'momentum_edge': _calculate_momentum_edge(market_data),
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
            
            # Generate AI insights
            ai_insights = await ai_engine.get_ai_insights()
            
            # Wait before next processing
            await asyncio.sleep(10)  # Process every 10 seconds
            
        except Exception as e:
            logger.error(f"Error processing live data with AI: {e}")
            await asyncio.sleep(30)  # Wait longer on error

def _calculate_technical_score(market_data: LiveMarketData) -> float:
    """Calculate technical score from live data"""
    try:
        # Base score from price action
        score = 50.0
        
        # Volume factor
        if market_data.volume_usdt > 10000000:  # High volume
            score += 10
        elif market_data.volume_usdt < 1000000:  # Low volume
            score -= 10
        
        # Spread factor (lower spread = higher score)
        if market_data.spread < 5:  # Very tight spread
            score += 15
        elif market_data.spread < 10:  # Good spread
            score += 5
        elif market_data.spread > 20:  # Wide spread
            score -= 10
        
        # Price change factor
        if market_data.change_percent_24h > 5:  # Strong positive momentum
            score += 10
        elif market_data.change_percent_24h < -5:  # Strong negative momentum
            score -= 10
        
        # Volatility factor (based on high-low range)
        if market_data.high_24h > 0 and market_data.low_24h > 0:
            volatility = (market_data.high_24h - market_data.low_24h) / market_data.price * 100
            if volatility > 10:  # High volatility
                score += 5
            elif volatility < 2:  # Low volatility
                score -= 5
        
        return max(0, min(100, score))  # Clamp between 0-100
        
    except Exception as e:
        logger.error(f"Error calculating technical score: {e}")
        return 50.0

def _calculate_atr(market_data: LiveMarketData) -> float:
    """Calculate ATR from live data"""
    try:
        if market_data.high_24h > 0 and market_data.low_24h > 0:
            return (market_data.high_24h - market_data.low_24h) / market_data.price * 100
        return 2.0  # Default ATR
    except:
        return 2.0

def _calculate_liquidity_edge(market_data: LiveMarketData) -> float:
    """Calculate liquidity edge from live data"""
    try:
        # Based on volume and spread
        volume_factor = min(5, market_data.volume_usdt / 10000000)  # Scale volume
        spread_factor = max(-2, 5 - market_data.spread / 2)  # Lower spread = higher edge
        return volume_factor + spread_factor
    except:
        return 0.0

def _calculate_momentum_edge(market_data: LiveMarketData) -> float:
    """Calculate momentum edge from live data"""
    try:
        # Based on 24h change
        return market_data.change_percent_24h / 10  # Scale to reasonable range
    except:
        return 0.0

# Health endpoint
@app.get("/health")
async def health():
    return {
        "status": "ok",
        "message": "Nexus Alpha Live is running",
        "ai_status": "ACTIVE",
        "data_status": data_status,
        "live_signals_count": len(live_signals)
    }

# Live Dashboard endpoint
@app.get("/dashboard", response_class=HTMLResponse)
async def live_dashboard():
    """Serve the Live AI Trading Dashboard."""
    template_path = Path(__file__).parent / "src" / "templates" / "nexus-ai-dashboard.html"
    
    if not template_path.exists():
        raise HTTPException(status_code=404, detail="Live Dashboard not found")
    
    with open(template_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    return HTMLResponse(content=content)

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
            "liquidity_edge": round(_calculate_liquidity_edge(live_data), 2),
            "momentum_edge": round(_calculate_momentum_edge(live_data), 2),
            "spread_bps": round(live_data.spread, 1),
            "slip_bps": round(live_data.spread * 0.5, 1),  # Estimated slippage
            "atr_pct": round(_calculate_atr(live_data), 2),
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
        "data_status": data_status,
        "ai_insights": ai_insights
    }

# Live Opportunities endpoint
@app.get("/opportunities")
async def live_opportunities(symbol: str = None, profile: str = "scalp", top: int = 5):
    """Live AI opportunities with real market data."""
    if not live_signals:
        return {"message": "No live data available yet", "status": "waiting"}
    
    if symbol:
        # Find symbol in live data
        for key, analysis in market_analysis.items():
            if analysis['live_data'].symbol == symbol:
                live_data = analysis['live_data']
                ai_signal = analysis['ai_signal']
                
                return {
                    "symbol": f"{live_data.symbol} {live_data.exchange.upper()}",
                    "score": round(analysis['technical_score'], 1),
                    "bias": "Long" if ai_signal.action == "BUY" else "Short" if ai_signal.action == "SELL" else "Neutral",
                    "confidence": round(ai_signal.confidence, 1),
                    "liquidity_edge": round(_calculate_liquidity_edge(live_data), 2),
                    "momentum_edge": round(_calculate_momentum_edge(live_data), 2),
                    "spread_bps": round(live_data.spread, 1),
                    "slip_bps": round(live_data.spread * 0.5, 1),
                    "atr_pct": round(_calculate_atr(live_data), 2),
                    "qvol_usdt": int(live_data.volume_usdt),
                    "price": round(live_data.price, 2),
                    "change_24h": round(live_data.change_percent_24h, 2),
                    "flags": [
                        {"name": f"AI {ai_signal.action}", "active": True},
                        {"name": f"AI {ai_signal.risk_level} Risk", "active": True},
                        {"name": f"Live {live_data.exchange.upper()}", "active": True}
                    ],
                    "ai_analysis": {
                        "action": ai_signal.action,
                        "confidence": ai_signal.confidence,
                        "risk_level": ai_signal.risk_level,
                        "expected_duration": ai_signal.expected_duration,
                        "reasoning": ai_signal.reasoning,
                        "insights": ai_signal.ai_insights,
                        "market_conditions": ai_signal.market_conditions
                    },
                    "live_data": {
                        "exchange": live_data.exchange,
                        "timestamp": live_data.timestamp,
                        "bid": live_data.bid,
                        "ask": live_data.ask,
                        "volume_24h": live_data.volume_24h,
                        "high_24h": live_data.high_24h,
                        "low_24h": live_data.low_24h
                    }
                }
        
        return {"message": f"Symbol {symbol} not found in live data", "status": "not_found"}
    else:
        return await live_rankings(top=top, profile=profile)

# Live Data Status endpoint
@app.get("/live/status")
async def live_status():
    """Get live data collection status."""
    return {
        "data_status": data_status,
        "exchanges": list(live_data_engine.exchanges.keys()),
        "symbols": live_data_engine.symbols,
        "live_signals_count": len(live_signals),
        "market_data_count": len(live_data_engine.market_data),
        "ai_insights": ai_insights
    }

# Live Prices endpoint
@app.get("/live/prices")
async def live_prices():
    """Get latest live prices."""
    prices = live_data_engine.get_latest_prices()
    return {
        "prices": prices,
        "timestamp": datetime.now().isoformat(),
        "count": len(prices)
    }

# Root endpoint
@app.get("/")
async def root():
    return {
        "message": "Nexus Alpha Live - Real-time AI Trading System",
        "version": "3.0.0",
        "status": "running",
        "ai_engine": "ACTIVE",
        "live_data": "ACTIVE",
        "endpoints": {
            "dashboard": "/dashboard",
            "rankings": "/rankings",
            "opportunities": "/opportunities",
            "live_status": "/live/status",
            "live_prices": "/live/prices",
            "health": "/health"
        }
    }

# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize live data and AI on startup."""
    logger.info("Initializing Nexus Alpha Live...")
    
    # Start live data collection in background
    asyncio.create_task(start_live_data_collection())
    
    # Start AI processing in background
    asyncio.create_task(process_live_data_with_ai())
    
    logger.info("Live data and AI processing started")

if __name__ == "__main__":
    print("Nexus Alpha Live - Real-time AI Trading System")
    print("=" * 60)
    print("Live Data: Real-time market data from exchanges")
    print("AI Engine: Autonomous decision making with live data")
    print("Features: Live prices, AI signals, real-time analysis")
    print("=" * 60)
    print("Starting server on http://localhost:8013")
    print("Access the live dashboard at: http://localhost:8013/dashboard")
    print("Press Ctrl+C to stop")
    print("=" * 60)
    
    uvicorn.run(app, host="0.0.0.0", port=8013)
