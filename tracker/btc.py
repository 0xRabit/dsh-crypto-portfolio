# -*- coding: utf-8 -*-
"""Bitcoin balance fetcher — configurable providers with automatic failover.

Providers are defined in portfolio_sources.json -> "btc" -> "providers":
  - type "batch": one call for all remaining addresses (e.g. blockchain.info)
  - type "per_address": one call per address (e.g. mempool.space, {addr} in url)

Providers are tried in order; results from later providers fill the addresses
the earlier ones could not resolve.
"""
from . import sources
from .api import http_get_json


def fetch_btc_satoshis(addresses):
    """Return {address: final_balance_in_satoshis} (None when unresolvable)."""
    addresses = [a for a in addresses if a]
    if not addresses:
        return {}
    cfg = sources.get_source("btc")
    if not cfg.get("enabled", True):
        return {a: None for a in addresses}

    out = {}
    remaining = list(addresses)

    def fetch_one(provider, missing):
        if provider.get("type") == "per_address":
            res = {}
            for a in missing:
                try:
                    d = http_get_json(provider["url"].format(addr=a), timeout=30)
                    cs = d.get("chain_stats", {}) or {}
                    ms = d.get("mempool_stats", {}) or {}
                    res[a] = (cs.get("funded_txo_sum", 0) - cs.get("spent_txo_sum", 0)
                              + ms.get("funded_txo_sum", 0) - ms.get("spent_txo_sum", 0))
                except Exception:  # noqa: BLE001
                    res[a] = None
            return res
        # default: batch
        data = http_get_json(provider["url"],
                             params={"active": "|".join(missing)}, timeout=25)
        return {a: (data.get(a) or {}).get("final_balance") for a in missing}

    for provider in sources.provider_order("btc", cfg.get("providers", [])):
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
