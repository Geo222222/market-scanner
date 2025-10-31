# Logging Configuration Guide

## Overview

The Nexus Alpha system now uses a production-grade logging configuration that suppresses verbose WebSocket and CCXT debug messages while maintaining essential diagnostic visibility.

## Problem Statement

Previously, the system was experiencing:
- **Verbose WebSocket logs**: Binary message dumps like `< BINARY 1f 8b 08 00 ...` flooding the console
- **CCXT debug spam**: Detailed HTTP request/response logs from exchange APIs
- **Performance impact**: Excessive logging affecting system performance
- **Poor readability**: Important messages buried in debug noise

## Solution

A centralized logging configuration module (`src/market_scanner/logging_config.py`) that:

1. ✅ Suppresses WebSocket debug logs (set to WARNING level)
2. ✅ Suppresses CCXT verbose output (`verbose=False` on all exchanges)
3. ✅ Maintains clean console output (INFO and above)
4. ✅ Captures detailed logs to file (DEBUG and above)
5. ✅ Keeps application logs visible at configured level
6. ✅ Provides custom filters for advanced use cases

---

## Quick Start

### Basic Usage

```python
from market_scanner.logging_config import configure_production_logging

# Configure logging at application startup
configure_production_logging(log_level="INFO")
```

### With File Logging

```python
from pathlib import Path
from market_scanner.logging_config import configure_production_logging

log_file = Path("logs") / "my_app.log"
configure_production_logging(
    log_level="INFO",
    log_file=log_file,
    enable_file_logging=True,
    enable_console_logging=True
)
```

### Get Logger Instance

```python
from market_scanner.logging_config import get_logger

logger = get_logger(__name__)
logger.info("Application started")
logger.warning("This is a warning")
logger.error("This is an error")
```

---

## Configuration Details

### Log Levels

The system uses standard Python logging levels:

| Level | Numeric Value | Usage |
|-------|---------------|-------|
| DEBUG | 10 | Detailed diagnostic information (file only) |
| INFO | 20 | General informational messages |
| WARNING | 30 | Warning messages (potential issues) |
| ERROR | 40 | Error messages (failures) |
| CRITICAL | 50 | Critical failures |

### Suppressed Loggers

The following loggers are set to **WARNING** level to suppress debug spam:

#### WebSocket Libraries
- `websockets`
- `websockets.client`
- `websockets.server`
- `websockets.protocol`

#### Exchange/HTTP Libraries
- `ccxt`
- `ccxt.base`
- `aiohttp`
- `aiohttp.access`
- `aiohttp.client`
- `urllib3`
- `urllib3.connectionpool`
- `httpx`

#### Database Libraries
- `sqlalchemy`
- `sqlalchemy.engine`
- `sqlalchemy.pool`

#### System Libraries
- `asyncio`

### Application Loggers

Application loggers remain at the configured level:
- `market_scanner.*` - All application modules
- `__main__` - Main application entry point

---

## CCXT Configuration

All CCXT exchange instances are configured with `verbose=False`:

```python
import ccxt

# ✅ Correct - Suppresses debug logs
exchange = ccxt.binance({
    'enableRateLimit': True,
    'verbose': False  # Important!
})

# ❌ Incorrect - Will spam console
exchange = ccxt.binance({
    'enableRateLimit': True
    # Missing verbose=False
})
```

### Updated Files

The following files have been updated to include `verbose=False`:

1. `src/market_scanner/adapters/ccxt.py`
2. `src/market_scanner/adapters/ccxt_adapter.py`
3. `src/market_scanner/engines/live_data_engine.py`
4. `src/market_scanner/engines/live_data_engine_refactored.py`
5. `src/market_scanner/feeds/order_book_fetcher.py`
6. `src/market_scanner/routers/live_chart.py`

---

## Advanced Features

### Custom Log Filters

For additional filtering beyond log levels:

```python
from market_scanner.logging_config import configure_production_logging, add_custom_filters

# Configure logging
configure_production_logging()

# Add custom filters to suppress specific message patterns
add_custom_filters()
```

Available filters:
- **BinaryMessageFilter**: Suppresses binary WebSocket message dumps
- **HTTPRequestFilter**: Suppresses verbose HTTP connection logs

### Setting CCXT Verbose Programmatically

```python
from market_scanner.logging_config import set_ccxt_verbose
import ccxt

exchange = ccxt.binance({'enableRateLimit': True})
set_ccxt_verbose(exchange, verbose=False)
```

---

## Output Examples

### Before (Verbose Debug Spam)

```
2024-01-15 10:30:45 - websockets.client - DEBUG - < BINARY 1f 8b 08 00 00 00 00 00 00 ff ...
2024-01-15 10:30:45 - websockets.client - DEBUG - > TEXT {"type":"ping"}
2024-01-15 10:30:45 - ccxt.base - DEBUG - Request: GET https://api.binance.com/api/v3/ticker/24hr
2024-01-15 10:30:45 - urllib3.connectionpool - DEBUG - Starting new HTTPS connection (1): api.binance.com:443
2024-01-15 10:30:45 - urllib3.connectionpool - DEBUG - https://api.binance.com:443 "GET /api/v3/ticker/24hr HTTP/1.1" 200 None
2024-01-15 10:30:45 - market_scanner.app - INFO - Application started
```

