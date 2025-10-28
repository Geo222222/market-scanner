"""Tests for the trading router."""
import pytest
from decimal import Decimal
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient
from market_scanner.app import app
from market_scanner.engine.trading import Order, OrderSide, OrderType, OrderStatus, Position


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def mock_trading_engine():
    """Create mock trading engine."""
    engine = AsyncMock()
    engine.get_portfolio_status.return_value = {
        "balance": 10000.0,
        "total_pnl": 150.0,
        "unrealized_pnl": 100.0,
        "realized_pnl": 50.0,
        "positions": [
            {
                "symbol": "BTC/USDT",
                "side": "buy",
                "size": 0.1,
                "entry_price": 50000.0,
                "current_price": 51000.0,
                "unrealized_pnl": 100.0,
                "realized_pnl": 0.0
            }
        ],
        "open_orders": 2
    }
    engine.orders = {
        "order_1": Order(
            id="order_1",
            symbol="BTC/USDT",
            side=OrderSide.BUY,
            type=OrderType.MARKET,
            amount=Decimal("0.1"),
            status=OrderStatus.FILLED,
            filled_amount=Decimal("0.1"),
            average_price=Decimal("50000.0")
        ),
        "order_2": Order(
            id="order_2",
            symbol="ETH/USDT",
            side=OrderSide.SELL,
            type=OrderType.LIMIT,
            amount=Decimal("1.0"),
            price=Decimal("3000.0"),
            status=OrderStatus.OPEN
        )
    }
    engine.positions = {
        "BTC/USDT": Position(
            symbol="BTC/USDT",
            side=OrderSide.BUY,
            size=Decimal("0.1"),
            entry_price=Decimal("50000.0"),
            current_price=Decimal("51000.0"),
            unrealized_pnl=Decimal("100.0")
        )
    }
    engine.running = True
    engine.balance = Decimal("10000")
    return engine


