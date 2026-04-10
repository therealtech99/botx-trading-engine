class DCABot:
    """
    Next-Level Professional DCA (Dollar Cost Averaging) Engine.
    Implements a pre-calculated trade plan with geometric volume and step scaling.
    Standard optimization for Elirox, 3Commas, and OpenTrader-style trading.
    """
    def __init__(self, 
                 base_order_size=10.0, 
                 safety_order_size=20.0, 
                 price_deviation=1.0, 
                 volume_scale=1.5, 
                 step_scale=1.1, 
                 max_safety_orders=10, 
                 take_profit=1.0):
        self.base_order_size = float(base_order_size)
        self.safety_order_size = float(safety_order_size)
        self.price_deviation = float(price_deviation)
        self.volume_scale = float(volume_scale)
        self.step_scale = float(step_scale)
        self.max_safety_orders = int(max_safety_orders)
        self.take_profit = float(take_profit)
        self.realized_pnl = 0.0

    def generate_trade_plan(self, entry_price, side='buy'):
        """
        Pre-calculates every safety order level for this deal cycle.
        Returns: List of dicts {level, price, size, total_size, avg_price, req_tp_price}
        """
        plan = []
        
        # 1. Base Order (Level 0)
        current_total_size = self.base_order_size
        current_total_cost = self.base_order_size * entry_price
        current_avg_price = entry_price
        
        plan.append({
            "level": 0,
            "type": "BASE",
            "price": entry_price,
            "size": self.base_order_size,
            "total_size": current_total_size,
            "avg_price": current_avg_price,
            "deviation_pct": 0.0
        })

        # 2. Safety Orders (Levels 1 to Max)
        last_so_price = entry_price
        last_so_size = self.safety_order_size
        last_step_deviation = self.price_deviation
        total_deviation = 0.0

        for i in range(1, self.max_safety_orders + 1):
            # Calculate next step deviation (Geometric)
            # Deviation grows by step_scale factor from the PREVIOUS step
            if i > 1:
                last_step_deviation *= self.step_scale
            
            total_deviation += last_step_deviation
            
            # Calculate next SO price
            # Long: price decreases | Short: price increases
            price_multiplier = (1 - total_deviation / 100) if side == 'buy' else (1 + total_deviation / 100)
            so_price = entry_price * price_multiplier
            
            # Calculate next SO volume (Geometric)
            if i > 1:
                last_so_size *= self.volume_scale
            
            current_total_size += last_so_size
            current_total_cost += last_so_size * so_price
            current_avg_price = current_total_cost / current_total_size
            
            plan.append({
                "level": i,
                "type": f"SO_{i}",
                "price": so_price,
                "size": last_so_size,
                "total_size": current_total_size,
                "avg_price": current_avg_price,
                "deviation_pct": total_deviation
            })
            
            last_so_price = so_price

        return plan

    def calculate_next_order(self, positions, current_price):
        """
        Reactive polling for platforms without Limit Order hooks.
        Checks if current price has crossed the next pre-calculated level.
        """
        if not positions:
            return {"action": "INITIAL_ORDER", "size_multiplier": 1.0}

        entry_price = float(positions[0]['entryPrice'])
        side = positions[0]['side']
        plan = self.generate_trade_plan(entry_price, side)
        
        # Determine current safety order count
        # In a real position, we'd compare filled contracts with plan sizes
        # Simplified: Use length of current positions list
        current_so_num = len(positions) - 1
        
        if current_so_num < self.max_safety_orders:
            next_level = plan[current_so_num + 1]
            next_price = next_level['price']
            
            # Trigger if price crossed the level
            triggered = (current_price <= next_price) if side == 'buy' else (current_price >= next_price)
            
            if triggered:
                return {
                    "action": "ADD_ORDER",
                    "size": next_level['size'],
                    "reason": f"DCA Standard Level {next_level['level']} Hit @ ${next_price:.2f}"
                }
        
        return {"action": "HOLD"}

    def check_take_profit(self, vwap, current_price, side):
        # Professional bots recalculate target from current VWAP
        pnl_pct = (current_price - vwap) / vwap if side == 'buy' else (vwap - current_price) / vwap
        if pnl_pct >= (self.take_profit / 100):
            return True, f"Take profit target {self.take_profit}% reached from average ${vwap:.2f}"
        return False, None
        
