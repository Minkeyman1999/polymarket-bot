"""
main.py — Bot entry point
─────────────────────────
Runs every 5 minutes via GitHub Actions.

Data source: Polymarket's own Chainlink WebSocket feed
This guarantees our price data matches exactly what
Polymarket uses to settle bets.

Flow:
  1. Connect to Polymarket Chainlink feed → collect prices
  2. Build 5-min OHLC candles from collected ticks
  3. Calculate indicators (RSI, EMA, MACD etc)
  4. Run strategy → get UP / DOWN / SKIP signal
  5. Place bet or log (paper trade mode)
"""

import os
from bot.price_feed import get_candles, prune_old_ticks
from bot.indicators import add_indicators
from bot.strategy   import get_signal
from bot.polymarket import place_bet, get_open_positions
from bot.logger     import log

# ── Config ────────────────────────────────────────────────
PAPER_TRADE   = os.environ.get("PAPER_TRADE", "true").lower() != "false"
BET_SIZE_USD  = float(os.environ.get("BET_SIZE_USD", "5"))
MIN_CANDLES   = 10   # minimum candles needed before trading


def main():
    log("=" * 50)
    log(f"Bot starting | paper_trade={PAPER_TRADE} | bet=${BET_SIZE_USD}")

    # ── Step 1: Prune old price data (keep last 48 hrs) ───
    prune_old_ticks(max_hours=48)

    # ── Step 2: Collect ticks + build candles ─────────────
    # price_feed.py connects to Polymarket's Chainlink WebSocket,
    # collects prices for 60 seconds, stores them, then builds
    # 5-min OHLC candles from all accumulated history.
    log("Connecting to Polymarket Chainlink price feed...")
    candles = get_candles(count=100, interval_mins=5)

    if not candles or len(candles) < MIN_CANDLES:
        log(f"Not enough candles yet ({len(candles) if candles else 0}/{MIN_CANDLES})")
        log("Bot needs several runs to accumulate price history.")
        log("This is normal on first few runs — check back in 30 mins.")
        log("=" * 50)
        return

    log(f"Got {len(candles)} candles | latest close: ${candles[-1]['close']:,.2f}")

    # ── Step 3: Calculate indicators ──────────────────────
    log("Calculating indicators...")
    candles = add_indicators(candles)

    # ── Step 4: Run strategy ───────────────────────────────
    log("Running strategy...")
    signal = get_signal(candles)

    if signal == "SKIP":
        log("No signal this round — skipping.")
        log("=" * 50)
        return

    # ── Step 5: Check for existing open positions ──────────
    open_positions = get_open_positions()
    if open_positions:
        log(f"Already have {len(open_positions)} open position(s) — skipping.")
        log("=" * 50)
        return

    # ── Step 6: Bet or paper trade ─────────────────────────
    if PAPER_TRADE:
        log(f"[PAPER TRADE] Would bet ${BET_SIZE_USD} → {signal}")
    else:
        log(f"Placing REAL bet: ${BET_SIZE_USD} → {signal}")
        result = place_bet(direction=signal, amount_usd=BET_SIZE_USD)
        log(f"Bet result: {result}")

    log("=" * 50)


if __name__ == "__main__":
    main()
