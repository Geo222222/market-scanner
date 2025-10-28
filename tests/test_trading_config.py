"""Test configuration and utilities for trading system tests."""
import pytest
from decimal import Decimal
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

from market_scanner.engine.trading import Order, OrderSide, OrderType, OrderStatus, Position


@pytest.fixture
def sample_order():
    """Create a sample order for testing."""
    return Order(
        id="test_order_1",
        symbol="BTC/USDT",
        side=OrderSide.BUY,
        type=OrderType.MARKET,
        amount=Decimal("0.1"),
        status=OrderStatus.PENDING
    )


@pytest.fixture
def sample_filled_order():
    """Create a sample filled order for testing."""
    return Order(
        id="test_order_2",
        symbol="ETH/USDT",
        side=OrderSide.SELL,
        type=OrderType.LIMIT,
        amount=Decimal("1.0"),
        price=Decimal("3000.0"),
        status=OrderStatus.FILLED,
        filled_amount=Decimal("1.0"),
        average_price=Decimal("3000.0")
    )


@pytest.fixture
def sample_position():
    """Create a sample position for testing."""
    return Position(
        symbol="BTC/USDT",
        side=OrderSide.BUY,
        size=Decimal("0.1"),
        entry_price=Decimal("50000.0"),
        current_price=Decimal("51000.0"),
        unrealized_pnl=Decimal("100.0")
    )


@pytest.fixture
def sample_opportunity():
    """Create a sample trading opportunity for testing."""
    return {
        "symbol": "BTC/USDT",
        "side_bias": "long",
        "confidence": 80.0,
        "current_price": 50000.0,
        "atr_pct": 2.0,
        "ret_1": 0.5,
        "ret_15": 1.2,
        "volume_ratio": 1.5,
        "manip_score": 20.0,
        "spread_bps": 5.0,
        "notional": 1000.0
    }


@pytest.fixture
def sample_portfolio_status():
    """Create sample portfolio status for testing."""
    return {
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


@pytest.fixture
def mock_ccxt_adapter():
    """Create mock CCXT adapter for testing."""
    adapter = AsyncMock()
    adapter.ex = AsyncMock()
    adapter.ex.create_order.return_value = {
        "id": "exchange_order_123",
        "status": "open"
    }
    adapter.ex.fetch_order.return_value = {
        "id": "exchange_order_123",
        "status": "closed",
        "filled": 0.1,
        "average": 50000.0
    }
    adapter.ex.fetch_ticker.return_value = {
        "last": 51000.0
    }
    return adapter


@pytest.fixture
def mock_scanner_api_response():
    """Create mock scanner API response for testing."""
    return {
        "items": [
            {
                "symbol": "BTC/USDT",
                "side_bias": "long",
                "confidence": 85.0,
                "current_price": 50000.0,
                "atr_pct": 2.0,
                "ret_1": 0.5,
                "ret_15": 1.2,
                "volume_ratio": 1.5,
                "manip_score": 15.0,
                "spread_bps": 4.0,
                "notional": 1000.0
            },
            {
                "symbol": "ETH/USDT",
                "side_bias": "short",
                "confidence": 75.0,
                "current_price": 3000.0,
                "atr_pct": 3.0,
                "ret_1": -0.3,
                "ret_15": -0.8,
                "volume_ratio": 1.2,
                "manip_score": 25.0,
                "spread_bps": 6.0,
                "notional": 1000.0
            }
        ]
    }


@pytest.fixture
def mock_historical_data():
    """Create mock historical data for backtesting."""
    return {
        "BTC/USDT": MagicMock(
            index=[datetime(2024, 1, 1, 9, i, tzinfo=timezone.utc) for i in range(20)],
            close=[50000 + i * 10 for i in range(20)],
            high=[50000 + i * 10 + 5 for i in range(20)],
            low=[50000 + i * 10 - 5 for i in range(20)],
            volume=[1000 + i * 10 for i in range(20)]
        )
    }


class TestTradingConfig:
    """Test configuration and utilities."""
    
    def test_sample_order_creation(self, sample_order):
        """Test sample order creation."""
        assert sample_order.symbol == "BTC/USDT"
        assert sample_order.side == OrderSide.BUY
        assert sample_order.type == OrderType.MARKET
        assert sample_order.amount == Decimal("0.1")
        assert sample_order.status == OrderStatus.PENDING
    
    def test_sample_position_creation(self, sample_position):
        """Test sample position creation."""
        assert sample_position.symbol == "BTC/USDT"
        assert sample_position.side == OrderSide.BUY
        assert sample_position.size == Decimal("0.1")
        assert sample_position.entry_price == Decimal("50000.0")
        assert sample_position.current_price == Decimal("51000.0")
        assert sample_position.unrealized_pnl == Decimal("100.0")
    
    def test_sample_opportunity_creation(self, sample_opportunity):
        """Test sample opportunity creation."""
        assert sample_opportunity["symbol"] == "BTC/USDT"
        assert sample_opportunity["side_bias"] == "long"
        assert sample_opportunity["confidence"] == 80.0
        assert sample_opportunity["current_price"] == 50000.0
        assert sample_opportunity["manip_score"] == 20.0
        assert sample_opportunity["spread_bps"] == 5.0
    
    def test_sample_portfolio_status_creation(self, sample_portfolio_status):
        """Test sample portfolio status creation."""
        assert sample_portfolio_status["balance"] == 10000.0
        assert sample_portfolio_status["total_pnl"] == 150.0
        assert sample_portfolio_status["unrealized_pnl"] == 100.0
        assert len(sample_portfolio_status["positions"]) == 1
        assert sample_portfolio_status["open_orders"] == 2
    
    def test_mock_ccxt_adapter_creation(self, mock_ccxt_adapter):
        """Test mock CCXT adapter creation."""
        assert mock_ccxt_adapter.ex is not None
        assert mock_ccxt_adapter.ex.create_order is not None
        assert mock_ccxt_adapter.ex.fetch_order is not None
        assert mock_ccxt_adapter.ex.fetch_ticker is not None
    
    def test_mock_scanner_api_response_creation(self, mock_scanner_api_response):
        """Test mock scanner API response creation."""
        assert "items" in mock_scanner_api_response
        assert len(mock_scanner_api_response["items"]) == 2
        assert mock_scanner_api_response["items"][0]["symbol"] == "BTC/USDT"
        assert mock_scanner_api_response["items"][1]["symbol"] == "ETH/USDT"
    
    def test_mock_historical_data_creation(self, mock_historical_data):
        """Test mock historical data creation."""
        assert "BTC/USDT" in mock_historical_data
        btc_data = mock_historical_data["BTC/USDT"]
        assert hasattr(btc_data, "index")
        assert hasattr(btc_data, "close")
        assert hasattr(btc_data, "high")
        assert hasattr(btc_data, "low")
        assert hasattr(btc_data, "volume")
