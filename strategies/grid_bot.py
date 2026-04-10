import time

class GridBot:
    """
    Professional Grid Trading Strategy.
    Executes 'Order Flipping' across a set range.
    """
    def __init__(self, bot_id, symbol, lower_price, upper_price, grid_count, investment):
        self.bot_id = bot_id
        self.symbol = symbol
        self.lower_price = float(lower_price)
        self.upper_price = float(upper_price)
        self.grid_count = int(grid_count)
        self.investment = float(investment)
        
        self.grid_levels = []
        self.inventory = 0.0 
        self.realized_pnl = 0.0
        self.is_initialized = False
        
        # Calculate precise step and amount per level
        self.step = (self.upper_price - self.lower_price) / (self.grid_count - 1)
        self.amount_per_grid = self.investment / self.grid_count

    def initialize_grid(self, current_price):
        """Builds the market-neutral grid structure."""
        self.grid_levels = []
        for i in range(self.grid_count):
            price = self.lower_price + (i * self.step)
            # Buy orders below market, Sell orders above market
            side = 'buy' if price < current_price else 'sell'
            self.grid_levels.append({
                'id': i,
                'price': price,
                'side': side,
                'status': 'active',
                'amount': self.amount_per_grid / price
            })
        
        self.is_initialized = True
        return self.grid_levels

    def process_tick(self, current_price):
        """Analyzes price action and 'flips' orders recursively."""
        if not self.is_initialized:
            return []

        triggered_trades = []
        for level in self.grid_levels:
            if level['status'] != 'active':
                continue

            # Check BUY TRIGGER
            if level['side'] == 'buy' and current_price <= level['price']:
                level['status'] = 'filled'
                self.inventory += level['amount']
                triggered_trades.append({'type': 'fill', 'side': 'buy', 'price': level['price']})
                self._flip_order(level['id'], 'sell')
                
            # Check SELL TRIGGER
            elif level['side'] == 'sell' and current_price >= level['price']:
                level['status'] = 'filled'
                if self.inventory >= level['amount']:
                    self.inventory -= level['amount']
                    # Calculation: (Sell Price - (Sell Price - Step)) * Amount
                    profit = self.step * level['amount']
                    self.realized_pnl += profit
                
                triggered_trades.append({'type': 'fill', 'side': 'sell', 'price': level['price']})
                self._flip_order(level['id'], 'buy')
                
        return triggered_trades

    def _flip_order(self, level_id, new_side):
        """Immediately re-arms the level with the opposite side (Market Making logic)."""
        level = self.grid_levels[level_id]
        level['side'] = new_side
        level['status'] = 'active'

    def get_status(self):
        return {
            "bot_id": self.bot_id,
            "realized_pnl": round(self.realized_pnl, 2),
            "inventory": round(self.inventory, 6),
            "active_grids": len([l for l in self.grid_levels if l['status'] == 'active']),
            "range": f"{self.lower_price} - {self.upper_price}"
        }
