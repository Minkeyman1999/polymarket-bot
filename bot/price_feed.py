"""
price_feed.py — BTC price data (Chainlink-first)
──────────────────────────────────────────────────
Priority order matches what Polymarket uses to settle bets:

  CANDLES:  Chainlink (via Polymarket API) -> Kraken -> Binance
  PRICE:    Chainlink (via Polymarket API) -> Kraken -> Binance

Using Chainlink as primary source means our strategy signals
are calculated on the exact same price series that determines
whether our bets win or lose. Zero price mismatch.
"""

import time
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from bot.logger import log

POLYMARKET_HISTORY = "https://clob.polymarket.com/prices-history"
KRAKEN_OHLC        = "https://api.kraken.com/0/public/OHLC"
KRAKEN_TICKER      = "https://api.kraken.com/0/public/Ticker"
BINANCE_OHLC       = "https://api.binance.com/api/v3/klines"
BINANCE_TICKER     = "https://api.binance.com/api/v3/ticker/price"

TIMEOUT = 10
RETRIES = 3


def _get(url, params=None, attempt=1):
    try:
        resp = requests.get(url, params=params, timeout=TIMEOUT)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        if attempt < RETRIES:
            wait = 2 ** attempt
            log(f"Retry {attempt}/{RETRIES} ({e})")
            time.sleep(wait)
            return _get(url, params, attempt + 1)
        log(f"Failed after {RETRIES} attempts: {e}")
        return None


def _candles_from_chainlink(count, interval_mins):
    """Build OHLC candles from Polymarket Chainlink price history."""
    data = _get(POLYMARKET_HISTORY, {
        "market":   "BTC-USD",
        "interval": "1m",
        "fidelity": count * interval_mins + 60,
    })
    if not data or not data.get("history") or len(data["history"]) < 5:
        return None

    interval_ms = interval_mins * 60 * 1000
    buckets = {}

    for tick in data["history"]:
        ts    = int(tick["t"]) * 1000
        price = float(tick["p"])
        key   = (ts // interval_ms) * interval_ms

        if key not in buckets:
            buckets[key] = {"timestamp": key, "open": price,
                            "high": price, "low": price,
                            "close": price, "volume": 1,
                            "source": "chainlink"}
        else:
            b = buckets[key]
            b["high"]  = max(b["high"], price)
            b["low"]   = min(b["low"],  price)
            b["close"] = price
            b["volume"] += 1

    candles = sorted(buckets.values(), key=lambda x: x["timestamp"])
    result = candles[-count:]
    return result if len(result) >= 10 else None


def _candles_from_kraken(count, interval_mins):
    data = _get(KRAKEN_OHLC, {"pair": "XBTUSD", "interval": interval_mins})
    if not data or data.get("error"):
        return None
    key = [k for k in data["result"] if k != "last"][0]
    return [{
        "timestamp": int(k[0]) * 1000, "open": float(k[1]),
        "high": float(k[2]), "low": float(k[3]),
        "close": float(k[4]), "volume": float(k[6]),
        "source": "kraken"
    } for k in data["result"][key]][-count:]


def _candles_from_binance(count, interval_mins):
    imap = {1: "1m", 5: "5m", 15: "15m", 60: "1h"}
    data = _get(BINANCE_OHLC, {"symbol": "BTCUSDT",
                                "interval": imap.get(interval_mins, "5m"),
                                "limit": count})
    if not data:
        return None
    return [{"timestamp": int(k[0]), "open": float(k[1]),
             "high": float(k[2]), "low": float(k[3]),
             "close": float(k[4]), "volume": float(k[5]),
             "source": "binance"} for k in data]


def _price_from_chainlink():
    data = _get(POLYMARKET_HISTORY, {"market": "BTC-USD",
                                      "interval": "1m", "fidelity": 5})
    if data and data.get("history"):
        return float(data["history"][-1]["p"])
    return None


def _price_from_kraken():
    data = _get(KRAKEN_TICKER, {"pair": "XBTUSD"})
    if not data or data.get("error"):
        return None
    key = list(data["result"].keys())[0]
    return float(data["result"][key]["c"][0])


def _price_from_binance():
    data = _get(BINANCE_TICKER, {"symbol": "BTCUSDT"})
    return float(data["price"]) if data and "price" in data else None


def get_candles_and_price(count=100, interval_mins=5):
    """
    Fetch candles + price in parallel.
    Chainlink is tried first for both — falls back to Kraken then Binance.
    Returns (candles, price, source_string).
    """
    candles_r = [None]
    price_r   = [None]
    source_r  = ["unknown"]

    def fetch_candles():
        log("Candles: trying Chainlink...")
        c = _candles_from_chainlink(count, interval_mins)
        if c:
            log(f"Chainlink candles: {len(c)} | ${c[-1]['close']:,.2f}")
            candles_r[0] = c
            source_r[0]  = "chainlink"
            return
        log("Chainlink failed, trying Kraken...")
        c = _candles_from_kraken(count, interval_mins)
        if c:
            log(f"Kraken candles: {len(c)} | ${c[-1]['close']:,.2f}")
            candles_r[0] = c
            source_r[0]  = "kraken"
            return
        log("Kraken failed, trying Binance...")
        c = _candles_from_binance(count, interval_mins)
        if c:
            log(f"Binance candles: {len(c)} | ${c[-1]['close']:,.2f}")
            candles_r[0] = c
            source_r[0]  = "binance"
        else:
            log("ERROR: All candle sources failed")

    def fetch_price():
        p = _price_from_chainlink()
        if p:
            log(f"Chainlink price: ${p:,.2f}")
            price_r[0] = p
            return
        p = _price_from_kraken()
        if p:
            log(f"Kraken price fallback: ${p:,.2f}")
            price_r[0] = p
            return
        p = _price_from_binance()
        if p:
            log(f"Binance price fallback: ${p:,.2f}")
            price_r[0] = p
        else:
            log("ERROR: All price sources failed")

    with ThreadPoolExecutor(max_workers=2) as executor:
        for f in as_completed([executor.submit(fetch_candles),
                                executor.submit(fetch_price)]):
            f.result()

    return candles_r[0] or [], price_r[0], source_r[0]
