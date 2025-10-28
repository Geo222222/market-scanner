"""Trading router for portfolio management and order execution."""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from ..engine.trading import get_trading_engine, TradingEngine, Order, OrderSide, OrderType

router = APIRouter()


class OrderRequest(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=64)
    side: OrderSide
    type: OrderType = OrderType.MARKET
    amount: float = Field(..., gt=0)
    price: Optional[float] = Field(None, gt=0)
    stop_price: Optional[float] = Field(None, gt=0)


class OrderResponse(BaseModel):
    id: str
    symbol: str
    side: str
    type: str
    amount: float
    price: Optional[float] = None
    stop_price: Optional[float] = None
    status: str
    filled_amount: float = 0.0
    average_price: Optional[float] = None
    timestamp: datetime
    strategy_id: str


class PositionResponse(BaseModel):
    symbol: str
    side: str
    size: float
    entry_price: float
    current_price: float
    unrealized_pnl: float
    realized_pnl: float = 0.0
    timestamp: datetime


class PortfolioResponse(BaseModel):
    balance: float
    total_pnl: float
    unrealized_pnl: float
    realized_pnl: float
    positions: List[PositionResponse]
    open_orders: int
    timestamp: datetime = Field(default_factory=datetime.now)


@router.get("/portfolio", response_model=PortfolioResponse)
async def get_portfolio(engine: TradingEngine = Depends(get_trading_engine)):
    """Get current portfolio status."""
    status = engine.get_portfolio_status()
    return PortfolioResponse(
        balance=status["balance"],
        total_pnl=status["total_pnl"],
        unrealized_pnl=status["unrealized_pnl"],
        realized_pnl=status["realized_pnl"],
        positions=[
            PositionResponse(
                symbol=pos["symbol"],
                side=pos["side"],
                size=pos["size"],
                entry_price=pos["entry_price"],
                current_price=pos["current_price"],
                unrealized_pnl=pos["unrealized_pnl"],
                realized_pnl=pos["realized_pnl"],
                timestamp=datetime.now()
            )
            for pos in status["positions"]
        ],
        open_orders=status["open_orders"]
    )


@router.get("/positions", response_model=List[PositionResponse])
async def get_positions(engine: TradingEngine = Depends(get_trading_engine)):
    """Get all current positions."""
    status = engine.get_portfolio_status()
    return [
        PositionResponse(
            symbol=pos["symbol"],
            side=pos["side"],
            size=pos["size"],
            entry_price=pos["entry_price"],
            current_price=pos["current_price"],
            unrealized_pnl=pos["unrealized_pnl"],
            realized_pnl=pos["realized_pnl"],
            timestamp=datetime.now()
        )
        for pos in status["positions"]
    ]


@router.get("/orders", response_model=List[OrderResponse])
async def get_orders(
    status: Optional[str] = Query(None, description="Filter by order status"),
    symbol: Optional[str] = Query(None, description="Filter by symbol"),
    engine: TradingEngine = Depends(get_trading_engine)
):
    """Get orders with optional filtering."""
    orders = list(engine.orders.values())
    
    if status:
        orders = [o for o in orders if o.status.value == status]
    
    if symbol:
        orders = [o for o in orders if o.symbol.upper() == symbol.upper()]
    
    return [
        OrderResponse(
            id=order.id,
            symbol=order.symbol,
            side=order.side.value,
            type=order.type.value,
            amount=float(order.amount),
            price=float(order.price) if order.price else None,
            stop_price=float(order.stop_price) if order.stop_price else None,
            status=order.status.value,
            filled_amount=float(order.filled_amount),
            average_price=float(order.average_price) if order.average_price else None,
            timestamp=order.timestamp,
            strategy_id=order.strategy_id
        )
        for order in orders
    ]


@router.post("/orders", response_model=OrderResponse)
async def create_order(
    order_request: OrderRequest,
    engine: TradingEngine = Depends(get_trading_engine)
):
    """Create a new order."""
    try:
        from decimal import Decimal
        
        order = Order(
            id=f"{order_request.symbol}_{int(datetime.now().timestamp())}",
            symbol=order_request.symbol,
            side=order_request.side,
            type=order_request.type,
            amount=Decimal(str(order_request.amount)),
            price=Decimal(str(order_request.price)) if order_request.price else None,
            stop_price=Decimal(str(order_request.stop_price)) if order_request.stop_price else None
        )
        
        await engine._submit_order(order)
        
        return OrderResponse(
            id=order.id,
            symbol=order.symbol,
            side=order.side.value,
            type=order.type.value,
            amount=float(order.amount),
            price=float(order.price) if order.price else None,
            stop_price=float(order.stop_price) if order.stop_price else None,
            status=order.status.value,
            filled_amount=float(order.filled_amount),
            average_price=float(order.average_price) if order.average_price else None,
            timestamp=order.timestamp,
            strategy_id=order.strategy_id
        )
        
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Order creation failed: {str(exc)}")


@router.post("/engine/start")
async def start_engine(engine: TradingEngine = Depends(get_trading_engine)):
    """Start the trading engine."""
    if engine.running:
        raise HTTPException(status_code=400, detail="Trading engine is already running")
    
    await engine.start()
    return {"message": "Trading engine started"}


@router.post("/engine/stop")
async def stop_engine(engine: TradingEngine = Depends(get_trading_engine)):
    """Stop the trading engine."""
    if not engine.running:
        raise HTTPException(status_code=400, detail="Trading engine is not running")
    
    await engine.stop()
    return {"message": "Trading engine stopped"}


@router.get("/engine/status")
async def get_engine_status(engine: TradingEngine = Depends(get_trading_engine)):
    """Get trading engine status."""
    return {
        "running": engine.running,
        "positions_count": len(engine.positions),
        "orders_count": len(engine.orders),
        "balance": float(engine.balance)
    }


@router.post("/positions/{symbol}/close")
async def close_position(
    symbol: str,
    engine: TradingEngine = Depends(get_trading_engine)
):
    """Close a position by creating an opposite order."""
    if symbol not in engine.positions:
        raise HTTPException(status_code=404, detail="Position not found")
    
    position = engine.positions[symbol]
    
    # Create opposite order
    opposite_side = OrderSide.SELL if position.side == OrderSide.BUY else OrderSide.BUY
    
    order = Order(
        id=f"close_{symbol}_{int(datetime.now().timestamp())}",
        symbol=symbol,
        side=opposite_side,
        type=OrderType.MARKET,
        amount=position.size
    )
    
    await engine._submit_order(order)
    
    return {"message": f"Closing order created for {symbol}"}


@router.get("/dashboard", response_class=HTMLResponse)
async def trading_dashboard():
    """Serve the trading dashboard."""
    from pathlib import Path
    
    template_path = Path(__file__).parent.parent / "templates" / "trading.html"
    
    if not template_path.exists():
        raise HTTPException(status_code=404, detail="Trading dashboard not found")
    
    with open(template_path, "r") as f:
        content = f.read()
    
    return HTMLResponse(content=content)
