# 🤖 Polymarket BTC Bot (v5)

Automated BTC up/down paper trading bot for Polymarket.
Runs entirely in the cloud via GitHub Actions — no local setup needed.
Live dashboard auto-updates every 5 minutes.

---

## 📊 Live Dashboard

View your paper trade performance at:

https://minkeyman1999.github.io/polymarket-bot

Updates automatically every time the bot runs.

---

## How It Works

Every 5 minutes, GitHub Actions:

1. Fetches BTC/USD candles — Chainlink first (same data Polymarket uses to settle bets), falling back to Kraken then Binance
2. Fetches current Chainlink BTC/USD price from Polymarket
3. Calculates indicators (RSI, EMA, MACD, Bollinger Bands)
4. Runs your chosen strategy — signal is UP, DOWN or SKIP
5. Logs the paper trade decision with Chainlink price
6. On the next run, checks if last prediction was correct
7. Updates ledger.json and pushes it back to the repo
8. Dashboard reads ledger.json and renders live charts

---

## Data Sources

| Source | Used for | Priority |
|---|---|---|
| Chainlink via Polymarket | Candles + settlement price | 1st |
| Kraken | Candle fallback + price fallback | 2nd |
| Binance | Last resort fallback | 3rd |

Using Chainlink as the primary source means strategy signals are calculated
on the exact same price series that determines whether bets win or lose.
Zero price mismatch at settlement.

---

## Protections Built In

| Protection | Detail |
|---|---|
| Circuit breaker | Pauses betting after 5 consecutive losses |
| Low liquidity filter | Skips betting between 2am and 4am UTC |
| Parallel data fetching | Candles and price fetched simultaneously |
| Retry logic | Every request retries 3 times with backoff |
| Fallback chain | 3 data sources — never crashes on one outage |
| Pip caching | Startup time reduced from ~90s to ~15s |

---

## File Structure

```
polymarket-bot/
├── .github/workflows/bot.yml   ← runs every 5 minutes
├── bot/
│   ├── main.py                 ← entry point + paper trade ledger
│   ├── price_feed.py           ← Chainlink-first data fetching
│   ├── indicators.py           ← RSI, MACD, EMA, Bollinger Bands
│   ├── strategy.py             ← betting logic — edit this
│   ├── polymarket.py           ← stubbed, ready for live trading
│   └── logger.py               ← timestamped logging
├── docs/
│   └── index.html              ← live dashboard (GitHub Pages)
├── logs/
│   ├── ledger.json             ← paper trade history (auto-updated)
│   ├── state.json              ← last signal + price (auto-updated)
│   └── bot.log                 ← full run logs (auto-updated)
├── requirements.txt
└── README.md
```

---

## Setup Guide

### Step 1 — Add GitHub Secrets

Go to Settings → Secrets and variables → Actions → New repository secret

| Secret | Value |
|---|---|
| POLYMARKET_KEY | Your Polygon wallet private key (for live trading later) |

Never put keys directly in code files.

### Step 2 — Add GitHub Variables

Go to Settings → Secrets and variables → Actions → Variables → New variable

| Variable | Value | Notes |
|---|---|---|
| PAPER_TRADE | true | Set to false only when ready to go live |
| BET_SIZE_USD | 5 | Dollar amount per bet when live |

### Step 3 — Enable GitHub Pages (live dashboard)

Go to Settings → Pages
- Source: Deploy from branch
- Branch: main
- Folder: /docs
- Click Save

Requires repo to be public on the free GitHub plan.

### Step 4 — Enable GitHub Actions

Go to the Actions tab and click Enable Actions if prompted.
Then click Polymarket BTC Bot → Run workflow to trigger the first run manually.

---

## Choosing a Strategy

Edit bot/strategy.py and change ACTIVE_STRATEGY:

| Strategy | Logic | Best when |
|---|---|---|
| previous_candle | Follow last candle direction | Trending markets |
| mean_reversion | Bet against last candle | Choppy/ranging markets |
| rsi | RSI oversold/overbought signals | High volatility |
| ema_cross | Price vs EMA trend | Strong trends |
| two_candle_momentum | Require 2 candles to agree | Reduces false signals |

---

## Reading the Logs

### In GitHub Actions

Go to Actions → Polymarket BTC Bot → latest run → run-bot

A healthy run looks like:

```
Bot v5 | 2026-03-25 13:00 UTC | paper=true | bet=$5
Execution drift: 42s past 5-min mark
Fetching data in parallel (Chainlink-first)...
Chainlink candles: 100 | $84,523.00
Chainlink price: $84,891.00
OUTCOME ✅  Signal: UP | Actual: UP
Price: $84,523.00 → $84,891.00 (+$368.00)
P&L this trade: +$4.50
Running total: +$4.50 | Win rate: 100.0% (1/1)
Strategy 'previous_candle' → UP
[PAPER TRADE] $5 → UP at Chainlink $84,891.00
```

### On the Dashboard

Visit https://minkeyman1999.github.io/polymarket-bot to see:

- Cumulative P&L equity curve
- Win/loss bar chart per trade
- Full stats (win rate, streak, best/worst trade)
- Last 20 trades table

---

## Going Live (when ready)

1. Set up MetaMask wallet connected to Polymarket
2. Add USDC to your Polygon wallet
3. Find your target BTC market on polymarket.com
4. Update BTC_MARKET_TOKEN_ID in bot/polymarket.py
5. Uncomment py-clob-client in requirements.txt
6. Change PAPER_TRADE variable to false

---

## Risk Warning

Prediction market betting carries real financial risk.
Always run in paper trade mode first and only use money you can afford to lose.
Past paper trade performance does not guarantee future real results.
