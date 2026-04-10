import pandas as pd
import numpy as np
import ccxt.async_support as ccxt
from typing import Dict, Any, List, Optional
import asyncio
import logging

logger = logging.getLogger(__name__)

class BacktestEngine:
    def __init__(self):
        self.exchange = ccxt.binance({'enableRateLimit': True})

    async def fetch_data(self, symbol: str, timeframe: str = '1h', limit: int = 168):
        """Fetch historical OHLCV data."""
        try:
            ohlcv = await self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            return df
        except Exception as e:
            logger.error(f"Error fetching historical data: {e}")
            return None

    def run_dca_backtest(self, df: pd.DataFrame, initial_balance: float, bot_params: Dict[str, Any]):
        """
        Simulate a DCA strategy.
        Params: step_percent, multiplier, max_orders, tp_percent
        """
        balance = initial_balance
        position_size = 0.0
        avg_entry_price = 0.0
        trades = []
        equity_curve = []
        
        # Simple Loop-based simulation for DCA (hard to vectorize perfectly due to state)
        for i, row in df.iterrows():
            price = row['close']
            
            # 1. Check if we need to open initial trade
            if position_size == 0:
                trade_amount = initial_balance * 0.1 # Start with 10%
                position_size = trade_amount / price
                avg_entry_price = price
                trades.append({'time': row['timestamp'], 'type': 'buy', 'price': price, 'size': position_size})
            
            # 2. Check for Take Profit
            tp_price = avg_entry_price * (1 + bot_params.get('tp_percent', 2.0) / 100)
            if price >= tp_price:
                pnl = position_size * (price - avg_entry_price)
                balance += pnl
                trades.append({'time': row['timestamp'], 'type': 'sell', 'price': price, 'pnl': pnl})
                position_size = 0.0
                avg_entry_price = 0.0
                continue

            # 3. Check for Safety Orders (DCA)
            drawdown = (avg_entry_price - price) / avg_entry_price
            if drawdown >= (bot_params.get('step_percent', 1.0) / 100) and len([t for t in trades if t['type'] == 'buy']) < bot_params.get('max_orders', 10):
                # Simple Martingale
                new_size = position_size * bot_params.get('multiplier', 1.5)
                new_total_size = position_size + new_size
                avg_entry_price = ((position_size * avg_entry_price) + (new_size * price)) / new_total_size
                position_size = new_total_size
                trades.append({'time': row['timestamp'], 'type': 'buy_dca', 'price': price, 'size': new_size})

            equity_curve.append(balance + (position_size * (price - avg_entry_price)))

        # Finalize
        if position_size > 0:
            pnl = position_size * (df.iloc[-1]['close'] - avg_entry_price)
            balance += pnl

        return self._calculate_metrics(initial_balance, balance, equity_curve, trades)

    def _calculate_metrics(self, initial, final, equity_curve, trades):
        total_pnl = final - initial
        return_pct = (total_pnl / initial) * 100
        
        # Max Drawdown
        peaks = pd.Series(equity_curve).expanding().max()
        drawdowns = (pd.Series(equity_curve) - peaks) / peaks
        max_dd = drawdowns.min() * 100 if not drawdowns.empty else 0
        
        # Sharpe (simplified)
        returns = pd.Series(equity_curve).pct_change().dropna()
        sharpe = (returns.mean() / returns.std() * np.sqrt(252)) if not returns.empty and returns.std() != 0 else 0

        return {
            "total_pnl": float(total_pnl),
            "return_pct": float(return_pct),
            "max_drawdown": float(max_dd),
            "sharpe_ratio": float(sharpe),
            "trade_count": len(trades)
        }
