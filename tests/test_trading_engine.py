"""Tests for the trading engine."""
import pytest
from decimal import Decimal
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from market_scanner.engine.trading import (
    TradingEngine, Order, OrderSide, OrderType, OrderStatus, Position
)


@pytest.fixture
def trading_engine():
    """Create a trading engine for testing."""
    with patch('market_scanner.engine.trading.CCXTAdapter'):
        engine = TradingEngine(scanner_api_url="http://test-scanner")
        engine.adapter = AsyncMock()
        engine.adapter.ex = AsyncMock()
        return engine


@pytest.fixture
def sample_order():
    """Create a sample order for testing."""
    return Order(
        id="test_order_1",
        symbol="BTC/USDT",
        side=OrderSide.BUY,
        type=OrderType.MARKET,
        amount=Decimal("0.1")
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


class TestOrder:
    """Test Order model."""
    
    def test_order_creation(self):
        """Test order creation with required fields."""
        order = Order(
            id="test_1",
            symbol="BTC/USDT",
            side=OrderSide.BUY,
            type=OrderType.MARKET,
            amount=Decimal("0.1")
        )
        
        assert order.id == "test_1"
        assert order.symbol == "BTC/USDT"
        assert order.side == OrderSide.BUY
        assert order.type == OrderType.MARKET
        assert order.amount == Decimal("0.1")
        assert order.status == OrderStatus.PENDING
        assert order.filled_amount == Decimal("0")
        assert order.timestamp is not None
    
    def test_order_with_optional_fields(self):
        """Test order creation with optional fields."""
        order = Order(
            id="test_2",
            symbol="ETH/USDT",
            side=OrderSide.SELL,
            type=OrderType.LIMIT,
            amount=Decimal("1.0"),
            price=Decimal("3000.0"),
            stop_price=Decimal("2900.0")
        )
        
        assert order.price == Decimal("3000.0")
        assert order.stop_price == Decimal("2900.0")


class TestPosition:
    """Test Position model."""
    
    def test_position_creation(self):
        """Test position creation."""
        position = Position(
            symbol="BTC/USDT",
            side=OrderSide.BUY,
            size=Decimal("0.1"),
            entry_price=Decimal("50000.0"),
            current_price=Decimal("51000.0"),
            unrealized_pnl=Decimal("100.0")
        )
        
        assert position.symbol == "BTC/USDT"
        assert position.side == OrderSide.BUY
        assert position.size == Decimal("0.1")
        assert position.entry_price == Decimal("50000.0")
        assert position.current_price == Decimal("51000.0")
        assert position.unrealized_pnl == Decimal("100.0")
        assert position.timestamp is not None


class TestTradingEngine:
    """Test TradingEngine class."""
    
    def test_engine_initialization(self, trading_engine):
        """Test engine initialization."""
        assert trading_engine.scanner_api == "http://test-scanner"
        assert trading_engine.balance == Decimal("10000")
        assert trading_engine.max_position_size == Decimal("0.1")
        assert trading_engine.running is False
        assert len(trading_engine.positions) == 0
        assert len(trading_engine.orders) == 0
    
    def test_calculate_position_size(self, trading_engine):
        """Test position size calculation."""
        opportunity = {
            "confidence": 80.0,
            "atr_pct": 2.0,
            "notional": 1000.0
        }
        
        size = trading_engine._calculate_position_size(opportunity)
        
        # Should be scaled by confidence and volatility
        assert size > 0
        assert size <= float(trading_engine.balance * trading_engine.max_position_size)
    
    def test_calculate_position_size_high_volatility(self, trading_engine):
        """Test position size calculation with high volatility."""
        opportunity = {
            "confidence": 80.0,
            "atr_pct": 10.0,  # High volatility
            "notional": 1000.0
        }
        
        size = trading_engine._calculate_position_size(opportunity)
        
        # Should be smaller due to high volatility
        assert size > 0
        assert size < float(trading_engine.balance * trading_engine.max_position_size)
    
    @pytest.mark.asyncio
    async def test_check_risk_limits_valid_opportunity(self, trading_engine):
        """Test risk limits check with valid opportunity."""
        opportunity = {
            "symbol": "BTC/USDT",
            "notional": 1000.0,
            "manip_score": 20.0,
            "spread_bps": 5.0
        }
        
        result = await trading_engine._check_risk_limits("BTC/USDT", opportunity)
        assert result is True
    
    @pytest.mark.asyncio
    async def test_check_risk_limits_high_manipulation(self, trading_engine):
        """Test risk limits check with high manipulation score."""
        opportunity = {
            "symbol": "BTC/USDT",
            "notional": 1000.0,
            "manip_score": 80.0,  # High manipulation
            "spread_bps": 5.0
        }
        
        result = await trading_engine._check_risk_limits("BTC/USDT", opportunity)
        assert result is False
    
    @pytest.mark.asyncio
    async def test_check_risk_limits_wide_spread(self, trading_engine):
        """Test risk limits check with wide spread."""
        opportunity = {
            "symbol": "BTC/USDT",
            "notional": 1000.0,
            "manip_score": 20.0,
            "spread_bps": 15.0  # Wide spread
        }
        
        result = await trading_engine._check_risk_limits("BTC/USDT", opportunity)
        assert result is False
    
    @pytest.mark.asyncio
    async def test_check_risk_limits_large_position(self, trading_engine):
        """Test risk limits check with large position."""
        opportunity = {
            "symbol": "BTC/USDT",
            "notional": 2000.0,  # Large position
            "manip_score": 20.0,
            "spread_bps": 5.0
        }
        
        result = await trading_engine._check_risk_limits("BTC/USDT", opportunity)
        assert result is False
    
    @pytest.mark.asyncio
    async def test_submit_order_success(self, trading_engine, sample_order):
        """Test successful order submission."""
        trading_engine.adapter.ex.create_order.return_value = {
            "id": "exchange_order_123",
            "status": "open"
        }
        
        await trading_engine._submit_order(sample_order)
        
        assert sample_order.id == "exchange_order_123"
        assert sample_order.status == OrderStatus.OPEN
        assert sample_order.id in trading_engine.orders
    
    @pytest.mark.asyncio
    async def test_submit_order_failure(self, trading_engine, sample_order):
        """Test order submission failure."""
        trading_engine.adapter.ex.create_order.side_effect = Exception("Exchange error")
        
        await trading_engine._submit_order(sample_order)
        
        assert sample_order.status == OrderStatus.REJECTED
        assert sample_order.id in trading_engine.orders
    
    @pytest.mark.asyncio
    async def test_update_position_new_position(self, trading_engine, sample_order):
        """Test creating new position from filled order."""
        sample_order.filled_amount = Decimal("0.1")
        sample_order.average_price = Decimal("50000.0")
        sample_order.status = OrderStatus.FILLED
        
        await trading_engine._update_position(sample_order)
        
        assert sample_order.symbol in trading_engine.positions
        position = trading_engine.positions[sample_order.symbol]
        assert position.symbol == sample_order.symbol
        assert position.side == sample_order.side
        assert position.size == sample_order.filled_amount
        assert position.entry_price == sample_order.average_price
    
    @pytest.mark.asyncio
    async def test_update_position_add_to_existing(self, trading_engine, sample_order):
        """Test adding to existing position."""
        # Create existing position
        existing_position = Position(
            symbol="BTC/USDT",
            side=OrderSide.BUY,
            size=Decimal("0.1"),
            entry_price=Decimal("49000.0"),
            current_price=Decimal("50000.0"),
            unrealized_pnl=Decimal("100.0")
        )
        trading_engine.positions["BTC/USDT"] = existing_position
        
        # Add to position
        sample_order.filled_amount = Decimal("0.1")
        sample_order.average_price = Decimal("51000.0")
        sample_order.status = OrderStatus.FILLED
        
        await trading_engine._update_position(sample_order)
        
        position = trading_engine.positions["BTC/USDT"]
        assert position.size == Decimal("0.2")  # 0.1 + 0.1
        # Entry price should be weighted average
        expected_entry = (Decimal("49000.0") * Decimal("0.1") + Decimal("51000.0") * Decimal("0.1")) / Decimal("0.2")
        assert position.entry_price == expected_entry
    
    @pytest.mark.asyncio
    async def test_update_position_close_position(self, trading_engine, sample_order):
        """Test closing position with opposite order."""
        # Create existing position
        existing_position = Position(
            symbol="BTC/USDT",
            side=OrderSide.BUY,
            size=Decimal("0.1"),
            entry_price=Decimal("50000.0"),
            current_price=Decimal("51000.0"),
            unrealized_pnl=Decimal("100.0")
        )
        trading_engine.positions["BTC/USDT"] = existing_position
        
        # Close position
        sample_order.side = OrderSide.SELL
        sample_order.filled_amount = Decimal("0.1")
        sample_order.average_price = Decimal("51000.0")
        sample_order.status = OrderStatus.FILLED
        
        await trading_engine._update_position(sample_order)
        
        # Position should be closed
        assert "BTC/USDT" not in trading_engine.positions
    
    def test_get_portfolio_status(self, trading_engine, sample_position):
        """Test portfolio status calculation."""
        trading_engine.positions["BTC/USDT"] = sample_position
        trading_engine.balance = Decimal("10000")
        
        status = trading_engine.get_portfolio_status()
        
        assert status["balance"] == 10000.0
        assert status["unrealized_pnl"] == 100.0
        assert status["total_pnl"] == 100.0
        assert len(status["positions"]) == 1
        assert status["positions"][0]["symbol"] == "BTC/USDT"
    
    @pytest.mark.asyncio
    async def test_process_opportunity_valid(self, trading_engine):
        """Test processing valid opportunity."""
        opportunity = {
            "symbol": "BTC/USDT",
            "side_bias": "long",
            "confidence": 80.0,
            "atr_pct": 2.0,
            "notional": 1000.0,
            "manip_score": 20.0,
            "spread_bps": 5.0
        }
        
        with patch.object(trading_engine, '_check_risk_limits', return_value=True):
            with patch.object(trading_engine, '_submit_order') as mock_submit:
                await trading_engine._process_opportunity(opportunity)
                
                mock_submit.assert_called_once()
                order = mock_submit.call_args[0][0]
                assert order.symbol == "BTC/USDT"
                assert order.side == OrderSide.BUY
    
    @pytest.mark.asyncio
    async def test_process_opportunity_low_confidence(self, trading_engine):
        """Test processing opportunity with low confidence."""
        opportunity = {
            "symbol": "BTC/USDT",
            "side_bias": "long",
            "confidence": 50.0,  # Low confidence
            "atr_pct": 2.0,
            "notional": 1000.0
        }
        
        with patch.object(trading_engine, '_submit_order') as mock_submit:
            await trading_engine._process_opportunity(opportunity)
            mock_submit.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_process_opportunity_neutral_bias(self, trading_engine):
        """Test processing opportunity with neutral bias."""
        opportunity = {
            "symbol": "BTC/USDT",
            "side_bias": "neutral",
            "confidence": 80.0,
            "atr_pct": 2.0,
            "notional": 1000.0
        }
        
        with patch.object(trading_engine, '_submit_order') as mock_submit:
            await trading_engine._process_opportunity(opportunity)
            mock_submit.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_process_opportunity_existing_position(self, trading_engine):
        """Test processing opportunity when position already exists."""
        trading_engine.positions["BTC/USDT"] = sample_position()
        
        opportunity = {
            "symbol": "BTC/USDT",
            "side_bias": "long",
            "confidence": 80.0,
            "atr_pct": 2.0,
            "notional": 1000.0
        }
        
        with patch.object(trading_engine, '_submit_order') as mock_submit:
            await trading_engine._process_opportunity(opportunity)
            mock_submit.assert_not_called()
