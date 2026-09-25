# -*- coding: utf-8 -*-
"""CEX wallet fetchers: Binance / Bybit / Backpack / OKX / Bitget.

Accounts are configured in portfolio_sources.json -> "cex" -> "accounts":
  [{"name", "exchange": "binance"|"bybit"|"backpack"|"okx"|"bitget",
    "key", "secret", "passphrase"?, "enabled"}]

OKX and Bitget additionally need a passphrase (created alongside the API key), so
their account entries carry a third field.

Each account becomes a portfolio wallet (type "cex", chain = exchange name).
Balances are priced with the exchange's own tickers, falling back to native
prices (BTC/ETH/SOL/HYPE), stables = 1.0, else 0.
"""
import base64
import hashlib
import hmac
import json
import time
import urllib.parse
from datetime import datetime, timezone

import requests

from . import sources
from .api import http_get_json

STABLES = {"USDT", "USDC", "BUSD", "FDUSD", "DAI", "TUSD", "USDP", "PYUSD",
           "EUR", "USD", "LDUSDT", "LDFDUSD"}
NATIVE_SYMBOL = {"BTC": "bitcoin", "ETH": "ethereum", "SOL": "solana", "HYPE": "hyperliquid"}
EXCHANGES = ("binance", "bybit", "backpack", "okx", "bitget")


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


# Backpack splits a balance across TWO signed views:
#   /api/v1/capital              spot                      (instruction=balanceQuery)
#   /api/v1/capital/collateral   futures collateral acct   (instruction=collateralQuery)
# The fiat-like "US Dollar" row the exchange UI shows is USDC held in the collateral
# account, so reading only the spot endpoint hid it completely — it was the single
# largest position in the account. The two views also overlap: an asset held in spot
# and pledged as collateral is reported in both with the SAME quantity, so we take the
# per-asset maximum rather than summing (summing would double count it).
#
# The collateral view also carries `assetMarkPrice` per asset, which is the only price
# source for tokenised equities: GOOGL.US has no *_USDC ticker at all.
_BACKPACK_NON_ASSETS = {"POINTS"}   # loyalty points: no price, absent from the UI list


def _backpack_sign(acc):
    """An Ed25519 signer + the per-instruction caller, or a clear error if pynacl is absent."""
    try:
        import nacl.signing  # provided by pynacl (see requirements.txt)
    except ImportError as e:  # noqa: BLE001
        raise RuntimeError(
            "Backpack needs the pynacl package for Ed25519 request signing. "
            "Install it with: pip3 install -r requirements.txt"
        ) from e
    priv = base64.b64decode(str(acc["secret"]).strip())
    pub = base64.b64decode(str(acc["key"]).strip())
    sk = nacl.signing.SigningKey(priv)

    def call(instruction, path):
        ts = str(int(time.time() * 1000))
        window = "10000"
        msg = f"instruction={instruction}&timestamp={ts}&window={window}"
        sig = base64.b64encode(sk.sign(msg.encode()).signature).decode()
        return http_get_json("https://api.backpack.exchange" + path, headers={
            "X-API-Key": base64.b64encode(pub).decode(),
            "X-Signature": sig, "X-Timestamp": ts, "X-Window": window})

    return call


def _backpack_state(acc):
    """(balances, prices) merged across both of Backpack's balance views."""
    call = _backpack_sign(acc)
    spot = call("balanceQuery", "/api/v1/capital") or {}
    try:
        coll = call("collateralQuery", "/api/v1/capital/collateral") or {}
    except Exception:  # noqa: BLE001
        coll = {}          # a spot-only API key can still read the spot balances

    balances, prices = {}, {}
    for asset, v in (spot or {}).items():
        if asset in _BACKPACK_NON_ASSETS:
            continue
        qty = (float(v.get("available") or 0) + float(v.get("locked") or 0)
               + float(v.get("staked") or 0))
        if qty > 0:
            balances[asset] = qty

    for e in (coll or {}).get("collateral") or []:
        sym = str(e.get("symbol") or "")
        if not sym or sym in _BACKPACK_NON_ASSETS:
            continue
        try:
            qty = float(e.get("totalQuantity") or 0)
        except (TypeError, ValueError):
            qty = 0.0
        if qty > 0:
            # maximum, not sum: the collateral view mirrors a pledged spot balance
            balances[sym] = max(balances.get(sym, 0.0), qty)
        try:
            mark = float(e.get("assetMarkPrice") or 0)
        except (TypeError, ValueError):
            mark = 0.0
        if mark > 0:
            prices[sym] = mark
    return balances, prices


