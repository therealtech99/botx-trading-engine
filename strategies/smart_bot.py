from services.indicator_engine import IndicatorEngine
import pandas as pd

class SmartBot:
    def __init__(self, threshold=75):
        self.threshold = threshold

    def generate_signal(self, df):
        if df.empty or len(df) < 30:
            return "HOLD", 0

        df = IndicatorEngine.apply_all(df)
        last = df.iloc[-1]
        score = 0
        
        # Trend Confirmation (EMA)
        if last['close'] > last['ema_20']:
            score += 25
        
        # Momentum (RSI)
        if last['rsi_14'] < 30: # Oversold
            score += 25
        elif last['rsi_14'] > 70: # Overbought
            score -= 25
            
        # Volatility (Bollinger Bands)
        if last['close'] < last['bb_lower']:
            score += 25
        elif last['close'] > last['bb_upper']:
            score -= 25
            
        # MACD Confirmation
        if last['macd'] > last['macd_signal']:
            score += 25
        
        # Final Decision
        if score >= self.threshold:
            return "BUY", score
        elif score <= -self.threshold:
            return "SELL", abs(score)
        else:
            return "HOLD", score

    def calculate_position_size(self, balance, risk_percent=0.01):
        return balance * risk_percent
