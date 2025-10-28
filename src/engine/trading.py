"""Trading engine that executes signals from the market scanner."""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Tuple
from decimal import Decimal

import httpx
from pydantic import BaseModel

from ..adapters.ccxt_adapter import CCXTAdapter
from ..core.metrics import SymbolSnapshot
from ..config import get_settings

LOGGER = logging.getLogger(__name__)


class OrderSide(str, Enum):
    BUY = "buy"
    SELL = "sell"


class OrderType(str, Enum):
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"


class OrderStatus(str, Enum):
    PENDING = "pending"
    OPEN = "open"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


@dataclass
class Position:
    symbol: str
    side: OrderSide
    size: Decimal
    entry_price: Decimal
    current_price: Decimal
    unrealized_pnl: Decimal
    realized_pnl: Decimal = Decimal("0")
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc)


class Order(BaseModel):
    id: str
    symbol: str
    side: OrderSide
    type: OrderType
    amount: Decimal
    price: Optional[Decimal] = None
    stop_price: Optional[Decimal] = None
    status: OrderStatus = OrderStatus.PENDING
    filled_amount: Decimal = Decimal("0")
    average_price: Optional[Decimal] = None
    timestamp: datetime = None
    strategy_id: str = "scanner"

    def __init__(self, **data):
        if data.get("timestamp") is None:
            data["timestamp"] = datetime.now(timezone.utc)
        super().__init__(**data)


