# -*- coding: utf-8 -*-
"""Configurable API sources with multi-provider failover.

Every external API (URLs + keys) lives in portfolio_sources.json
(auto-generated with defaults on first run; edits take effect without
restart — the file is re-read when it changes).

Each source may define several providers tried in order:
  - an enabled provider is skipped when it throws or returns an empty result,
    and the next enabled provider is used automatically;
  - the last working provider per source is remembered, so subsequent calls
    start from it and only fall back when it fails again.

Env overrides (highest priority, applied at load time):
  DEBANK_API_KEY, BIRDEYE_API_KEY, COINGECKO_API_KEY, SOLANA_RPC
"""
import json
import os
import threading

from . import config, profiles

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

_DEFAULTS = {
    "debank": {
        "enabled": True,
        "chain_list_url": "https://api.debank.com/chain/list",
        "providers": [
            {"name": "debank-pro", "type": "pro", "key": "",
             "base_url": "https://pro-openapi.debank.com", "paid": True, "enabled": True},
            {"name": "debank-public", "type": "public", "key": "",
             "base_url": "https://api.debank.com", "paid": False, "enabled": True},
        ],
    },
    "btc": {
        "enabled": True,
        "providers": [
            {"name": "blockchain.info", "type": "batch",
             "url": "https://blockchain.info/balance", "enabled": True},
            {"name": "mempool.space", "type": "per_address",
             "url": "https://mempool.space/api/address/{addr}", "enabled": True},
        ],
    },
    "prices": {
        "enabled": True,
        "providers": [
            {"name": "coingecko", "type": "batch",
             "url": "https://api.coingecko.com/api/v3/simple/price", "key": "", "enabled": True},
            {"name": "binance", "type": "batch",
             "url": "https://api.binance.com/api/v3/ticker/price", "enabled": True},
            {"name": "coinbase", "type": "per_pair",
             "url": "https://api.coinbase.com/v2/prices/{pair}-USD/spot", "enabled": True},
            {"name": "okx", "type": "per_pair",
             "url": "https://www.okx.com/api/v5/market/ticker", "enabled": True},
        ],
    },
    "solana": {
        "enabled": True,
        "rpc": [
            {"name": "mainnet-beta", "url": "https://api.mainnet-beta.solana.com", "enabled": True},
            {"name": "ankr-public", "url": "https://rpc.ankr.com/solana", "enabled": True},
        ],
        "spl_prices": {
            "providers": [
                {"name": "dexscreener", "type": "batch",
                 "url": "https://api.dexscreener.com/latest/dex/tokens/{mints}", "enabled": True},
                {"name": "coingecko", "type": "per_mint",
                 "url": "https://api.coingecko.com/api/v3/simple/token_price/solana",
                 "key": "", "enabled": True},
            ],
        },
        "birdeye": {
            "enabled": False,
            "key": "",
            "url": "https://public-api.birdeye.so/defi/wallet_tokens",
        },
    },
    "hyperliquid": {
        "enabled": True,
        "providers": [
            {"name": "api.hyperliquid.xyz", "url": "https://api.hyperliquid.xyz/info", "enabled": True},
            {"name": "hyperliquid-api.mainnet", "url": "https://hyperliquid-api.mainnet.hyperliquid.xyz/info", "enabled": True},
        ],
    },
    "etherscan": {
        "enabled": True,
        "api_key": "",
        "chains": ["eth"],
    },
    "cex": {
        "enabled": True,
        "accounts": [],
    },
}

_cache = {"mtime": None, "data": None}
_last_ok = {}          # source_key -> provider index of last success
_lock = threading.RLock()


def sources_file():
    return profiles.sources_file()


def _deep_merge(base, override):
    out = dict(base)
    for k, v in (override or {}).items():
        if isinstance(v, dict) and isinstance(base.get(k), dict):
            out[k] = _deep_merge(base[k], v)
        else:
            out[k] = v
    return out


def load(force=False):
    """Merged config; re-reads the file whenever it changes on disk."""
    global _cache
    with _lock:
        try:
            mtime = os.path.getmtime(profiles.sources_file()) if os.path.exists(profiles.sources_file()) else None
        except OSError:
            mtime = None
        if force or _cache["data"] is None or _cache["mtime"] != mtime:
            user = {}
            if os.path.exists(profiles.sources_file()):
                try:
                    with open(profiles.sources_file(), "r", encoding="utf-8") as f:
                        user = json.load(f) or {}
                except Exception:  # noqa: BLE001
                    user = {}
            data = _deep_merge(_DEFAULTS, user)
            _normalize(data)
            _apply_env(data)
            _cache = {"mtime": mtime, "data": data}
        return _cache["data"]


