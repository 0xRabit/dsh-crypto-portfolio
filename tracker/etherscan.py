# -*- coding: utf-8 -*-
"""Etherscan (classic EVM explorer) — native-coin balance source via API V2.

Free API keys support Ethereum only (chainid=1); other chains need a paid plan.

This is a *reference* source: it fetches native balances per EVM wallet and
stores the readout (per chain) under the profile's status.json, surfaced in the
Sources panel. It does NOT merge into token tables / totals, so it never
double-counts the same native coin that DeBank already reports.
"""
from . import sources
from .api import http_get_json

V2 = "https://api.etherscan.io/v2/api"
SRC = "etherscan"

# our chain id -> (etherscan chainid, native symbol)
CHAINS = {
    "eth": (1, "ETH"), "bsc": (56, "BNB"), "matic": (137, "POL"),
    "op": (10, "ETH"), "arb": (42161, "ETH"), "base": (8453, "ETH"),
    "xdai": (100, "xDai"), "avax": (43114, "AVAX"), "ftm": (250, "FTM"),
}


def etherscan_cfg():
    c = sources.get_source("etherscan")
    if not c.get("enabled", True):
        return None
    key = (c.get("api_key") or "").strip()
    if not key:
        return None
    chains = c.get("chains") or ["eth"]
    if isinstance(chains, str):
        chains = [x.strip() for x in chains.split(",") if x.strip()]
    return {"api_key": key, "chains": [c for c in chains if c in CHAINS]}


def _price(native, symbol):
    return {"ETH": native.get("ethereum")}.get(symbol) or 0.0


def _balance(api_key, chainid, address):
    d = http_get_json(
        V2, params={"chainid": chainid, "module": "account", "action": "balance",
                    "address": address, "tag": "latest", "apikey": api_key},
        timeout=20, retries=2)
    if str(d.get("status")) != "1":
        return None
    try:
        return int(d.get("result"))
    except (TypeError, ValueError):
        return None


def fetch_etherscan(wallets, native):
    """Returns (detail, errors).

    detail: {wallet_name: [{chain, symbol, amount, price, usd, address}]}
    errors: list of "chain@chainid" that failed.
    """
    cfg = etherscan_cfg()
    if not cfg:
        return {}, ["etherscan disabled / no api key"]
    detail = {}
    errors = []
    for w in wallets:
        rows = []
        for cid in cfg["chains"]:
            chainid, sym = CHAINS[cid]
            wei = _balance(cfg["api_key"], chainid, w["address"])
            if wei is None:
                errors.append(f"{w['name']}:{cid}@{chainid}")
                continue
            amount = wei / 1e18
            if amount <= 0:
                continue
            price = _price(native, sym)
            rows.append({"chain": cid, "symbol": sym, "amount": amount,
                         "price": price, "usd": round(amount * price, 6),
                         "address": w["address"]})
        if rows:
            detail[w["name"]] = rows
    return detail, errors
