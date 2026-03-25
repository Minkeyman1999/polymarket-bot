"""
indicators.py — Technical indicators using 'ta' library
Uses lazy import to avoid slow cold-start on every run.
"""

import pandas as pd

_ta = None  # lazy loaded

def _load_ta():
    global _ta
    if _ta is None:
        try:
            import ta
            _ta = ta
        except ImportError:
            pass
    return _ta


def add_indicators(candles):
    ta = _load_ta()
    if ta is None or len(candles) < 52:
        return candles

    df = pd.DataFrame(candles)

    df["rsi"]    = ta.momentum.RSIIndicator(df["close"], window=14).rsi()
    df["ema_20"] = ta.trend.EMAIndicator(df["close"], window=20).ema_indicator()
    df["ema_50"] = ta.trend.EMAIndicator(df["close"], window=50).ema_indicator()

    macd = ta.trend.MACD(df["close"])
    df["macd"]        = macd.macd()
    df["macd_signal"] = macd.macd_signal()
    df["macd_hist"]   = macd.macd_diff()

    bb = ta.volatility.BollingerBands(df["close"], window=20, window_dev=2)
    df["bb_upper"] = bb.bollinger_hband()
    df["bb_lower"] = bb.bollinger_lband()
    df["bb_mid"]   = bb.bollinger_mavg()

    return df.where(pd.notnull(df), None).to_dict(orient="records")
