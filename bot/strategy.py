"""
strategy.py — Betting strategy logic
──────────────────────────────────────
This is where YOUR strategy lives. Change this file to test
different ideas without touching anything else.

get_signal() receives the full list of candles (with indicators)
and must return one of:
  "UP"   → bet that BTC price goes up
  "DOWN" → bet that BTC price goes down
  "SKIP" → don't bet this round

Available per candle:
  candle['open'], candle['high'], candle['low'], candle['close']
  candle['volume'], candle['timestamp']
  candle['rsi'], candle['ema_20'], candle['ema_50']
  candle['macd'], candle['macd_signal'], candle['macd_hist']
  candle['bb_upper'], candle['bb_lower'], candle['bb_mid']
  (indicators may be None for early candles)
"""

from bot.logger import log


# ── Active strategy ────────────────────────────────────────
# Change ACTIVE_STRATEGY to switch between strategies
# without modifying any logic below.
ACTIVE_STRATEGY = "previous_candle"


def get_signal(candles):
    """
    Main entry point. Calls the active strategy and returns the signal.
    """
    if len(candles) < 3:
        return "SKIP"

    strategies = {
        "previous_candle":     strategy_previous_candle,
        "mean_reversion":      strategy_mean_reversion,
        "rsi":                 strategy_rsi,
        "ema_cross":           strategy_ema_cross,
        "two_candle_momentum": strategy_two_candle_momentum,
    }

    strategy_fn = strategies.get(ACTIVE_STRATEGY)
    if not strategy_fn:
        log(f"Unknown strategy: {ACTIVE_STRATEGY}")
        return "SKIP"

    signal = strategy_fn(candles)
    log(f"Strategy '{ACTIVE_STRATEGY}' → {signal}")
    return signal


# ── Strategy definitions ───────────────────────────────────

def strategy_previous_candle(candles):
    """
    Simple momentum: if the last candle was green, bet UP.
    If the last candle was red, bet DOWN.
    """
    prev = candles[-2]
    if prev["close"] > prev["open"]:
        return "UP"
    elif prev["close"] < prev["open"]:
        return "DOWN"
    return "SKIP"


def strategy_mean_reversion(candles):
    """
    Contrarian: if the last candle was red, expect a bounce → bet UP.
    If the last candle was green, expect a pullback → bet DOWN.
    """
    prev = candles[-2]
    if prev["close"] < prev["open"]:
        return "UP"
    elif prev["close"] > prev["open"]:
        return "DOWN"
    return "SKIP"


def strategy_rsi(candles):
    """
    RSI-based strategy:
    - RSI < 30 (oversold) → bet UP
    - RSI > 70 (overbought) → bet DOWN
    - Otherwise → SKIP (no edge)
    """
    latest = candles[-1]
    rsi = latest.get("rsi")

    if rsi is None:
        log("RSI not available yet — skipping")
        return "SKIP"

    if rsi < 30:
        log(f"RSI oversold ({rsi:.1f}) → UP")
        return "UP"
    elif rsi > 70:
        log(f"RSI overbought ({rsi:.1f}) → DOWN")
        return "DOWN"

    log(f"RSI neutral ({rsi:.1f}) → SKIP")
    return "SKIP"


def strategy_ema_cross(candles):
    """
    EMA crossover:
    - Price above EMA 20 AND EMA 20 above EMA 50 → strong uptrend → UP
    - Price below EMA 20 AND EMA 20 below EMA 50 → strong downtrend → DOWN
    - Mixed → SKIP
    """
    latest = candles[-1]
    close  = latest["close"]
    ema_20 = latest.get("ema_20")
    ema_50 = latest.get("ema_50")

    if ema_20 is None or ema_50 is None:
        return "SKIP"

    if close > ema_20 and ema_20 > ema_50:
        return "UP"
    elif close < ema_20 and ema_20 < ema_50:
        return "DOWN"

    return "SKIP"


def strategy_two_candle_momentum(candles):
    """
    Only bet when the last TWO candles agree on direction.
    Skip if they conflict (reduces trade frequency, improves quality).
    """
    p1 = candles[-2]
    p2 = candles[-3]

    p1_green = p1["close"] > p1["open"]
    p2_green = p2["close"] > p2["open"]

    if p1_green and p2_green:
        return "UP"
    elif not p1_green and not p2_green:
        return "DOWN"

    return "SKIP"  # Mixed signal — sit out
