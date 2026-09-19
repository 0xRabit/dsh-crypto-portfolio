# -*- coding: utf-8 -*-
"""Cardano (ADA) balance fetcher — Koios API (free, no key).

Providers are defined in portfolio_sources.json -> "ada" -> "providers".
Koios exposes a batch POST endpoint that answers many addresses in one call:
  POST {"_addresses": [...]} -> [{"address": ..., "balance": "<lovelace>"}]

A stake address (starts with "stake") is answered by the account endpoint:
  POST {"_stake_addresses": [...]} -> [{"stake_address": ..., "total_balance": "<lovelace>"}]

Amounts come back as strings in lovelace (1 ADA = 1_000_000 lovelace).
"""
from . import sources
from .api import http_post_json

SRC = "ada"
LOVELACE = 1_000_000

ADDR_URL = "https://api.koios.rest/api/v1/address_info"
STAKE_URL = "https://api.koios.rest/api/v1/account_info"


def _is_stake(addr):
    return str(addr or "").lower().startswith("stake")


def fetch_ada_lovelace(addresses):
    """Return {address: balance_in_lovelace} (None when unresolvable)."""
    addresses = [a for a in addresses if a]
    if not addresses:
        return {}
    cfg = sources.get_source(SRC)
    if not cfg.get("enabled", True):
        return {a: None for a in addresses}

    out = {}
    remaining = list(addresses)

    def fetch_one(provider, missing):
        # payment addresses and stake addresses use different Koios endpoints
        pay = [a for a in missing if not _is_stake(a)]
        stake = [a for a in missing if _is_stake(a)]
        res = {}
        if pay:
            d = http_post_json(provider.get("url") or ADDR_URL,
                               json_body={"_addresses": pay}, timeout=30)
            for item in d or []:
                bal = item.get("balance")
                if bal is not None:
                    res[item.get("address")] = int(bal)
        if stake:
            d = http_post_json(provider.get("stake_url") or STAKE_URL,
                               json_body={"_stake_addresses": stake}, timeout=30)
            for item in d or []:
                bal = item.get("total_balance")
                if bal is not None:
                    res[item.get("stake_address")] = int(bal)
        for a in missing:
            res.setdefault(a, None)
        return res

    for provider in sources.provider_order(SRC, cfg.get("providers", [])):
        try:
            res = fetch_one(provider, remaining)
        except Exception:  # noqa: BLE001
            continue
        for a, v in res.items():
            if v is not None:
                out[a] = v
        remaining = [a for a in remaining if a not in out]
        if not remaining:
            break
    for a in remaining:
        out[a] = None
    return out
