import pandas as pd
import numpy as np

class IndicatorEngine:
    @staticmethod
    def calculate_ema(df, period=20):
        return df['close'].ewm(span=period, adjust=False).mean()

    @staticmethod
    def calculate_rsi(df, period=14):
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (10 + rs))

    @staticmethod
    def calculate_bollinger_bands(df, period=20, std_dev=2):
        sma = df['close'].rolling(window=period).mean()
        std = df['close'].rolling(window=period).std()
        upper = sma + (std * std_dev)
        lower = sma - (std * std_dev)
        return upper, lower

    @staticmethod
    def calculate_macd(df, fast=12, slow=26, signal=9):
        ema_fast = df['close'].ewm(span=fast, adjust=False).mean()
        ema_slow = df['close'].ewm(span=slow, adjust=False).mean()
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal, adjust=False).mean()
        return macd_line, signal_line

    @staticmethod
    def calculate_atr(df, period=14):
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = np.max(ranges, axis=1)
        return true_range.rolling(period).mean()

    @classmethod
    def apply_all(cls, df):
        df['ema_20'] = cls.calculate_ema(df, 20)
        df['rsi_14'] = cls.calculate_rsi(df, 14)
        df['bb_upper'], df['bb_lower'] = cls.calculate_bollinger_bands(df, 20)
        df['macd'], df['macd_signal'] = cls.calculate_macd(df)
        df['atr'] = cls.calculate_atr(df)
        return df