class TestTradingRouter:
    """Test trading router endpoints."""
    
    @patch('market_scanner.routers.trading.get_trading_engine')
    def test_get_portfolio(self, mock_get_engine, client, mock_trading_engine):
        """Test GET /trading/portfolio endpoint."""
        mock_get_engine.return_value = mock_trading_engine
        
        response = client.get("/trading/portfolio")
        
        assert response.status_code == 200
        data = response.json()
        assert data["balance"] == 10000.0
        assert data["total_pnl"] == 150.0
        assert data["unrealized_pnl"] == 100.0
        assert data["realized_pnl"] == 50.0
        assert len(data["positions"]) == 1
        assert data["open_orders"] == 2
    
    @patch('market_scanner.routers.trading.get_trading_engine')
    def test_get_positions(self, mock_get_engine, client, mock_trading_engine):
        """Test GET /trading/positions endpoint."""
        mock_get_engine.return_value = mock_trading_engine
        
        response = client.get("/trading/positions")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["symbol"] == "BTC/USDT"
        assert data[0]["side"] == "buy"
        assert data[0]["size"] == 0.1
        assert data[0]["unrealized_pnl"] == 100.0
    
    @patch('market_scanner.routers.trading.get_trading_engine')
    def test_get_orders(self, mock_get_engine, client, mock_trading_engine):
        """Test GET /trading/orders endpoint."""
        mock_get_engine.return_value = mock_trading_engine
        
        response = client.get("/trading/orders")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        
        # Check first order
        order1 = next(o for o in data if o["id"] == "order_1")
        assert order1["symbol"] == "BTC/USDT"
        assert order1["side"] == "buy"
        assert order1["type"] == "market"
        assert order1["status"] == "filled"
        assert order1["filled_amount"] == 0.1
        assert order1["average_price"] == 50000.0
    
    @patch('market_scanner.routers.trading.get_trading_engine')
    def test_get_orders_with_status_filter(self, mock_get_engine, client, mock_trading_engine):
        """Test GET /trading/orders with status filter."""
        mock_get_engine.return_value = mock_trading_engine
        
        response = client.get("/trading/orders?status=filled")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["status"] == "filled"
    
    @patch('market_scanner.routers.trading.get_trading_engine')
    def test_get_orders_with_symbol_filter(self, mock_get_engine, client, mock_trading_engine):
        """Test GET /trading/orders with symbol filter."""
        mock_get_engine.return_value = mock_trading_engine
        
        response = client.get("/trading/orders?symbol=BTC/USDT")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["symbol"] == "BTC/USDT"
    
    @patch('market_scanner.routers.trading.get_trading_engine')
    def test_create_order(self, mock_get_engine, client, mock_trading_engine):
        """Test POST /trading/orders endpoint."""
        mock_get_engine.return_value = mock_trading_engine
        
        order_data = {
            "symbol": "BTC/USDT",
            "side": "buy",
            "type": "market",
            "amount": 0.1
        }
        
        response = client.post("/trading/orders", json=order_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["symbol"] == "BTC/USDT"
        assert data["side"] == "buy"
        assert data["type"] == "market"
        assert data["amount"] == 0.1
        assert data["status"] == "pending"
    
    @patch('market_scanner.routers.trading.get_trading_engine')
    def test_create_limit_order(self, mock_get_engine, client, mock_trading_engine):
        """Test POST /trading/orders with limit order."""
        mock_get_engine.return_value = mock_trading_engine
        
        order_data = {
            "symbol": "ETH/USDT",
            "side": "sell",
            "type": "limit",
            "amount": 1.0,
            "price": 3000.0
        }
        
        response = client.post("/trading/orders", json=order_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["symbol"] == "ETH/USDT"
        assert data["side"] == "sell"
        assert data["type"] == "limit"
        assert data["amount"] == 1.0
        assert data["price"] == 3000.0
    
    @patch('market_scanner.routers.trading.get_trading_engine')
    def test_create_order_invalid_data(self, mock_get_engine, client, mock_trading_engine):
        """Test POST /trading/orders with invalid data."""
        mock_get_engine.return_value = mock_trading_engine
        
        order_data = {
            "symbol": "BTC/USDT",
            "side": "invalid_side",  # Invalid side
            "type": "market",
            "amount": 0.1
        }
        
        response = client.post("/trading/orders", json=order_data)
        
        assert response.status_code == 422  # Validation error
    
    @patch('market_scanner.routers.trading.get_trading_engine')
    def test_start_engine(self, mock_get_engine, client, mock_trading_engine):
        """Test POST /trading/engine/start endpoint."""
        mock_trading_engine.running = False
        mock_get_engine.return_value = mock_trading_engine
        
        response = client.post("/trading/engine/start")
        
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Trading engine started"
        mock_trading_engine.start.assert_called_once()
    
    @patch('market_scanner.routers.trading.get_trading_engine')
    def test_start_engine_already_running(self, mock_get_engine, client, mock_trading_engine):
        """Test POST /trading/engine/start when already running."""
        mock_trading_engine.running = True
        mock_get_engine.return_value = mock_trading_engine
        
        response = client.post("/trading/engine/start")
        
        assert response.status_code == 400
        data = response.json()
        assert "already running" in data["detail"]
    
    @patch('market_scanner.routers.trading.get_trading_engine')
    def test_stop_engine(self, mock_get_engine, client, mock_trading_engine):
        """Test POST /trading/engine/stop endpoint."""
        mock_trading_engine.running = True
        mock_get_engine.return_value = mock_trading_engine
        
        response = client.post("/trading/engine/stop")
        
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Trading engine stopped"
        mock_trading_engine.stop.assert_called_once()
    
    @patch('market_scanner.routers.trading.get_trading_engine')
    def test_stop_engine_not_running(self, mock_get_engine, client, mock_trading_engine):
        """Test POST /trading/engine/stop when not running."""
        mock_trading_engine.running = False
        mock_get_engine.return_value = mock_trading_engine
        
        response = client.post("/trading/engine/stop")
        
        assert response.status_code == 400
        data = response.json()
        assert "not running" in data["detail"]
    
    @patch('market_scanner.routers.trading.get_trading_engine')
    def test_get_engine_status(self, mock_get_engine, client, mock_trading_engine):
        """Test GET /trading/engine/status endpoint."""
        mock_get_engine.return_value = mock_trading_engine
        
        response = client.get("/trading/engine/status")
        
        assert response.status_code == 200
        data = response.json()
        assert data["running"] is True
        assert data["positions_count"] == 1
        assert data["orders_count"] == 2
        assert data["balance"] == 10000.0
    
    @patch('market_scanner.routers.trading.get_trading_engine')
    def test_close_position(self, mock_get_engine, client, mock_trading_engine):
        """Test POST /trading/positions/{symbol}/close endpoint."""
        mock_get_engine.return_value = mock_trading_engine
        
        response = client.post("/trading/positions/BTC/USDT/close")
        
        assert response.status_code == 200
        data = response.json()
        assert "Closing order created" in data["message"]
        mock_trading_engine._submit_order.assert_called_once()
    
    @patch('market_scanner.routers.trading.get_trading_engine')
    def test_close_position_not_found(self, mock_get_engine, client, mock_trading_engine):
        """Test POST /trading/positions/{symbol}/close with non-existent position."""
        mock_trading_engine.positions = {}  # No positions
        mock_get_engine.return_value = mock_trading_engine
        
        response = client.post("/trading/positions/BTC/USDT/close")
        
        assert response.status_code == 404
        data = response.json()
        assert "Position not found" in data["detail"]
    
    def test_trading_dashboard(self, client):
        """Test GET /trading/dashboard endpoint."""
        response = client.get("/trading/dashboard")
        
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        assert "Trading Dashboard" in response.text
