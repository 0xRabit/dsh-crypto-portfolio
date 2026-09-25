# -*- coding: utf-8 -*-
"""Per-source connection tests ("Test" buttons in Settings).

Each configured source can be probed on its own so a broken key, a wrong URL or a
missing permission is named *before* a refresh turns the whole dashboard into error
rows. A probe is deliberately cheap: one authenticated request where a key exists,
and a tiny public one where it does not.

Every probe returns the same shape, so the UI can render any of them identically:

    {"ok": bool, "ms": int, "message": str, "detail": {...}}

`message` is what the user reads — the provider's own wording where there is one,
because "401" tells nobody which field to fix.
"""
import time
from urllib.parse import urlsplit

from . import cex, sources
from .api import http_get_json, http_post_json


def _origin(url):
    """Scheme+host of a configured endpoint (those carry a full path, e.g.
    `https://blockchain.info/balance` or `…/api/v3/simple/price`)."""
    parts = urlsplit(url or "")
    return "%s://%s" % (parts.scheme, parts.netloc)

_TIMEOUT = 20


def _timed(fn):
    t0 = time.time()
    try:
        detail = fn()
        return {"ok": True, "ms": int((time.time() - t0) * 1000),
                "message": "", "detail": detail or {}}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "ms": int((time.time() - t0) * 1000),
                "message": _explain(e), "detail": {}}


def _explain(exc):
    """Provider wording over a bare HTTP status."""
    resp = getattr(exc, "response", None)
    if resp is not None:
        body = ""
        try:
            data = resp.json()
            if isinstance(data, dict):
                for key in ("msg", "message", "error", "error_message", "description", "detail"):
                    if data.get(key):
                        body = str(data[key])
                        break
                if not body and data.get("code") is not None:
                    body = "code %s" % data["code"]
            elif isinstance(data, list) and data and isinstance(data[0], dict):
                body = str(data[0].get("msg") or data[0].get("error") or "")
        except Exception:  # noqa: BLE001
            body = (getattr(resp, "text", "") or "")[:160]
        return "%s (HTTP %s)" % (body or type(exc).__name__, resp.status_code)
    text = str(exc)
    return text if text else type(exc).__name__


def _first_wallet(wtype):
    """An address to probe with: the user's own first wallet of that type."""
    from . import walletstore
    for w in walletstore.all_wallets():
        if w.get("type") == wtype and w.get("address"):
            return w["address"]
    return None


# ---------------------------------------------------------------- CEX accounts
def test_cex(account):
    """Read the account with the same fetcher the refresh uses.

    A full read is the honest test: a key can pass an auth probe and still fail on a
    sub-account (Binance futures, OKX funding, Bitget mix) that the refresh needs.
    """
    def run():
        ex = str(account.get("exchange") or "").lower()
        if ex not in cex.EXCHANGES:
            raise ValueError("unknown exchange %r" % ex)
        res = cex.fetch_cex_accounts([dict(account, enabled=True)], {})[0]
        if res["error"]:
            raise RuntimeError(res["error"])
        return {"total_usd": res["total_usd"], "assets": len(res["rows"]),
                "notes": res.get("notes") or [],
                "top": [{"symbol": r["symbol"], "usd": round(r["usd"], 2)}
                        for r in sorted(res["rows"], key=lambda x: -x["usd"])[:5]]}
    return _timed(run)


# --------------------------------------------------------------------- DeBank
def test_debank(cfg):
    def run():
        provs = [p for p in cfg.get("providers", []) if p.get("enabled", True)]
        if not provs:
            raise ValueError("no enabled provider")
        tried = []
        for p in provs:
            base = (p.get("base_url") or "").rstrip("/")
            key = (p.get("key") or "").strip()
            headers = {"AccessKey": key} if key else {}
            try:
                d = http_get_json(base + "/chain/list", headers=headers, timeout=_TIMEOUT, retries=0)
                chains = ((d or {}).get("data") or {}).get("chains") or []
                tried.append({"provider": p["name"], "chains": len(chains), "key_used": bool(key)})
                if not chains:
                    raise RuntimeError("no chains in the response")
            except Exception as e:  # noqa: BLE001
                tried.append({"provider": p["name"], "error": _explain(e)})
        ok = [t for t in tried if "chains" in t]
        if not ok:
            raise RuntimeError("; ".join("%s: %s" % (t["provider"], t.get("error")) for t in tried))
        return {"providers": tried}
    return _timed(run)


def test_chain_list_url(cfg):
    def run():
        d = http_get_json(cfg["chain_list_url"], timeout=_TIMEOUT, retries=0)
        chains = ((d or {}).get("data") or {}).get("chains") or []
        if not chains:
            raise RuntimeError("the endpoint answered without a chain list")
        return {"chains": len(chains)}
    return _timed(run)


def test_etherscan(cfg):
    def run():
        key = (cfg.get("api_key") or "").strip()
        addr = _first_wallet("evm")
        if not addr:
            raise ValueError("add an EVM wallet first — the probe needs an address")
        from . import etherscan as eth
        d = http_get_json(eth.V2, params={
            "chainid": eth.CHAINS["eth"][0], "module": "account", "action": "balance",
            "address": addr, "tag": "latest", "apikey": key}, timeout=_TIMEOUT, retries=0)
        if str(d.get("status")) != "1":
            raise RuntimeError(str(d.get("result") or d.get("message") or "rejected"))
        return {"balance_wei": d.get("result"), "key_used": bool(key)}
    return _timed(run)


