"""
backtest.py — Strategy backtester
───────────────────────────────────
Tests strategies against accumulated Chainlink price history.

NOTE: The bot must have run at least 10+ times before you
have enough candle history to backtest meaningfully.
Each run collects ~60 seconds of ticks. After ~2 hours of
runs you will have enough data for a proper backtest.

Run manually via GitHub Actions → Actions tab → Run workflow
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from bot.price_feed import get_candles
from bot.indicators import add_indicators
from bot.strategy   import (
    strategy_previous_candle,
    strategy_mean_reversion,
    strategy_rsi,
    strategy_ema_cross,
    strategy_two_candle_momentum,
)

BET_SIZE    = 10
PAYOUT_MULT = 0.9

STRATEGIES = {
    "Previous Candle":     strategy_previous_candle,
    "Mean Reversion":      strategy_mean_reversion,
    "RSI":                 strategy_rsi,
    "EMA Cross":           strategy_ema_cross,
    "Two Candle Momentum": strategy_two_candle_momentum,
}


def run_backtest(candles, strategy_fn):
    balance = 0
    wins = losses = skips = 0

    for i in range(2, len(candles) - 1):
        signal = strategy_fn(candles[:i + 1])
        if signal == "SKIP":
            skips += 1
            continue
        outcome = "UP" if candles[i+1]["close"] > candles[i]["close"] else "DOWN"
        won = signal == outcome
        balance += BET_SIZE * PAYOUT_MULT if won else -BET_SIZE
        wins += won
        losses += not won

    total = wins + losses
    win_rate = (wins / total * 100) if total > 0 else 0
    return {
        "total_pnl":    round(balance, 2),
        "wins":         wins,
        "losses":       losses,
        "skips":        skips,
        "total_trades": total,
        "win_rate":     round(win_rate, 1),
    }


def main():
    print("=" * 55)
    print("  POLYMARKET BOT — STRATEGY BACKTESTER")
    print("  Data source: Polymarket Chainlink feed")
    print("=" * 55)

    print("\nLoading accumulated Chainlink price candles...")
    candles = get_candles(count=500, interval_mins=5)

    if not candles:
        print("\nERROR: No price history found.")
        print("The bot needs to run several times first to collect data.")
        print("Wait ~2 hours of 5-min runs then try again.")
        return

    print(f"Loaded {len(candles)} candles")
    print(f"Price range: ${candles[0]['close']:,.0f} → ${candles[-1]['close']:,.0f}")
    print(f"\nBreak-even win rate: 52.6%\n")

    candles = add_indicators(candles)

    print(f"{'Strategy':<25} {'P&L':>8} {'Win%':>7} {'Trades':>7} {'Wins':>6} {'Losses':>7}")
    print("-" * 62)

    results = []
    for name, fn in STRATEGIES.items():
        r = run_backtest(candles, fn)
        results.append((name, r))
        pnl = f"+${r['total_pnl']}" if r['total_pnl'] >= 0 else f"-${abs(r['total_pnl'])}"
        flag = "✅" if r["win_rate"] >= 52.6 else "❌"
        print(f"{name:<25} {pnl:>8} {r['win_rate']:>6}% {r['total_trades']:>7} "
              f"{r['wins']:>6} {r['losses']:>7} {flag}")

    print("-" * 62)
    best = max(results, key=lambda x: x[1]["total_pnl"])
    print(f"\nBest: {best[0]} (${best[1]['total_pnl']} P&L, {best[1]['win_rate']}% win rate)")
    print(f"To use it: set ACTIVE_STRATEGY in bot/strategy.py")


if __name__ == "__main__":
    main()
