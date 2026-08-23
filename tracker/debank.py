# -*- coding: utf-8 -*-
"""EVM wallet fetcher via DeBank (multi-chain).

Two providers are configured in portfolio_sources.json -> "debank" -> "providers":
  - debank-pro    (type "pro",    AccessKey header, pro-openapi.debank.com, PAID)
  - debank-public (type "public", keyless,          api.debank.com,         FREE, rate-limited)

They are tried in order with automatic failover: if the paid provider fails
(e.g. invalid key / quota), the free public API is used. The public API is
heavily rate-limited, so it fetches chains sequentially with spacing + retries.
"""
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

from . import config, sources
from .api import http_get_json
from .blacklist import filter_rows

_chain_cache = None
_chain_lock = threading.Lock()


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


# --------------------------------------------------------------------------
# per-provider chain fetch
# --------------------------------------------------------------------------

def _fetch_pro_chain(provider, address, chain_id, session):
    headers = {"AccessKey": provider.get("key"), "accept": "application/json"}
    return http_get_json(
        f"{provider['base_url']}/v1/user/token_list",
        headers=headers,
        params={"id": address, "chain_id": chain_id, "is_all": "true"},
        session=session,
    )


def _fetch_public_chain(provider, address, chain_id):
    # free public API: keyless but aggressively rate-limited -> spacing + retries
    last = None
    for attempt in range(3):
        try:
            return http_get_json(
                f"{provider['base_url']}/token/balance_list",
                params={"user": address, "chain_id": chain_id, "is_all": "true"},
                timeout=20, retries=0,
            )
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(2 + attempt * 2)
    raise last


def _fetch_with_provider(provider, wallet, chains, max_workers):
    """Fetch all chains for one wallet with a given provider."""
    address = wallet["address"]
    ptype = provider.get("type", "pro")
    results = {}
    errors = []
    if ptype == "public":
        # sequential, rate-limit friendly
        for cid in chains:
            try:
                results[cid] = _fetch_public_chain(provider, address, cid)
            except Exception as e:  # noqa: BLE001
                errors.append(cid)
            time.sleep(0.35)
    else:
        workers = max_workers or config.MAX_EVM_WORKERS
        sessions = [requests.Session() for _ in range(workers)]

        def work(idx_chain):
            idx, cid = idx_chain
            try:
                tokens = _fetch_pro_chain(provider, address, cid, sessions[idx % workers])
                return cid, tokens
            except Exception as e:  # noqa: BLE001
                return cid, {"__error__": f"{type(e).__name__}: {e}"}

        with ThreadPoolExecutor(max_workers=workers) as ex:
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


def fetch_evm_wallet(wallet, api_key=None, chains=None, max_workers=None):
    """Fetch all token holdings of one EVM wallet across every DeBank chain,
    trying configured providers in order (paid pro first, free public fallback)."""
    cfg = sources.get_source("debank")
    if not cfg.get("enabled", True):
        return {"wallet": wallet["name"], "address": wallet["address"], "type": "evm",
                "total_usd": 0.0, "chain_totals": {}, "tokens": [], "chain_errors": []}
    providers = cfg.get("providers") or []
    chains = chains or chain_ids()
    allowed = cfg.get("chains")
    if allowed:
        if isinstance(allowed, str):
            allowed = [c.strip() for c in allowed.split(",") if c.strip()]
        chains = [c for c in chains if c in allowed]
    max_workers = max_workers or config.MAX_EVM_WORKERS

    def fetch_one(provider):
        return _fetch_with_provider(provider, wallet, chains, max_workers)

    try:
        result, used = sources.try_providers("debank", providers, fetch_one)
        result["provider_used"] = used.get("name", "")
        return result
    except Exception as e:  # noqa: BLE001
        return {"wallet": wallet["name"], "address": wallet["address"], "type": "evm",
                "total_usd": 0.0, "chain_totals": {}, "tokens": [],
                "chain_errors": ["all-providers"], "error": f"{type(e).__name__}: {e}"}
