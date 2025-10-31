"""
Multi-exchange order book fetcher with automatic fallbacks.
Fetches Level 2 order book data from multiple exchanges with automatic failover.
"""

from __future__ import annotations

import asyncio
import logging
import ccxt
from typing import Dict, List, Optional, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)


class OrderBookFetcher:
    """Fetches order book data from multiple exchanges with automatic fallback."""
    
    def __init__(self):
        self.exchanges = {}
        self.priority_order = ['binance', 'bybit', 'okx', 'bitget']
        self._initialize_exchanges()
    
    def _initialize_exchanges(self):
        """Initialize exchange instances for public data access."""
        exchange_configs = {
            'binance': {
                'enableRateLimit': True,
                'verbose': False,  # Suppress CCXT debug logs
                'options': {'defaultType': 'spot'}
            },
            'bybit': {
                'enableRateLimit': True,
                'verbose': False,  # Suppress CCXT debug logs
            },
            'okx': {
                'enableRateLimit': True,
                'verbose': False,  # Suppress CCXT debug logs
            },
            'bitget': {
                'enableRateLimit': True,
                'verbose': False,  # Suppress CCXT debug logs
            },
        }

        for name, config in exchange_configs.items():
            try:
                exchange_class = getattr(ccxt, name)
                self.exchanges[name] = exchange_class(config)
                logger.info(f"Initialized {name} exchange for order book fetching")
            except Exception as e:
                logger.warning(f"Failed to initialize {name}: {e}")
    
    def _normalize_symbol(self, symbol: str, exchange: ccxt.Exchange) -> Optional[str]:
        """
        Normalize symbol format for the exchange.
        Converts BTC-USDT or BTC/USDT to exchange-specific format.
        """
        try:
            # Try both formats
            for fmt in [symbol.replace('-', '/'), symbol]:
                if fmt in exchange.markets:
                    market = exchange.markets[fmt]
                    if market['active']:
                        return fmt
        except Exception as e:
            logger.debug(f"Symbol normalization error: {e}")
        
        return None
    
    async def fetch_order_book(
        self, 
        symbol: str, 
        limit: int = 20,
        exchange_name: Optional[str] = None
    ) -> Optional[Dict]:
        """
        Fetch order book from exchanges with automatic fallback.
        
        Args:
            symbol: Trading pair (e.g., 'BTC-USDT' or 'BTC/USDT')
            limit: Number of order book levels (default 20)
            exchange_name: Specific exchange to use, or None for auto-fallback
            
        Returns:
            Dict with bids/asks in format:
            {
                'bids': [[price, amount], ...],
                'asks': [[price, amount], ...],
                'timestamp': datetime,
                'exchange': str
            }
        """
        exchanges_to_try = [exchange_name] if exchange_name else self.priority_order
        
        for exchange_name in exchanges_to_try:
            if exchange_name not in self.exchanges:
                continue
            
            exchange = self.exchanges[exchange_name]
            
            try:
                # Load markets if not already loaded (synchronous)
                if not exchange.markets:
                    exchange.load_markets()
                
                # Normalize symbol for this exchange
                normalized_symbol = self._normalize_symbol(symbol, exchange)
                if not normalized_symbol:
                    logger.debug(f"{exchange_name}: No active market for {symbol}")
                    continue
                
                # Fetch order book (synchronous CCXT call in thread executor)
                logger.info(f"Fetching order book for {symbol} from {exchange_name}")
                loop = asyncio.get_event_loop()
                orderbook = await loop.run_in_executor(
                    None, 
                    exchange.fetch_order_book,
                    normalized_symbol,
                    limit
                )
                
                if orderbook and 'bids' in orderbook and 'asks' in orderbook:
                    # Convert to our format
                    result = {
                        'bids': [[float(b[0]), float(b[1])] for b in orderbook['bids']],
                        'asks': [[float(a[0]), float(a[1])] for a in orderbook['asks']],
                        'timestamp': datetime.now(),
                        'exchange': exchange_name,
                        'symbol': normalized_symbol
                    }
                    logger.info(f"Successfully fetched order book from {exchange_name}")
                    return result
                    
            except ccxt.NetworkError as e:
                logger.warning(f"{exchange_name} network error: {e}")
                continue
            except ccxt.ExchangeError as e:
                logger.warning(f"{exchange_name} exchange error: {e}")
                continue
            except Exception as e:
                logger.warning(f"{exchange_name} unexpected error: {e}")
                continue
        
        logger.warning(f"Failed to fetch order book for {symbol} from all exchanges")
        return None
    
    async def fetch_multiple_symbols(
        self,
        symbols: List[str],
        limit: int = 20
    ) -> Dict[str, Dict]:
        """
        Fetch order books for multiple symbols in parallel.
        
        Args:
            symbols: List of trading pairs
            limit: Number of order book levels
            
        Returns:
            Dict mapping symbol to order book data
        """
        tasks = []
        for symbol in symbols:
            tasks.append(self.fetch_order_book(symbol, limit))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        order_books = {}
        for symbol, result in zip(symbols, results):
            if isinstance(result, dict):
                order_books[symbol] = result
            elif isinstance(result, Exception):
                logger.error(f"Error fetching {symbol}: {result}")
        
        return order_books
    
    def get_available_exchanges(self) -> List[str]:
        """Get list of available exchanges."""
        return list(self.exchanges.keys())
    
    def health_check(self) -> Dict[str, bool]:
        """Check health of all exchanges."""
        health = {}
        for name, exchange in self.exchanges.items():
            try:
                if not exchange.markets:
                    exchange.load_markets()
                health[name] = True
            except Exception:
                health[name] = False
        return health


# Global instance
_order_book_fetcher = None

def get_order_book_fetcher() -> OrderBookFetcher:
    """Get or create the global OrderBookFetcher instance."""
    global _order_book_fetcher
    if _order_book_fetcher is None:
        _order_book_fetcher = OrderBookFetcher()
    return _order_book_fetcher

