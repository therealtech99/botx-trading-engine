import ccxt.async_support as ccxt
from .base_broker import BrokerBase
import os
from typing import Optional

class BybitBroker(BrokerBase):
    def __init__(self, api_key: str, secret_key: str, testnet: bool = True):
        self.exchange = ccxt.bybit({
            'apiKey': api_key,
            'secret': secret_key,
            'enableRateLimit': True,
            'options': {'defaultType': 'future'}
        })
        self.exchange.set_sandbox_mode(testnet)

    async def get_balance(self):
        try:
            balance = await self.exchange.fetch_balance()
            return balance['total']
        except Exception as e:
            return {"error": str(e)}

    async def get_price(self, symbol: str):
        try:
            ticker = await self.exchange.fetch_ticker(symbol)
            return ticker['last']
        except Exception as e:
            return {"error": str(e)}

    async def execute_trade(self, symbol: str, side: str, amount: float, order_type: str = 'market', price: Optional[float] = None, sl: Optional[float] = None, tp: Optional[float] = None):
        try:
            params = {}
            if sl: params['stop_loss'] = sl
            if tp: params['take_profit'] = tp
            
            order = await self.exchange.create_order(
                symbol=symbol,
                type=order_type,
                side=side,
                amount=amount,
                price=price,
                params=params
            )
            return order
        except Exception as e:
            return {"error": str(e)}

    async def get_positions(self):
        try:
            positions = await self.exchange.fetch_positions()
            return [p for p in positions if float(p['contracts']) > 0]
        except Exception as e:
            return {"error": str(e)}

    async def cancel_order(self, order_id: str, symbol: str):
        try:
            return await self.exchange.cancel_order(order_id, symbol)
        except Exception as e:
            return {"error": str(e)}

    async def close(self):
        await self.exchange.close()
