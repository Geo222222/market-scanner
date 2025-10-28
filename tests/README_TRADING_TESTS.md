# Trading System Tests

This directory contains comprehensive tests for the trading system components built on top of the market scanner.

## Test Structure

### Core Components
- **`test_trading_engine.py`** - Tests for the core trading engine logic
- **`test_trading_router.py`** - Tests for the trading API endpoints
- **`test_backtesting_engine.py`** - Tests for the backtesting engine
- **`test_backtesting_router.py`** - Tests for the backtesting API endpoints
- **`test_trading_integration.py`** - End-to-end integration tests
- **`test_trading_config.py`** - Test configuration and utilities

### Test Categories

#### 1. Trading Engine Tests (`test_trading_engine.py`)
Tests the core trading logic including:
- Order creation and management
- Position tracking and P&L calculation
- Risk management and filtering
- Signal processing and execution
- Portfolio status calculation

**Key Test Classes:**
- `TestOrder` - Order model validation
- `TestPosition` - Position model validation
- `TestTradingEngine` - Core trading engine functionality

#### 2. Trading Router Tests (`test_trading_router.py`)
Tests the trading API endpoints including:
- Portfolio status endpoints
- Order management endpoints
- Position management endpoints
- Engine control endpoints
- Error handling

**Key Test Classes:**
- `TestTradingRouter` - API endpoint functionality

#### 3. Backtesting Engine Tests (`test_backtesting_engine.py`)
Tests the backtesting functionality including:
- Historical data processing
- Strategy simulation
- Performance metrics calculation
- Position size calculation
- Trade result analysis

**Key Test Classes:**
- `TestBacktestResult` - Trade result model validation
- `TestBacktestStats` - Performance stats model validation
- `TestBacktestEngine` - Core backtesting functionality

#### 4. Backtesting Router Tests (`test_backtesting_router.py`)
Tests the backtesting API endpoints including:
- Full backtest execution
- Quick backtest functionality
- Data range and symbol queries
- Error handling and validation

**Key Test Classes:**
- `TestBacktestingRouter` - API endpoint functionality

#### 5. Integration Tests (`test_trading_integration.py`)
Tests the complete trading workflow including:
- End-to-end trading workflows
- Backtesting workflows
- Position management workflows
- Error handling across components
- Dashboard functionality

**Key Test Classes:**
- `TestTradingIntegration` - Complete system integration

#### 6. Test Configuration (`test_trading_config.py`)
Provides test utilities and fixtures including:
- Sample data creation
- Mock objects and adapters
- Test configuration validation

**Key Test Classes:**
- `TestTradingConfig` - Test utility validation

## Running Tests

### Run All Trading Tests
```bash
# From project root
python tests/run_trading_tests.py
```

### Run Specific Test Files
```bash
# Trading engine tests
pytest tests/test_trading_engine.py -v

# Trading router tests
pytest tests/test_trading_router.py -v

# Backtesting engine tests
pytest tests/test_backtesting_engine.py -v

# Backtesting router tests
pytest tests/test_backtesting_router.py -v

# Integration tests
pytest tests/test_trading_integration.py -v
```

### Run with Coverage
```bash
pytest tests/test_trading_*.py --cov=market_scanner.engine.trading --cov=market_scanner.routers.trading --cov=market_scanner.engine.backtesting --cov=market_scanner.routers.backtesting
```

## Test Data and Fixtures

### Sample Orders
- `sample_order` - Basic market order
- `sample_filled_order` - Completed limit order

### Sample Positions
- `sample_position` - Long position with unrealized P&L

### Sample Opportunities
- `sample_opportunity` - Trading signal from scanner

### Mock Objects
- `mock_ccxt_adapter` - Mocked exchange adapter
- `mock_scanner_api_response` - Mocked scanner API response
- `mock_historical_data` - Mocked historical price data

## Test Coverage

The tests cover:

### Trading Engine
- ✅ Order creation and validation
- ✅ Position tracking and updates
- ✅ Risk management and filtering
- ✅ Signal processing
- ✅ Portfolio status calculation
- ✅ Error handling

### Trading API
- ✅ All REST endpoints
- ✅ Request/response validation
- ✅ Error handling and status codes
- ✅ Authentication and authorization
- ✅ Data serialization

### Backtesting Engine
- ✅ Historical data processing
- ✅ Strategy simulation
- ✅ Performance metrics calculation
- ✅ Position sizing
- ✅ Trade analysis

### Backtesting API
- ✅ All REST endpoints
- ✅ Parameter validation
- ✅ Data queries
- ✅ Error handling

### Integration
- ✅ Complete workflows
- ✅ Component interaction
- ✅ Error propagation
- ✅ Dashboard functionality

## Mocking Strategy

### External Dependencies
- **CCXT Adapter** - Mocked to avoid real exchange calls
- **Database** - Mocked for backtesting data queries
- **Scanner API** - Mocked for signal generation tests

### Internal Components
- **Trading Engine** - Mocked for router tests
- **Backtest Engine** - Mocked for router tests
- **Time-dependent functions** - Mocked for consistent testing

## Test Data Management

### Fixtures
- Reusable test data created via pytest fixtures
- Consistent data across test files
- Easy to modify and extend

### Sample Data
- Realistic but synthetic data
- Covers edge cases and normal scenarios
- Includes both valid and invalid data

## Continuous Integration

### Pre-commit Hooks
- Linting with ruff
- Type checking with mypy
- Test execution

### CI Pipeline
- Automated test execution
- Coverage reporting
- Performance regression testing

## Debugging Tests

### Verbose Output
```bash
pytest tests/test_trading_engine.py -v -s
```

### Debug Mode
```bash
pytest tests/test_trading_engine.py --pdb
```

### Specific Test
```bash
pytest tests/test_trading_engine.py::TestTradingEngine::test_calculate_position_size -v
```

## Adding New Tests

### Test Naming Convention
- Test files: `test_<component>.py`
- Test classes: `Test<Component>`
- Test methods: `test_<functionality>`

### Test Structure
```python
def test_functionality(self, fixture1, fixture2):
    """Test description."""
    # Arrange
    setup_data = fixture1
    
    # Act
    result = function_under_test(setup_data)
    
    # Assert
    assert result == expected_value
```

### Fixture Usage
- Use existing fixtures when possible
- Create new fixtures for complex setup
- Keep fixtures focused and reusable

## Performance Testing

### Load Testing
- Multiple concurrent orders
- Large position portfolios
- High-frequency backtesting

### Memory Testing
- Large historical datasets
- Long-running backtests
- Memory leak detection

## Security Testing

### Input Validation
- Malicious order data
- SQL injection attempts
- XSS prevention

### Authentication
- API key validation
- Permission checks
- Rate limiting

## Future Enhancements

### Planned Tests
- [ ] Performance benchmarks
- [ ] Load testing scenarios
- [ ] Security penetration tests
- [ ] Chaos engineering tests
- [ ] End-to-end user workflows

### Test Infrastructure
- [ ] Test data factories
- [ ] Automated test generation
- [ ] Visual regression testing
- [ ] API contract testing