# --------------------------------------------------------------------------
# OKX
#
# Signature (v5 REST): base64(HMAC-SHA256(timestamp + method + requestPath, secret))
# where requestPath INCLUDES the query string ("/api/v5/account/balance?ccy=BTC"),
# and the timestamp is ISO-8601 with milliseconds (2020-12-08T09:08:57.715Z).
# Three headers are needed: key, sign and the passphrase set with the API key.
# --------------------------------------------------------------------------
OKX_BASE = "https://www.okx.com"


def _signed_get(url, headers, timeout=20):
    """http_get_json, but an HTTP error body is parsed instead of thrown away.

    OKX and Bitget report a bad key or passphrase as HTTP 401 with the actual reason
    ("Invalid API Key", "Invalid Passphrase") only inside the JSON body; surfacing the
    bare "HTTPError: 401" would leave the user guessing which of the three fields to fix.
    """
    try:
        return http_get_json(url, headers=headers, timeout=timeout, retries=0)
    except requests.exceptions.HTTPError as e:
        resp = getattr(e, "response", None)
        if resp is not None:
            try:
                return resp.json()
            except ValueError:
                pass
        raise


def _okx_request(acc, method, path, query=None):
    query = query or {}
    secret = str(acc.get("secret") or "").strip()
    # ISO-8601 with milliseconds, UTC — OKX rejects a plain epoch
    now = datetime.now(timezone.utc)
    ts = now.strftime("%Y-%m-%dT%H:%M:%S.") + f"{now.microsecond // 1000:03d}Z"
    request_path = path
    if query:
        request_path += "?" + urllib.parse.urlencode(sorted(query.items()))
    prehash = ts + method.upper() + request_path
    sign = base64.b64encode(
        hmac.new(secret.encode(), prehash.encode(), hashlib.sha256).digest()).decode()
    return _signed_get(OKX_BASE + request_path, {
        "OK-ACCESS-KEY": str(acc.get("key") or "").strip(),
        "OK-ACCESS-SIGN": sign,
        "OK-ACCESS-TIMESTAMP": ts,
        "OK-ACCESS-PASSPHRASE": str(acc.get("passphrase") or "").strip(),
    })


def _okx_balances(acc):
    """(balances, prices). OKX reports `eqUsd` per currency, so the price is implied
    by eqUsd/eq and needs no extra call.

    /account/balance only covers the *trading* sub-account; deposits sit in the
    funding sub-account, which OKX itself counts as part of the same total assets.
    The two are distinct balances of the same currency, so they are summed.
    """
    d = _okx_request(acc, "GET", "/api/v5/account/balance") or {}
    if str(d.get("code")) not in ("0", ""):
        raise RuntimeError(f"OKX: {d.get('msg') or d.get('code')}")
    data = (d.get("data") or [{}])[0]
    balances, prices = {}, {}
    try:
        f = _okx_request(acc, "GET", "/api/v5/asset/balances") or {}
        if str(f.get("code")) in ("0", ""):
            for row in f.get("data") or []:
                ccy = str(row.get("ccy") or "").upper()
                try:
                    qty = float(row.get("bal") or 0)
                except (TypeError, ValueError):
                    qty = 0.0
                if ccy and qty > 0:
                    balances[ccy] = balances.get(ccy, 0.0) + qty
    except Exception:  # noqa: BLE001
        pass   # a key without funding read permission still gets the trading account
    for row in data.get("details") or []:
        ccy = str(row.get("ccy") or "").upper()
        if not ccy:
            continue
        try:
            qty = float(row.get("eq") or 0)      # equity: cash + unrealised PnL
        except (TypeError, ValueError):
            qty = 0.0
        if qty <= 0:
            continue
        balances[ccy] = balances.get(ccy, 0.0) + qty
        try:
            usd = float(row.get("eqUsd") or 0)
        except (TypeError, ValueError):
            usd = 0.0
        if usd > 0:
            prices[ccy] = usd / qty
    return balances, prices


# --------------------------------------------------------------------------
# Bitget
#
# Signature (v2 REST): base64(HMAC-SHA256(timestamp + method + requestPath, secret)),
# timestamp in milliseconds. The query string is signed in a stable key order and,
# per Bitget's own docs, the signature uses the RAW (non-percent-encoded) values
# while the URL uses the encoded ones — identical for plain values like
# "productType=USDT-FUTURES", so both are built the same way here.
# --------------------------------------------------------------------------
BITGET_BASE = "https://api.bitget.com"


