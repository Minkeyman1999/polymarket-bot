"""
price_feed.py — BTC price from Polymarket's Chainlink feed
────────────────────────────────────────────────────────────
Polymarket streams the exact same Chainlink BTC/USD price
that is used to SETTLE bets. Using this guarantees our bot
is working with the same data the bets resolve against.

Two functions:
  get_candles()      → builds 5-min OHLC candles from recent prices
  get_current_price() → returns the latest Chainlink BTC/USD price

Source: Polymarket Real-Time Data Socket (no auth required)
Docs:   https://docs.polymarket.com/developers/RTDS/RTDS-crypto-prices

WebSocket endpoint:
  wss://ws-subscriptions-clob.polymarket.com/ws/

Subscribe message:
  {
    "action": "subscribe",
    "subscriptions": [{
      "topic": "crypto_prices_chainlink",
      "type": "update",
      "filters": "btc/usd"
    }]
  }

Each message received:
  {
    "topic": "crypto_prices_chainlink",
    "type": "update",
    "timestamp": 1234567890000,
    "payload": {
      "symbol": "btc/usd",
      "timestamp": 1234567890000,
      "value": 84523.10
    }
  }
"""

import json
import time
import websocket  # pip install websocket-client
from datetime import datetime, timezone
from bot.logger import log

# ── Config ────────────────────────────────────────────────
WS_URL        = "wss://ws-subscriptions-clob.polymarket.com/ws/"
CANDLE_MINS   = 5          # candle size in minutes
COLLECT_SECS  = 60         # how long to collect prices before building candles
MAX_CANDLES   = 100        # how many candles to return


def get_current_price():
    """
    Connect to Polymarket's Chainlink feed, grab a single
    BTC/USD price update, disconnect, and return the price.

    Returns float price or None on failure.
    """
    price = [None]  # use list so inner function can write to it

    def on_open(ws):
        subscribe_msg = {
            "action": "subscribe",
            "subscriptions": [{
                "topic": "crypto_prices_chainlink",
                "type": "update",
                "filters": "btc/usd"
            }]
        }
        ws.send(json.dumps(subscribe_msg))
        log("Connected to Polymarket Chainlink feed")

    def on_message(ws, message):
        try:
            data = json.loads(message)
            if data.get("topic") == "crypto_prices_chainlink":
                price[0] = float(data["payload"]["value"])
                log(f"Chainlink BTC/USD: ${price[0]:,.2f}")
                ws.close()  # got what we need
        except Exception as e:
            log(f"Error parsing price message: {e}")

    def on_error(ws, error):
        log(f"WebSocket error: {error}")

    def on_close(ws, code, msg):
        log("Disconnected from Polymarket feed")

    try:
        ws = websocket.WebSocketApp(
            WS_URL,
            on_open=on_open,
            on_message=on_message,
            on_error=on_error,
            on_close=on_close,
        )
        # run_forever with timeout — don't hang forever
        ws.run_forever(ping_interval=10, ping_timeout=5)
    except Exception as e:
        log(f"WebSocket connection failed: {e}")

    return price[0]


def get_candles(count=MAX_CANDLES, interval_mins=CANDLE_MINS):
    """
    Collect BTC/USD price ticks from Polymarket's Chainlink feed
    for COLLECT_SECS seconds, then bucket them into OHLC candles.

    Because GitHub Actions runs every 5 minutes, we collect prices
    for 60 seconds on each run to get enough ticks to build candles.
    We store prices in a log file between runs to accumulate history.

    Returns list of candle dicts:
      [{ "timestamp": int ms,
         "open": float, "high": float,
         "low": float,  "close": float,
         "volume": int  (tick count) }, ...]
    """
    import os

    PRICE_LOG = os.path.join(
        os.path.dirname(__file__), "..", "logs", "prices.jsonl"
    )

    # ── Step 1: Collect new price ticks for COLLECT_SECS ──
    ticks = []
    stop_time = time.time() + COLLECT_SECS

    def on_open(ws):
        subscribe_msg = {
            "action": "subscribe",
            "subscriptions": [{
                "topic": "crypto_prices_chainlink",
                "type": "update",
                "filters": "btc/usd"
            }]
        }
        ws.send(json.dumps(subscribe_msg))

    def on_message(ws, message):
        try:
            data = json.loads(message)
            if data.get("topic") == "crypto_prices_chainlink":
                tick = {
                    "t": data["payload"]["timestamp"],
                    "p": float(data["payload"]["value"])
                }
                ticks.append(tick)
                if time.time() >= stop_time:
                    ws.close()
        except Exception as e:
            log(f"Tick parse error: {e}")

    def on_error(ws, error):
        log(f"Feed error: {error}")

    def on_close(ws, *args):
        pass

    try:
        ws = websocket.WebSocketApp(
            WS_URL,
            on_open=on_open,
            on_message=on_message,
            on_error=on_error,
            on_close=on_close,
        )
        ws.run_forever(ping_interval=10, ping_timeout=5)
    except Exception as e:
        log(f"Failed to collect ticks: {e}")

    log(f"Collected {len(ticks)} price ticks")

    # ── Step 2: Append new ticks to price log file ─────────
    os.makedirs(os.path.dirname(PRICE_LOG), exist_ok=True)
    with open(PRICE_LOG, "a") as f:
        for tick in ticks:
            f.write(json.dumps(tick) + "\n")

    # ── Step 3: Read all stored ticks ─────────────────────
    all_ticks = []
    try:
        with open(PRICE_LOG, "r") as f:
            for line in f:
                line = line.strip()
                if line:
                    all_ticks.append(json.loads(line))
    except FileNotFoundError:
        log("No price history yet — need more runs to build candles")
        return []

    if len(all_ticks) < 5:
        log(f"Only {len(all_ticks)} ticks stored — need more data")
        return []

    # ── Step 4: Bucket ticks into OHLC candles ─────────────
    interval_ms = interval_mins * 60 * 1000
    candles = {}

    for tick in all_ticks:
        # Which candle bucket does this tick belong to?
        bucket = (tick["t"] // interval_ms) * interval_ms
        if bucket not in candles:
            candles[bucket] = {
                "timestamp": bucket,
                "open":   tick["p"],
                "high":   tick["p"],
                "low":    tick["p"],
                "close":  tick["p"],
                "volume": 1,
            }
        else:
            c = candles[bucket]
            c["high"]   = max(c["high"],  tick["p"])
            c["low"]    = min(c["low"],   tick["p"])
            c["close"]  = tick["p"]
            c["volume"] += 1

    # Sort by timestamp, return most recent `count`
    sorted_candles = sorted(candles.values(), key=lambda x: x["timestamp"])
    log(f"Built {len(sorted_candles)} candles from {len(all_ticks)} ticks")

    return sorted_candles[-count:]


def prune_old_ticks(max_hours=48):
    """
    Keep the price log from growing forever.
    Deletes ticks older than max_hours.
    Call this from main.py periodically.
    """
    import os
    PRICE_LOG = os.path.join(
        os.path.dirname(__file__), "..", "logs", "prices.jsonl"
    )
    cutoff_ms = (time.time() - max_hours * 3600) * 1000

    try:
        with open(PRICE_LOG, "r") as f:
            lines = f.readlines()

        kept = [l for l in lines if json.loads(l.strip())["t"] >= cutoff_ms]

        with open(PRICE_LOG, "w") as f:
            f.writelines(kept)

        log(f"Pruned price log: kept {len(kept)}/{len(lines)} ticks")
    except Exception as e:
        log(f"Prune error: {e}")
