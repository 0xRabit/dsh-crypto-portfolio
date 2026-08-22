# -*- coding: utf-8 -*-
"""Solana wallet fetcher — configurable RPC nodes + SPL price providers.

- RPC nodes: portfolio_sources.json -> "solana" -> "rpc" (tried in order,
  automatic failover; last working node remembered)
- SPL prices: "solana" -> "spl_prices" -> "providers" (dexscreener / coingecko)
- Optional Birdeye wallet pricing: "solana" -> "birdeye" (needs free API key)
"""
import time

from . import sources
from .api import http_get_json, http_post_json

TOKEN_PROGRAMS = (
    "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA",   # SPL Token
    "TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb",   # Token-2022
)
WSOL = "So11111111111111111111111111111111111111112"


def _rpc(method, params):
    cfg = sources.get_source("solana")
    providers = cfg.get("rpc", [])
    if not cfg.get("enabled", True):
        raise RuntimeError("solana source disabled")

    def fetch_one(node):
        d = http_post_json(node["url"],
                           json_body={"jsonrpc": "2.0", "id": 1,
                                      "method": method, "params": params},
                           timeout=30, retries=1)
        if "error" in d:
            raise RuntimeError(f"solana rpc {method}: {d['error']}")
        return d.get("result")

    result, _ = sources.try_providers("solana_rpc", providers, fetch_one)
    return result


def fetch_solana_wallet(wallet):
    """SOL lamports + native staked lamports + SPL/Token-2022 accounts.

    Returns {wallet, address, type, sol_lamports, staked_lamports,
             tokens: [{mint, amount, decimals}]}
    """
    address = wallet["address"]
    bal = _rpc("getBalance", [address]) or {}
    sol_lamports = bal.get("value", 0)
    staked_lamports = fetch_native_staked_sol(address)

    accounts = {}
    for program in TOKEN_PROGRAMS:
        res = _rpc("getTokenAccountsByOwner",
                   [address, {"programId": program}, {"encoding": "jsonParsed"}]) or {}
        for item in res.get("value", []):
            parsed = (item.get("account", {}).get("data", {}) or {}).get("parsed")
            if not parsed:
                continue
            info = parsed.get("info", {})
            mint = info.get("mint")
            if not mint:
                continue
            amount = (info.get("tokenAmount", {}) or {}).get("uiAmount") or 0
            decimals = (info.get("tokenAmount", {}) or {}).get("decimals") or 0
            if mint not in accounts:
                accounts[mint] = {"mint": mint, "amount": 0.0, "decimals": decimals}
            accounts[mint]["amount"] += amount

    return {
        "wallet": wallet["name"],
        "address": address,
        "type": "sol",
        "sol_lamports": sol_lamports,
        "staked_lamports": staked_lamports,
        "tokens": sorted(accounts.values(), key=lambda t: -t["amount"]),
    }


STAKE_PROGRAM = "Stake11111111111111111111111111111111111111"


def fetch_native_staked_sol(address):
    """Native delegated stake (lamports) for a wallet.

    Uses getProgramAccounts on the Stake program with memcmp filters on the
    staker (offset 12) and withdrawer (offset 44) fields — this also finds
    stake accounts that getParsedStakeAccounts misses (e.g. accounts whose
    authority is the wallet but that were created via staking tools/pools).
    Returns active+activating delegated lamports; 0 when none.
    """
    total = 0
    seen = set()
    for offset in (12, 44):  # staker / withdrawer
        try:
            res = _rpc("getProgramAccounts", [
                STAKE_PROGRAM,
                {"encoding": "jsonParsed",
                 "filters": [{"memcmp": {"offset": offset, "bytes": address}}]},
            ]) or []
        except Exception:  # noqa: BLE001
            continue
        for item in res:
            pubkey = item.get("pubkey")
            if pubkey in seen:
                continue
            seen.add(pubkey)
            parsed = (item.get("account", {}).get("data", {}) or {}).get("parsed")
            if not parsed:
                continue
            if parsed.get("type") != "delegated":
                continue  # initialized / uninitialized accounts carry no stake
            info = parsed.get("info", {})
            delegation = (info.get("stake", {}) or {}).get("delegation", {}) or {}
            amount = int(delegation.get("stake") or 0)
            if amount > 0:
                total += amount
    return total


