from typing import Dict, Any, Optional
import logging
from .base_broker import BrokerBase

logger = logging.getLogger(__name__)

class PaperBroker(BrokerBase):
    """
    Virtual broker that simulates trades using real-time market data.
    """
    def __init__(self, user_id: str, initial_balance: float = 10000.0, market_data=None):
        self.user_id = user_id
        self.balance = initial_balance
        self.positions: Dict[str, float] = {} # symbol -> amount
        self.market_data = market_data 

    async def get_balance(self) -> Dict[str, Any]:
        return {"balance": self.balance, "currency": "USDT"}

    async def get_price(self, symbol: str) -> float:
        """Fetch current price from cache or fallback to a default."""
        if self.market_data:
            # Try binance then bybit
            price = self.market_data.get_price('binance', symbol.replace('/', ''))
            if not price:
                price = self.market_data.get_price('bybit', symbol.replace('/', ''))
            if price:
                return price
        
        # Fallback for BTC if data not yet synced
        return 65000.0 if 'BTC' in symbol else 3000.0

    async def execute_trade(self, symbol: str, side: str, amount: float, order_type: str = 'market', price: Optional[float] = None, sl: Optional[float] = None, tp: Optional[float] = None) -> Dict[str, Any]:
        """Simulate trade execution at current market price."""
        # Simple simulation: assume instant fill at current price
        current_price = await self.get_price(symbol)
        cost = amount * current_price
        
        if side == 'buy':
            if self.balance < cost:
                return {"status": "failed", "reason": "Insufficient virtual balance"}
            self.balance -= cost
            self.positions[symbol] = self.positions.get(symbol, 0.0) + amount
        else:
            if self.positions.get(symbol, 0.0) < amount:
                return {"status": "failed", "reason": "Insufficient virtual position"}
            self.balance += cost
            self.positions[symbol] -= amount

        logger.info(f"PAPER TRADE: {side} {amount} {symbol} at {current_price}")
        return {
            "status": "success",
            "price": current_price,
            "cost": cost,
            "side": side,
            "virtual_balance": self.balance
        }

    async def get_positions(self):
        return [{"symbol": s, "amount": a} for s, a in self.positions.items() if a > 0]

    async def cancel_order(self, order_id: str, symbol: str):
        return {"status": "success", "message": "Virtual order cancelled"}

    async def cleanup(self, symbol: str):
        """Close all positions for a symbol (Virtual Market Sell)."""
        amount = self.positions.get(symbol, 0.0)
        if amount > 0:
            await self.execute_trade(symbol, 'sell', amount, 'market')
            self.positions[symbol] = 0.0
        return {"status": "success", "closed_amount": amount}

    async def close(self):
        pass
