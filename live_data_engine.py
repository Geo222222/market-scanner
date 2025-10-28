#!/usr/bin/env python3
"""
Nexus Alpha Live Data Engine
Real-time market data from exchanges
"""
import asyncio
import ccxt
import ccxt.async_support as ccxt_async
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import logging
from dataclasses import dataclass, asdict

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class LiveMarketData:
    """Live market data structure"""
    symbol: str
    exchange: str
    timestamp: float
    price: float
    bid: float
    ask: float
    spread: float
    volume_24h: float
    volume_usdt: float
    high_24h: float
    low_24h: float
    change_24h: float
    change_percent_24h: float
    orderbook_bids: List[List[float]]
    orderbook_asks: List[List[float]]
    trades: List[Dict]
    status: str = "live"

class LiveDataEngine:
    """Live data engine for real-time market data"""
    
    def __init__(self):
        self.exchanges = {}
        self.market_data = {}
        self.running = False
        self.symbols = [
            'BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'ADA/USDT', 'SOL/USDT',
            'XRP/USDT', 'DOT/USDT', 'DOGE/USDT', 'AVAX/USDT', 'MATIC/USDT'
        ]
        
        # Initialize exchanges
        self._init_exchanges()
    
    def _init_exchanges(self):
        """Initialize exchange connections"""
        try:
            # HTX (Huobi)
            self.exchanges['htx'] = ccxt_async.htx({
                'apiKey': '',  # No API key needed for public data
                'secret': '',
                'sandbox': False,
                'enableRateLimit': True,
            })
            
            # Binance
            self.exchanges['binance'] = ccxt_async.binance({
                'apiKey': '',  # No API key needed for public data
                'secret': '',
                'sandbox': False,
                'enableRateLimit': True,
            })
            
            # OKX
            self.exchanges['okx'] = ccxt_async.okx({
                'apiKey': '',  # No API key needed for public data
                'secret': '',
                'sandbox': False,
                'enableRateLimit': True,
            })
            
            logger.info(f"Initialized {len(self.exchanges)} exchanges")
            
        except Exception as e:
            logger.error(f"Error initializing exchanges: {e}")
    
    async def start_live_data(self):
        """Start live data collection"""
        self.running = True
        logger.info("Starting live data collection...")
        
        # Start data collection tasks
        tasks = []
        for exchange_name, exchange in self.exchanges.items():
            task = asyncio.create_task(self._collect_exchange_data(exchange_name, exchange))
            tasks.append(task)
        
        # Wait for all tasks
        await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _collect_exchange_data(self, exchange_name: str, exchange):
        """Collect data from a specific exchange"""
        try:
            await exchange.load_markets()
            logger.info(f"Connected to {exchange_name}")
            
            while self.running:
                try:
                    # Get ticker data for all symbols
                    for symbol in self.symbols:
                        try:
                            # Check if symbol exists on this exchange
                            if symbol in exchange.markets:
                                ticker = await exchange.fetch_ticker(symbol)
                                orderbook = await exchange.fetch_order_book(symbol, limit=10)
                                trades = await exchange.fetch_trades(symbol, limit=5)
                                
                                # Process and store data
                                market_data = self._process_ticker_data(
                                    symbol, exchange_name, ticker, orderbook, trades
                                )
                                
                                self.market_data[f"{symbol}_{exchange_name}"] = market_data
                                
                        except Exception as e:
                            logger.warning(f"Error fetching {symbol} from {exchange_name}: {e}")
                            continue
                    
                    # Wait before next update
                    await asyncio.sleep(5)  # Update every 5 seconds
                    
                except Exception as e:
                    logger.error(f"Error in {exchange_name} data collection: {e}")
                    await asyncio.sleep(10)  # Wait longer on error
                    
        except Exception as e:
            logger.error(f"Failed to connect to {exchange_name}: {e}")
        finally:
            await exchange.close()
    
    def _process_ticker_data(self, symbol: str, exchange: str, ticker: Dict, orderbook: Dict, trades: List) -> LiveMarketData:
        """Process ticker data into our format"""
        try:
            # Calculate spread
            bid = ticker.get('bid', 0)
            ask = ticker.get('ask', 0)
            spread = ((ask - bid) / bid * 10000) if bid > 0 else 0  # Spread in bps
            
            # Calculate volume in USDT
            volume_usdt = ticker.get('quoteVolume', 0)
            
            # Calculate 24h change
            change_24h = ticker.get('change', 0)
            change_percent_24h = ticker.get('percentage', 0)
            
            return LiveMarketData(
                symbol=symbol,
                exchange=exchange,
                timestamp=ticker.get('timestamp', time.time() * 1000),
                price=ticker.get('last', 0),
                bid=bid,
                ask=ask,
                spread=spread,
                volume_24h=ticker.get('baseVolume', 0),
                volume_usdt=volume_usdt,
                high_24h=ticker.get('high', 0),
                low_24h=ticker.get('low', 0),
                change_24h=change_24h,
                change_percent_24h=change_percent_24h,
                orderbook_bids=orderbook.get('bids', []),
                orderbook_asks=orderbook.get('asks', []),
                trades=trades[-5:] if trades else [],  # Last 5 trades
                status="live"
            )
            
        except Exception as e:
            logger.error(f"Error processing ticker data for {symbol}: {e}")
            # Return minimal data on error
            return LiveMarketData(
                symbol=symbol,
                exchange=exchange,
                timestamp=time.time() * 1000,
                price=0,
                bid=0,
                ask=0,
                spread=0,
                volume_24h=0,
                volume_usdt=0,
                high_24h=0,
                low_24h=0,
                change_24h=0,
                change_percent_24h=0,
                orderbook_bids=[],
                orderbook_asks=[],
                trades=[],
                status="error"
            )
    
    def get_live_data(self, symbol: str = None, exchange: str = None) -> Dict:
        """Get live market data"""
        if symbol and exchange:
            key = f"{symbol}_{exchange}"
            data = self.market_data.get(key)
            return data if data else None
        elif symbol:
            # Get data for symbol across all exchanges
            symbol_data = {}
            for key, data in self.market_data.items():
                if key.startswith(f"{symbol}_"):
                    exchange_name = key.split('_', 1)[1]
                    symbol_data[exchange_name] = data
            return symbol_data
        else:
            # Return all data
            return self.market_data
    
    def get_latest_prices(self) -> Dict:
        """Get latest prices for all symbols"""
        prices = {}
        for key, data in self.market_data.items():
            symbol = data.symbol
            if symbol not in prices:
                prices[symbol] = {}
            prices[symbol][data.exchange] = {
                'price': data.price,
                'spread': data.spread,
                'volume_usdt': data.volume_usdt,
                'change_24h': data.change_percent_24h,
                'timestamp': data.timestamp
            }
        return prices
    
    def stop(self):
        """Stop live data collection"""
        self.running = False
        logger.info("Stopping live data collection...")

