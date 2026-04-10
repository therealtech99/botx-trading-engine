import pandas as pd

class CandlePatternEngine:
    @staticmethod
    def is_doji(df, threshold=0.1):
        last = df.iloc[-1]
        body = abs(last['close'] - last['open'])
        range_val = last['high'] - last['low']
        return body <= range_val * threshold

    @staticmethod
    def is_hammer(df):
        last = df.iloc[-1]
        body = abs(last['close'] - last['open'])
        lower_wick = min(last['open'], last['close']) - last['low']
        upper_wick = last['high'] - max(last['open'], last['close'])
        return lower_wick >= 2 * body and upper_wick <= 0.1 * body

    @staticmethod
    def is_engulfing(df):
        if len(df) < 2: return "NONE"
        last = df.iloc[-1]
        prev = df.iloc[-2]
        
        # Bullish Engulfing
        if (prev['close'] < prev['open'] and 
            last['close'] > last['open'] and 
            last['open'] <= prev['close'] and 
            last['close'] >= prev['open']):
            return "BULLISH"
            
        # Bearish Engulfing
        if (prev['close'] > prev['open'] and 
            last['close'] < last['open'] and 
            last['open'] >= prev['close'] and 
            last['close'] <= prev['open']):
            return "BEARISH"
            
        return "NONE"

    @classmethod
    def detect_all(cls, df):
        patterns = []
        if cls.is_doji(df): patterns.append("Doji")
        if cls.is_hammer(df): patterns.append("Hammer")
        eng = cls.is_engulfing(df)
        if eng != "NONE": patterns.append(f"{eng} Engulfing")
        return patterns
