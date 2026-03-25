"""
main.py — Bot entry point (v4, fully optimized)
─────────────────────────────────────────────────
Optimizations vs v3:
  - Parallel data fetching (candles + price simultaneously)
  - Circuit breaker (pauses after N consecutive losses)
  - Time-of-day filter (skip low-liquidity hours)
  - Execution drift logging (how late did we actually run?)
  - Full stats printed every run
  - State/ledger persisted back to repo via git commit
"""

import os
import json
from datetime import datetime, timezone

from bot.price_feed  import get_candles_and_price
from bot.indicators  import add_indicators
from bot.strategy    import get_signal
from bot.polymarket  import place_bet, get_open_positions
from bot.logger      import log

# ── Config ────────────────────────────────────────────────
PAPER_TRADE       = os.environ.get("PAPER_TRADE", "true").lower() != "false"
BET_SIZE_USD      = float(os.environ.get("BET_SIZE_USD", "5"))
MIN_CANDLES       = 52

# Circuit breaker — stop betting after this many losses in a row
MAX_CONSECUTIVE_LOSSES = 5

# Low liquidity hours (UTC) — skip betting during these hours
# 2am-4am UTC is historically thin for BTC prediction markets
LOW_LIQUIDITY_HOURS = {2, 3}

# File paths for persistent state
LOGS_DIR    = os.path.join(os.path.dirname(__file__), "..", "logs")
STATE_FILE  = os.path.join(LOGS_DIR, "state.json")
LEDGER_FILE = os.path.join(LOGS_DIR, "ledger.json")


# ── State helpers ──────────────────────────────────────────

def load_json(path, default):
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return default


def save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


# ── Outcome evaluation ─────────────────────────────────────

def evaluate_last_prediction(state, current_price, ledger):
    """
    Compare last run's prediction against what actually happened.
    Appends result to ledger and prints outcome.
    Returns updated ledger.
    """
    if not state or not state.get("signal"):
        return ledger

    signal    = state["signal"]
    old_price = state.get("price")
    timestamp = state.get("timestamp", "unknown")

    if not old_price or not current_price:
        log("Cannot evaluate — missing price data")
        return ledger

    actual  = "UP" if current_price > old_price else "DOWN"
    correct = signal == actual
    pnl     = BET_SIZE_USD * 0.9 if correct else -BET_SIZE_USD

    result = {
        "time":         timestamp,
        "signal":       signal,
        "actual":       actual,
        "correct":      correct,
        "price_then":   old_price,
        "price_now":    current_price,
        "change":       round(current_price - old_price, 2),
        "pnl":          round(pnl, 2),
    }
    ledger.append(result)

    # ── Print outcome ──────────────────────────────────────
    icon = "✅" if correct else "❌"
    log("─" * 50)
    log(f"OUTCOME {icon}  Signal: {signal} | Actual: {actual}")
    log(f"Price:  ${old_price:,.2f} → ${current_price:,.2f} "
        f"({'+' if result['change'] >= 0 else ''}${result['change']:,.2f})")
    log(f"P&L this trade: ${pnl:+.2f}")
    log("─" * 50)

    return ledger


def print_stats(ledger):
    """Print a full performance summary."""
    if not ledger:
        log("No trades recorded yet.")
        return

    total      = len(ledger)
    wins       = sum(1 for r in ledger if r["correct"])
    losses     = total - wins
    win_rate   = wins / total * 100
    total_pnl  = sum(r["pnl"] for r in ledger)
    best_trade = max(r["pnl"] for r in ledger)
    worst_trade= min(r["pnl"] for r in ledger)

    # Consecutive losses streak
    streak = 0
    for r in reversed(ledger):
        if not r["correct"]:
            streak += 1
        else:
            break

    log("📊 PERFORMANCE SUMMARY")
    log(f"   Trades:     {total} ({wins}W / {losses}L)")
    log(f"   Win rate:   {win_rate:.1f}% "
        f"({'✅ above' if win_rate >= 52.6 else '❌ below'} 52.6% break-even)")
    log(f"   Total P&L:  ${total_pnl:+.2f}")
    log(f"   Best trade: ${best_trade:+.2f}")
    log(f"   Worst:      ${worst_trade:+.2f}")
    log(f"   Loss streak:{streak} (circuit breaker at {MAX_CONSECUTIVE_LOSSES})")