# Global live data engine
live_data_engine = LiveDataEngine()

async def test_exchange_connections():
    """Test connections to exchanges"""
    logger.info("Testing exchange connections...")
    
    for exchange_name, exchange in live_data_engine.exchanges.items():
        try:
            await exchange.load_markets()
            logger.info(f"✓ {exchange_name}: Connected successfully")
            
            # Test fetching a simple ticker
            ticker = await exchange.fetch_ticker('BTC/USDT')
            logger.info(f"✓ {exchange_name}: BTC/USDT price: ${ticker.get('last', 'N/A')}")
            
            await exchange.close()
            
        except Exception as e:
            logger.error(f"✗ {exchange_name}: Connection failed - {e}")

async def test_live_data_collection():
    """Test live data collection for a short period"""
    logger.info("Testing live data collection for 30 seconds...")
    
    # Start data collection
    data_task = asyncio.create_task(live_data_engine.start_live_data())
    
    # Wait 30 seconds
    await asyncio.sleep(30)
    
    # Stop collection
    live_data_engine.stop()
    
    # Get collected data
    data = live_data_engine.get_live_data()
    logger.info(f"Collected data for {len(data)} symbols/exchanges")
    
    # Show sample data
    for key, market_data in list(data.items())[:3]:
        logger.info(f"Sample: {key} - Price: ${market_data['price']}, Spread: {market_data['spread']:.2f}bps")
    
    return data

if __name__ == "__main__":
    async def main():
        print("Nexus Alpha Live Data Engine Test")
        print("=" * 40)
        
        # Test connections
        await test_exchange_connections()
        print()
        
        # Test live data collection
        await test_live_data_collection()
    
    asyncio.run(main())
