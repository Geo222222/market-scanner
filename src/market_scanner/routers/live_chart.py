"""Live chart WebSocket router for real-time price streaming."""
from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from pydantic import BaseModel
import ccxt

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ws", tags=["websocket"])


class ConnectionManager:
    """Manages WebSocket connections for live chart updates."""
    
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}
        self._price_cache: Dict[str, Dict] = {}
        self._update_tasks: Dict[str, asyncio.Task] = {}
    
    async def connect(self, websocket: WebSocket, symbol: str):
        """Accept new WebSocket connection."""
        await websocket.accept()
        
        if symbol not in self.active_connections:
            self.active_connections[symbol] = []
        
        self.active_connections[symbol].append(websocket)
        logger.info(f"WebSocket connected for {symbol}. Total connections: {len(self.active_connections[symbol])}")
        
        # Start price update task if not already running
        if symbol not in self._update_tasks or self._update_tasks[symbol].done():
            self._update_tasks[symbol] = asyncio.create_task(self._price_updater(symbol))
    
    def disconnect(self, websocket: WebSocket, symbol: str):
        """Remove WebSocket connection."""
        if symbol in self.active_connections:
            if websocket in self.active_connections[symbol]:
                self.active_connections[symbol].remove(websocket)
                logger.info(f"WebSocket disconnected for {symbol}. Remaining: {len(self.active_connections[symbol])}")
            
            # Stop update task if no more connections
            if len(self.active_connections[symbol]) == 0:
                if symbol in self._update_tasks and not self._update_tasks[symbol].done():
                    self._update_tasks[symbol].cancel()
                del self.active_connections[symbol]
    
    async def broadcast(self, symbol: str, message: dict):
        """Broadcast message to all connections for a symbol."""
        if symbol not in self.active_connections:
            return
        
        disconnected = []
        for connection in self.active_connections[symbol]:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.warning(f"Failed to send to connection: {e}")
                disconnected.append(connection)
        
        # Clean up disconnected clients
        for connection in disconnected:
            self.disconnect(connection, symbol)
    
    async def _price_updater(self, symbol: str):
        """Background task to fetch and broadcast price updates."""
        exchange = ccxt.okx({'enableRateLimit': True, 'verbose': False})
        normalized_symbol = symbol.replace('-', '/')
        
        logger.info(f"Started price updater for {symbol}")
        
        try:
            while symbol in self.active_connections and len(self.active_connections[symbol]) > 0:
                try:
                    # Fetch latest ticker
                    ticker = await asyncio.get_event_loop().run_in_executor(
                        None,
                        exchange.fetch_ticker,
                        normalized_symbol
                    )
                    
                    # Fetch recent trades for tick data
                    trades = await asyncio.get_event_loop().run_in_executor(
                        None,
                        exchange.fetch_trades,
                        normalized_symbol,
                        None,
                        10  # Last 10 trades
                    )
                    
                    # Prepare update message
                    update = {
                        "type": "price_update",
                        "symbol": normalized_symbol,
                        "timestamp": datetime.now().isoformat(),
                        "ticker": {
                            "last": ticker.get('last'),
                            "bid": ticker.get('bid'),
                            "ask": ticker.get('ask'),
                            "high": ticker.get('high'),
                            "low": ticker.get('low'),
                            "volume": ticker.get('volume'),
                            "change": ticker.get('percentage')
                        },
                        "trades": [
                            {
                                "price": trade['price'],
                                "amount": trade['amount'],
                                "side": trade['side'],
                                "timestamp": trade['timestamp']
                            }
                            for trade in trades[-5:]  # Last 5 trades
                        ]
                    }
                    
                    # Cache the update
                    self._price_cache[symbol] = update
                    
                    # Broadcast to all connected clients
                    await self.broadcast(symbol, update)
                    
                    # Update every 1 second for scalping
                    await asyncio.sleep(1.0)
                    
                except Exception as e:
                    logger.error(f"Error fetching price for {symbol}: {e}")
                    await asyncio.sleep(2.0)  # Back off on error
        
        except asyncio.CancelledError:
            logger.info(f"Price updater cancelled for {symbol}")
        except Exception as e:
            logger.error(f"Price updater error for {symbol}: {e}")


# Global connection manager
manager = ConnectionManager()


