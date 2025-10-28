"""Backtesting router for strategy testing and analysis."""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field

from ..engine.backtesting import BacktestEngine, BacktestStats, BacktestResult

router = APIRouter()


class BacktestRequest(BaseModel):
    start_date: datetime = Field(..., description="Start date for backtest")
    end_date: datetime = Field(..., description="End date for backtest")
    symbols: Optional[List[str]] = Field(None, description="Symbols to test (None for all)")
    min_confidence: float = Field(70.0, ge=0, le=100, description="Minimum confidence threshold")
    max_positions: int = Field(5, ge=1, le=20, description="Maximum concurrent positions")
    initial_balance: float = Field(10000.0, gt=0, description="Starting balance")


class BacktestResponse(BaseModel):
    stats: BacktestStats
    trades: List[BacktestResult]
    equity_curve: List[tuple[datetime, float]]
    start_date: datetime
    end_date: datetime
    duration_days: float


@router.post("/run", response_model=BacktestResponse)
async def run_backtest(request: BacktestRequest):
    """Run a backtest on historical data."""
    
    # Validate dates
    if request.start_date >= request.end_date:
        raise HTTPException(status_code=400, detail="Start date must be before end date")
    
    if request.end_date > datetime.now():
        raise HTTPException(status_code=400, detail="End date cannot be in the future")
    
    # Check date range
    duration = request.end_date - request.start_date
    if duration.days > 365:
        raise HTTPException(status_code=400, detail="Backtest period cannot exceed 1 year")
    
    try:
        # Create backtest engine
        engine = BacktestEngine(initial_balance=request.initial_balance)
        
        # Run backtest
        stats = await engine.run_backtest(
            start_date=request.start_date,
            end_date=request.end_date,
            symbols=request.symbols,
            min_confidence=request.min_confidence,
            max_positions=request.max_positions
        )
        
        # Prepare response
        equity_curve = [(datetime.now(), request.initial_balance)] + engine.equity_curve
        
        return BacktestResponse(
            stats=stats,
            trades=engine.trades,
            equity_curve=equity_curve,
            start_date=request.start_date,
            end_date=request.end_date,
            duration_days=duration.days
        )
        
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Backtest failed: {str(exc)}")


@router.get("/quick-test")
async def quick_backtest(
    days: int = Query(7, ge=1, le=30, description="Number of days to test"),
    symbols: Optional[str] = Query(None, description="Comma-separated symbols"),
    min_confidence: float = Query(70.0, ge=0, le=100, description="Minimum confidence threshold")
):
    """Run a quick backtest for the last N days."""
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    
    symbol_list = None
    if symbols:
        symbol_list = [s.strip().upper() for s in symbols.split(",") if s.strip()]
    
    try:
        engine = BacktestEngine()
        stats = await engine.run_backtest(
            start_date=start_date,
            end_date=end_date,
            symbols=symbol_list,
            min_confidence=min_confidence,
            max_positions=5
        )
        
        return {
            "period": f"{days} days",
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "stats": {
                "total_trades": stats.total_trades,
                "win_rate": f"{stats.win_rate:.1f}%",
                "total_pnl": f"${stats.total_pnl:.2f}",
                "avg_pnl": f"${stats.avg_pnl:.2f}",
                "profit_factor": f"{stats.profit_factor:.2f}",
                "max_drawdown": f"{stats.max_drawdown:.1f}%",
                "sharpe_ratio": f"{stats.sharpe_ratio:.2f}",
                "avg_hold_time": f"{stats.avg_hold_time:.1f} minutes"
            },
            "trades_count": len(engine.trades)
        }
        
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Quick backtest failed: {str(exc)}")


@router.get("/symbols")
async def get_available_symbols():
    """Get list of symbols available for backtesting."""
    
    try:
        from ..stores.pg_store import get_engine
        
        engine = get_engine()
        
        query = """
        SELECT DISTINCT symbol 
        FROM bars_1m 
        WHERE timestamp >= NOW() - INTERVAL '30 days'
        ORDER BY symbol
        """
        
        with engine.connect() as conn:
            result = conn.execute(query)
            symbols = [row[0] for row in result.fetchall()]
        
        return {
            "symbols": symbols,
            "count": len(symbols),
            "note": "Symbols with data in the last 30 days"
        }
        
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to get symbols: {str(exc)}")


@router.get("/data-range")
async def get_data_range():
    """Get the available date range for backtesting."""
    
    try:
        from ..stores.pg_store import get_engine
        
        engine = get_engine()
        
        query = """
        SELECT 
            MIN(timestamp) as earliest,
            MAX(timestamp) as latest,
            COUNT(DISTINCT symbol) as symbol_count
        FROM bars_1m
        """
        
        with engine.connect() as conn:
            result = conn.execute(query)
            row = result.fetchone()
        
        return {
            "earliest_date": row[0].isoformat() if row[0] else None,
            "latest_date": row[1].isoformat() if row[1] else None,
            "symbol_count": row[2] or 0,
            "note": "Available historical data range"
        }
        
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to get data range: {str(exc)}")
