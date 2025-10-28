"""Integration tests for the trading system."""
import pytest
from decimal import Decimal
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient
from market_scanner.app import app


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


class TestTradingIntegration:
    """Integration tests for the complete trading system."""
    
    @patch('market_scanner.engine.trading.CCXTAdapter')
    @patch('market_scanner.routers.trading.get_trading_engine')
    def test_trading_workflow(self, mock_get_engine, mock_adapter_class, client):
        """Test complete trading workflow from signal to execution."""
        # Mock trading engine
        mock_engine = AsyncMock()
        mock_engine.running = False
        mock_engine.balance = Decimal("10000")
        mock_engine.positions = {}
        mock_engine.orders = {}
        mock_engine.get_portfolio_status.return_value = {
            "balance": 10000.0,
            "total_pnl": 0.0,
            "unrealized_pnl": 0.0,
            "realized_pnl": 0.0,
            "positions": [],
            "open_orders": 0
        }
        mock_get_engine.return_value = mock_engine
        
        # Mock CCXT adapter
        mock_adapter = AsyncMock()
        mock_adapter.ex = AsyncMock()
        mock_adapter_class.return_value = mock_adapter
        
        # 1. Start trading engine
        response = client.post("/trading/engine/start")
        assert response.status_code == 200
        mock_engine.start.assert_called_once()
        
        # 2. Check engine status
        mock_engine.running = True
        response = client.get("/trading/engine/status")
        assert response.status_code == 200
        data = response.json()
        assert data["running"] is True
        
        # 3. Create a market order
        order_data = {
            "symbol": "BTC/USDT",
            "side": "buy",
            "type": "market",
            "amount": 0.1
        }
        
        # Mock successful order creation
        mock_adapter.ex.create_order.return_value = {
            "id": "exchange_order_123",
            "status": "open"
        }
        
        response = client.post("/trading/orders", json=order_data)
        assert response.status_code == 200
        data = response.json()
        assert data["symbol"] == "BTC/USDT"
        assert data["side"] == "buy"
        assert data["type"] == "market"
        assert data["amount"] == 0.1
        
        # 4. Check portfolio status
        mock_engine.get_portfolio_status.return_value = {
            "balance": 10000.0,
            "total_pnl": 0.0,
            "unrealized_pnl": 0.0,
            "realized_pnl": 0.0,
            "positions": [],
            "open_orders": 1
        }
        
        response = client.get("/trading/portfolio")
        assert response.status_code == 200
        data = response.json()
        assert data["open_orders"] == 1
        
        # 5. Stop trading engine
        response = client.post("/trading/engine/stop")
        assert response.status_code == 200
        mock_engine.stop.assert_called_once()
    
    @patch('market_scanner.engine.backtesting.BacktestEngine')
    def test_backtesting_workflow(self, mock_engine_class, client):
        """Test complete backtesting workflow."""
        # Mock backtest engine
        mock_engine = AsyncMock()
        mock_engine.run_backtest.return_value = MagicMock(
            total_trades=5,
            winning_trades=3,
            losing_trades=2,
            win_rate=60.0,
            total_pnl=250.0,
            avg_pnl=50.0,
            avg_win=100.0,
            avg_loss=-50.0,
            profit_factor=2.0,
            max_drawdown=5.0,
            sharpe_ratio=1.2,
            avg_hold_time=90.0
        )
        mock_engine.trades = []
        mock_engine.equity_curve = [
            (datetime(2024, 1, 1, 10, 0, tzinfo=timezone.utc), 10000.0),
            (datetime(2024, 1, 1, 11, 0, tzinfo=timezone.utc), 10250.0)
        ]
        mock_engine_class.return_value = mock_engine
        
        # 1. Run quick backtest
        response = client.get("/backtesting/quick-test?days=7&min_confidence=70")
        assert response.status_code == 200
        data = response.json()
        assert data["period"] == "7 days"
        assert data["stats"]["total_trades"] == 5
        assert data["stats"]["win_rate"] == "60.0%"
        
        # 2. Run full backtest
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
        assert data["stats"]["total_trades"] == 5
        assert data["stats"]["win_rate"] == 60.0
        assert data["stats"]["total_pnl"] == 250.0
        assert data["duration_days"] == 1.0
    
    @patch('market_scanner.engine.trading.CCXTAdapter')
    @patch('market_scanner.routers.trading.get_trading_engine')
    def test_position_management(self, mock_get_engine, mock_adapter_class, client):
        """Test position management workflow."""
        # Mock trading engine with existing position
        mock_engine = AsyncMock()
        mock_engine.running = True
        mock_engine.positions = {
            "BTC/USDT": MagicMock(
                symbol="BTC/USDT",
                side="buy",
                size=0.1,
                entry_price=50000.0,
                current_price=51000.0,
                unrealized_pnl=100.0
            )
        }
        mock_engine.get_portfolio_status.return_value = {
            "balance": 10000.0,
            "total_pnl": 100.0,
            "unrealized_pnl": 100.0,
            "realized_pnl": 0.0,
            "positions": [{
                "symbol": "BTC/USDT",
                "side": "buy",
                "size": 0.1,
                "entry_price": 50000.0,
                "current_price": 51000.0,
                "unrealized_pnl": 100.0,
                "realized_pnl": 0.0
            }],
            "open_orders": 0
        }
        mock_get_engine.return_value = mock_engine
        
        # Mock CCXT adapter
        mock_adapter = AsyncMock()
        mock_adapter.ex = AsyncMock()
        mock_adapter_class.return_value = mock_adapter
        
        # 1. Check positions
        response = client.get("/trading/positions")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["symbol"] == "BTC/USDT"
        assert data[0]["unrealized_pnl"] == 100.0
        
        # 2. Close position
        mock_adapter.ex.create_order.return_value = {
            "id": "close_order_123",
            "status": "open"
        }
        
        response = client.post("/trading/positions/BTC/USDT/close")
        assert response.status_code == 200
        data = response.json()
        assert "Closing order created" in data["message"]
        
        # 3. Check portfolio after closing
        response = client.get("/trading/portfolio")
        assert response.status_code == 200
        data = response.json()
        assert data["unrealized_pnl"] == 100.0  # Still showing unrealized until filled
    
    @patch('market_scanner.engine.trading.CCXTAdapter')
    @patch('market_scanner.routers.trading.get_trading_engine')
    def test_order_filtering(self, mock_get_engine, mock_adapter_class, client):
        """Test order filtering by status and symbol."""
        # Mock trading engine with multiple orders
        mock_engine = AsyncMock()
        mock_engine.orders = {
            "order_1": MagicMock(
                id="order_1",
                symbol="BTC/USDT",
                side="buy",
                type="market",
                amount=Decimal("0.1"),
                status="filled",
                filled_amount=Decimal("0.1"),
                average_price=Decimal("50000.0"),
                timestamp=datetime.now(timezone.utc)
            ),
            "order_2": MagicMock(
                id="order_2",
                symbol="ETH/USDT",
                side="sell",
                type="limit",
                amount=Decimal("1.0"),
                price=Decimal("3000.0"),
                status="open",
                filled_amount=Decimal("0.0"),
                average_price=None,
                timestamp=datetime.now(timezone.utc)
            ),
            "order_3": MagicMock(
                id="order_3",
                symbol="BTC/USDT",
                side="buy",
                type="market",
                amount=Decimal("0.2"),
                status="rejected",
                filled_amount=Decimal("0.0"),
                average_price=None,
                timestamp=datetime.now(timezone.utc)
            )
        }
        mock_get_engine.return_value = mock_engine
        
        # 1. Get all orders
        response = client.get("/trading/orders")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3
        
        # 2. Filter by status
        response = client.get("/trading/orders?status=filled")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["id"] == "order_1"
        assert data[0]["status"] == "filled"
        
        # 3. Filter by symbol
        response = client.get("/trading/orders?symbol=BTC/USDT")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert all(order["symbol"] == "BTC/USDT" for order in data)
        
        # 4. Filter by both status and symbol
        response = client.get("/trading/orders?status=open&symbol=ETH/USDT")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["id"] == "order_2"
        assert data[0]["status"] == "open"
        assert data[0]["symbol"] == "ETH/USDT"
    
    def test_trading_dashboard_access(self, client):
        """Test trading dashboard is accessible."""
        response = client.get("/trading/dashboard")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        assert "Trading Dashboard" in response.text
        assert "Start Engine" in response.text
        assert "Portfolio" in response.text
        assert "Backtesting" in response.text
    
    @patch('market_scanner.engine.trading.CCXTAdapter')
    @patch('market_scanner.routers.trading.get_trading_engine')
    def test_error_handling(self, mock_get_engine, mock_adapter_class, client):
        """Test error handling in trading system."""
        # Mock trading engine that raises errors
        mock_engine = AsyncMock()
        mock_engine.start.side_effect = Exception("Engine start failed")
        mock_engine.get_portfolio_status.side_effect = Exception("Portfolio error")
        mock_get_engine.return_value = mock_engine
        
        # 1. Test engine start error
        response = client.post("/trading/engine/start")
        assert response.status_code == 200  # Should still return 200, error handled internally
        
        # 2. Test portfolio error
        response = client.get("/trading/portfolio")
        assert response.status_code == 200  # Should still return 200, error handled internally
        
        # 3. Test invalid order data
        invalid_order = {
            "symbol": "BTC/USDT",
            "side": "invalid_side",  # Invalid side
            "type": "market",
            "amount": 0.1
        }
        
        response = client.post("/trading/orders", json=invalid_order)
        assert response.status_code == 422  # Validation error
        
        # 4. Test close non-existent position
        mock_engine.positions = {}  # No positions
        response = client.post("/trading/positions/BTC/USDT/close")
        assert response.status_code == 404
        data = response.json()
        assert "Position not found" in data["detail"]
