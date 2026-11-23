"""
strategy.py — Betting strategies
Change ACTIVE_STRATEGY to switch between them.
"""
from typing import List, Dict, Optional
from bot.logger import log

ACTIVE_STRATEGY = "previous_candle"


def get_signal(candles: List[Dict]) -> str:
    if len(candles) < 3:
        return "SKIP"
    strategies = {
        "previous_candle":      strategy_previous_candle,
        "mean_reversion":       strategy_mean_reversion,
        "rsi":                  strategy_rsi,
        "ema_cross":            strategy_ema_cross,
        "two_candle_momentum":  strategy_two_candle_momentum,
        "bollinger_bounce":     strategy_bollinger_bounce,
        "macd_cross":           strategy_macd_cross,
    }
    fn = strategies.get(ACTIVE_STRATEGY)
    if not fn:
        return "SKIP"
    signal = fn(candles)
    log(f"Strategy '{ACTIVE_STRATEGY}' → {signal}")
    return signal


def strategy_previous_candle(candles: List[Dict]) -> str:
    # Always use [-2] — the last COMPLETE candle
    # [-1] is still forming and unreliable
    prev = candles[-2]
    if prev["close"] > prev["open"]: return "UP"
    if prev["close"] < prev["open"]: return "DOWN"
    return "SKIP"

def strategy_mean_reversion(candles: List[Dict]) -> str:
    prev = candles[-2]
    if prev["close"] < prev["open"]: return "UP"
    if prev["close"] > prev["open"]: return "DOWN"
    return "SKIP"

def strategy_rsi(candles: List[Dict]) -> str:
    # Use [-2] (last complete candle) for consistency with other strategies
    rsi = candles[-2].get("rsi")
    if rsi is None:
        return "SKIP"
    if rsi < 30:
        log(f"RSI oversold ({rsi:.1f})")
        return "UP"
    if rsi > 70:
        log(f"RSI overbought ({rsi:.1f})")
        return "DOWN"
    return "SKIP"

def strategy_ema_cross(candles: List[Dict]) -> str:
    # Use [-2] (last complete candle) for consistency
    c = candles[-2]
    ema_20, ema_50 = c.get("ema_20"), c.get("ema_50")
    if ema_20 is None or ema_50 is None:
        return "SKIP"
    if c["close"] > ema_20 and ema_20 > ema_50: return "UP"
    if c["close"] < ema_20 and ema_20 < ema_50: return "DOWN"
    return "SKIP"

def strategy_two_candle_momentum(candles: List[Dict]) -> str:
    p1, p2 = candles[-2], candles[-3]
    g1 = p1["close"] > p1["open"]
    g2 = p2["close"] > p2["open"]
    if g1 and g2:   return "UP"
    if not g1 and not g2: return "DOWN"
    return "SKIP"

def strategy_bollinger_bounce(candles: List[Dict]) -> str:
    """
    Bet UP when price touches lower band (oversold),
    bet DOWN when price touches upper band (overbought).
    Uses last complete candle [-2].
    """
    c = candles[-2]
    bb_upper = c.get("bb_upper")
    bb_lower = c.get("bb_lower")
    if bb_upper is None or bb_lower is None:
        return "SKIP"
    close = c["close"]
    if close <= bb_lower:
        log(f"Price ${close:,.2f} at lower BB ${bb_lower:,.2f}")
        return "UP"
    if close >= bb_upper:
        log(f"Price ${close:,.2f} at upper BB ${bb_upper:,.2f}")
        return "DOWN"
    return "SKIP"

def strategy_macd_cross(candles: List[Dict]) -> str:
    """
    Bet UP when MACD crosses above signal line (bullish),
    bet DOWN when MACD crosses below signal line (bearish).
    Compares last two complete candles for crossover detection.
    """
    c_now = candles[-2]
    c_prev = candles[-3]
    macd_now = c_now.get("macd")
    sig_now = c_now.get("macd_signal")
    macd_prev = c_prev.get("macd")
    sig_prev = c_prev.get("macd_signal")
    if any(v is None for v in [macd_now, sig_now, macd_prev, sig_prev]):
        return "SKIP"
    # Bullish crossover: MACD was below signal, now above
    if macd_prev < sig_prev and macd_now > sig_now:
        log(f"MACD bullish cross ({macd_now:.2f} > {sig_now:.2f})")
        return "UP"
    # Bearish crossover: MACD was above signal, now below
    if macd_prev > sig_prev and macd_now < sig_now:
        log(f"MACD bearish cross ({macd_now:.2f} < {sig_now:.2f})")
        return "DOWN"
    return "SKIP"
