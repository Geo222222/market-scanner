#!/usr/bin/env python3
"""
Nexus Alpha AI-Enhanced Application
Intelligent trading system with autonomous decision making
"""
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import HTMLResponse
from pathlib import Path
import uvicorn
import random
import asyncio
from datetime import datetime
import json

# Import our AI engine
from ai_engine import ai_engine, AISignal

# Create FastAPI app
app = FastAPI(
    title="Nexus Alpha AI",
    description="The Intelligent Trading Ecosystem with AI Decision Making",
    version="2.0.0"
)

# Global state for AI-enhanced data
ai_signals = {}
ai_insights = {}
market_analysis = {}

async def generate_ai_enhanced_data():
    """Generate AI-enhanced market data with intelligent signals"""
    global ai_signals, ai_insights, market_analysis
    
    mock_symbols = [
        "BTC/USDT:USDT", "ETH/USDT:USDT", "BNB/USDT:USDT", 
        "ADA/USDT:USDT", "SOL/USDT:USDT", "XRP/USDT:USDT",
        "DOT/USDT:USDT", "DOGE/USDT:USDT", "AVAX/USDT:USDT", "MATIC/USDT:USDT"
    ]
    
    ai_signals = {}
    market_analysis = {}
    
    for symbol in mock_symbols:
        # Generate base market data
        base_data = {
            'symbol': symbol,
            'score': round(random.uniform(20, 80), 2),
            'spread_bps': round(random.uniform(2, 15), 1),
            'qvol_usdt': random.randint(1000000, 50000000),
            'atr_pct': round(random.uniform(0.5, 3.0), 2),
            'liquidity_edge': round(random.uniform(-2, 5), 2),
            'momentum_edge': round(random.uniform(-3, 4), 2),
            'timestamp': datetime.now().isoformat()
        }
        
        # AI Analysis
        ai_signal = await ai_engine.analyze_market(base_data)
        ai_signals[symbol] = ai_signal
        
        # Store market analysis
        market_analysis[symbol] = {
            'base_data': base_data,
            'ai_signal': ai_signal,
            'ai_confidence': ai_signal.confidence,
            'ai_action': ai_signal.action,
            'ai_risk': ai_signal.risk_level
        }
    
    # Generate AI insights
    ai_insights = await ai_engine.get_ai_insights()

# Health endpoint
@app.get("/health")
async def health():
    return {
        "status": "ok", 
        "message": "Nexus Alpha AI is running",
        "ai_status": "ACTIVE",
        "ai_engine": "ONLINE"
    }

