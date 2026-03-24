"""
indicators.py — Technical indicators
──────────────────────────────────────
Uses pandas-ta to calculate indicators from candle data.
pandas-ta replicates every TradingView indicator in Python.

All indicators are added as new keys to each candle dict.
Strategy.py can then read them like: candle['rsi'], candle['ema_20'] etc.

Add or remove indicators here freely — they won't affect anything
until you actually reference them in strategy.py.
"""

import pandas as pd
try:
    import pandas_ta as ta
    PANDAS_TA_AVAILABLE = True
except ImportError:
    PANDAS_TA_AVAILABLE = False


def add_indicators(candles):
    """
    Takes a list of candle dicts, adds indicator values to each,
    returns the updated list.

    Indicators added:
      - rsi         → Relative Strength Index (14)
      - ema_20      → Exponential Moving Average (20 candles)
      - ema_50      → Exponential Moving Average (50 candles)
      - macd        → MACD line
      - macd_signal → MACD signal line
      - macd_hist   → MACD histogram
      - bb_upper    → Bollinger Band upper
      - bb_lower    → Bollinger Band lower
      - bb_mid      → Bollinger Band middle
    """
    if not PANDAS_TA_AVAILABLE:
        # If pandas-ta isn't installed, return candles unchanged
        # Strategy will fall back to pure price action
        return candles

    if len(candles) < 50:
        # Not enough candles to calculate meaningful indicators
        return candles

    # Convert to DataFrame for pandas-ta
    df = pd.DataFrame(candles)
    df = df.rename(columns={
        "open": "open", "high": "high",
        "low": "low",   "close": "close", "volume": "volume"
    })

    # ── RSI ──────────────────────────────────────────────
    # > 70 = overbought (price may drop)
    # < 30 = oversold   (price may rise)
    df["rsi"] = ta.rsi(df["close"], length=14)

    # ── EMA ───────────────────────────────────────────────
    # Price above EMA = uptrend, below = downtrend
    df["ema_20"] = ta.ema(df["close"], length=20)
    df["ema_50"] = ta.ema(df["close"], length=50)

    # ── MACD ──────────────────────────────────────────────
    # macd crossing above signal = bullish
    # macd crossing below signal = bearish
    macd = ta.macd(df["close"], fast=12, slow=26, signal=9)
    if macd is not None:
        df["macd"]        = macd["MACD_12_26_9"]
        df["macd_signal"] = macd["MACDs_12_26_9"]
        df["macd_hist"]   = macd["MACDh_12_26_9"]

    # ── Bollinger Bands ────────────────────────────────────
    # Price touching upper band = overbought
    # Price touching lower band = oversold
    bbands = ta.bbands(df["close"], length=20, std=2)
    if bbands is not None:
        df["bb_upper"] = bbands["BBU_20_2.0"]
        df["bb_lower"] = bbands["BBL_20_2.0"]
        df["bb_mid"]   = bbands["BBM_20_2.0"]

    # Convert back to list of dicts, filling NaN with None
    result = df.where(pd.notnull(df), None).to_dict(orient="records")
    return result
