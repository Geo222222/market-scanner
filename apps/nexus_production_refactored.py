"""
Nexus Alpha Production System - REFACTORED
Production-grade multi-exchange AI trading system with proper concurrency controls
"""

import os
import asyncio
import logging
import random
from datetime import datetime
from typing import Dict, List, Optional
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, BackgroundTasks, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import uvicorn

# Import from installed package
from market_scanner.engines.live_data_engine_refactored import live_data_engine_refactored, LiveMarketData
from market_scanner.engines.ai_engine import ai_engine, AISignal
from market_scanner.engines.ai_engine_enhanced import enhanced_ai_engine, AISignalEnhanced
from market_scanner.feeds.collector import start_data_collection, stop_data_collection, data_collector_manager
from market_scanner.feeds.events import FeedEvent, FeedEventType
from market_scanner.feeds.validators import FeedDataFormatter
from market_scanner.routers import ml_status, level2, rankings, chart_data, live_chart
from market_scanner.jobs.loop import loop as scanner_loop
from market_scanner.logging_config import configure_production_logging, get_logger

# Configure production-grade logging (suppresses WebSocket debug spam)
log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)
log_file = log_dir / f"nexus_{datetime.now().strftime('%Y%m%d')}.log"

configure_production_logging(
    log_level="INFO",  # Changed from DEBUG to INFO for production
    log_file=log_file,
    enable_file_logging=True,
    enable_console_logging=True
)

logger = get_logger(__name__)
logger.info(f"Logging to file: {log_file}")


# ============================================================================
# THREAD-SAFE STATE MANAGEMENT
# ============================================================================

class ThreadSafeState:
    """Thread-safe state management with async locks."""
    
    def __init__(self):
        self._lock = asyncio.Lock()
        self._production_data: Dict = {}
        self._websocket_data: Dict = {}
        self._system_metrics = {
            "uptime": 0,
            "signals_generated": 0,
            "data_quality": 0.0,
            "last_update": None,
            "exchanges_connected": 0,
            "websocket_events_received": 0,
            "websocket_events_processed": 0,
            "errors": 0,
            "last_error": None,
            "error_details": []
        }
        self._background_task: Optional[asyncio.Task] = None
        self._is_shutting_down = False
        
    async def get_production_data(self, symbol: Optional[str] = None) -> Dict:
        """Thread-safe read of production data."""
        async with self._lock:
            if symbol:
                return self._production_data.get(symbol, {})
            return self._production_data.copy()
    
    async def set_production_data(self, symbol: str, data: Dict) -> None:
        """Thread-safe write of production data."""
        async with self._lock:
            self._production_data[symbol] = data
    
    async def get_websocket_data(self, symbol: Optional[str] = None) -> Dict:
        """Thread-safe read of websocket data."""
        async with self._lock:
            if symbol:
                return self._websocket_data.get(symbol, {})
            return self._websocket_data.copy()
    
    async def update_websocket_data(self, symbol: str, event_type: str, data: Dict) -> None:
        """Thread-safe update of websocket data."""
        async with self._lock:
            if symbol not in self._websocket_data:
                self._websocket_data[symbol] = {
                    "trades": [],
                    "tickers": [],
                    "order_books": [],
                    "funding_rates": [],
                    "last_update": None
                }
            
            if event_type == "trade":
                self._websocket_data[symbol]["trades"].append(data)
                if len(self._websocket_data[symbol]["trades"]) > 100:
                    self._websocket_data[symbol]["trades"] = self._websocket_data[symbol]["trades"][-100:]
            
            elif event_type == "ticker":
                self._websocket_data[symbol]["tickers"].append(data)
                if len(self._websocket_data[symbol]["tickers"]) > 10:
                    self._websocket_data[symbol]["tickers"] = self._websocket_data[symbol]["tickers"][-10:]
            
            elif event_type == "order_book":
                self._websocket_data[symbol]["order_books"].append(data)
                if len(self._websocket_data[symbol]["order_books"]) > 5:
                    self._websocket_data[symbol]["order_books"] = self._websocket_data[symbol]["order_books"][-5:]
            
            elif event_type == "funding":
                self._websocket_data[symbol]["funding_rates"].append(data)
                if len(self._websocket_data[symbol]["funding_rates"]) > 5:
                    self._websocket_data[symbol]["funding_rates"] = self._websocket_data[symbol]["funding_rates"][-5:]
            
            self._websocket_data[symbol]["last_update"] = datetime.now()
    
    async def get_metrics(self) -> Dict:
        """Thread-safe read of system metrics."""
        async with self._lock:
            return self._system_metrics.copy()
    
    async def increment_metric(self, key: str, value: int = 1) -> None:
        """Thread-safe increment of metric."""
        async with self._lock:
            if key in self._system_metrics:
                self._system_metrics[key] += value
    
    async def update_metric(self, key: str, value) -> None:
        """Thread-safe update of metric."""
        async with self._lock:
            self._system_metrics[key] = value
    
    async def record_error(self, error: Exception, context: str = "") -> None:
        """Thread-safe error recording."""
        async with self._lock:
            self._system_metrics["errors"] += 1
            error_info = {
                "timestamp": datetime.now(),
                "error": str(error),
                "type": type(error).__name__,
                "context": context
            }
            self._system_metrics["last_error"] = error_info
            self._system_metrics["error_details"].append(error_info)
            # Keep only last 50 errors
            if len(self._system_metrics["error_details"]) > 50:
                self._system_metrics["error_details"] = self._system_metrics["error_details"][-50:]
    
    def set_background_task(self, task: asyncio.Task) -> None:
        """Register the background processing task."""
        self._background_task = task
    
    async def shutdown(self) -> None:
        """Gracefully shutdown background tasks."""
        self._is_shutting_down = True
        if self._background_task and not self._background_task.done():
            self._background_task.cancel()
            try:
                await self._background_task
            except asyncio.CancelledError:
                logger.info("Background task cancelled successfully")
    
    def is_shutting_down(self) -> bool:
        """Check if system is shutting down."""
        return self._is_shutting_down


