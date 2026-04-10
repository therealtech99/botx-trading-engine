from typing import Optional, Dict

class TrailingPosition:
    def __init__(self, entry_price: float, side: str, trailing_sl_percent: Optional[float] = None, trailing_tp_percent: Optional[float] = None):
        self.entry_price = entry_price
        self.side = side # 'buy' or 'sell'
        self.trailing_sl_percent = trailing_sl_percent
        self.trailing_tp_percent = trailing_tp_percent
        
        self.highest_price = entry_price if side == 'buy' else 0.0
        self.lowest_price = entry_price if side == 'sell' else float('inf')
        
        self.current_sl: Optional[float] = None
        self.current_tp_target: Optional[float] = None # Price at which TTP starts trailing
        self.tp_activated = False
        self.trailing_tp_exit: Optional[float] = None

    def update(self, current_price: float):
        if self.side == 'buy':
            # Update SL
            if current_price > self.highest_price:
                self.highest_price = current_price
                if self.trailing_sl_percent is not None:
                    self.current_sl = self.highest_price * (1 - self.trailing_sl_percent / 100)
            
            # Update TTP
            if self.trailing_tp_percent is not None and self.current_tp_target is not None:
                if current_price >= self.current_tp_target:
                    self.tp_activated = True
                
                if self.tp_activated:
                    self.trailing_tp_exit = self.highest_price * (1 - self.trailing_tp_percent / 100)

        else: # Sell/Short
            if current_price < self.lowest_price:
                self.lowest_price = current_price
                if self.trailing_sl_percent is not None:
                    self.current_sl = self.lowest_price * (1 + self.trailing_sl_percent / 100)
            
            # Update TTP for Short
            if self.trailing_tp_percent is not None and self.current_tp_target is not None:
                if current_price <= self.current_tp_target:
                    self.tp_activated = True
                
                if self.tp_activated:
                    self.trailing_tp_exit = self.lowest_price * (1 + self.trailing_tp_percent / 100)

class RiskManager:
    def __init__(self, daily_loss_limit=0.05, max_drawdown=0.15, max_risk_per_trade=0.01):
        self.daily_loss_limit = daily_loss_limit
        self.max_drawdown = max_drawdown
        self.max_risk_per_trade = max_risk_per_trade
        self.trading_halted = False
        self.active_trailers: Dict[str, TrailingPosition] = {} # key -> TrailingPosition

    def validate_trade(self, balance, current_drawdown, daily_pnl):
        if self.trading_halted:
            return False, "Trading halted due to risk breach"

        if daily_pnl <= - (balance * self.daily_loss_limit):
            self.trading_halted = True
            return False, "Daily loss limit breached"

        if current_drawdown >= self.max_drawdown:
            self.trading_halted = True
            return False, "Max drawdown reached"

        return True, "Success"

    def calculate_max_size(self, balance, entry_price, sl_price):
        if not sl_price or sl_price == entry_price:
            return balance * self.max_risk_per_trade / entry_price
        
        risk_amount = balance * self.max_risk_per_trade
        sl_distance = abs(entry_price - sl_price)
        return risk_amount / sl_distance

    def update_trailing(self, user_id, symbol, current_price):
        key = f"{user_id}_{symbol}"
        if key in self.active_trailers:
            trailer = self.active_trailers[key]
            trailer.update(current_price)
            return trailer.current_sl
        return None