def is_circuit_breaker_tripped(ledger):
    """Return True if we've had too many losses in a row."""
    if len(ledger) < MAX_CONSECUTIVE_LOSSES:
        return False
    recent = ledger[-MAX_CONSECUTIVE_LOSSES:]
    if all(not r["correct"] for r in recent):
        log(f"🛑 CIRCUIT BREAKER: {MAX_CONSECUTIVE_LOSSES} consecutive losses")
        log("Pausing bets until manually reset.")
        return True
    return False


def is_low_liquidity():
    """Return True during low-liquidity hours (UTC)."""
    hour = datetime.now(timezone.utc).hour
    if hour in LOW_LIQUIDITY_HOURS:
        log(f"⏸ Low liquidity hour ({hour}:00 UTC) — skipping bet")
        return True
    return False


def log_execution_drift():
    """Log how late we're actually running vs the 5-min schedule."""
    now     = datetime.now(timezone.utc)
    minutes = now.minute
    seconds = now.second
    # How many seconds past the last 5-min mark are we?
    drift = (minutes % 5) * 60 + seconds
    log(f"⏱ Execution drift: {drift}s past 5-min mark "
        f"(target <90s, ideal <30s)")
    return drift


# ── Main ───────────────────────────────────────────────────

def main():
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    log("=" * 50)
    log(f"Bot v4 | {now_str} | paper={PAPER_TRADE} | bet=${BET_SIZE_USD}")

    # ── Execution drift check ──────────────────────────────
    log_execution_drift()

    # ── Load persistent state ──────────────────────────────
    state  = load_json(STATE_FILE,  default=None)
    ledger = load_json(LEDGER_FILE, default=[])

    # ── Fetch candles + price IN PARALLEL ─────────────────
    log("Fetching data (parallel)...")
    candles, chainlink_price, data_source = get_candles_and_price(count=100, interval_mins=5)

    # ── Evaluate last prediction ───────────────────────────
    ledger = evaluate_last_prediction(state, chainlink_price, ledger)
    save_json(LEDGER_FILE, ledger)

    # ── Print stats ────────────────────────────────────────
    print_stats(ledger)

    # ── Guards ─────────────────────────────────────────────
    if len(candles) < MIN_CANDLES:
        log(f"Not enough candles ({len(candles)}/{MIN_CANDLES}) — exiting")
        log("=" * 50)
        return

    if is_circuit_breaker_tripped(ledger):
        log("=" * 50)
        return

    if is_low_liquidity():
        log("=" * 50)
        return

    # ── Add indicators ─────────────────────────────────────
    candles = add_indicators(candles)

    # ── Get signal ─────────────────────────────────────────
    signal = get_signal(candles)

    if signal == "SKIP":
        log("No signal — skipping.")
        # Don't save state — nothing to evaluate next run
        log("=" * 50)
        return

    # ── Check open positions ───────────────────────────────
    if get_open_positions():
        log("Open position exists — skipping.")
        log("=" * 50)
        return

    # ── Save state for next run ────────────────────────────
    save_json(STATE_FILE, {
        "signal":    signal,
        "price":     chainlink_price,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })

    # ── Bet or paper trade ─────────────────────────────────
    if PAPER_TRADE:
        log(f"📝 [PAPER TRADE] ${BET_SIZE_USD} → {signal} "
            f"at Chainlink ${chainlink_price:,.2f}")
    else:
        log(f"🎯 Placing REAL bet: ${BET_SIZE_USD} → {signal}")
        result = place_bet(direction=signal, amount_usd=BET_SIZE_USD)
        log(f"Bet result: {result}")

    log("=" * 50)


if __name__ == "__main__":
    main()