### After (Clean Production Logs)

```
======================================================================
Production logging configured successfully
Log level: INFO
Log file: logs/nexus_20240115.log
WebSocket debug logs: SUPPRESSED
CCXT debug logs: SUPPRESSED
Essential diagnostics: ENABLED
======================================================================
2024-01-15 10:30:45 - market_scanner.app - INFO - Application started
2024-01-15 10:30:46 - market_scanner.feeds.htx - INFO - HTX feed started for 10 symbols
2024-01-15 10:30:47 - market_scanner.engines.live_data_engine_refactored - INFO - Initialized 3 exchanges
```

---

## File Structure

### Console Output (INFO+)
- Clean, readable messages
- Only important events
- No binary dumps or HTTP details

### File Output (DEBUG+)
- Detailed diagnostic information
- Full stack traces
- Function names and line numbers
- All application debug messages

### Log File Location

Default: `logs/nexus_YYYYMMDD.log`

Example:
```
logs/
├── nexus_20240115.log
├── nexus_20240116.log
└── nexus_20240117.log
```

---

## Integration Points

### Main Application (`src/market_scanner/app.py`)

```python
from .logging_config import configure_production_logging

# Configure at module level (before app creation)
configure_production_logging(log_level="INFO", enable_file_logging=False)
```

### Production App (`apps/nexus_production_refactored.py`)

```python
from market_scanner.logging_config import configure_production_logging, get_logger
from pathlib import Path
from datetime import datetime

# Configure with file logging
log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)
log_file = log_dir / f"nexus_{datetime.now().strftime('%Y%m%d')}.log"

configure_production_logging(
    log_level="INFO",
    log_file=log_file,
    enable_file_logging=True,
    enable_console_logging=True
)

logger = get_logger(__name__)
```

---

## Troubleshooting

### Still Seeing Debug Messages?

1. **Check log level**: Ensure `log_level="INFO"` or higher
2. **Check logger name**: Some third-party libraries may use different logger names
3. **Add custom filters**: Use `add_custom_filters()` for pattern-based suppression

### Missing Important Messages?

1. **Lower log level**: Use `log_level="DEBUG"` temporarily
2. **Check file logs**: Debug messages are always in the file
3. **Check logger configuration**: Ensure application loggers aren't suppressed

### Performance Still Slow?

1. **Disable file logging**: Set `enable_file_logging=False`
2. **Reduce log retention**: Clean up old log files
3. **Check other bottlenecks**: Logging may not be the issue

---

## Best Practices

### ✅ Do

- Use `configure_production_logging()` at application startup
- Set `verbose=False` on all CCXT exchanges
- Use appropriate log levels (INFO for production, DEBUG for development)
- Keep log files for debugging but rotate them regularly
- Use structured logging for important events

### ❌ Don't

- Don't call `logging.basicConfig()` after `configure_production_logging()`
- Don't set individual logger levels before configuration
- Don't log sensitive data (API keys, passwords)
- Don't use DEBUG level in production console output
- Don't ignore WARNING and ERROR messages

---

## Migration Guide

### From Old Configuration

**Before:**
```python
import logging

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

**After:**
```python
from market_scanner.logging_config import configure_production_logging

configure_production_logging(log_level="INFO")
```

### From CCXT Without Verbose Flag

**Before:**
```python
exchange = ccxt.binance({'enableRateLimit': True})
```

**After:**
```python
exchange = ccxt.binance({'enableRateLimit': True, 'verbose': False})
```

---

## Testing

### Verify Configuration

```python
import logging
from market_scanner.logging_config import configure_production_logging, get_logger

# Configure
configure_production_logging(log_level="INFO")

# Test loggers
app_logger = get_logger("market_scanner.test")
ws_logger = logging.getLogger("websockets.client")

# These should appear
app_logger.info("This should appear")
app_logger.warning("This should appear")

# These should NOT appear in console (but in file)
app_logger.debug("This should NOT appear in console")
ws_logger.debug("This should NOT appear")

# This should appear (WARNING level)
ws_logger.warning("This should appear")
```

---

## Support

For issues or questions:
1. Check this documentation
2. Review `src/market_scanner/logging_config.py` source code
3. Check application logs in `logs/` directory
4. Raise an issue with log samples

---

## Summary

The new logging configuration provides:
- ✅ **Clean console output** - No binary dumps or HTTP spam
- ✅ **Detailed file logs** - Full diagnostic information preserved
- ✅ **Production-ready** - Optimized for performance and readability
- ✅ **Flexible** - Easy to customize for different environments
- ✅ **Maintainable** - Centralized configuration in one module

**Result**: Minimal runtime console output while maintaining essential diagnostic visibility.

