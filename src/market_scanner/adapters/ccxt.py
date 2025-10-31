import os
import ccxt.async_support as ccxt


class CCXTAdapter:
    def __init__(self, exchange_id: str = "htx"):
        ex_cls = getattr(ccxt, exchange_id)
        self.ex = ex_cls(
            {
                "apiKey": os.getenv("HTX_KEY", ""),
                "secret": os.getenv("HTX_SECRET", ""),
                "enableRateLimit": True,
                "verbose": False,  # Suppress CCXT debug logs
            }
        )

    async def fetch_market(self, symbol: str) -> dict:
        # Use 1m candles for short-term signals
        ohlcv = await self.ex.fetch_ohlcv(symbol, timeframe="1m", limit=5)
        ticker = await self.ex.fetch_ticker(symbol)
        last = ticker.get("last")
        bid, ask = ticker.get("bid"), ticker.get("ask")
        spread_bps = 0.0 if not (bid and ask) else (ask - bid) / ((ask + bid) / 2) * 1e4
        vol5 = sum([c[5] for c in ohlcv[-5:]]) if ohlcv else 0.0
        base_close = ohlcv[-5][4] if ohlcv else (last or 1.0)
        mom = ((last or base_close) - base_close) / max(1e-9, base_close) * 100.0
        return {"last": last, "spread_bps": spread_bps, "volume_5m": vol5, "mom_1m": mom}
    
    async def close(self):
        """Close exchange connection."""
        await self.ex.close()


__all__ = ["CCXTAdapter"]
