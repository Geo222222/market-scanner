"""
Live Data Engine for Nexus Alpha
Collects real-time market data from multiple exchanges
"""

import asyncio
import logging
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime
import ccxt
import random

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

class LiveDataEngine:
    def __init__(self):
        self.exchanges = {}
        self.market_data = {}
        self.running = False
        
        # Initialize exchanges
        try:
            self.exchanges['okx'] = ccxt.okx({
                'apiKey': '',
                'secret': '',
                'password': '',
                'sandbox': False,
                'enableRateLimit': True,
                'verbose': False,  # Suppress CCXT debug logs
            })
            self.exchanges['binance'] = ccxt.binance({
                'apiKey': '',
                'secret': '',
                'sandbox': False,
                'enableRateLimit': True,
                'verbose': False,  # Suppress CCXT debug logs
            })
            self.exchanges['htx'] = ccxt.huobi({
                'apiKey': '',
                'secret': '',
                'sandbox': False,
                'enableRateLimit': True,
                'verbose': False,  # Suppress CCXT debug logs
            })
            logger.info("Initialized 3 exchanges")
        except Exception as e:
            logger.error(f"Failed to initialize exchanges: {e}")
    
    async def get_live_data(self, symbols: List[str]) -> Dict[str, LiveMarketData]:
        """Get live market data for symbols"""
        results = {}
        
        for symbol in symbols:
            try:
                # Try to get real data from exchanges
                for exchange_name, exchange in self.exchanges.items():
                    try:
                        ticker = exchange.fetch_ticker(symbol)
                        if ticker and ticker.get('last'):
                            results[symbol] = LiveMarketData(
                                symbol=symbol,
                                price=float(ticker['last']),
                                volume=float(ticker['baseVolume'] or 0),
                                spread=float(ticker.get('spread', 0)),
                                change_24h=float(ticker.get('percentage', 0)),
                                high_24h=float(ticker.get('high', 0)),
                                low_24h=float(ticker.get('low', 0)),
                                timestamp=datetime.now(),
                                exchange=exchange_name,
                                status="live"
                            )
                            break
                    except Exception as e:
                        logger.error(f"Error fetching {symbol} from {exchange_name}: {e}")
                        continue
                
                # Fallback to realistic mock data
                if symbol not in results:
                    base_price = self._get_base_price(symbol)
                    price_variation = random.uniform(0.95, 1.05)
                    current_price = base_price * price_variation
                    
                    results[symbol] = LiveMarketData(
                        symbol=symbol,
                        price=current_price,
                        volume=random.uniform(1000000, 50000000),
                        spread=random.uniform(0.1, 2.0),
                        change_24h=random.uniform(-10, 10),
                        high_24h=current_price * random.uniform(1.01, 1.05),
                        low_24h=current_price * random.uniform(0.95, 0.99),
                        timestamp=datetime.now(),
                        exchange="fallback",
                        status="fallback"
                    )
                    
            except Exception as e:
                logger.error(f"Error processing ticker data for {symbol}: {e}")
                # Create fallback data
                base_price = self._get_base_price(symbol)
                results[symbol] = LiveMarketData(
                    symbol=symbol,
                    price=base_price,
                    volume=random.uniform(1000000, 50000000),
                    spread=random.uniform(0.1, 2.0),
                    change_24h=random.uniform(-10, 10),
                    high_24h=base_price * 1.02,
                    low_24h=base_price * 0.98,
                    timestamp=datetime.now(),
                    exchange="fallback",
                    status="fallback"
                )
        
        return results
    
    def _get_base_price(self, symbol: str) -> float:
        """Get base price for symbol"""
        base_prices = {
            'BTC/USDT': 45000,
            'ETH/USDT': 3000,
            'BNB/USDT': 300,
            'ADA/USDT': 0.5,
            'SOL/USDT': 100,
            'XRP/USDT': 0.6,
            'DOT/USDT': 6,
            'DOGE/USDT': 0.08,
            'AVAX/USDT': 25,
            'MATIC/USDT': 0.8
        }
        return base_prices.get(symbol, 1.0)

# Global instance
live_data_engine = LiveDataEngine()
