# -*- coding: utf-8 -*-
"""CEX wallet fetchers: Binance / Bybit / Backpack.

Accounts are configured in portfolio_sources.json -> "cex" -> "accounts":
  [{"name", "exchange": "binance"|"bybit"|"backpack", "key", "secret", "enabled"}]

Each account becomes a portfolio wallet (type "cex", chain = exchange name).
Balances are priced with the exchange's own tickers, falling back to native
prices (BTC/ETH/SOL/HYPE), stables = 1.0, else 0.
"""
import base64
import hashlib
import hmac
import json
import time

from . import sources
from .api import http_get_json

STABLES = {"USDT", "USDC", "BUSD", "FDUSD", "DAI", "TUSD", "USDP", "PYUSD",
           "EUR", "USD", "LDUSDT", "LDFDUSD"}
NATIVE_SYMBOL = {"BTC": "bitcoin", "ETH": "ethereum", "SOL": "solana", "HYPE": "hyperliquid"}
EXCHANGES = ("binance", "bybit", "backpack")


def cex_accounts():
    cfg = sources.get_source("cex")
    if not cfg.get("enabled", True):
        return []
    out = []
    for a in cfg.get("accounts", []):
        if not a.get("enabled", True):
            continue
        # skip rows with no credentials (placeholder CEX entries shown in the UI)
        if not (a.get("key") or "").strip() and not (a.get("secret") or "").strip():
            continue
        out.append(a)
    return out


# --------------------------------------------------------------------------
# balance fetchers
# --------------------------------------------------------------------------

def _binance_balances(acc):
    key = str(acc["key"]).split(":")[-1].strip()   # allow "label:key" prefixes
    secret = str(acc["secret"]).strip()
    ts = int(time.time() * 1000)
    qs = f"timestamp={ts}&recvWindow=5000"
    sig = hmac.new(secret.encode(), qs.encode(), hashlib.sha256).hexdigest()
    d = http_get_json("https://api.binance.com/api/v3/account",
                      params={"timestamp": ts, "recvWindow": 5000, "signature": sig},
                      headers={"X-MBX-APIKEY": key})
    out = {}
    for b in (d or {}).get("balances", []):
        total = float(b.get("free") or 0) + float(b.get("locked") or 0)
        if total > 0:
            out[b["asset"]] = total
    return out


def _bybit_signed_get(acc, path, params):
    key, secret = str(acc["key"]).strip(), str(acc["secret"]).strip()
    ts = str(int(time.time() * 1000))
    recv = "5000"
    qs = "&".join(f"{k}={v}" for k, v in sorted(params.items()))
    sig = hmac.new(secret.encode(), (ts + key + recv + qs).encode(), hashlib.sha256).hexdigest()
    return http_get_json("https://api.bybit.com" + path, params=params,
                         headers={"X-BAPI-API-KEY": key, "X-BAPI-TIMESTAMP": ts,
                                  "X-BAPI-RECV-WINDOW": recv, "X-BAPI-SIGN": sig})


def _bybit_balances(acc):
    """Bybit balances: UNIFIED (trading) + FUND (funding) + EARN (best effort).

    - UNIFIED: /v5/account/wallet-balance?accountType=UNIFIED
    - FUND:    /v5/asset/transfer/query-account-coins-balance?accountType=FUND
    - EARN:    /v5/earn/fixed-term/position, /v5/earn/rwa/position,
               /v5/earn/advance/position (categories SmartLeverage/DiscountBuy/
               DoubleWin/DualAssets) — some earn products (e.g. Easy Onchain)
               no longer have a working API endpoint; those need Earn API
               permission on the key.
    """
    out = {}
    try:
        d = _bybit_signed_get(acc, "/v5/account/wallet-balance", {"accountType": "UNIFIED"})
        if (d or {}).get("retCode") != 0:
            raise RuntimeError(f"bybit UNIFIED: {d.get('retCode')} {d.get('retMsg')}")
        lst = ((d.get("result") or {}).get("list") or [{}])
        for coin in (lst[0] if lst else {}).get("coin", []):
            amt = float(coin.get("walletBalance") or 0)
            if amt > 0:
                out[coin.get("coin")] = out.get(coin.get("coin"), 0.0) + amt
    except Exception as e:  # noqa: BLE001
        raise RuntimeError(f"bybit UNIFIED: {e}")

    try:
        d = _bybit_signed_get(acc, "/v5/asset/transfer/query-account-coins-balance",
                              {"accountType": "FUND"})
        if (d or {}).get("retCode") != 0:
            raise RuntimeError(f"bybit FUND: {d.get('retCode')} {d.get('retMsg')}")
        for b in ((d.get("result") or {}).get("balance") or []):
            amt = float(b.get("walletBalance") or 0)
            if amt > 0:
                out[b.get("coin")] = out.get(b.get("coin"), 0.0) + amt
    except Exception as e:  # noqa: BLE001
        raise RuntimeError(f"bybit FUND: {e}")

    # EARN — best effort across the product endpoints that still exist
    earn_calls = [("/v5/earn/fixed-term/position", {}),
                  ("/v5/earn/rwa/position", {}),
                  ("/v5/earn/advance/position", {"category": "SmartLeverage"}),
                  ("/v5/earn/advance/position", {"category": "DiscountBuy"}),
                  ("/v5/earn/advance/position", {"category": "DoubleWin"}),
                  ("/v5/earn/advance/position", {"category": "DualAssets"})]
    for path, params in earn_calls:
        try:
            d = _bybit_signed_get(acc, path, params)
            if (d or {}).get("retCode") != 0:
                continue
            for pos in ((d.get("result") or {}).get("list") or []):
                coin = pos.get("coin") or pos.get("productCoin") or ""
                amt = float(pos.get("holding") or pos.get("balance")
                            or pos.get("positionBalance") or 0)
                if coin and amt > 0:
                    out[coin] = out.get(coin, 0.0) + amt
        except Exception:  # noqa: BLE001
            continue
    return out


