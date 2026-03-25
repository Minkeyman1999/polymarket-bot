"""
indicators.py — Technical indicators using 'ta' library
"""

import pandas as pd
try:
    import ta
    TA_AVAILABLE = True
except ImportError:
    TA_AVAILABLE = False


def add_indicators(candles):
    if not TA_AVAILABLE or len(candles) < 50:
        return candles

    df = pd.DataFrame(candles)

    # RSI
    df['rsi'] = ta.momentum.RSIIndicator(df['close'], window=14).rsi()

    # EMA
    df['ema_20'] = ta.trend.EMAIndicator(df['close'], window=20).ema_indicator()
    df['ema_50'] = ta.trend.EMAIndicator(df['close'], window=50).ema_indicator()

    # MACD
    macd = ta.trend.MACD(df['close'])
    df['macd']        = macd.macd()
    df['macd_signal'] = macd.macd_signal()
    df['macd_hist']   = macd.macd_diff()

    # Bollinger Bands
    bb = ta.volatility.BollingerBands(df['close'], window=20, window_dev=2)
    df['bb_upper'] = bb.bollinger_hband()
    df['bb_lower'] = bb.bollinger_lband()
    df['bb_mid']   = bb.bollinger_mavg()

    return df.where(pd.notnull(df), None).to_dict(orient='records')