# ------------------------------------------------------------------ public APIs
_PROBE_PATH = {
    "koios": ("GET", "/api/v1/tip"),
    "blockcypher": ("GET", "/v1/doge/main"),
    "blockchain.info": ("GET", "/q/getblockcount"),
    "mempool.space": ("GET", "/api/blocks/tip/height"),
    "coingecko": ("GET", "/api/v3/ping"),
    "dexscreener": ("GET", "/latest/dex/search"),
    "binance-prices": ("GET", "/api/v3/ticker/price"),
    "binance": ("GET", "/api/v3/ticker/price"),
    "coinbase": ("GET", "/v2/exchange-rates"),
    "okx": ("GET", "/api/v5/market/ticker"),
    "okx-prices": ("GET", "/api/v5/market/ticker"),
    "hyperliquid": ("POST", "/info"),
}


def test_provider(name, url, params=None):
    def run():
        if name not in _PROBE_PATH:
            raise ValueError("no probe for %r" % name)
        method, path = _PROBE_PATH[name]
        target = _origin(url) + path
        if name == "koios":
            d = http_get_json(target, timeout=_TIMEOUT, retries=0)
            return {"tip": (d or [{}])[0].get("abs_slot") if isinstance(d, list) else d}
        if name == "blockcypher":
            d = http_get_json(target, timeout=_TIMEOUT, retries=0)
            return {"height": d.get("height"), "name": d.get("name")}
        if name in ("blockchain.info", "mempool.space"):
            return {"height": http_get_json(target, timeout=_TIMEOUT, retries=0)}
        if name == "coingecko":
            d = http_get_json(target, timeout=_TIMEOUT, retries=0)
            return {"gecko_says": (d or {}).get("gecko_says")}
        if name == "dexscreener":
            d = http_get_json(target, params={"q": "SOL"}, timeout=_TIMEOUT, retries=0)
            return {"pairs": len((d or {}).get("pairs") or [])}
        if name in ("binance-prices", "binance"):
            d = http_get_json(target, params={"symbol": "BTCUSDT"}, timeout=_TIMEOUT, retries=0)
            return {"BTCUSDT": (d or {}).get("price")}
        if name == "coinbase":
            d = http_get_json(target, params={"currency": "BTC"}, timeout=_TIMEOUT, retries=0)
            return {"BTC/USD": ((d or {}).get("data") or {}).get("rates", {}).get("USD")}
        if name in ("okx", "okx-prices"):
            d = http_get_json(target, params={"instId": "BTC-USDT"}, timeout=_TIMEOUT, retries=0)
            return {"last": (((d or {}).get("data") or [{}])[0]).get("last")}
        d = http_post_json(target, json_body={"type": "meta"}, timeout=_TIMEOUT, retries=0)
        return {"universe": len((d or {}).get("universe") or [])}
    return _timed(run)


def test_solana_rpc(url):
    def run():
        d = http_post_json(url, json_body={"jsonrpc": "2.0", "id": 1, "method": "getHealth"},
                           timeout=_TIMEOUT, retries=0)
        if (d or {}).get("error"):
            raise RuntimeError(str(d["error"].get("message") or d["error"]))
        return {"health": (d or {}).get("result")}
    return _timed(run)


def test_birdeye(cfg):
    def run():
        key = (cfg.get("key") or "").strip()
        if not key:
            raise ValueError("no API key configured")
        d = http_get_json(_origin(cfg.get("url")) + "/defi/price",
                          params={"address": "So11111111111111111111111111111111111111112"},
                          headers={"X-API-KEY": key, "accept": "application/json"},
                          timeout=_TIMEOUT, retries=0)
        if (d or {}).get("success") is False:
            raise RuntimeError(str(d.get("message") or "rejected"))
        return {"value": ((d or {}).get("data") or {}).get("value")}
    return _timed(run)


def test_spl_prices(cfg):
    """The SPL price providers are ordinary HTTP providers with a key."""
    provs = [p for p in (cfg.get("providers") or []) if p.get("enabled", True)]
    if not provs:
        return {"ok": False, "ms": 0, "message": "no enabled provider", "detail": {}}
    name = provs[0]["name"]
    url = provs[0]["url"]
    return test_provider("dexscreener" if name == "dexscreener" else "coingecko", url)


# ------------------------------------------------------------------- dispatch
def run_test(target, name=None, url=None):
    """`target` names what the row is; the config is read fresh from disk."""
    cfg = sources.load()
    t = str(target or "")
    if t == "cex":
        acc = next((a for a in cfg.get("cex", {}).get("accounts", [])
                    if a.get("name") == name), None)
        if acc is None:
            return {"ok": False, "ms": 0, "message": "no such account: %s" % name, "detail": {}}
        return test_cex(acc)
    if t == "debank":
        return test_debank(cfg.get("debank", {}))
    if t == "debank-chain-list":
        return test_chain_list_url(cfg.get("debank", {}))
    if t == "etherscan":
        return test_etherscan(cfg.get("etherscan", {}))
    if t == "solana-rpc":
        return test_solana_rpc(url)
    if t == "birdeye":
        return test_birdeye(cfg.get("solana", {}).get("birdeye", {}))
    if t == "spl-prices":
        return test_spl_prices(cfg.get("solana", {}).get("spl_prices", {}))
    if t in ("btc", "doge", "ada", "prices", "hyperliquid"):
        provs = [p for p in cfg.get(t, {}).get("providers", []) if p.get("enabled", True)]
        if not provs:
            return {"ok": False, "ms": 0, "message": "no enabled provider", "detail": {}}
        p = provs[0]
        if name:
            p = next((x for x in provs if x.get("name") == name), p)
        url = url or p.get("url")
        probe = p.get("name")
        if t == "prices":
            probe = {"binance-prices": "binance", "okx-prices": "okx"}.get(probe, probe)
        elif t == "hyperliquid":
            probe = "hyperliquid"
        return test_provider(probe, url)
    return {"ok": False, "ms": 0, "message": "unknown target: %s" % t, "detail": {}}
