"""Backtesting engine using historical scanner data."""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Tuple

try:
    import pandas as pd
except ImportError:
    pd = None

from ..core.scoring import score_with_breakdown
from ..core.metrics import SymbolSnapshot
from ..stores.pg_store import get_engine

LOGGER = logging.getLogger(__name__)


@dataclass
class BacktestResult:
    symbol: str
    entry_time: datetime
    exit_time: Optional[datetime]
    side: str
    entry_price: float
    exit_price: Optional[float]
    size: float
    pnl: float
    pnl_pct: float
    hold_time_minutes: int
    max_drawdown: float
    max_runup: float


@dataclass
class BacktestStats:
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    total_pnl: float
    avg_pnl: float
    avg_win: float
    avg_loss: float
    profit_factor: float
    max_drawdown: float
    sharpe_ratio: float
    avg_hold_time: float


class BacktestEngine:
    """Backtesting engine for scanner signals."""
    
    def __init__(self, initial_balance: float = 10000.0):
        self.initial_balance = Decimal(str(initial_balance))
        self.balance = self.initial_balance
        self.positions: Dict[str, Dict] = {}
        self.trades: List[BacktestResult] = []
        self.equity_curve: List[Tuple[datetime, float]] = []
        self.max_position_size = Decimal("0.1")  # 10% max per position
        
    async def run_backtest(
        self,
        start_date: datetime,
        end_date: datetime,
        symbols: Optional[List[str]] = None,
        min_confidence: float = 70.0,
        max_positions: int = 5
    ) -> BacktestStats:
        """Run backtest on historical data."""
        
        LOGGER.info(f"Starting backtest from {start_date} to {end_date}")
        
        # Get historical data
        historical_data = await self._load_historical_data(start_date, end_date, symbols)
        
        # Process each time period
        current_time = start_date
        while current_time <= end_date:
            await self._process_time_period(current_time, historical_data, min_confidence, max_positions)
            current_time += timedelta(minutes=1)  # Process every minute
        
        # Close any remaining positions
        await self._close_all_positions(end_date)
        
        # Calculate statistics
        stats = self._calculate_stats()
        
        LOGGER.info(f"Backtest completed. Total P&L: {stats.total_pnl:.2f}")
        return stats
    
    async def _load_historical_data(
        self, 
        start_date: datetime, 
        end_date: datetime, 
        symbols: Optional[List[str]]
    ) -> Dict[str, pd.DataFrame]:
        """Load historical OHLCV data from database."""
        
        if pd is None:
            raise ImportError("pandas is required for backtesting. Install with: pip install pandas")
        
        engine = get_engine()
        
        # Build query for historical bars
        query = """
        SELECT symbol, timestamp, open, high, low, close, volume
        FROM bars_1m 
        WHERE timestamp >= %s AND timestamp <= %s
        """
        
        params = [start_date, end_date]
        if symbols:
            placeholders = ','.join(['%s'] * len(symbols))
            query += f" AND symbol IN ({placeholders})"
            params.extend(symbols)
        
        query += " ORDER BY symbol, timestamp"
        
        # Execute query
        with engine.connect() as conn:
            result = conn.execute(query, params)
            data = result.fetchall()
        
        # Convert to DataFrame and group by symbol
        df = pd.DataFrame(data, columns=['symbol', 'timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        return {symbol: group.set_index('timestamp') for symbol, group in df.groupby('symbol')}
    
    async def _process_time_period(
        self,
        current_time: datetime,
        historical_data: Dict[str, pd.DataFrame],
        min_confidence: float,
        max_positions: int
    ):
        """Process signals for a specific time period."""
        
        # Get current opportunities (simulate scanner output)
        opportunities = await self._get_opportunities_at_time(current_time, historical_data)
        
        # Filter by confidence and existing positions
        valid_opportunities = [
            opp for opp in opportunities
            if (opp['confidence'] >= min_confidence and 
                opp['symbol'] not in self.positions and
                len(self.positions) < max_positions)
        ]
        
        # Sort by confidence and take top opportunities
        valid_opportunities.sort(key=lambda x: x['confidence'], reverse=True)
        
        for opp in valid_opportunities[:max_positions - len(self.positions)]:
            await self._execute_signal(opp, current_time, historical_data)
    
    async def _get_opportunities_at_time(
        self,
        current_time: datetime,
        historical_data: Dict[str, pd.DataFrame]
    ) -> List[Dict]:
        """Simulate scanner opportunities at a specific time."""
        
        opportunities = []
        
        for symbol, data in historical_data.items():
            # Get data up to current time
            historical = data[data.index <= current_time]
            
            if len(historical) < 20:  # Need minimum data
                continue
            
            # Calculate basic metrics
            closes = historical['close'].values
            current_price = closes[-1]
            
            # Calculate returns
            ret_1 = (closes[-1] - closes[-2]) / closes[-2] if len(closes) > 1 else 0
            ret_15 = (closes[-1] - closes[-15]) / closes[-15] if len(closes) > 15 else 0
            
            # Calculate ATR
            high_low = historical['high'] - historical['low']
            high_close = abs(historical['high'] - historical['close'].shift(1))
            low_close = abs(historical['low'] - historical['close'].shift(1))
            true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
            atr = true_range.rolling(14).mean().iloc[-1]
            atr_pct = (atr / current_price) * 100
            
            # Calculate volume metrics
            volume_ma = historical['volume'].rolling(20).mean().iloc[-1]
            volume_ratio = historical['volume'].iloc[-1] / volume_ma if volume_ma > 0 else 1
            
            # Simple scoring (simplified version of your scoring system)
            score = 0
            score += min(50, ret_15 * 10)  # Momentum component
            score += min(30, volume_ratio * 10)  # Volume component
            score += min(20, atr_pct * 2)  # Volatility component
            
            # Determine side bias
            if ret_1 > 0 and ret_15 > 0:
                side_bias = "long"
            elif ret_1 < 0 and ret_15 < 0:
                side_bias = "short"
            else:
                side_bias = "neutral"
            
            # Calculate confidence
            confidence = min(100, max(0, score))
            
            opportunities.append({
                'symbol': symbol,
                'side_bias': side_bias,
                'confidence': confidence,
                'current_price': current_price,
                'atr_pct': atr_pct,
                'ret_1': ret_1,
                'ret_15': ret_15,
                'volume_ratio': volume_ratio
            })
        
        return opportunities
    
    async def _execute_signal(self, opportunity: Dict, current_time: datetime, historical_data: Dict[str, pd.DataFrame]):
        """Execute a trading signal."""
        
        symbol = opportunity['symbol']
        side_bias = opportunity['side_bias']
        current_price = opportunity['current_price']
        
        if side_bias == "neutral":
            return
        
        # Calculate position size
        position_size = self._calculate_position_size(opportunity)
        
        # Create position
        self.positions[symbol] = {
            'side': side_bias,
            'size': position_size,
            'entry_price': current_price,
            'entry_time': current_time,
            'max_drawdown': 0.0,
            'max_runup': 0.0
        }
        
        LOGGER.debug(f"Opened {side_bias} position in {symbol} at {current_price}")
    
    def _calculate_position_size(self, opportunity: Dict) -> float:
        """Calculate position size based on risk and opportunity."""
        confidence = opportunity['confidence']
        atr_pct = opportunity['atr_pct']
        
        # Base position size
        base_size = float(self.balance * self.max_position_size)
        
        # Scale by confidence
        confidence_multiplier = confidence / 100.0
        
        # Scale by volatility (lower volatility = larger position)
        volatility_multiplier = max(0.5, min(1.5, 1.0 / (atr_pct / 2.0 + 0.1)))
        
        return base_size * confidence_multiplier * volatility_multiplier
    
    async def _close_all_positions(self, end_time: datetime):
        """Close all remaining positions at end of backtest."""
        
        for symbol, position in list(self.positions.items()):
            # Use last available price
            if symbol in historical_data:
                last_price = historical_data[symbol]['close'].iloc[-1]
                await self._close_position(symbol, last_price, end_time)
    
    async def _close_position(self, symbol: str, exit_price: float, exit_time: datetime):
        """Close a position and record the trade."""
        
        if symbol not in self.positions:
            return
        
        position = self.positions[symbol]
        
        # Calculate P&L
        if position['side'] == 'long':
            pnl = (exit_price - position['entry_price']) * position['size']
        else:
            pnl = (position['entry_price'] - exit_price) * position['size']
        
        pnl_pct = (pnl / (position['entry_price'] * position['size'])) * 100
        hold_time = (exit_time - position['entry_time']).total_seconds() / 60
        
        # Record trade
        trade = BacktestResult(
            symbol=symbol,
            entry_time=position['entry_time'],
            exit_time=exit_time,
            side=position['side'],
            entry_price=position['entry_price'],
            exit_price=exit_price,
            size=position['size'],
            pnl=pnl,
            pnl_pct=pnl_pct,
            hold_time_minutes=int(hold_time),
            max_drawdown=position['max_drawdown'],
            max_runup=position['max_runup']
        )
        
        self.trades.append(trade)
        
        # Update balance
        self.balance += Decimal(str(pnl))
        
        # Update equity curve
        self.equity_curve.append((exit_time, float(self.balance)))
        
        # Remove position
        del self.positions[symbol]
        
        LOGGER.debug(f"Closed {position['side']} position in {symbol}: P&L {pnl:.2f}")
    
    def _calculate_stats(self) -> BacktestStats:
        """Calculate backtesting statistics."""
        
        if not self.trades:
            return BacktestStats(
                total_trades=0, winning_trades=0, losing_trades=0,
                win_rate=0.0, total_pnl=0.0, avg_pnl=0.0,
                avg_win=0.0, avg_loss=0.0, profit_factor=0.0,
                max_drawdown=0.0, sharpe_ratio=0.0, avg_hold_time=0.0
            )
        
        # Basic stats
        total_trades = len(self.trades)
        winning_trades = len([t for t in self.trades if t.pnl > 0])
        losing_trades = len([t for t in self.trades if t.pnl < 0])
        
        win_rate = (winning_trades / total_trades) * 100 if total_trades > 0 else 0
        
        # P&L stats
        total_pnl = sum(t.pnl for t in self.trades)
        avg_pnl = total_pnl / total_trades if total_trades > 0 else 0
        
        wins = [t.pnl for t in self.trades if t.pnl > 0]
        losses = [t.pnl for t in self.trades if t.pnl < 0]
        
        avg_win = sum(wins) / len(wins) if wins else 0
        avg_loss = sum(losses) / len(losses) if losses else 0
        
        profit_factor = abs(sum(wins) / sum(losses)) if losses else float('inf')
        
        # Drawdown calculation
        equity_values = [float(self.initial_balance)] + [eq[1] for eq in self.equity_curve]
        peak = equity_values[0]
        max_drawdown = 0
        
        for value in equity_values:
            if value > peak:
                peak = value
            drawdown = (peak - value) / peak
            max_drawdown = max(max_drawdown, drawdown)
        
        # Sharpe ratio (simplified)
        returns = [t.pnl_pct for t in self.trades]
        if len(returns) > 1:
            mean_return = sum(returns) / len(returns)
            std_return = (sum((r - mean_return) ** 2 for r in returns) / (len(returns) - 1)) ** 0.5
            sharpe_ratio = mean_return / std_return if std_return > 0 else 0
        else:
            sharpe_ratio = 0
        
        # Average hold time
        avg_hold_time = sum(t.hold_time_minutes for t in self.trades) / total_trades if total_trades > 0 else 0
        
        return BacktestStats(
            total_trades=total_trades,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            win_rate=win_rate,
            total_pnl=total_pnl,
            avg_pnl=avg_pnl,
            avg_win=avg_win,
            avg_loss=avg_loss,
            profit_factor=profit_factor,
            max_drawdown=max_drawdown * 100,
            sharpe_ratio=sharpe_ratio,
            avg_hold_time=avg_hold_time
        )
