"""
strategy.py — Betting strategies
Change ACTIVE_STRATEGY to switch between them.
"""
from bot.logger import log

ACTIVE_STRATEGY = "previous_candle"


def get_signal(candles):
    if len(candles) < 3:
        return "SKIP"
    strategies = {
        "previous_candle":     strategy_previous_candle,
        "mean_reversion":      strategy_mean_reversion,
        "rsi":                 strategy_rsi,
        "ema_cross":           strategy_ema_cross,
        "two_candle_momentum": strategy_two_candle_momentum,
    }
    fn = strategies.get(ACTIVE_STRATEGY)
    if not fn:
        return "SKIP"
    signal = fn(candles)
    log(f"Strategy '{ACTIVE_STRATEGY}' → {signal}")
    return signal


def strategy_previous_candle(candles):
    # Always use [-2] — the last COMPLETE candle
    # [-1] is still forming and unreliable
    prev = candles[-2]
    if prev["close"] > prev["open"]: return "UP"
    if prev["close"] < prev["open"]: return "DOWN"
    return "SKIP"

def strategy_mean_reversion(candles):
    prev = candles[-2]
    if prev["close"] < prev["open"]: return "UP"
    if prev["close"] > prev["open"]: return "DOWN"
    return "SKIP"

def strategy_rsi(candles):
    rsi = candles[-1].get("rsi")
    if rsi is None:
        return "SKIP"
    if rsi < 30:
        log(f"RSI oversold ({rsi:.1f})")
        return "UP"
    if rsi > 70:
        log(f"RSI overbought ({rsi:.1f})")
        return "DOWN"
    return "SKIP"

def strategy_ema_cross(candles):
    c = candles[-1]
    ema_20, ema_50 = c.get("ema_20"), c.get("ema_50")
    if ema_20 is None or ema_50 is None:
        return "SKIP"
    if c["close"] > ema_20 and ema_20 > ema_50: return "UP"
    if c["close"] < ema_20 and ema_20 < ema_50: return "DOWN"
    return "SKIP"

def strategy_two_candle_momentum(candles):
    p1, p2 = candles[-2], candles[-3]
    g1 = p1["close"] > p1["open"]
    g2 = p2["close"] > p2["open"]
    if g1 and g2:   return "UP"
    if not g1 and not g2: return "DOWN"
    return "SKIP"