class TradingEngine:
    """Core trading engine that executes scanner signals."""
    
    def __init__(self, scanner_api_url: str = "http://localhost:8010"):
        self.scanner_api = scanner_api_url
        self.adapter = CCXTAdapter(get_settings().exchange)
        self.positions: Dict[str, Position] = {}
        self.orders: Dict[str, Order] = {}
        self.balance: Decimal = Decimal("10000")  # Starting balance
        self.max_position_size = Decimal("0.1")  # 10% max per position
        self.running = False
        
    async def start(self):
        """Start the trading engine."""
        self.running = True
        LOGGER.info("Trading engine started")
        
        # Start background tasks
        asyncio.create_task(self._signal_processor())
        asyncio.create_task(self._order_monitor())
        asyncio.create_task(self._position_monitor())
    
    async def stop(self):
        """Stop the trading engine."""
        self.running = False
        await self.adapter.close()
        LOGGER.info("Trading engine stopped")
    
    async def _signal_processor(self):
        """Process signals from the market scanner."""
        while self.running:
            try:
                # Get top opportunities from scanner
                async with httpx.AsyncClient() as client:
                    response = await client.get(
                        f"{self.scanner_api}/opportunities",
                        params={"profile": "scalp", "top": 5, "notional": 1000}
                    )
                    opportunities = response.json()
                
                for opp in opportunities.get("items", []):
                    await self._process_opportunity(opp)
                
                await asyncio.sleep(5)  # Check every 5 seconds
                
            except Exception as exc:
                LOGGER.error(f"Signal processing error: {exc}")
                await asyncio.sleep(10)
    
    async def _process_opportunity(self, opportunity: dict):
        """Process a single trading opportunity."""
        symbol = opportunity["symbol"]
        side_bias = opportunity["side_bias"]
        confidence = opportunity["confidence"]
        
        # Skip if confidence too low or already have position
        if confidence < 70 or symbol in self.positions:
            return
        
        # Skip if neutral bias
        if side_bias == "neutral":
            return
        
        # Check risk limits
        if not await self._check_risk_limits(symbol, opportunity):
            return
        
        # Create order
        side = OrderSide.BUY if side_bias == "long" else OrderSide.SELL
        amount = self._calculate_position_size(opportunity)
        
        order = Order(
            id=f"{symbol}_{int(datetime.now().timestamp())}",
            symbol=symbol,
            side=side,
            type=OrderType.MARKET,
            amount=amount
        )
        
        await self._submit_order(order)
    
    async def _check_risk_limits(self, symbol: str, opportunity: dict) -> bool:
        """Check if the opportunity passes risk limits."""
        # Check position size limit
        notional = opportunity.get("notional", 1000)
        if notional > self.balance * self.max_position_size:
            LOGGER.debug(f"Position size too large for {symbol}")
            return False
        
        # Check manipulation score
        manip_score = opportunity.get("manip_score")
        if manip_score and manip_score > 50:
            LOGGER.debug(f"Manipulation score too high for {symbol}: {manip_score}")
            return False
        
        # Check spread
        spread_bps = opportunity.get("spread_bps", 0)
        if spread_bps > 10:  # 10 bps max spread
            LOGGER.debug(f"Spread too wide for {symbol}: {spread_bps}bps")
            return False
        
        return True
    
    def _calculate_position_size(self, opportunity: dict) -> Decimal:
        """Calculate position size based on risk and opportunity."""
        notional = Decimal(str(opportunity.get("notional", 1000)))
        confidence = opportunity.get("confidence", 50)
        
        # Scale position size by confidence
        confidence_multiplier = Decimal(str(confidence)) / Decimal("100")
        max_size = self.balance * self.max_position_size * confidence_multiplier
        
        return min(notional, max_size)
    
    async def _submit_order(self, order: Order):
        """Submit order to exchange."""
        try:
            self.orders[order.id] = order
            
            # Convert to exchange format
            exchange_order = {
                "symbol": order.symbol,
                "side": order.side.value,
                "type": order.type.value,
                "amount": float(order.amount),
            }
            
            if order.price:
                exchange_order["price"] = float(order.price)
            
            # Submit to exchange
            result = await self.adapter.ex.create_order(**exchange_order)
            
            # Update order status
            order.status = OrderStatus.OPEN
            order.id = result["id"]  # Use exchange order ID
            
            LOGGER.info(f"Order submitted: {order.symbol} {order.side} {order.amount}")
            
        except Exception as exc:
            LOGGER.error(f"Order submission failed: {exc}")
            order.status = OrderStatus.REJECTED
    
    async def _order_monitor(self):
        """Monitor order status and update positions."""
        while self.running:
            try:
                for order_id, order in list(self.orders.items()):
                    if order.status in [OrderStatus.FILLED, OrderStatus.CANCELLED, OrderStatus.REJECTED]:
                        continue
                    
                    # Check order status
                    try:
                        status = await self.adapter.ex.fetch_order(order.id, order.symbol)
                        await self._update_order_status(order, status)
                    except Exception as exc:
                        LOGGER.debug(f"Order status check failed: {exc}")
                
                await asyncio.sleep(2)
                
            except Exception as exc:
                LOGGER.error(f"Order monitoring error: {exc}")
                await asyncio.sleep(5)
    
    async def _update_order_status(self, order: Order, status: dict):
        """Update order status from exchange response."""
        if status["filled"] > 0:
            order.filled_amount = Decimal(str(status["filled"]))
            order.average_price = Decimal(str(status["average"] or status["price"]))
            
            if status["status"] == "closed":
                order.status = OrderStatus.FILLED
                await self._update_position(order)
            else:
                order.status = OrderStatus.OPEN
        elif status["status"] == "canceled":
            order.status = OrderStatus.CANCELLED
        elif status["status"] == "rejected":
            order.status = OrderStatus.REJECTED
    
    async def _update_position(self, order: Order):
        """Update position when order is filled."""
        symbol = order.symbol
        
        if symbol in self.positions:
            # Update existing position
            position = self.positions[symbol]
            if position.side == order.side:
                # Add to position
                total_size = position.size + order.filled_amount
                total_value = (position.size * position.entry_price + 
                             order.filled_amount * order.average_price)
                position.entry_price = total_value / total_size
                position.size = total_size
            else:
                # Close/reduce position
                if order.filled_amount >= position.size:
                    # Position closed
                    del self.positions[symbol]
                else:
                    # Position reduced
                    position.size -= order.filled_amount
        else:
            # Create new position
            self.positions[symbol] = Position(
                symbol=symbol,
                side=order.side,
                size=order.filled_amount,
                entry_price=order.average_price,
                current_price=order.average_price,
                unrealized_pnl=Decimal("0")
            )
    
    async def _position_monitor(self):
        """Monitor positions and update P&L."""
        while self.running:
            try:
                for symbol, position in self.positions.items():
                    # Get current price
                    ticker = await self.adapter.ex.fetch_ticker(symbol)
                    current_price = Decimal(str(ticker["last"]))
                    position.current_price = current_price
                    
                    # Calculate unrealized P&L
                    if position.side == OrderSide.BUY:
                        position.unrealized_pnl = (current_price - position.entry_price) * position.size
                    else:
                        position.unrealized_pnl = (position.entry_price - current_price) * position.size
                
                await asyncio.sleep(10)  # Update every 10 seconds
                
            except Exception as exc:
                LOGGER.error(f"Position monitoring error: {exc}")
                await asyncio.sleep(30)
    
    def get_portfolio_status(self) -> dict:
        """Get current portfolio status."""
        total_unrealized = sum(pos.unrealized_pnl for pos in self.positions.values())
        total_realized = sum(pos.realized_pnl for pos in self.positions.values())
        
        return {
            "balance": float(self.balance),
            "total_pnl": float(total_unrealized + total_realized),
            "unrealized_pnl": float(total_unrealized),
            "realized_pnl": float(total_realized),
            "positions": [
                {
                    "symbol": pos.symbol,
                    "side": pos.side.value,
                    "size": float(pos.size),
                    "entry_price": float(pos.entry_price),
                    "current_price": float(pos.current_price),
                    "unrealized_pnl": float(pos.unrealized_pnl)
                }
                for pos in self.positions.values()
            ],
            "open_orders": len([o for o in self.orders.values() if o.status == OrderStatus.OPEN])
        }


# Global trading engine instance
_trading_engine: Optional[TradingEngine] = None


def get_trading_engine() -> TradingEngine:
    """Get the global trading engine instance."""
    global _trading_engine
    if _trading_engine is None:
        _trading_engine = TradingEngine()
    return _trading_engine
