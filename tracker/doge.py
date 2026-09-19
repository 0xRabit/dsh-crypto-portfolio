# -*- coding: utf-8 -*-
"""Dogecoin balance fetcher — configurable providers with automatic failover.

Providers are defined in portfolio_sources.json -> "doge" -> "providers":
  - type "per_address": one call per address (e.g. BlockCypher, {addr} in url)

BlockCypher returns the confirmed balance as ``final_balance`` in koinu
(1 DOGE = 100_000_000 koinu). Providers are tried in order; results from later
providers fill the addresses the earlier ones could not resolve.
"""
from . import sources
from .api import http_get_json

SRC = "doge"
KOINU = 100_000_000


def fetch_doge_koinu(addresses):
    """Return {address: final_balance_in_koinu} (None when unresolvable)."""
    addresses = [a for a in addresses if a]
    if not addresses:
        return {}
    cfg = sources.get_source(SRC)
    if not cfg.get("enabled", True):
        return {a: None for a in addresses}

    out = {}
    remaining = list(addresses)

    def fetch_one(provider, missing):
        res = {}
        for a in missing:
            try:
                d = http_get_json(provider["url"].format(addr=a), timeout=30)
                # BlockCypher: final_balance (koinu). Be tolerant of other shapes.
                bal = d.get("final_balance")
                if bal is None:
                    bal = d.get("balance")
                res[a] = int(bal) if bal is not None else None
            except Exception:  # noqa: BLE001
                res[a] = None
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