def _bitget_request(acc, method, path, query=None):
    query = query or {}
    secret = str(acc.get("secret") or "").strip()
    ts = str(int(time.time() * 1000))
    request_path = path
    if query:
        ordered = sorted(query.items())
        request_path += "?" + urllib.parse.urlencode(ordered)
    prehash = ts + method.upper() + request_path
    sign = base64.b64encode(
        hmac.new(secret.encode(), prehash.encode(), hashlib.sha256).digest()).decode()
    return _signed_get(BITGET_BASE + request_path, {
        "ACCESS-KEY": str(acc.get("key") or "").strip(),
        "ACCESS-SIGN": sign,
        "ACCESS-TIMESTAMP": ts,
        "ACCESS-PASSPHRASE": str(acc.get("passphrase") or "").strip(),
    })


def _bitget_balances(acc):
    """(balances, prices) summed across the spot account and the futures accounts.

    A Bitget API key can be scoped to one account type, so a failure on one call is
    not fatal as long as the other answered.
    """
    balances, prices, errors = {}, {}, []

    # spot
    try:
        d = _bitget_request(acc, "GET", "/api/v2/spot/account/assets") or {}
        if str(d.get("code")) == "00000":
            for row in d.get("data") or []:
                coin = str(row.get("coin") or "").upper()
                if not coin:
                    continue
                qty = 0.0
                for field in ("available", "frozen", "locked"):
                    try:
                        qty += float(row.get(field) or 0)
                    except (TypeError, ValueError):
                        pass
                if qty > 0:
                    balances[coin] = balances.get(coin, 0.0) + qty
        else:
            errors.append(f"spot: {d.get('msg') or d.get('code')}")
    except Exception as e:  # noqa: BLE001
        errors.append(f"spot: {type(e).__name__}")

    # futures: accountEquity is the whole position value in the margin coin.
    # The S-prefixed products (SUSDT-FUTURES/SUSDC-FUTURES/SCOIN-FUTURES) are the
    # *simulated* demo accounts: they answer with a 3000-each play-money balance on
    # a real read-only key, so including them would add $6000 of money that does
    # not exist.
    for product in ("USDT-FUTURES", "USDC-FUTURES", "COIN-FUTURES"):
        try:
            d = _bitget_request(acc, "GET", "/api/v2/mix/account/accounts",
                                {"productType": product}) or {}
            if str(d.get("code")) != "00000":
                continue
            for row in d.get("data") or []:
                coin = str(row.get("marginCoin") or "").upper()
                try:
                    qty = float(row.get("accountEquity") or 0)
                except (TypeError, ValueError):
                    qty = 0.0
                if coin and qty > 0:
                    balances[coin] = balances.get(coin, 0.0) + qty
        except Exception:  # noqa: BLE001
            continue

    if not balances and errors:
        raise RuntimeError("Bitget: " + "; ".join(errors))
    return balances, prices


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
    elif exchange == "okx":
        # OKX's own spot tickers, so an asset outside the account's implied prices
        # still gets a live price
        try:
            d = http_get_json("https://www.okx.com/api/v5/market/tickers",
                              params={"instType": "SPOT"}, timeout=15, retries=0)
            for t in (d or {}).get("data") or []:
                inst = str(t.get("instId") or "")
                if not inst.endswith("-USDT"):
                    continue
                try:
                    prices[inst[:-5]] = float(t["last"])
                except (KeyError, ValueError):
                    pass
        except Exception:  # noqa: BLE001
            pass
    elif exchange == "bitget":
        try:
            d = http_get_json("https://api.bitget.com/api/v2/spot/market/tickers",
                              timeout=15, retries=0)
            for t in (d or {}).get("data") or []:
                sym = str(t.get("symbol") or "")
                if not sym.endswith("USDT"):
                    continue
                try:
                    prices[sym[:-4]] = float(t["lastPr"])
                except (KeyError, ValueError):
                    pass
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
        # the on-chain price is preferred, but if that pipeline is down the exchange's
        # own price is far better than reporting the holding as worth nothing
        p = native.get(NATIVE_SYMBOL[asset])
        if p:
            return p
        return ticker.get(asset, 0.0)
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
                balances, mark_prices = _backpack_state(acc)
            elif ex == "okx":
                balances, mark_prices = _okx_balances(acc)
            elif ex == "bitget":
                balances, mark_prices = _bitget_balances(acc)
            else:
                raise ValueError(f"未知交易所: {ex}（支持 {'/'.join(EXCHANGES)}）")
            ticker = _ticker_map(ex, list(balances.keys()))
            if ex in ("backpack", "okx", "bitget"):
                # a *_USDC lastPrice is the better price for a spot balance; the
                # account-implied price fills in anything with no pair (OKX reports
                # eqUsd per currency, Backpack marks tokenised stocks)
                ticker = dict(mark_prices, **ticker)
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
