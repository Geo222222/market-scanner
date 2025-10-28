"""Tests for the backtesting engine."""
import pytest
from decimal import Decimal
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from market_scanner.engine.backtesting import BacktestEngine, BacktestResult, BacktestStats


@pytest.fixture
def backtest_engine():
    """Create a backtest engine for testing."""
    return BacktestEngine(initial_balance=10000.0)


@pytest.fixture
def sample_trades():
    """Create sample trades for testing."""
    return [
        BacktestResult(
            symbol="BTC/USDT",
            entry_time=datetime(2024, 1, 1, 10, 0, tzinfo=timezone.utc),
            exit_time=datetime(2024, 1, 1, 11, 0, tzinfo=timezone.utc),
            side="long",
            entry_price=50000.0,
            exit_price=51000.0,
            size=0.1,
            pnl=100.0,
            pnl_pct=2.0,
            hold_time_minutes=60,
            max_drawdown=0.0,
            max_runup=2.0
        ),
        BacktestResult(
            symbol="ETH/USDT",
            entry_time=datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc),
            exit_time=datetime(2024, 1, 1, 13, 0, tzinfo=timezone.utc),
            side="short",
            entry_price=3000.0,
            exit_price=2900.0,
            size=1.0,
            pnl=100.0,
            pnl_pct=3.33,
            hold_time_minutes=60,
            max_drawdown=0.0,
            max_runup=3.33
        ),
        BacktestResult(
            symbol="ADA/USDT",
            entry_time=datetime(2024, 1, 1, 14, 0, tzinfo=timezone.utc),
            exit_time=datetime(2024, 1, 1, 15, 0, tzinfo=timezone.utc),
            side="long",
            entry_price=0.5,
            exit_price=0.48,
            size=1000.0,
            pnl=-20.0,
            pnl_pct=-4.0,
            hold_time_minutes=60,
            max_drawdown=4.0,
            max_runup=0.0
        )
    ]


class TestBacktestResult:
    """Test BacktestResult model."""
    
    def test_backtest_result_creation(self):
        """Test BacktestResult creation."""
        result = BacktestResult(
            symbol="BTC/USDT",
            entry_time=datetime(2024, 1, 1, 10, 0, tzinfo=timezone.utc),
            exit_time=datetime(2024, 1, 1, 11, 0, tzinfo=timezone.utc),
            side="long",
            entry_price=50000.0,
            exit_price=51000.0,
            size=0.1,
            pnl=100.0,
            pnl_pct=2.0,
            hold_time_minutes=60,
            max_drawdown=0.0,
            max_runup=2.0
        )
        
        assert result.symbol == "BTC/USDT"
        assert result.side == "long"
        assert result.entry_price == 50000.0
        assert result.exit_price == 51000.0
        assert result.pnl == 100.0
        assert result.pnl_pct == 2.0


class TestBacktestStats:
    """Test BacktestStats model."""
    
    def test_backtest_stats_creation(self):
        """Test BacktestStats creation."""
        stats = BacktestStats(
            total_trades=10,
            winning_trades=6,
            losing_trades=4,
            win_rate=60.0,
            total_pnl=500.0,
            avg_pnl=50.0,
            avg_win=100.0,
            avg_loss=-50.0,
            profit_factor=2.0,
            max_drawdown=5.0,
            sharpe_ratio=1.5,
            avg_hold_time=120.0
        )
        
        assert stats.total_trades == 10
        assert stats.win_rate == 60.0
        assert stats.total_pnl == 500.0
        assert stats.profit_factor == 2.0


