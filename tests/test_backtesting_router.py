"""Tests for the backtesting router."""
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient
from market_scanner.app import app
from market_scanner.engine.backtesting import BacktestStats, BacktestResult


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def sample_backtest_stats():
    """Create sample backtest stats."""
    return BacktestStats(
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


@pytest.fixture
def sample_backtest_trades():
    """Create sample backtest trades."""
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
        )
    ]


class TestBacktestingRouter:
    """Test backtesting router endpoints."""
    
    @patch('market_scanner.routers.backtesting.BacktestEngine')
    def test_run_backtest_success(self, mock_engine_class, client, sample_backtest_stats, sample_backtest_trades):
        """Test POST /backtesting/run endpoint success."""
        # Mock engine instance
        mock_engine = AsyncMock()
        mock_engine.run_backtest.return_value = sample_backtest_stats
        mock_engine.trades = sample_backtest_trades
        mock_engine.equity_curve = [
            (datetime(2024, 1, 1, 10, 0, tzinfo=timezone.utc), 10000.0),
            (datetime(2024, 1, 1, 11, 0, tzinfo=timezone.utc), 10100.0)
        ]
        mock_engine_class.return_value = mock_engine
        
        request_data = {
            "start_date": "2024-01-01T00:00:00Z",
            "end_date": "2024-01-02T00:00:00Z",
            "symbols": ["BTC/USDT", "ETH/USDT"],
            "min_confidence": 70.0,
            "max_positions": 5,
            "initial_balance": 10000.0
        }
        
        response = client.post("/backtesting/run", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["stats"]["total_trades"] == 10
        assert data["stats"]["win_rate"] == 60.0
        assert data["stats"]["total_pnl"] == 500.0
        assert len(data["trades"]) == 2
        assert data["duration_days"] == 1.0
    
    @patch('market_scanner.routers.backtesting.BacktestEngine')
    def test_run_backtest_invalid_dates(self, mock_engine_class, client):
        """Test POST /backtesting/run with invalid dates."""
        request_data = {
            "start_date": "2024-01-02T00:00:00Z",  # After end date
            "end_date": "2024-01-01T00:00:00Z",
            "symbols": ["BTC/USDT"],
            "min_confidence": 70.0,
            "max_positions": 5,
            "initial_balance": 10000.0
        }
        
        response = client.post("/backtesting/run", json=request_data)
        
        assert response.status_code == 400
        data = response.json()
        assert "Start date must be before end date" in data["detail"]
    
    @patch('market_scanner.routers.backtesting.BacktestEngine')
    def test_run_backtest_future_end_date(self, mock_engine_class, client):
        """Test POST /backtesting/run with future end date."""
        future_date = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
        
        request_data = {
            "start_date": "2024-01-01T00:00:00Z",
            "end_date": future_date,
            "symbols": ["BTC/USDT"],
            "min_confidence": 70.0,
            "max_positions": 5,
            "initial_balance": 10000.0
        }
        
        response = client.post("/backtesting/run", json=request_data)
        
        assert response.status_code == 400
        data = response.json()
        assert "End date cannot be in the future" in data["detail"]
    
    @patch('market_scanner.routers.backtesting.BacktestEngine')
    def test_run_backtest_too_long_period(self, mock_engine_class, client):
        """Test POST /backtesting/run with period too long."""
        request_data = {
            "start_date": "2023-01-01T00:00:00Z",
            "end_date": "2024-01-01T00:00:00Z",  # 1 year
            "symbols": ["BTC/USDT"],
            "min_confidence": 70.0,
            "max_positions": 5,
            "initial_balance": 10000.0
        }
        
        response = client.post("/backtesting/run", json=request_data)
        
        assert response.status_code == 400
        data = response.json()
        assert "Backtest period cannot exceed 1 year" in data["detail"]
    
    @patch('market_scanner.routers.backtesting.BacktestEngine')
    def test_run_backtest_engine_error(self, mock_engine_class, client):
        """Test POST /backtesting/run with engine error."""
        mock_engine = AsyncMock()
        mock_engine.run_backtest.side_effect = Exception("Database error")
        mock_engine_class.return_value = mock_engine
        
        request_data = {
            "start_date": "2024-01-01T00:00:00Z",
            "end_date": "2024-01-02T00:00:00Z",
            "symbols": ["BTC/USDT"],
            "min_confidence": 70.0,
            "max_positions": 5,
            "initial_balance": 10000.0
        }
        
        response = client.post("/backtesting/run", json=request_data)
        
        assert response.status_code == 500
        data = response.json()
        assert "Backtest failed" in data["detail"]
    
    @patch('market_scanner.routers.backtesting.BacktestEngine')
    def test_quick_backtest_success(self, mock_engine_class, client, sample_backtest_stats):
        """Test GET /backtesting/quick-test endpoint success."""
        mock_engine = AsyncMock()
        mock_engine.run_backtest.return_value = sample_backtest_stats
        mock_engine.trades = []
        mock_engine_class.return_value = mock_engine
        
        response = client.get("/backtesting/quick-test?days=7&min_confidence=70")
        
        assert response.status_code == 200
        data = response.json()
        assert data["period"] == "7 days"
        assert data["stats"]["total_trades"] == 10
        assert data["stats"]["win_rate"] == "60.0%"
        assert data["stats"]["total_pnl"] == "$500.00"
        assert data["trades_count"] == 0
    
    @patch('market_scanner.routers.backtesting.BacktestEngine')
    def test_quick_backtest_with_symbols(self, mock_engine_class, client, sample_backtest_stats):
        """Test GET /backtesting/quick-test with specific symbols."""
        mock_engine = AsyncMock()
        mock_engine.run_backtest.return_value = sample_backtest_stats
        mock_engine.trades = []
        mock_engine_class.return_value = mock_engine
        
        response = client.get("/backtesting/quick-test?days=7&symbols=BTC/USDT,ETH/USDT&min_confidence=80")
        
        assert response.status_code == 200
        data = response.json()
        assert data["period"] == "7 days"
        assert data["stats"]["total_trades"] == 10
    
    @patch('market_scanner.routers.backtesting.BacktestEngine')
    def test_quick_backtest_engine_error(self, mock_engine_class, client):
        """Test GET /backtesting/quick-test with engine error."""
        mock_engine = AsyncMock()
        mock_engine.run_backtest.side_effect = Exception("Database error")
        mock_engine_class.return_value = mock_engine
        
        response = client.get("/backtesting/quick-test?days=7")
        
        assert response.status_code == 500
        data = response.json()
        assert "Quick backtest failed" in data["detail"]
    
    @patch('market_scanner.routers.backtesting.get_engine')
    def test_get_available_symbols(self, mock_get_engine, client):
        """Test GET /backtesting/symbols endpoint."""
        # Mock database connection
        mock_conn = MagicMock()
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [
            ("BTC/USDT",),
            ("ETH/USDT",),
            ("ADA/USDT",)
        ]
        mock_conn.execute.return_value = mock_result
        mock_engine = MagicMock()
        mock_engine.connect.return_value.__enter__.return_value = mock_conn
        mock_get_engine.return_value = mock_engine
        
        response = client.get("/backtesting/symbols")
        
        assert response.status_code == 200
        data = response.json()
        assert data["symbols"] == ["BTC/USDT", "ETH/USDT", "ADA/USDT"]
        assert data["count"] == 3
        assert "last 30 days" in data["note"]
    
    @patch('market_scanner.routers.backtesting.get_engine')
    def test_get_available_symbols_error(self, mock_get_engine, client):
        """Test GET /backtesting/symbols with database error."""
        mock_get_engine.side_effect = Exception("Database connection failed")
        
        response = client.get("/backtesting/symbols")
        
        assert response.status_code == 500
        data = response.json()
        assert "Failed to get symbols" in data["detail"]
    
    @patch('market_scanner.routers.backtesting.get_engine')
    def test_get_data_range(self, mock_get_engine, client):
        """Test GET /backtesting/data-range endpoint."""
        # Mock database connection
        mock_conn = MagicMock()
        mock_result = MagicMock()
        mock_result.fetchone.return_value = (
            datetime(2023, 1, 1, tzinfo=timezone.utc),
            datetime(2024, 1, 1, tzinfo=timezone.utc),
            50
        )
        mock_conn.execute.return_value = mock_result
        mock_engine = MagicMock()
        mock_engine.connect.return_value.__enter__.return_value = mock_conn
        mock_get_engine.return_value = mock_engine
        
        response = client.get("/backtesting/data-range")
        
        assert response.status_code == 200
        data = response.json()
        assert "2023-01-01T00:00:00" in data["earliest_date"]
        assert "2024-01-01T00:00:00" in data["latest_date"]
        assert data["symbol_count"] == 50
        assert "Available historical data range" in data["note"]
    
    @patch('market_scanner.routers.backtesting.get_engine')
    def test_get_data_range_error(self, mock_get_engine, client):
        """Test GET /backtesting/data-range with database error."""
        mock_get_engine.side_effect = Exception("Database connection failed")
        
        response = client.get("/backtesting/data-range")
        
        assert response.status_code == 500
        data = response.json()
        assert "Failed to get data range" in data["detail"]
    
    def test_quick_backtest_default_parameters(self, client):
        """Test GET /backtesting/quick-test with default parameters."""
        with patch('market_scanner.routers.backtesting.BacktestEngine') as mock_engine_class:
            mock_engine = AsyncMock()
            mock_engine.run_backtest.return_value = sample_backtest_stats
            mock_engine.trades = []
            mock_engine_class.return_value = mock_engine
            
            response = client.get("/backtesting/quick-test")
            
            assert response.status_code == 200
            # Should use default values
            mock_engine.run_backtest.assert_called_once()
            call_args = mock_engine.run_backtest.call_args
            assert call_args[1]["min_confidence"] == 70.0  # Default value