def birdeye_wallet_prices(address, api_key=None):
    """Optional: Birdeye wallet-token prices (free tier API key).

    Returns ({mint: usd_price}, sol_usd or None), or (None, None) when
    disabled / failed. Enable via portfolio_sources.json -> solana -> birdeye
    (or set BIRDEYE_API_KEY env var).
    """
    cfg = (sources.get_source("solana") or {}).get("birdeye") or {}
    api_key = api_key or cfg.get("key")
    if not cfg.get("enabled", False) or not api_key:
        return None, None
    try:
        d = http_get_json(cfg.get("url", "https://public-api.birdeye.so/defi/wallet_tokens"),
                          params={"wallet": address},
                          headers={"X-API-KEY": api_key, "x-chain": "solana"},
                          timeout=10, retries=0)
        data = (d or {}).get("data") or {}
        prices = {}
        sol_usd = None
        for it in data.get("items") or []:
            mint = (it or {}).get("address")
            px = (it or {}).get("priceUsd")
            if mint and px and float(px) > 0:
                prices[mint] = float(px)
                if mint == WSOL:
                    sol_usd = float(px)
        return prices, sol_usd
    except Exception:  # noqa: BLE001
        return None, None


def get_sol_token_prices(mints, budget=40.0):
    """mint -> usd price via configured providers (dexscreener batch, then
    coingecko per missing mint). A hard time budget keeps rate-limited
    fallbacks from stalling a refresh; unpriced mints stay at 0.
    """
    t0 = time.time()
    mints = [m for m in set(mints) if m]
    out = {}
    cfg = sources.get_source("solana")
    providers = (cfg.get("spl_prices") or {}).get("providers", [])

    for provider in sources.provider_order("solana_spl", providers):
        name = provider.get("name")
        missing = [m for m in mints if m not in out]
        if not missing or time.time() - t0 > budget:
            break
        if name == "dexscreener":
            _fill_dexscreener(provider, missing, out)
        elif name == "coingecko":
            for m in missing:
                if time.time() - t0 > budget:
                    break
                try:
                    headers = {}
                    if provider.get("key"):
                        headers["x-cg-demo-api-key"] = provider["key"]
                    d = http_get_json(provider["url"], headers=headers,
                                      params={"contract_addresses": m,
                                              "vs_currencies": "usd"},
                                      timeout=8, retries=0)
                    v = (d.get(m) or {}).get("usd")
                    if v:
                        out[m] = float(v)
                except Exception:  # noqa: BLE001
                    pass
                time.sleep(0.2)
    return out


def _fill_dexscreener(provider, mints, out):
    for i in range(0, len(mints), 30):
        chunk = mints[i:i + 30]
        try:
            d = http_get_json(provider["url"].format(mints=",".join(chunk)),
                              timeout=15, retries=1)
            best = {}  # mint -> (liquidity, priceUsd)
            for p in (d.get("pairs") or []):
                if p.get("chainId") != "solana":
                    continue
                bt = p.get("baseToken") or {}
                mint = bt.get("address")
                if not mint:
                    continue
                price = p.get("priceUsd")
                if price is None:
                    continue
                liq = (p.get("liquidity") or {}).get("usd") or 0
                if mint in best:
                    if liq > best[mint][0]:
                        best[mint] = (liq, float(price))
                else:
                    best[mint] = (liq, float(price))
            for mint, (_, price) in best.items():
                if price > 0:
                    out[mint] = price
        except Exception:  # noqa: BLE001
            pass