# Global state instance
app_state = ThreadSafeState()


# ============================================================================
# PYDANTIC MODELS
# ============================================================================

class ProductionMetrics(BaseModel):
    uptime: float
    signals_generated: int
    data_quality: float
    last_update: Optional[datetime]
    exchanges_connected: int
    websocket_events_received: int
    websocket_events_processed: int
    errors: int
    last_error: Optional[Dict] = None


class ProductionSignal(BaseModel):
    symbol: str
    action: str
    confidence: float
    risk_level: str
    reasoning: str
    timestamp: datetime
    price_target: Optional[float] = None
    stop_loss: Optional[float] = None


class ErrorResponse(BaseModel):
    error: str
    timestamp: datetime
    details: Optional[str] = None


# ============================================================================
# LIFESPAN MANAGEMENT (Modern FastAPI approach)
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Modern FastAPI lifespan management."""
    logger.info("=" * 70)
    logger.info("Initializing Nexus Alpha Production System REFACTORED...")
    logger.info("=" * 70)
    
    # Startup
    try:
        # CRITICAL FIX: Start the main scanner loop for Redis-backed data
        scanner_task = asyncio.create_task(scanner_loop())
        logger.info("✅ Scanner loop started - will populate Redis with real exchange data")
        
        # Start WebSocket data collection
        symbols = ['BTC-USDT', 'ETH-USDT', 'BNB-USDT', 'ADA-USDT', 'SOL-USDT', 
                  'XRP-USDT', 'DOT-USDT', 'DOGE-USDT', 'AVAX-USDT', 'MATIC-USDT']
        
        collector = await start_data_collection(symbols)
        
        # Add event handler
        async def event_handler(event: FeedEvent):
            await handle_websocket_event(event)
        
        collector.add_event_handler(event_handler)
        logger.info("WebSocket data collection started")
        
        # Start background processing
        task = asyncio.create_task(background_processor())
        app_state.set_background_task(task)
        logger.info("Background processor started")
        
        logger.info("Production system REFACTORED started successfully")
        logger.info("=" * 70)
        
        yield  # Application runs here
        
    except Exception as e:
        logger.error(f"Startup error: {e}")
        await app_state.record_error(e, "startup")
        raise
    
    finally:
        # Shutdown
        logger.info("Shutting down Nexus Alpha Production System...")
        
        try:
            await app_state.shutdown()
            await stop_data_collection()
            logger.info("WebSocket data collection stopped")
        except Exception as e:
            logger.error(f"Shutdown error: {e}")
        
        logger.info("Production system shutdown complete")


# ============================================================================
# FASTAPI APPLICATION
# ============================================================================

app = FastAPI(
    title="Nexus Alpha Production REFACTORED",
    description="Production-grade Multi-Exchange AI Trading System",
    version="2.0.0",
    lifespan=lifespan
)

# Serve static assets and templates
base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
static_dir = os.path.join(base_dir, 'src', 'market_scanner', 'static')
templates_dir = os.path.join(base_dir, 'src', 'market_scanner', 'templates')

logger.info(f"Static directory: {static_dir}")
logger.info(f"Templates directory: {templates_dir}")
logger.info(f"Static directory exists: {os.path.isdir(static_dir)}")
logger.info(f"Templates directory exists: {os.path.isdir(templates_dir)}")

if os.path.isdir(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")
    logger.info("Static files mounted successfully")
else:
    logger.warning(f"Static directory not found: {static_dir}")

# Initialize Jinja2 templates
templates = Jinja2Templates(directory=templates_dir)

# Include ML status router
app.include_router(ml_status.router, prefix="/api", tags=["ml"])
# Set app state getter for ML status router to access production data
ml_status.set_app_state_getter(app_state.get_production_data)
logger.info("ML status router included with production data access")

# Include Level 2 order book router
app.include_router(level2.router, prefix="/api", tags=["level2"])
# Set app state for Level 2 router to access WebSocket data
level2.set_app_state(app_state)
logger.info("Level 2 router included with WebSocket data access")

# Include Chart Data router for live OHLCV data
app.include_router(chart_data.router, tags=["chart"])
logger.info("Chart data router included for live price charts")

# Include Live Chart WebSocket router for real-time streaming
app.include_router(live_chart.router, tags=["websocket", "live"])
logger.info("Live chart WebSocket router included for real-time price streaming")

# NOTE: Rankings router requires Redis - not suitable for standalone mode
# app.include_router(rankings.router, prefix="/rankings", tags=["rankings"])
# logger.info("Rankings router included - will serve Redis-backed data from scanner_loop")


# ============================================================================
# EVENT HANDLERS
# ============================================================================

async def handle_websocket_event(event: FeedEvent):
    """Handle WebSocket events from data collector with thread safety."""
    try:
        await app_state.increment_metric("websocket_events_received")
        
        # Format event for storage
        formatted_event = FeedDataFormatter.format_for_ui(event)
        
        # Determine event type
        event_type_map = {
            FeedEventType.TRADE: "trade",
            FeedEventType.TICKER: "ticker",
            FeedEventType.ORDER_BOOK: "order_book",
            FeedEventType.FUNDING: "funding"
        }
        
        event_type = event_type_map.get(event.event_type, "unknown")
        
        # Thread-safe update
        await app_state.update_websocket_data(event.symbol, event_type, formatted_event)
        await app_state.increment_metric("websocket_events_processed")
        
        logger.debug(f"Processed {event.event_type.value} event for {event.symbol}")
        
    except Exception as e:
        logger.error(f"Error handling WebSocket event: {e}")
        await app_state.record_error(e, f"websocket_event:{event.symbol}")


# ============================================================================
# BACKGROUND PROCESSING
# ============================================================================

async def process_production_data():
    """Process production data with AI analysis (thread-safe)."""
    try:
        # Get live data (non-blocking)
        symbols = ['BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'ADA/USDT', 'SOL/USDT', 
                  'XRP/USDT', 'DOT/USDT', 'DOGE/USDT', 'AVAX/USDT', 'MATIC/USDT']
        
        live_data = await live_data_engine_refactored.get_live_data(symbols)
        
        processed_count = 0
        error_count = 0
        
        # Process each symbol
        for symbol, market_data in live_data.items():
            try:
                if isinstance(market_data, LiveMarketData):
                    # Convert to dict for AI processing
                    data_dict = {
                        'symbol': market_data.symbol,
                        'price': market_data.price,
                        'volume': market_data.volume,
                        'spread': market_data.spread,
                        'change_24h': market_data.change_24h,
                        'high_24h': market_data.high_24h,
                        'low_24h': market_data.low_24h,
                        'timestamp': market_data.timestamp,
                        'exchange': market_data.exchange,
                        'status': market_data.status
                    }
                    
                    # Generate enhanced AI signal
                    signal = enhanced_ai_engine.analyze_market_data_enhanced(data_dict)
                    
                    # Thread-safe storage
                    await app_state.set_production_data(symbol, {
                        'signal': signal,
                        'price': market_data.price,
                        'volume': market_data.volume,
                        'change_24h': market_data.change_24h,
                        'status': market_data.status,
                        'timestamp': market_data.timestamp,
                        'exchange': market_data.exchange
                    })
                    
                    await app_state.increment_metric('signals_generated')
                    processed_count += 1
                    
                else:
                    logger.warning(f"Invalid market data type for {symbol}: {type(market_data)}")
                    error_count += 1
                    
            except Exception as e:
                logger.error(f"Error processing {symbol}: {e}")
                await app_state.record_error(e, f"process_symbol:{symbol}")
                error_count += 1
        
        # Update metrics
        await app_state.update_metric('last_update', datetime.now())
        await app_state.update_metric('data_quality', min(1.0, processed_count / len(symbols)))
        
        production_data = await app_state.get_production_data()
        exchanges = set(
            data.get('exchange', 'unknown') 
            for data in production_data.values() 
            if isinstance(data, dict)
        )
        await app_state.update_metric('exchanges_connected', len(exchanges))
        
        logger.info(f"Processed {processed_count} symbols ({error_count} errors)")
        
    except Exception as e:
        logger.error(f"Error in production data processing: {e}")
        await app_state.record_error(e, "process_production_data")


async def background_processor():
    """Background task for continuous data processing with graceful shutdown."""
    logger.info("Background processor starting...")
    
    while not app_state.is_shutting_down():
        try:
            await process_production_data()
            await asyncio.sleep(5)  # Process every 5 seconds
            
        except asyncio.CancelledError:
            logger.info("Background processor cancelled")
            break
            
        except Exception as e:
            logger.error(f"Error in background processor: {e}")
            await app_state.record_error(e, "background_processor")
            await asyncio.sleep(10)  # Wait longer on error
    
    logger.info("Background processor stopped")


# ============================================================================
# API ENDPOINTS
# ============================================================================

@app.get("/", response_class=HTMLResponse)
async def dashboard():
    """Main dashboard - serve the enhanced Nexus Alpha dashboard."""
    try:
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        dashboard_path = os.path.join(base_dir, 'src', 'market_scanner', 'templates', 'dashboard.html')
        
        with open(dashboard_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return HTMLResponse(content=content)
        
    except Exception as e:
        logger.error(f"Error loading dashboard: {e}")
        await app_state.record_error(e, "dashboard_load")
        return HTMLResponse(
            content=f"<h1>Dashboard Error</h1><p>Unable to load dashboard</p><p>{str(e)}</p>",
            status_code=500
        )


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard_alt():
    """Alternative dashboard route."""
    return await dashboard()


@app.get("/health")
async def health_check():
    """Health check endpoint with detailed status."""
    metrics = await app_state.get_metrics()
    
    is_healthy = (
        metrics.get('errors', 0) < 100 and  # Less than 100 total errors
        metrics.get('data_quality', 0) > 0.5  # At least 50% data quality
    )
    
    return {
        "status": "healthy" if is_healthy else "degraded",
        "timestamp": datetime.now(),
        "version": "2.0.0",
        "system": "Nexus Alpha Production REFACTORED",
        "metrics": {
            "signals_generated": metrics.get('signals_generated', 0),
            "data_quality": metrics.get('data_quality', 0),
            "errors": metrics.get('errors', 0)
        }
    }


@app.get("/metrics", response_model=ProductionMetrics)
async def get_metrics():
    """Get production metrics (thread-safe)."""
    metrics = await app_state.get_metrics()
    return ProductionMetrics(**metrics)


@app.get("/errors")
async def get_errors(limit: int = 20):
    """Get recent error details."""
    metrics = await app_state.get_metrics()
    error_details = metrics.get('error_details', [])
    return {
        "total_errors": metrics.get('errors', 0),
        "last_error": metrics.get('last_error'),
        "recent_errors": error_details[-limit:] if error_details else []
    }


@app.get("/websocket-data")
async def get_websocket_data():
    """Get real-time WebSocket data (thread-safe)."""
    websocket_data = await app_state.get_websocket_data()
    metrics = await app_state.get_metrics()
    
    return {
        "data": websocket_data,
        "metrics": {
            "events_received": metrics.get("websocket_events_received", 0),
            "events_processed": metrics.get("websocket_events_processed", 0),
            "symbols_count": len(websocket_data),
            "last_update": metrics.get("last_update")
        }
    }


@app.get("/websocket-health")
async def get_websocket_health():
    """Get WebSocket data collector health status."""
    health = data_collector_manager.get_all_health()
    metrics = await app_state.get_metrics()

    return {
        "status": "healthy" if all(h["status"] == "healthy" for h in health.values()) else "unhealthy",
        "collectors": health,
        "metrics": metrics
    }


@app.get("/api/csrf-token")
async def get_csrf_token():
    """CSRF token endpoint for dashboard (standalone mode - no CSRF needed)."""
    return {
        "token": "standalone-mode-no-csrf",
        "message": "CSRF protection disabled in standalone mode"
    }


@app.get("/live-chart/{symbol}", response_class=HTMLResponse)
async def get_live_chart(request: Request, symbol: str):
    """
    Serve live trading chart for a symbol.

    Real-time candlestick chart with WebSocket streaming, order book, and trades.
    Optimized for scalpers and day traders.
    """
    # Get AI signal data for this symbol
    production_data = await app_state.get_production_data()
    signal_data = production_data.get(symbol, {})

    # Extract AI analysis
    pattern = signal_data.get('pattern_detected', 'none')
    confidence = signal_data.get('ai_confidence', 0)
    action = signal_data.get('action', 'HOLD')
    insight = signal_data.get('ai_insight', 'No AI insight available')

    return templates.TemplateResponse("live_trading_chart.html", {
        "request": request,
        "symbol": symbol,
        "pattern": pattern,
        "confidence": confidence,
        "action": action,
        "insight": insight
    })


@app.get("/rankings")
async def get_rankings_standalone(
    top: int = 50,
    profile: str = "scalp",
    page: int = 1,
    page_size: int = 25
):
    """
    Standalone rankings endpoint using production data (no Redis required).
    Returns signals generated by the background processor.
    """
    try:
        # Get production data from app state
        production_data = await app_state.get_production_data()

        if not production_data:
            return []

        # Convert production data to rankings format
        rankings = []
        for symbol, data in production_data.items():
            if not isinstance(data, dict):
                continue

            signal = data.get('signal')

            # Handle AISignalEnhanced object or dict
            if signal:
                if hasattr(signal, 'action'):  # AISignalEnhanced object
                    action = signal.action
                    confidence = signal.confidence
                    price_target = signal.price_target
                    stop_loss = signal.stop_loss
                    ai_insight = signal.ai_insight or signal.ai_reasoning
                    pattern = signal.pattern_detected or 'N/A'
                    bias = 'Long' if action == 'BUY' else 'Short' if action == 'SELL' else 'Neutral'
                else:  # dict
                    action = signal.get('action', 'HOLD')
                    confidence = signal.get('confidence', 50.0)
                    price_target = signal.get('price_target')
                    stop_loss = signal.get('stop_loss')
                    ai_insight = signal.get('ai_insight', '')
                    pattern = signal.get('pattern_name', 'N/A')
                    bias = signal.get('bias', 'Neutral')
            else:
                action = 'HOLD'
                confidence = 50.0
                price_target = None
                stop_loss = None
                ai_insight = ''
                pattern = 'N/A'
                bias = 'Neutral'

            # Calculate metrics from available data
            price_val = data.get('price', 0.0)
            volume_val = data.get('volume', 0.0)
            change_24h_val = data.get('change_24h', 0.0)

            # Calculate spread from market data (estimate based on volatility)
            # Typical spread is 0.01-0.10% for liquid pairs, higher for volatile
            spread_estimate = abs(change_24h_val) * 0.05  # 5% of daily change as spread estimate
            spread_bps = max(1.0, min(50.0, spread_estimate * 100))  # Clamp between 1-50 bps

            # Calculate liquidity edge (volume-based metric)
            # Higher volume = better liquidity = higher edge
            # Normalize to 0-1 range based on typical volumes
            if volume_val > 0:
                liquidity_edge = min(1.0, volume_val / 10_000_000)  # 10M as reference
            else:
                liquidity_edge = 0.0

            # Calculate momentum edge (price change based)
            # Positive change = positive momentum
            momentum_edge = change_24h_val / 100.0  # Convert to decimal

            # Calculate ATR estimate (Average True Range as % of price)
            # Use 24h change as proxy for volatility
            atr_pct = abs(change_24h_val) / 100.0

            # Estimate slippage based on spread and volume
            # Lower volume = higher slippage
            if volume_val > 1_000_000:
                slip_bps = spread_bps * 0.5  # Low slippage for high volume
            elif volume_val > 100_000:
                slip_bps = spread_bps * 1.0  # Medium slippage
            else:
                slip_bps = spread_bps * 2.0  # High slippage for low volume

            # Estimate order book depth (top 5 levels)
            # Proportional to volume
            top5_depth_usdt = volume_val * 0.01  # 1% of volume as depth estimate

            # Create ranking item
            ranking = {
                'symbol': symbol,
                'price': price_val,
                'volume': volume_val,
                'change_24h': change_24h_val,
                'exchange': data.get('exchange', 'unknown'),
                'status': data.get('status', 'unknown'),
                'timestamp': data.get('timestamp', datetime.now().isoformat()),

                # AI Signal fields
                'action': action,
                'bias': bias,
                'ai_confidence': confidence,
                'price_target': price_target,
                'stop_loss': stop_loss,
                'ai_insight': ai_insight,
                'pattern_detected': pattern,

                # Scoring fields (use confidence as score)
                'score': confidence / 100.0,
                'qvol_usdt': volume_val,
                'spread_bps': round(spread_bps, 2),
                'atr_pct': round(atr_pct, 4),
                'slip_bps': round(slip_bps, 2),
                'top5_depth_usdt': round(top5_depth_usdt, 2),
                'liquidity_edge': round(liquidity_edge, 4),
                'momentum_edge': round(momentum_edge, 4),
                'ret_15': 0.0,  # Not available without historical data
                'ret15': 0.0,
                'ret_1': change_24h_val / 100.0,
                'ret1': change_24h_val / 100.0,

                # Optional fields
                'arbitrage_opportunity': False,
                'manip_score': None,
                'manip_flags': [],
                'flags': []
            }

            rankings.append(ranking)

        # Sort by confidence (descending)
        rankings.sort(key=lambda x: x.get('ai_confidence', 0), reverse=True)

        # Apply top limit
        rankings = rankings[:top]

        # Apply pagination
        start = (page - 1) * page_size
        end = start + page_size
        paged_rankings = rankings[start:end]

        return paged_rankings

    except Exception as e:
        logger.error(f"Error in standalone rankings: {e}")
        await app_state.record_error(e, "get_rankings_standalone")
        return []


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("Nexus Alpha Production REFACTORED - Multi-Exchange AI Trading System")
    print("=" * 70)
    print("Version: 2.0.0")
    print("Features: Thread-safe state, explicit lifecycle, error surfacing")
    print("Production Mode: Enhanced monitoring and reliability")
    print("=" * 70)
    print("Starting production server on http://localhost:8019")
    print("Access dashboard at: http://localhost:8019/")
    print("View rankings at: http://localhost:8019/rankings")
    print("View metrics at: http://localhost:8019/metrics")
    print("View errors at: http://localhost:8019/errors")
    print("API docs at: http://localhost:8019/docs")
    print("Press Ctrl+C to stop")
    print("=" * 70)
    
    uvicorn.run(app, host="0.0.0.0", port=8019, log_level="info")