def _backpack_balances(acc):
    import nacl.signing  # vendored dependency (pynacl)
    priv = base64.b64decode(str(acc["secret"]).strip())
    pub = base64.b64decode(str(acc["key"]).strip())
    sk = nacl.signing.SigningKey(priv)
    ts = str(int(time.time() * 1000))
    window = "10000"
    msg = f"instruction=balanceQuery&timestamp={ts}&window={window}"
    sig = base64.b64encode(sk.sign(msg.encode()).signature).decode()
    d = http_get_json("https://api.backpack.exchange/api/v1/capital", headers={
        "X-API-Key": base64.b64encode(pub).decode(),
        "X-Signature": sig, "X-Timestamp": ts, "X-Window": window})
    out = {}
    for asset, v in (d or {}).items():
        total = (float(v.get("available") or 0) + float(v.get("locked") or 0)
                 + float(v.get("staked") or 0))
        if total > 0:
            out[asset] = total
    return out


# --------------------------------------------------------------------------
# ticker pricing
# --------------------------------------------------------------------------

def _ticker_map(exchange, assets):
    """{asset: usd_price} from the exchange's own public tickers."""
    prices = {}
    if exchange == "binance":
        try:
            d = http_get_json("https://api.binance.com/api/v3/ticker/price",
                              params={"symbols": json.dumps([f"{a}USDT" for a in assets])},
                              timeout=12, retries=0)
            for t in d or []:
                sym = t.get("symbol", "")
                if sym.endswith("USDT"):
                    prices[sym[:-4]] = float(t["price"])
        except Exception:  # noqa: BLE001
            pass
        for a in assets:
            if a in prices:
                continue
            for q in ("USDT", "USDC"):
                try:
                    t = http_get_json("https://api.binance.com/api/v3/ticker/price",
                                      params={"symbol": f"{a}{q}"}, timeout=8, retries=0)
                    prices[a] = float(t["price"])
                    break
                except Exception:  # noqa: BLE001
                    pass
    elif exchange == "bybit":
        for a in assets:
            try:
                d = http_get_json("https://api.bybit.com/v5/market/tickers",
                                  params={"category": "spot", "symbol": f"{a}USDT"},
                                  timeout=8, retries=0)
                lst = ((d or {}).get("result") or {}).get("list") or []
                if lst:
                    prices[a] = float(lst[0]["lastPrice"])
            except Exception:  # noqa: BLE001
                pass
    elif exchange == "backpack":
        try:
            d = http_get_json("https://api.backpack.exchange/api/v1/tickers", timeout=12, retries=0)
            for t in d or []:
                sym = t.get("symbol") or ""
                for a in assets:
                    if sym in (f"{a}_USDC", f"{a}_USDT"):
                        try:
                            prices[a] = float(t["lastPrice"])
                        except (KeyError, ValueError):
                            pass
        except Exception:  # noqa: BLE001
            pass
    return prices


def _price_of(asset, native, ticker):
    if asset in STABLES:
        return 1.0
    if asset in NATIVE_SYMBOL:
        return native.get(NATIVE_SYMBOL[asset]) or 0.0
    return ticker.get(asset, 0.0)


def fetch_cex_accounts(accounts, native):
    """[{account, rows, total_usd, error}] for each enabled account."""
    results = []
    for acc in accounts:
        ex = str(acc.get("exchange") or "").lower()
        try:
            if ex == "binance":
                balances = _binance_balances(acc)
            elif ex == "bybit":
                balances = _bybit_balances(acc)
            elif ex == "backpack":
                balances = _backpack_balances(acc)
            else:
                raise ValueError(f"未知交易所: {ex}（支持 {'/'.join(EXCHANGES)}）")
            ticker = _ticker_map(ex, list(balances.keys()))
            rows = []
            for asset, amount in sorted(balances.items()):
                if amount <= 0:
                    continue
                price = _price_of(asset, native, ticker)
                rows.append({
                    "wallet": acc["name"], "chain": ex, "symbol": asset,
                    "name": f"{ex} {asset}", "amount": amount,
                    "price": price, "usd": round(amount * price, 6),
                    "logo": "", "token_id": f"{ex}-{asset}",
                })
            results.append({"account": acc, "rows": rows,
                            "total_usd": round(sum(r["usd"] for r in rows), 2),
                            "error": None})
        except Exception as e:  # noqa: BLE001
            results.append({"account": acc, "rows": [], "total_usd": 0.0,
                            "error": f"{type(e).__name__}: {e}"})
    return results