class TestBacktestEngine:
    """Test BacktestEngine class."""
    
    def test_engine_initialization(self, backtest_engine):
        """Test engine initialization."""
        assert backtest_engine.initial_balance == Decimal("10000.0")
        assert backtest_engine.balance == Decimal("10000.0")
        assert backtest_engine.max_position_size == Decimal("0.1")
        assert len(backtest_engine.positions) == 0
        assert len(backtest_engine.trades) == 0
        assert len(backtest_engine.equity_curve) == 0
    
    def test_calculate_position_size(self, backtest_engine):
        """Test position size calculation."""
        opportunity = {
            "confidence": 80.0,
            "atr_pct": 2.0,
            "notional": 1000.0
        }
        
        size = backtest_engine._calculate_position_size(opportunity)
        
        # Should be scaled by confidence and volatility
        assert size > 0
        assert size <= float(backtest_engine.balance * backtest_engine.max_position_size)
    
    def test_calculate_position_size_high_volatility(self, backtest_engine):
        """Test position size calculation with high volatility."""
        opportunity = {
            "confidence": 80.0,
            "atr_pct": 10.0,  # High volatility
            "notional": 1000.0
        }
        
        size = backtest_engine._calculate_position_size(opportunity)
        
        # Should be smaller due to high volatility
        assert size > 0
        assert size < float(backtest_engine.balance * backtest_engine.max_position_size)
    
    def test_calculate_position_size_low_confidence(self, backtest_engine):
        """Test position size calculation with low confidence."""
        opportunity = {
            "confidence": 30.0,  # Low confidence
            "atr_pct": 2.0,
            "notional": 1000.0
        }
        
        size = backtest_engine._calculate_position_size(opportunity)
        
        # Should be smaller due to low confidence
        assert size > 0
        assert size < float(backtest_engine.balance * backtest_engine.max_position_size)
    
    @pytest.mark.asyncio
    async def test_close_position(self, backtest_engine):
        """Test closing a position."""
        # Create a position
        backtest_engine.positions["BTC/USDT"] = {
            "side": "long",
            "size": 0.1,
            "entry_price": 50000.0,
            "entry_time": datetime(2024, 1, 1, 10, 0, tzinfo=timezone.utc),
            "max_drawdown": 0.0,
            "max_runup": 0.0
        }
        
        exit_price = 51000.0
        exit_time = datetime(2024, 1, 1, 11, 0, tzinfo=timezone.utc)
        
        await backtest_engine._close_position("BTC/USDT", exit_price, exit_time)
        
        # Position should be closed
        assert "BTC/USDT" not in backtest_engine.positions
        
        # Trade should be recorded
        assert len(backtest_engine.trades) == 1
        trade = backtest_engine.trades[0]
        assert trade.symbol == "BTC/USDT"
        assert trade.side == "long"
        assert trade.entry_price == 50000.0
        assert trade.exit_price == 51000.0
        assert trade.pnl == 100.0  # (51000 - 50000) * 0.1
        
        # Balance should be updated
        assert backtest_engine.balance == Decimal("10100.0")
    
    @pytest.mark.asyncio
    async def test_close_short_position(self, backtest_engine):
        """Test closing a short position."""
        # Create a short position
        backtest_engine.positions["ETH/USDT"] = {
            "side": "short",
            "size": 1.0,
            "entry_price": 3000.0,
            "entry_time": datetime(2024, 1, 1, 10, 0, tzinfo=timezone.utc),
            "max_drawdown": 0.0,
            "max_runup": 0.0
        }
        
        exit_price = 2900.0
        exit_time = datetime(2024, 1, 1, 11, 0, tzinfo=timezone.utc)
        
        await backtest_engine._close_position("ETH/USDT", exit_price, exit_time)
        
        # Trade should be recorded
        trade = backtest_engine.trades[0]
        assert trade.symbol == "ETH/USDT"
        assert trade.side == "short"
        assert trade.entry_price == 3000.0
        assert trade.exit_price == 2900.0
        assert trade.pnl == 100.0  # (3000 - 2900) * 1.0
    
    def test_calculate_stats_no_trades(self, backtest_engine):
        """Test stats calculation with no trades."""
        stats = backtest_engine._calculate_stats()
        
        assert stats.total_trades == 0
        assert stats.winning_trades == 0
        assert stats.losing_trades == 0
        assert stats.win_rate == 0.0
        assert stats.total_pnl == 0.0
        assert stats.avg_pnl == 0.0
        assert stats.profit_factor == 0.0
        assert stats.max_drawdown == 0.0
        assert stats.sharpe_ratio == 0.0
        assert stats.avg_hold_time == 0.0
    
    def test_calculate_stats_with_trades(self, backtest_engine, sample_trades):
        """Test stats calculation with trades."""
        backtest_engine.trades = sample_trades
        backtest_engine.equity_curve = [
            (datetime(2024, 1, 1, 10, 0, tzinfo=timezone.utc), 10000.0),
            (datetime(2024, 1, 1, 11, 0, tzinfo=timezone.utc), 10100.0),
            (datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc), 10100.0),
            (datetime(2024, 1, 1, 13, 0, tzinfo=timezone.utc), 10200.0),
            (datetime(2024, 1, 1, 14, 0, tzinfo=timezone.utc), 10200.0),
            (datetime(2024, 1, 1, 15, 0, tzinfo=timezone.utc), 10180.0)
        ]
        
        stats = backtest_engine._calculate_stats()
        
        assert stats.total_trades == 3
        assert stats.winning_trades == 2
        assert stats.losing_trades == 1
        assert stats.win_rate == 66.67  # 2/3 * 100
        assert stats.total_pnl == 180.0  # 100 + 100 - 20
        assert stats.avg_pnl == 60.0  # 180 / 3
        assert stats.avg_win == 100.0  # (100 + 100) / 2
        assert stats.avg_loss == -20.0  # -20 / 1
        assert stats.profit_factor == 10.0  # 200 / 20
        assert stats.avg_hold_time == 60.0  # All trades held for 60 minutes
    
    def test_calculate_stats_single_trade(self, backtest_engine):
        """Test stats calculation with single trade."""
        backtest_engine.trades = [sample_trades[0]]  # Only winning trade
        backtest_engine.equity_curve = [
            (datetime(2024, 1, 1, 10, 0, tzinfo=timezone.utc), 10000.0),
            (datetime(2024, 1, 1, 11, 0, tzinfo=timezone.utc), 10100.0)
        ]
        
        stats = backtest_engine._calculate_stats()
        
        assert stats.total_trades == 1
        assert stats.winning_trades == 1
        assert stats.losing_trades == 0
        assert stats.win_rate == 100.0
        assert stats.total_pnl == 100.0
        assert stats.avg_pnl == 100.0
        assert stats.avg_win == 100.0
        assert stats.avg_loss == 0.0
        assert stats.profit_factor == float('inf')  # No losses
        assert stats.sharpe_ratio == 0.0  # Single trade, no standard deviation
    
    @pytest.mark.asyncio
    async def test_run_backtest_mock_data(self, backtest_engine):
        """Test running backtest with mocked data."""
        start_date = datetime(2024, 1, 1, tzinfo=timezone.utc)
        end_date = datetime(2024, 1, 2, tzinfo=timezone.utc)
        
        # Mock historical data
        mock_data = {
            "BTC/USDT": MagicMock(),  # Mock DataFrame
            "ETH/USDT": MagicMock()
        }
        
        with patch.object(backtest_engine, '_load_historical_data', return_value=mock_data):
            with patch.object(backtest_engine, '_get_opportunities_at_time', return_value=[]):
                with patch.object(backtest_engine, '_close_all_positions'):
                    stats = await backtest_engine.run_backtest(
                        start_date=start_date,
                        end_date=end_date,
                        symbols=["BTC/USDT", "ETH/USDT"],
                        min_confidence=70.0,
                        max_positions=5
                    )
                    
                    assert isinstance(stats, BacktestStats)
                    assert stats.total_trades == 0  # No opportunities in mock
    
    @pytest.mark.asyncio
    async def test_get_opportunities_at_time(self, backtest_engine):
        """Test getting opportunities at a specific time."""
        # Mock historical data
        mock_data = {
            "BTC/USDT": MagicMock()
        }
        
        # Mock DataFrame with OHLCV data
        mock_df = MagicMock()
        mock_df.index = [datetime(2024, 1, 1, 9, i, tzinfo=timezone.utc) for i in range(20)]
        mock_df['close'] = [50000 + i * 10 for i in range(20)]  # Rising prices
        mock_df['high'] = [50000 + i * 10 + 5 for i in range(20)]
        mock_df['low'] = [50000 + i * 10 - 5 for i in range(20)]
        mock_df['volume'] = [1000 + i * 10 for i in range(20)]
        
        # Mock rolling calculations
        mock_df['close'].shift.return_value = [50000 + (i-1) * 10 for i in range(20)]
        mock_df['high'] - mock_df['low'] = [10] * 20
        abs(mock_df['high'] - mock_df['close'].shift.return_value) = [5] * 20
        abs(mock_df['low'] - mock_df['close'].shift.return_value) = [5] * 20
        
        # Mock rolling mean
        mock_rolling = MagicMock()
        mock_rolling.mean.return_value = MagicMock()
        mock_rolling.mean.return_value.iloc = [-1]
        mock_rolling.mean.return_value.iloc[-1] = 5.0  # ATR
        
        mock_df['volume'].rolling.return_value = mock_rolling
        mock_df['volume'].iloc = [-1]
        mock_df['volume'].iloc[-1] = 1200.0  # Current volume
        
        mock_data["BTC/USDT"] = mock_df
        
        current_time = datetime(2024, 1, 1, 9, 19, tzinfo=timezone.utc)
        
        opportunities = await backtest_engine._get_opportunities_at_time(current_time, mock_data)
        
        assert len(opportunities) == 1
        opp = opportunities[0]
        assert opp["symbol"] == "BTC/USDT"
        assert opp["side_bias"] == "long"  # Rising prices
        assert opp["confidence"] > 0
        assert opp["current_price"] > 0
