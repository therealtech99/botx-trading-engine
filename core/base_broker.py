from abc import ABC, abstractmethod

class BrokerBase(ABC):
    @abstractmethod
    async def get_balance(self):
        pass

    @abstractmethod
    async def get_price(self, symbol: str):
        pass

    @abstractmethod
    async def execute_trade(self, symbol: str, side: str, amount: float, order_type: str = 'market', price: float = None, sl: float = None, tp: float = None):
        pass

    @abstractmethod
    async def get_positions(self):
        pass

    @abstractmethod
    async def cancel_order(self, order_id: str, symbol: str):
        pass

    @abstractmethod
    async def cleanup(self, symbol: str):
        """Close all positions and cancel orders for a given symbol."""
        pass