# AI Dashboard endpoint
@app.get("/dashboard", response_class=HTMLResponse)
async def ai_dashboard():
    """Serve the AI-enhanced Signal Intelligence Dashboard."""
    template_path = Path(__file__).parent / "src" / "templates" / "nexus-ai-dashboard.html"
    
    if not template_path.exists():
        raise HTTPException(status_code=404, detail="AI Dashboard not found")
    
    with open(template_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    return HTMLResponse(content=content)

# AI Rankings endpoint with intelligent signals
@app.get("/rankings")
async def ai_rankings(top: int = 10, profile: str = "scalp"):
    """AI-enhanced rankings with intelligent decision making."""
    if not ai_signals:
        await generate_ai_enhanced_data()
    
    # Sort by AI confidence and score
    sorted_signals = sorted(
        market_analysis.items(),
        key=lambda x: (x[1]['ai_confidence'], x[1]['base_data']['score']),
        reverse=True
    )
    
    items = []
    for i, (symbol, analysis) in enumerate(sorted_signals[:top]):
        ai_signal = analysis['ai_signal']
        base_data = analysis['base_data']
        
        # Determine bias based on AI action
        if ai_signal.action == "BUY":
            bias = "Long"
        elif ai_signal.action == "SELL":
            bias = "Short"
        else:
            bias = "Neutral"
        
        # AI-enhanced flags
        flags = []
        if ai_signal.confidence > 80:
            flags.append({"name": "AI High Confidence", "active": True})
        if ai_signal.risk_level == "LOW":
            flags.append({"name": "AI Low Risk", "active": True})
        if ai_signal.expected_duration == "SCALP":
            flags.append({"name": "AI Scalp Signal", "active": True})
        
        items.append({
            "symbol": f"{symbol} AI",
            "rank": i + 1,
            "score": base_data['score'],
            "bias": bias,
            "confidence": round(ai_signal.confidence, 1),
            "liquidity_edge": base_data['liquidity_edge'],
            "momentum_edge": base_data['momentum_edge'],
            "spread_bps": base_data['spread_bps'],
            "slip_bps": round(random.uniform(1, 8), 1),
            "atr_pct": base_data['atr_pct'],
            "qvol_usdt": base_data['qvol_usdt'],
            "flags": flags,
            "ai_action": ai_signal.action,
            "ai_risk": ai_signal.risk_level,
            "ai_duration": ai_signal.expected_duration,
            "ai_reasoning": ai_signal.reasoning
        })
    
    return {
        "items": items, 
        "profile": profile, 
        "total": len(items),
        "ai_enhanced": True,
        "ai_insights": ai_insights
    }

# AI Opportunities endpoint
@app.get("/opportunities")
async def ai_opportunities(symbol: str = None, profile: str = "scalp", top: int = 5):
    """AI-enhanced opportunities with intelligent analysis."""
    if not ai_signals:
        await generate_ai_enhanced_data()
    
    if symbol and symbol in market_analysis:
        analysis = market_analysis[symbol]
        ai_signal = analysis['ai_signal']
        base_data = analysis['base_data']
        
        return {
            "symbol": f"{symbol} AI",
            "score": base_data['score'],
            "bias": "Long" if ai_signal.action == "BUY" else "Short" if ai_signal.action == "SELL" else "Neutral",
            "confidence": round(ai_signal.confidence, 1),
            "liquidity_edge": base_data['liquidity_edge'],
            "momentum_edge": base_data['momentum_edge'],
            "spread_bps": base_data['spread_bps'],
            "slip_bps": round(random.uniform(1, 6), 1),
            "atr_pct": base_data['atr_pct'],
            "qvol_usdt": base_data['qvol_usdt'],
            "price": round(random.uniform(20000, 70000), 2),
            "flags": [
                {"name": f"AI {ai_signal.action}", "active": True},
                {"name": f"AI {ai_signal.risk_level} Risk", "active": True},
                {"name": f"AI {ai_signal.expected_duration}", "active": True}
            ],
            "ai_analysis": {
                "action": ai_signal.action,
                "confidence": ai_signal.confidence,
                "risk_level": ai_signal.risk_level,
                "expected_duration": ai_signal.expected_duration,
                "reasoning": ai_signal.reasoning,
                "insights": ai_signal.ai_insights,
                "market_conditions": ai_signal.market_conditions
            }
        }
    else:
        return await ai_rankings(top=top, profile=profile)

# AI Insights endpoint
@app.get("/ai/insights")
async def get_ai_insights(symbol: str = None):
    """Get AI insights and recommendations."""
    if not ai_insights:
        await generate_ai_enhanced_data()
    
    if symbol:
        return await ai_engine.get_ai_insights(symbol)
    else:
        return ai_insights

# AI Learning endpoint
@app.get("/ai/learning")
async def get_ai_learning():
    """Get AI learning status and memory."""
    return {
        "ai_engine_status": "ACTIVE",
        "learning_rate": ai_engine.learning_rate,
        "confidence_threshold": ai_engine.confidence_threshold,
        "symbols_monitored": len(ai_engine.market_memory),
        "total_decisions": sum(len(decisions) for decisions in ai_engine.market_memory.values()),
        "ai_capabilities": [
            "Pattern Recognition",
            "Risk Assessment", 
            "Sentiment Analysis",
            "Autonomous Decision Making",
            "Continuous Learning",
            "Market Adaptation"
        ]
    }

# AI Control endpoint
@app.post("/ai/refresh")
async def refresh_ai_analysis(background_tasks: BackgroundTasks):
    """Refresh AI analysis with new data."""
    background_tasks.add_task(generate_ai_enhanced_data)
    return {"message": "AI analysis refresh initiated", "status": "processing"}

# Root endpoint
@app.get("/")
async def root():
    return {
        "message": "Nexus Alpha AI - Intelligent Trading Ecosystem",
        "version": "2.0.0",
        "status": "running",
        "ai_engine": "ACTIVE",
        "endpoints": {
            "dashboard": "/dashboard",
            "rankings": "/rankings",
            "opportunities": "/opportunities",
            "ai_insights": "/ai/insights",
            "ai_learning": "/ai/learning",
            "ai_refresh": "/ai/refresh",
            "health": "/health"
        }
    }

# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize AI engine on startup."""
    print("AI: Initializing Nexus Alpha AI Engine...")
    await generate_ai_enhanced_data()
    print("AI: Engine ready - Autonomous decision making active")

if __name__ == "__main__":
    print("Nexus Alpha AI - Intelligent Trading Ecosystem")
    print("=" * 60)
    print("AI Engine: Pattern Recognition, Risk Assessment, Sentiment Analysis")
    print("Autonomous Decision Making: BUY/SELL/HOLD with reasoning")
    print("Continuous Learning: Adapts to market conditions")
    print("=" * 60)
    print("Starting server on http://localhost:8012")
    print("Access the AI dashboard at: http://localhost:8012/dashboard")
    print("Press Ctrl+C to stop")
    print("=" * 60)
    
    uvicorn.run(app, host="0.0.0.0", port=8012)
