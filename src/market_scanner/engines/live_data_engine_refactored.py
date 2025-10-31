"""
Live Data Engine (Refactored)
- Non-blocking CCXT calls using asyncio.to_thread()
- Configuration-based API keys
- Deterministic mock data for testing
"""

import asyncio
import logging
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
import ccxt

from ..config import get_settings
from .mock_data import mock_data_generator
from ..data_integrity import (
    is_strict_mode,
    is_permissive_mode,
    log_data_error,
    log_data_success,
    DataSource
)

logger = logging.getLogger(__name__)


@dataclass
class LiveMarketData:
    symbol: str
    price: float
    volume: float
    spread: float
    change_24h: float
    high_24h: float
    low_24h: float
    timestamp: datetime
    exchange: str
    status: str = "live"


class LiveDataEngineRefactored:
    """
    Live data engine with non-blocking I/O and configuration-based credentials.
    """
    
    def __init__(self):
        self.settings = get_settings()
        self.exchanges = {}
        self.executor = ThreadPoolExecutor(max_workers=3, thread_name_prefix="ccxt")
        self.running = False
        self._initialize_exchanges()
    
    def _initialize_exchanges(self):
        """Initialize exchanges with configuration-based credentials."""
        try:
            # Only initialize if not using mock data
            if self.settings.use_mock_data:
                logger.info("Using deterministic mock data (no live exchanges)")
                return
            
            # OKX
            if self.settings.okx_api_key or True:  # Initialize even without keys for public data
                self.exchanges['okx'] = ccxt.okx({
                    'apiKey': self.settings.okx_api_key or '',
                    'secret': self.settings.okx_secret or '',
                    'password': self.settings.okx_password or '',
                    'sandbox': self.settings.use_sandbox,
                    'enableRateLimit': True,
                    'verbose': False,  # Suppress CCXT debug logs
                })
                logger.info("Initialized OKX exchange")

            # Binance
            if self.settings.binance_api_key or True:
                self.exchanges['binance'] = ccxt.binance({
                    'apiKey': self.settings.binance_api_key or '',
                    'secret': self.settings.binance_secret or '',
                    'sandbox': self.settings.use_sandbox,
                    'enableRateLimit': True,
                    'verbose': False,  # Suppress CCXT debug logs
                })
                logger.info("Initialized Binance exchange")

            # HTX (Huobi)
            if self.settings.htx_api_key or True:
                try:
                    self.exchanges['htx'] = ccxt.huobi({
                        'apiKey': self.settings.htx_api_key or '',
                        'secret': self.settings.htx_secret or '',
                        'sandbox': self.settings.use_sandbox,
                        'enableRateLimit': True,
                        'verbose': False,  # Suppress CCXT debug logs
                    })
                    logger.info("Initialized HTX exchange")
                except Exception as e:
                    logger.warning(f"HTX initialization skipped: {e}")
            
            logger.info(f"Initialized {len(self.exchanges)} exchanges")
            
        except Exception as e:
            logger.error(f"Failed to initialize exchanges: {e}")
    
    async def _fetch_ticker_async(self, exchange_name: str, exchange: ccxt.Exchange, symbol: str) -> Optional[Dict]:
        """Fetch ticker data asynchronously (non-blocking)."""
        try:
            # Run blocking CCXT call in executor to avoid blocking event loop
            loop = asyncio.get_event_loop()
            ticker = await loop.run_in_executor(
                self.executor,
                exchange.fetch_ticker,
                symbol
            )
            return ticker
        except Exception as e:
            logger.debug(f"Error fetching {symbol} from {exchange_name}: {e}")
            return None
    
    def _get_mock_data(self, symbol: str) -> LiveMarketData:
        """Generate deterministic mock data for a symbol."""
        ticker = mock_data_generator.generate_ticker(symbol)
        
        return LiveMarketData(
            symbol=symbol,
            price=float(ticker['last']),
            volume=float(ticker['baseVolume']),
            spread=float(ticker['spread']),
            change_24h=float(ticker['percentage']),
            high_24h=float(ticker['high']),
            low_24h=float(ticker['low']),
            timestamp=datetime.now(),
            exchange='mock',
            status='mock'
        )
    
    async def get_live_data(self, symbols: List[str]) -> Dict[str, LiveMarketData]:
        """
        Get live market data for symbols.
        Non-blocking implementation using asyncio.to_thread().
        """
        results = {}
        
        # Use mock data if configured (only allowed in permissive mode)
        if self.settings.use_mock_data:
            if is_permissive_mode():
                logger.info("PERMISSIVE MODE: Using mock data (use_mock_data=True)")
                for symbol in symbols:
                    results[symbol] = self._get_mock_data(symbol)
                return results
            else:
                logger.error("STRICT MODE: use_mock_data=True is not allowed in strict mode")
                raise ValueError("Mock data is not allowed in strict mode. Set FALLBACK_POLICY=permissive or use_mock_data=False")
        
        # Fetch from real exchanges (non-blocking)
        for symbol in symbols:
            try:
                # Try exchanges in parallel (non-blocking)
                tasks = []
                for exchange_name, exchange in self.exchanges.items():
                    task = self._fetch_ticker_async(exchange_name, exchange, symbol)
                    tasks.append((exchange_name, task))
                
                # Wait for first successful response
                for exchange_name, task in tasks:
                    try:
                        ticker = await asyncio.wait_for(task, timeout=5.0)
                        
                        if ticker and ticker.get('last'):
                            results[symbol] = LiveMarketData(
                                symbol=symbol,
                                price=float(ticker['last']),
                                volume=float(ticker.get('baseVolume', 0) or 0),
                                spread=float(ticker.get('spread', 0)),
                                change_24h=float(ticker.get('percentage', 0)),
                                high_24h=float(ticker.get('high', 0)),
                                low_24h=float(ticker.get('low', 0)),
                                timestamp=datetime.now(),
                                exchange=exchange_name,
                                status="live"
                            )
                            break  # Got data, move to next symbol
                            
                    except asyncio.TimeoutError:
                        logger.warning(f"Timeout fetching {symbol} from {exchange_name}")
                        continue
                    except Exception as e:
                        logger.debug(f"Error fetching {symbol} from {exchange_name}: {e}")
                        continue
                
                # Handle missing data based on FALLBACK_POLICY
                if symbol not in results:
                    if is_strict_mode():
                        # In strict mode: log error and skip symbol (no fallback)
                        log_data_error(
                            exchange="all",
                            symbol=symbol,
                            operation="fetch_ticker",
                            error="All exchanges failed",
                            retries=len(self.exchanges)
                        )
                        logger.warning(f"STRICT MODE: Skipping {symbol} - no data available from any exchange")
                    else:
                        # In permissive mode: allow mock data with explicit labeling
                        logger.info(f"PERMISSIVE MODE: Using mock data for {symbol} (exchange fetch failed)")
                        results[symbol] = self._get_mock_data(symbol)

            except Exception as e:
                logger.error(f"Error processing {symbol}: {e}")

                if is_strict_mode():
                    # In strict mode: log error and skip symbol
                    log_data_error(
                        exchange="unknown",
                        symbol=symbol,
                        operation="process_ticker",
                        error=str(e),
                        retries=0
                    )
                    logger.warning(f"STRICT MODE: Skipping {symbol} due to processing error")
                else:
                    # In permissive mode: provide mock data
                    logger.info(f"PERMISSIVE MODE: Using mock data for {symbol} after error")
                    results[symbol] = self._get_mock_data(symbol)
        
        return results
    
    def _get_base_price(self, symbol: str) -> float:
        """Get base price for a symbol (for backward compatibility)."""
        return mock_data_generator.BASE_PRICES.get(symbol, 100.0)
    
    def cleanup(self):
        """Cleanup resources."""
        self.executor.shutdown(wait=True)
        logger.info("Live data engine cleaned up")


# Singleton instance (backward compatible)
live_data_engine_refactored = LiveDataEngineRefactored()

