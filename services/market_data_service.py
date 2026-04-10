import asyncio
import ccxt.async_support as ccxt
from typing import Dict, List, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MarketDataService:
    def __init__(self):
        self.price_cache: Dict[str, float] = {}
        self.exchanges: Dict[str, ccxt.Exchange] = {
            'binance': ccxt.binance({'enableRateLimit': True}),
            'bybit': ccxt.bybit({'enableRateLimit': True}),
        }
        self.active_tasks: List[asyncio.Task] = []
        self.running = False

    async def start(self):
        self.running = True
        logger.info("MarketDataService starting...")
        # Default symbols to watch
        symbols = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT']
        
        for exc_id, exchange in self.exchanges.items():
            task = asyncio.create_task(self._watch_exchange(exc_id, exchange, symbols))
            self.active_tasks.append(task)

    async def stop(self):
        self.running = False
        for task in self.active_tasks:
            task.cancel()
        for exchange in self.exchanges.values():
            await exchange.close()
        logger.info("MarketDataService stopped.")

    async def _watch_exchange(self, exc_id: str, exchange: ccxt.Exchange, symbols: List[str]):
        """
        Fallback to periodic REST fetching if watch_ticker is not available (non-Pro CCXT).
        In a professional setup, you'd use ccxt.pro or exchange-specific SDKs.
        """
        while self.running:
            try:
                for symbol in symbols:
                    ticker = await exchange.fetch_ticker(symbol)
                    self.price_cache[f"{exc_id}_{symbol}"] = ticker['last']
                    # logger.debug(f"Updated {exc_id} {symbol}: {ticker['last']}")
                
                # REST Polling interval (high-freq fallback)
                await asyncio.sleep(1) 
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"DEBUG: Error watching {exc_id}: {e}")
                logger.error(f"Error watching {exc_id}: {e}")
                await asyncio.sleep(5)

    def get_price(self, exchange_id: str, symbol: str) -> Optional[float]:
        return self.price_cache.get(f"{exchange_id}_{symbol}")
