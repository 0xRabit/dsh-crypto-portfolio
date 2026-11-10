# -*- coding: utf-8 -*-
"""Native-coin USD prices — configurable multi-source with automatic failover.

Providers live in portfolio_sources.json -> "prices" -> "providers" and are
tried in order; the first provider that returns non-empty prices wins, and the
last working provider is remembered for the next call.

Supported provider names: coingecko | binance | coinbase | okx
"""
import json
import time

from . import sources
from .api import http_get_json

# coingecko_id -> exchange symbol
NATIVE_IDS = ("bitcoin", "ethereum", "solana", "hyperliquid", "dogecoin", "cardano")
EXCHANGE_SYMBOLS = {"bitcoin": "BTC", "ethereum": "ETH", "solana": "SOL", "hyperliquid": "HYPE",
                    "dogecoin": "DOGE", "cardano": "ADA"}


# Public venues that quote things Binance only holds as a receipt. Backpack lists
# tokenised equities as `AAPL.US` (ticker is public, no key needed); Binance has no
# pair for the same underlying, so this is how its EQ_* receipt gets a market value.
VENUE_TTL = 900.0
_VENUE_CACHE = {}


def venue_price(source, symbol):
    """USD quote for `symbol` from a public venue, 0.0 when it cannot be fetched.

    Cached for VENUE_TTL: a refresh asks about the same handful of symbols, and the
    ticker would otherwise be hit once per asset on every refresh.
    """
    source = str(source or "").strip().lower()
    symbol = str(symbol or "").strip()
    if not source or not symbol:
        return 0.0
    key = (source, symbol)
    hit = _VENUE_CACHE.get(key)
    if hit and time.time() - hit[0] < VENUE_TTL:
        return hit[1]
    price = 0.0
    try:
        if source == "backpack":
            d = http_get_json("https://api.backpack.exchange/api/v1/ticker",
                              params={"symbol": symbol}, timeout=12, retries=1)
            if isinstance(d, dict):
                price = float(d.get("lastPrice") or 0)
    except Exception:                                        # noqa: BLE001
        price = 0.0
    if price > 0 and price != float("inf"):
        _VENUE_CACHE[key] = (time.time(), price)
        return price
    return 0.0


def stated_price(entry):
    """A configured price: either a number or {"source", "symbol"} from a venue."""
    if isinstance(entry, dict):
        return venue_price(entry.get("source"), entry.get("symbol"))
    try:
        value = float(entry)
    except (TypeError, ValueError):
        return 0.0
    return value if value > 0 and value != float("inf") else 0.0


def get_native_prices(ids=NATIVE_IDS):
    """{coingecko_id: usd_price}; {} when every provider fails."""
    cfg = sources.get_source("prices")
    if not cfg.get("enabled", True):
        return {}
    providers = cfg.get("providers", [])
    try:
        prices, _ = sources.try_providers("prices", providers,
                                          lambda p: _fetch_one(p, ids), nonempty=True)
        return prices or {}
    except Exception:  # noqa: BLE001
        return {}


def _fetch_one(provider, ids):
    name = provider.get("name")
    if name == "coingecko":
        return _coin_gecko(ids, provider)
    if name == "binance":
        return _binance(ids, provider)
    if name == "coinbase":
        return _coinbase(ids, provider)
    if name == "okx":
        return _okx(ids, provider)
    raise ValueError(f"未知价格 provider: {name}")


def _coin_gecko(ids, p):
    headers = {}
    if p.get("key"):
        headers["x-cg-demo-api-key"] = p["key"]
    d = http_get_json(p["url"], headers=headers,
                      params={"ids": ",".join(ids), "vs_currencies": "usd"},
                      timeout=20, retries=1)
    return {k: float(v["usd"]) for k, v in (d or {}).items() if v}


def _binance(ids, p):
    symbols = [EXCHANGE_SYMBOLS[i] + "USDT" for i in ids if i in EXCHANGE_SYMBOLS]
    d = http_get_json(p["url"], params={"symbols": json.dumps(symbols)},
                      timeout=15, retries=1)
    out = {}
    for item in d or []:
        sym = item.get("symbol", "").replace("USDT", "")
        for cid, xsym in EXCHANGE_SYMBOLS.items():
            if sym == xsym:
                try:
                    out[cid] = float(item["price"])
                except (KeyError, ValueError):
                    pass
    return out


def _coinbase(ids, p):
    out = {}
    for cid in ids:
        pair = EXCHANGE_SYMBOLS.get(cid)
        if not pair:
            continue
        d = http_get_json(p["url"].format(pair=pair), timeout=15)
        amt = ((d or {}).get("data") or {}).get("amount")
        if amt:
            out[cid] = float(amt)
        time.sleep(0.1)
    return out


def _okx(ids, p):
    out = {}
    for cid in ids:
        pair = EXCHANGE_SYMBOLS.get(cid)
        if not pair:
            continue
        d = http_get_json(p["url"], params={"instId": pair + "-USDT"}, timeout=15)
        data = (d or {}).get("data") or []
        if data and data[0].get("last"):
            out[cid] = float(data[0]["last"])
        time.sleep(0.1)
    return out