@router.websocket("/chart/{symbol}")
async def websocket_chart_endpoint(websocket: WebSocket, symbol: str):
    """
    WebSocket endpoint for real-time chart data.
    
    Streams live price updates every 1 second for scalping/day trading.
    
    Args:
        symbol: Trading pair (e.g., BTC-USDT)
    """
    await manager.connect(websocket, symbol)
    
    try:
        # Send initial cached data if available
        if symbol in manager._price_cache:
            await websocket.send_json(manager._price_cache[symbol])
        
        # Keep connection alive and handle client messages
        while True:
            try:
                # Wait for client messages (ping/pong, commands, etc.)
                data = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
                
                # Handle client commands
                try:
                    message = json.loads(data)
                    if message.get('type') == 'ping':
                        await websocket.send_json({'type': 'pong', 'timestamp': datetime.now().isoformat()})
                except json.JSONDecodeError:
                    pass
                    
            except asyncio.TimeoutError:
                # Send keepalive ping
                await websocket.send_json({'type': 'keepalive', 'timestamp': datetime.now().isoformat()})
                
    except WebSocketDisconnect:
        logger.info(f"Client disconnected from {symbol}")
    except Exception as e:
        logger.error(f"WebSocket error for {symbol}: {e}")
    finally:
        manager.disconnect(websocket, symbol)


@router.get("/chart/orderbook/{symbol}")
async def get_orderbook(
    symbol: str,
    depth: int = Query(default=10, ge=5, le=50)
):
    """
    Get current order book depth for a symbol.
    
    Args:
        symbol: Trading pair (e.g., BTC-USDT)
        depth: Number of levels to return (5-50)
    
    Returns:
        Order book with bids and asks
    """
    try:
        exchange = ccxt.okx({'enableRateLimit': True})
        normalized_symbol = symbol.replace('-', '/')
        
        # Fetch order book
        orderbook = await asyncio.get_event_loop().run_in_executor(
            None,
            exchange.fetch_order_book,
            normalized_symbol,
            depth
        )
        
        return {
            "symbol": normalized_symbol,
            "timestamp": datetime.now().isoformat(),
            "bids": [
                {"price": bid[0], "amount": bid[1], "total": bid[0] * bid[1]}
                for bid in orderbook['bids'][:depth]
            ],
            "asks": [
                {"price": ask[0], "amount": ask[1], "total": ask[0] * ask[1]}
                for ask in orderbook['asks'][:depth]
            ],
            "spread": orderbook['asks'][0][0] - orderbook['bids'][0][0] if orderbook['asks'] and orderbook['bids'] else 0,
            "spread_pct": ((orderbook['asks'][0][0] - orderbook['bids'][0][0]) / orderbook['bids'][0][0] * 100) if orderbook['asks'] and orderbook['bids'] else 0
        }
    
    except Exception as e:
        logger.error(f"Error fetching order book for {symbol}: {e}")
        return {
            "error": str(e),
            "symbol": symbol,
            "timestamp": datetime.now().isoformat()
        }


@router.get("/chart/recent-trades/{symbol}")
async def get_recent_trades(
    symbol: str,
    limit: int = Query(default=50, ge=10, le=100)
):
    """
    Get recent trades for a symbol.
    
    Args:
        symbol: Trading pair (e.g., BTC-USDT)
        limit: Number of trades to return (10-100)
    
    Returns:
        List of recent trades
    """
    try:
        exchange = ccxt.okx({'enableRateLimit': True})
        normalized_symbol = symbol.replace('-', '/')
        
        # Fetch recent trades
        trades = await asyncio.get_event_loop().run_in_executor(
            None,
            exchange.fetch_trades,
            normalized_symbol,
            None,
            limit
        )
        
        return {
            "symbol": normalized_symbol,
            "timestamp": datetime.now().isoformat(),
            "trades": [
                {
                    "price": trade['price'],
                    "amount": trade['amount'],
                    "side": trade['side'],
                    "timestamp": datetime.fromtimestamp(trade['timestamp'] / 1000).isoformat(),
                    "id": trade.get('id')
                }
                for trade in trades
            ],
            "count": len(trades)
        }
    
    except Exception as e:
        logger.error(f"Error fetching trades for {symbol}: {e}")
        return {
            "error": str(e),
            "symbol": symbol,
            "timestamp": datetime.now().isoformat()
        }

