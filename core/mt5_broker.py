import MetaTrader5 as mt5
from .base_broker import BrokerBase
import os
import platform
from typing import Optional

class MT5Broker(BrokerBase):
    def __init__(self, login, password, server):
        self.login = login
        self.password = password
        self.server = server
        self._initialize()

    def _initialize(self):
        if platform.system() != 'Windows':
            print("MT5 library is only supported on Windows.")
            return

        if not mt5.initialize(login=self.login, password=self.password, server=self.server):
            print("MT5 initialization failed, error code =", mt5.last_error())
            return False
        return True

    async def get_balance(self):
        account_info = mt5.account_info()
        if account_info is None:
            return {"error": "Failed to get account info"}
        return {"balance": account_info.balance, "equity": account_info.equity}

    async def get_price(self, symbol: str):
        symbol_info = mt5.symbol_info_tick(symbol)
        if symbol_info is None:
            return {"error": f"Symbol {symbol} not found"}
        return symbol_info.last

    async def execute_trade(self, symbol: str, side: str, amount: float, order_type: str = 'market', price: Optional[float] = None, sl: Optional[float] = None, tp: Optional[float] = None):
        if not mt5.initialize():
            return {"error": "MT5 not initialized"}

        symbol_info = mt5.symbol_info(symbol)
        if symbol_info is None:
            return {"error": f"{symbol} not found"}

        if not symbol_info.visible:
            if not mt5.symbol_select(symbol, True):
                return {"error": f"symbol_select({symbol}) failed"}

        type_dict = {
            'buy': mt5.ORDER_TYPE_BUY,
            'sell': mt5.ORDER_TYPE_SELL
        }

        action = type_dict.get(side.lower())
        if action is None:
            return {"error": "Invalid side"}

        price_val = mt5.symbol_info_tick(symbol).ask if side.lower() == 'buy' else mt5.symbol_info_tick(symbol).bid

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": amount,
            "type": action,
            "price": price_val,
            "sl": sl if sl else 0.0,
            "tp": tp if tp else 0.0,
            "deviation": 20,
            "magic": 234000,
            "comment": "BotX Pro Execution",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }

        result = mt5.order_send(request)
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            return {"error": f"Order send failed, retcode={result.retcode}"}
        
        return result._asdict()

    async def get_positions(self):
        positions = mt5.positions_get()
        if positions is None:
            return {"error": "Failed to get positions"}
        return [p._asdict() for p in positions]

    async def cancel_order(self, order_id: str, symbol: str):
        # MT5 pending orders cancellation
        request = {
            "action": mt5.TRADE_ACTION_REMOVE,
            "order": int(order_id),
        }
        result = mt5.order_send(request)
        return result._asdict()

    async def close(self):
        mt5.shutdown()
