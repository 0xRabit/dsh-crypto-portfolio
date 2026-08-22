# -*- coding: utf-8 -*-
"""EVM wallet fetcher via DeBank Open API (multi-chain).

Iterates every chain in DeBank's chain list so that positions on as many
protocols/chains as possible are captured. DeBank's token_list already prices
all tokens (including protocol positions such as aTokens, LP tokens, staking
positions), so no extra price lookup is needed for EVM assets.
"""
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

from . import config, sources
from .api import http_get_json
from .blacklist import filter_rows

_chain_cache = None
_chain_lock = threading.Lock()


def _base_url():
    cfg = sources.get_source("debank")
    return cfg.get("base_url") or "https://pro-openapi.debank.com"


def _chain_list_url():
    cfg = sources.get_source("debank")
    return cfg.get("chain_list_url") or "https://api.debank.com/chain/list"


def get_chains(force=False):
    """Return the full DeBank chain list (id + name), cached."""
    global _chain_cache
    with _chain_lock:
        if _chain_cache is None or force:
            data = http_get_json(_chain_list_url(), timeout=30)
            _chain_cache = data.get("data", {}).get("chains", [])
        return list(_chain_cache)


def chain_ids():
    return [c["id"] for c in get_chains()]


def chain_names():
    return {c["id"]: c.get("name", c["id"]) for c in get_chains()}


def _fetch_chain_tokens(api_key, base_url, address, chain_id, session):
    headers = {"AccessKey": api_key, "accept": "application/json"}
    data = http_get_json(
        f"{base_url}/v1/user/token_list",
        headers=headers,
        params={"id": address, "chain_id": chain_id, "is_all": "true"},
        session=session,
    )
    return data


def fetch_evm_wallet(wallet, api_key=None, chains=None, max_workers=None):
    """Fetch all token holdings of one EVM wallet across every DeBank chain.

    Returns dict:
      {wallet, address, type, total_usd, chain_totals: {chain: usd},
       tokens: [row...], chain_errors: [chain...]}
    """
    cfg = sources.get_source("debank")
    if not cfg.get("enabled", True):
        return {"wallet": wallet["name"], "address": wallet["address"], "type": "evm",
                "total_usd": 0.0, "chain_totals": {}, "tokens": [], "chain_errors": []}
    api_key = api_key or cfg.get("key") or config.DEBANK_API_KEY
    base_url = cfg.get("base_url") or "https://pro-openapi.debank.com"
    max_workers = max_workers or config.MAX_EVM_WORKERS
    chains = chains or chain_ids()
    address = wallet["address"]

    sessions = [requests.Session() for _ in range(max_workers)]
    results = {}
    errors = []

    def work(idx_chain):
        idx, cid = idx_chain
        try:
            tokens = _fetch_chain_tokens(api_key, base_url, address, cid, sessions[idx % max_workers])
            return cid, tokens
        except Exception as e:  # noqa: BLE001
            return cid, {"__error__": f"{type(e).__name__}: {e}"}

    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futs = [ex.submit(work, (i, c)) for i, c in enumerate(chains)]
        for f in as_completed(futs):
            cid, tokens = f.result()
            results[cid] = tokens

    rows = []
    for cid, tokens in results.items():
        if isinstance(tokens, dict) and tokens.get("__error__"):
            errors.append(cid)
            continue
        for t in tokens or []:
            amount = t.get("amount") or 0
            price = t.get("price") or 0
            usd = amount * price
            symbol = (t.get("symbol") or t.get("optimized_symbol")
                      or t.get("display_symbol") or t.get("name") or "?")
            rows.append({
                "wallet": wallet["name"],
                "chain": cid,
                "symbol": symbol,
                "name": t.get("name") or "",
                "amount": amount,
                "price": price,
                "usd": round(usd, 6),
                "logo": t.get("logo_url") or "",
                "token_id": t.get("id") or "",
                "protocol_id": t.get("protocol_id") or "",
                "is_verified": bool(t.get("is_verified")),
            })

    # exclude blacklisted (phishing/fake) tokens, then recompute per-chain totals
    rows = filter_rows(rows)
    chain_totals = {}
    for r in rows:
        chain_totals[r["chain"]] = round(chain_totals.get(r["chain"], 0.0) + r["usd"], 2)

    return {
        "wallet": wallet["name"],
        "address": address,
        "type": "evm",
        "total_usd": round(sum(chain_totals.values()), 2),
        "chain_totals": chain_totals,
        "tokens": rows,
        "chain_errors": errors,
    }