def _normalize(data):
    """Backward compatibility: old debank {key, base_url} -> pro provider."""
    db = data.get("debank") or {}
    if not db.get("providers"):
        db["providers"] = [
            {"name": "debank-pro", "type": "pro",
             "key": db.get("key") or "",
             "base_url": db.get("base_url") or "https://pro-openapi.debank.com",
             "paid": True, "enabled": True},
        ]
    # if the top-level key holds a value the pro provider lacks, copy it over
    top_key = db.get("key") or ""
    if top_key:
        for p in db.get("providers", []):
            if p.get("type") == "pro" and not p.get("key"):
                p["key"] = top_key


def _apply_env(data):
    env = os.environ
    if env.get("DEBANK_API_KEY"):
        data["debank"]["key"] = env["DEBANK_API_KEY"].strip()
        for p in data["debank"].get("providers", []):
            if p.get("type") == "pro":
                p["key"] = env["DEBANK_API_KEY"].strip()
                p["enabled"] = True
    if env.get("BIRDEYE_API_KEY"):
        bd = data["solana"]["birdeye"]
        bd["key"] = env["BIRDEYE_API_KEY"].strip()
        bd["enabled"] = True
    if env.get("COINGECKO_API_KEY"):
        for p in data["prices"]["providers"] + data["solana"]["spl_prices"]["providers"]:
            if p.get("name") == "coingecko":
                p["key"] = env["COINGECKO_API_KEY"].strip()
    if env.get("SOLANA_RPC"):
        data["solana"]["rpc"].insert(0, {"name": "env", "url": env["SOLANA_RPC"].strip(), "enabled": True})
    # CEX account env overrides: BINANCE_API_KEY/SECRET, BYBIT_API_KEY/SECRET, BACKPACK_API_KEY/SECRET
    cex_accounts = data.get("cex", {}).get("accounts", [])
    for ex, envk, envs in (("binance", "BINANCE_API_KEY", "BINANCE_API_SECRET"),
                           ("bybit", "BYBIT_API_KEY", "BYBIT_API_SECRET"),
                           ("backpack", "BACKPACK_API_KEY", "BACKPACK_API_SECRET")):
        if env.get(envk) and env.get(envs):
            found = next((a for a in cex_accounts if a.get("exchange") == ex), None)
            entry = {"name": f"{ex}_env", "exchange": ex,
                     "key": env[envk].strip(), "secret": env[envs].strip(), "enabled": True}
            if found:
                found.update(entry)
            else:
                cex_accounts.append(entry)


def ensure_file():
    """Write the default config file if it does not exist yet."""
    if not os.path.exists(profiles.sources_file()):
        with _lock:
            os.makedirs(os.path.dirname(profiles.sources_file()), exist_ok=True)
            with open(profiles.sources_file(), "w", encoding="utf-8") as f:
                json.dump(_DEFAULTS, f, ensure_ascii=False, indent=2)


def save(cfg):
    """Persist a user-supplied config.

    The written file is always the full merged config (defaults + previous
    file + this update), so partial updates never leave the file incomplete.
    """
    with _lock:
        current = {}
        if os.path.exists(profiles.sources_file()):
            try:
                with open(profiles.sources_file(), "r", encoding="utf-8") as f:
                    current = json.load(f) or {}
            except Exception:  # noqa: BLE001
                current = {}
        merged = _deep_merge(_DEFAULTS, _deep_merge(current, cfg if isinstance(cfg, dict) else {}))
        os.makedirs(os.path.dirname(profiles.sources_file()), exist_ok=True)
        with open(profiles.sources_file(), "w", encoding="utf-8") as f:
            json.dump(merged, f, ensure_ascii=False, indent=2)
        load(force=True)


def get_source(name):
    return load().get(name) or {}


def provider_order(source_key, providers):
    """Enabled providers, last-successful first (failover-aware order)."""
    with _lock:
        last = _last_ok.get(source_key)
    enabled = [(i, p) for i, p in enumerate(providers) if p.get("enabled", True)]
    if last is not None:
        enabled.sort(key=lambda ip: (0 if ip[0] == last else 1, ip[0]))
    return [p for _, p in enabled]


def try_providers(source_key, providers, fetch_one, nonempty=False):
    """Run fetch_one(p) over enabled providers until one succeeds.

    nonempty=True treats a falsy result (None/{}[]) as failure and keeps trying.
    Returns (result, provider); raises the last error when all providers fail.
    """
    last_err = None
    for p in provider_order(source_key, providers):
        try:
            result = fetch_one(p)
            if nonempty and not result:
                raise ValueError("empty result from provider")
            with _lock:
                _last_ok[source_key] = providers.index(p)
            return result, p
        except Exception as e:  # noqa: BLE001
            last_err = e
            continue
    if last_err is None:
        raise RuntimeError(f"source '{source_key}': no enabled provider")
    raise last_err


def reset_failover():
    with _lock:
        _last_ok.clear()


def failover_state():
    """{source_key: index of last successful provider} for display."""
    with _lock:
        return dict(_last_ok)
