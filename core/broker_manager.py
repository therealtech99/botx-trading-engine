from .binance_broker import BinanceBroker
from .bybit_broker import BybitBroker
from .mt5_broker import MT5Broker
from .paper_broker import PaperBroker
from .base_broker import BrokerBase
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class BrokerManager:
    def __init__(self):
        self.brokers: Dict[str, BrokerBase] = {}

    async def add_broker(self, user_id: str, broker_type: str, credentials: Dict[str, Any]) -> BrokerBase:
        if broker_type == 'binance':
            broker = BinanceBroker(credentials['api_key'], credentials['secret_key'], credentials.get('testnet', True))
        elif broker_type == 'bybit':
            broker = BybitBroker(credentials['api_key'], credentials['secret_key'], credentials.get('testnet', True))
        elif broker_type == 'mt5':
            broker = MT5Broker(credentials['login'], credentials['password'], credentials['server'])
        elif broker_type == 'paper':
            broker = PaperBroker(user_id, initial_balance=credentials.get('balance', 10000.0))
        else:
            raise ValueError(f"Unsupported broker type: {broker_type}")
        
        self.brokers[f"{user_id}_{broker_type}"] = broker
        return broker

    def get_broker(self, user_id: str, broker_type: str):
        return self.brokers.get(f"{user_id}_{broker_type}")

    async def close_all(self):
        for broker in self.brokers.values():
            await broker.close()
