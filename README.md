# 🤖 Polymarket BTC Bot

Automated BTC up/down betting bot for Polymarket.
Runs entirely in the cloud via GitHub Actions — no local setup needed.

---

## How It Works

Every 5 minutes, GitHub Actions:
1. Fetches latest BTC/USD 5-min candles from Kraken
2. Calculates indicators (RSI, EMA, MACD etc)
3. Runs your chosen strategy
4. Places a bet on Polymarket (or logs it in paper trade mode)

---

## Setup Guide

### Step 1 — Add your API keys as GitHub Secrets

Go to your repo → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**

Add these secrets:

| Secret name | Value |
|---|---|
| `KRAKEN_API_KEY` | Your Kraken API key |
| `KRAKEN_API_SECRET` | Your Kraken API secret |
| `POLYMARKET_KEY` | Your Polygon wallet private key |

⚠️ **Never put API keys in code files — secrets only.**

### Step 2 — Set paper trade mode

Go to **Settings** → **Secrets and variables** → **Variables** → **New variable**

| Variable | Value |
|---|---|
| `PAPER_TRADE` | `true` (start here — no real money) |
| `BET_SIZE_USD` | `5` (dollars per bet when live) |

### Step 3 — Enable GitHub Actions

Go to the **Actions** tab in your repo and click **Enable Actions**.

The bot will now run every 5 minutes automatically.
Check the Actions tab to see each run's log output.

### Step 4 — Choose your strategy

Edit `bot/strategy.py` and change `ACTIVE_STRATEGY` to one of:
- `previous_candle` — follow last candle direction
- `mean_reversion` — bet against last candle
- `rsi` — RSI overbought/oversold signals
- `ema_cross` — EMA trend following
- `two_candle_momentum` — require 2 candles to agree

### Step 5 — Go live (when ready)

1. Set up MetaMask wallet and connect to Polymarket
2. Add USDC to your Polygon wallet
3. Find your target BTC market on Polymarket and update `BTC_MARKET_TOKEN_ID` in `bot/polymarket.py`
4. Uncomment `py-clob-client` in `requirements.txt`
5. Change `PAPER_TRADE` variable to `false`

---

## File Structure

```
polymarket-bot/
├── .github/workflows/bot.yml   # Runs every 5 minutes
├── bot/
│   ├── main.py                 # Entry point
│   ├── kraken.py               # Fetches BTC price data
│   ├── indicators.py           # RSI, MACD, EMA etc
│   ├── strategy.py             # YOUR betting logic ← edit this
│   ├── polymarket.py           # Places bets
│   └── logger.py               # Logging
├── backtest/
│   └── backtest.py             # Test strategies offline
├── logs/bot.log                # Run history
├── config.yml                  # Settings
└── requirements.txt            # Python libraries
```

---

## Viewing Logs

Go to your repo → **Actions** tab → click any run → click **run-bot** to see full output.

---

## ⚠️ Risk Warning

Prediction market betting carries real financial risk.
Always start with paper trading and small amounts.
Past strategy performance does not guarantee future results.
