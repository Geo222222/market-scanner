"""
Production-grade logging configuration for Nexus Alpha.

This module configures logging to suppress verbose WebSocket debug messages
while maintaining essential diagnostic visibility for production systems.
"""
import logging
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional


def configure_production_logging(
    log_level: str = "INFO",
    log_file: Optional[Path] = None,
    enable_file_logging: bool = True,
    enable_console_logging: bool = True,
) -> None:
    """
    Configure production-grade logging with suppressed WebSocket debug spam.
    
    This function:
    1. Sets up clean console and file logging handlers
    2. Suppresses verbose WebSocket binary message dumps
    3. Suppresses CCXT debug messages
    4. Maintains WARNING+ messages for all libraries
    5. Keeps application logs at the specified level
    
    Args:
        log_level: Root logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional path to log file. If None and enable_file_logging=True,
                 creates logs/nexus_YYYYMMDD.log
        enable_file_logging: Whether to log to file
        enable_console_logging: Whether to log to console
    
    Example:
        >>> from market_scanner.logging_config import configure_production_logging
        >>> configure_production_logging(log_level="INFO")
    """
    # Create handlers list
    handlers = []
    
    # Console handler with clean formatting
    if enable_console_logging:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)  # Console shows INFO and above
        console_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        console_handler.setFormatter(console_formatter)
        handlers.append(console_handler)
    
    # File handler with detailed formatting
    if enable_file_logging:
        if log_file is None:
            log_dir = Path("logs")
            log_dir.mkdir(exist_ok=True)
            log_file = log_dir / f"nexus_{datetime.now().strftime('%Y%m%d')}.log"
        
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)  # File captures everything
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_formatter)
        handlers.append(file_handler)
    
    # Configure root logger
    # Set root to DEBUG so file handler can capture everything
    # Individual handlers control what actually gets output
    root_level = logging.DEBUG if enable_file_logging else getattr(logging, log_level.upper())
    logging.basicConfig(
        level=root_level,
        handlers=handlers,
        force=True  # Override any existing configuration
    )
    
    # ========================================================================
    # SUPPRESS VERBOSE WEBSOCKET DEBUG LOGS
    # ========================================================================
    # The websockets library logs binary message dumps at DEBUG level
    # Example: "< BINARY 1f 8b 08 00 ..." - these flood the console
    logging.getLogger('websockets').setLevel(logging.WARNING)
    logging.getLogger('websockets.client').setLevel(logging.WARNING)
    logging.getLogger('websockets.server').setLevel(logging.WARNING)
    logging.getLogger('websockets.protocol').setLevel(logging.WARNING)
    
    # ========================================================================
    # SUPPRESS CCXT VERBOSE LOGS
    # ========================================================================
    # CCXT can be very verbose with HTTP request/response details
    logging.getLogger('ccxt').setLevel(logging.WARNING)
    logging.getLogger('ccxt.base').setLevel(logging.WARNING)
    
    # ========================================================================
    # SUPPRESS OTHER NOISY LIBRARIES
    # ========================================================================
    # aiohttp can be verbose with connection pool messages
    logging.getLogger('aiohttp').setLevel(logging.WARNING)
    logging.getLogger('aiohttp.access').setLevel(logging.WARNING)
    logging.getLogger('aiohttp.client').setLevel(logging.WARNING)
    logging.getLogger('aiohttp.server').setLevel(logging.WARNING)
    logging.getLogger('aiohttp.web').setLevel(logging.WARNING)
    
    # urllib3 (used by requests/httpx) connection pool messages
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('urllib3.connectionpool').setLevel(logging.WARNING)
    
    # httpx verbose request logging
    logging.getLogger('httpx').setLevel(logging.WARNING)
    
    # asyncio debug messages
    logging.getLogger('asyncio').setLevel(logging.WARNING)
    
    # SQLAlchemy can be very verbose
    logging.getLogger('sqlalchemy').setLevel(logging.WARNING)
    logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)
    logging.getLogger('sqlalchemy.pool').setLevel(logging.WARNING)
    
    # Alembic migration logs
    logging.getLogger('alembic').setLevel(logging.INFO)
    
    # ========================================================================
    # KEEP APPLICATION LOGS VISIBLE
    # ========================================================================
    # Ensure our application logs are visible at the specified level
    # If file logging is enabled, set to DEBUG so file can capture everything
    app_level = logging.DEBUG if enable_file_logging else getattr(logging, log_level.upper())
    logging.getLogger('market_scanner').setLevel(app_level)
    logging.getLogger('__main__').setLevel(app_level)
    
    # Log the configuration
    logger = logging.getLogger(__name__)
    logger.info("=" * 70)
    logger.info("Production logging configured successfully")
    logger.info(f"Log level: {log_level.upper()}")
    if enable_file_logging and log_file:
        logger.info(f"Log file: {log_file}")
    logger.info("WebSocket debug logs: SUPPRESSED")
    logger.info("CCXT debug logs: SUPPRESSED")
    logger.info("Essential diagnostics: ENABLED")
    logger.info("=" * 70)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with the specified name.
    
    This is a convenience function that ensures consistent logger naming.
    
    Args:
        name: Logger name (typically __name__)
    
    Returns:
        Configured logger instance
    
    Example:
        >>> from market_scanner.logging_config import get_logger
        >>> logger = get_logger(__name__)
        >>> logger.info("Application started")
    """
    return logging.getLogger(name)


def set_ccxt_verbose(exchange_instance, verbose: bool = False) -> None:
    """
    Set verbose mode for a CCXT exchange instance.
    
    Args:
        exchange_instance: CCXT exchange object
        verbose: Whether to enable verbose logging (default: False)
    
    Example:
        >>> import ccxt
        >>> from market_scanner.logging_config import set_ccxt_verbose
        >>> exchange = ccxt.binance({'enableRateLimit': True})
        >>> set_ccxt_verbose(exchange, verbose=False)
    """
    if hasattr(exchange_instance, 'verbose'):
        exchange_instance.verbose = verbose


# ============================================================================
# CUSTOM LOG FILTERS (Optional - for advanced use cases)
# ============================================================================

class BinaryMessageFilter(logging.Filter):
    """
    Filter out binary WebSocket message logs.
    
    This filter suppresses log messages that contain binary data dumps
    like "< BINARY 1f 8b 08 00 ..." which are common in WebSocket libraries.
    """
    
    def filter(self, record: logging.LogRecord) -> bool:
        """Return False to suppress the log record."""
        message = record.getMessage()
        # Suppress messages containing binary dumps
        if '< BINARY' in message or '> BINARY' in message:
            return False
        # Suppress gzip/compressed data indicators
        if 'x1f x8b' in message.lower() or '1f 8b 08' in message:
            return False
        return True


class HTTPRequestFilter(logging.Filter):
    """
    Filter out verbose HTTP request/response logs.
    
    This filter suppresses detailed HTTP logs from libraries like
    urllib3, httpx, and aiohttp that can flood the console.
    """
    
    def filter(self, record: logging.LogRecord) -> bool:
        """Return False to suppress the log record."""
        message = record.getMessage()
        # Suppress connection pool messages
        if 'Starting new HTTPS connection' in message:
            return False
        if 'Resetting dropped connection' in message:
            return False
        # Suppress detailed request logs
        if 'HTTP Request:' in message and record.levelno < logging.WARNING:
            return False
        return True


def add_custom_filters() -> None:
    """
    Add custom log filters to suppress specific message patterns.
    
    This is optional and provides additional filtering beyond log levels.
    Use this if you still see unwanted messages after setting log levels.
    
    Example:
        >>> from market_scanner.logging_config import configure_production_logging, add_custom_filters
        >>> configure_production_logging()
        >>> add_custom_filters()  # Extra filtering if needed
    """
    # Add binary message filter to websockets loggers
    binary_filter = BinaryMessageFilter()
    logging.getLogger('websockets').addFilter(binary_filter)
    logging.getLogger('websockets.client').addFilter(binary_filter)
    logging.getLogger('websockets.protocol').addFilter(binary_filter)
    
    # Add HTTP request filter to connection libraries
    http_filter = HTTPRequestFilter()
    logging.getLogger('urllib3').addFilter(http_filter)
    logging.getLogger('httpx').addFilter(http_filter)
    logging.getLogger('aiohttp').addFilter(http_filter)
    
    logger = logging.getLogger(__name__)
    logger.debug("Custom log filters applied")

