# -*- coding: utf-8 -*-
"""Hyperliquid native L1 balances via the official public API (free, no key).

DeBank only covers HyperEVM (the EVM side). This fetcher adds the NATIVE L1
ledger, which DeBank does not track:
  - staked HYPE            (info type: delegatorSummary)
  - L1 spot token balances (info type: spotClearinghouseState)
  - perp account equity    (info type: clearinghouseState, USD, if nonzero)

Pricing (Hyperliquid's spot "markPx" is unreliable for non-canonical pairs,
so we use trusted external prices):
  - HYPE  -> external price (CoinGecko/OKX/Coinbase, via prices.get_native_prices)
  - stables (USDC/USDT0/USDE/USDH/...) -> 1.0
  - UBTC/UETH (Unit Bitcoin/Ethereum)  -> BTC/ETH price (approximation)
  - other spot tokens -> amount only, USD 0 (no trustworthy free price source)
"""
from . import sources
from .api import http_post_json

CHAIN = "hyperliquid"

STABLECOINS = {
    "USDC", "USDT", "USDT0", "USDE", "USDH", "FEUSD", "USDXL", "USD",
    "DAI", "PYUSD", "USDY", "USDV", "USDR", "USDF",
}
PEGGED = {"UBTC": "bitcoin", "UETH": "ethereum", "WBTC": "bitcoin", "WETH": "ethereum"}


def _info(payload, timeout=25):
    cfg = sources.get_source("hyperliquid")
    providers = cfg.get("providers", [])
    if not cfg.get("enabled", True):
        raise RuntimeError("hyperliquid source disabled")

    def fetch_one(p):
        return http_post_json(p["url"], json_body=payload, timeout=timeout)

    result, _ = sources.try_providers("hyperliquid", providers, fetch_one)
    return result


def _vault_rows(address, wallet_name):
    """Hyperliquid vault positions (leader vaults the user follows).

    userVaultEquities returns equities in USD; vaultDetails gives the name.
    Rows are USD-valued (amount = equity, price = 1).
    """
    rows = []
    try:
        d = _info({"type": "userVaultEquities", "user": address})
        for v in (d or []):
            addr = v.get("vaultAddress") or ""
            equity = float(v.get("equity") or 0)
            if equity <= 0:
                continue
            name = "Vault"
            try:
                det = _info({"type": "vaultDetails", "vaultAddress": addr})
                name = (det or {}).get("name") or name
            except Exception:  # noqa: BLE001
                pass
            sym = _vault_symbol(name)
            rows.append({
                "wallet": wallet_name, "chain": CHAIN, "symbol": sym,
                "name": f"Hyperliquid Vault · {name} ({addr[:6]}…)",
                "amount": round(equity, 2), "price": 1.0, "usd": round(equity, 6),
                "logo": "", "token_id": f"hl-vault-{addr}",
            })
    except Exception:  # noqa: BLE001
        pass
    return rows


def _vault_symbol(name):
    name = (name or "").strip()
    # "Hyperliquidity Provider (HLP)" -> "HLP"; otherwise first word
    import re
    m = re.search(r"\(([A-Z0-9]+)\)", name)
    if m:
        return m.group(1)
    return name.split()[0][:8] if name else "Vault"


def _spot_price(coin, hype_price, btc_usd, eth_usd):
    if coin == "HYPE":
        return hype_price or 0.0
    if coin in STABLECOINS:
        return 1.0
    if coin in PEGGED:
        return {"bitcoin": btc_usd, "ethereum": eth_usd}.get(PEGGED[coin]) or 0.0
    return 0.0


def fetch_hyperliquid_wallet(wallet, hype_price, btc_usd, eth_usd, include_perp=True):
    """Rows (portfolio token format) for one wallet's Hyperliquid L1 balances."""
    address = wallet["address"].lower()
    rows = []

    # 1) staked HYPE
    try:
        d = _info({"type": "delegatorSummary", "user": address})
        staked = float(d.get("delegated") or 0)
        if staked > 0:
            rows.append({
                "wallet": wallet["name"], "chain": CHAIN, "symbol": "HYPE (staked)",
                "name": "Hyperliquid staked HYPE", "amount": staked,
                "price": hype_price or 0.0, "usd": round(staked * (hype_price or 0.0), 6),
                "logo": "", "token_id": "HYPE-staked",
            })
    except Exception:  # noqa: BLE001
        pass

    # 2) L1 spot balances
    try:
        d = _info({"type": "spotClearinghouseState", "user": address})
        for b in d.get("balances") or []:
            amount = float(b.get("total") or 0)
            if amount <= 0:
                continue
            coin = b.get("coin") or ""
            price = _spot_price(coin, hype_price, btc_usd, eth_usd)
            rows.append({
                "wallet": wallet["name"], "chain": CHAIN, "symbol": coin,
                "name": f"Hyperliquid L1 {coin}", "amount": amount,
                "price": price, "usd": round(amount * price, 6),
                "logo": "", "token_id": f"hl-{coin}",
            })
    except Exception:  # noqa: BLE001
        pass

    # 3) perp account equity (account value is already in USD)
    if include_perp:
        try:
            d = _info({"type": "clearinghouseState", "user": address})
            eq = float((d.get("marginSummary") or {}).get("accountValue") or 0)
            if eq > 0:
                rows.append({
                    "wallet": wallet["name"], "chain": CHAIN, "symbol": "HL Perp Equity",
                    "name": "Hyperliquid perpetual account equity", "amount": round(eq, 2),
                    "price": 1.0, "usd": round(eq, 6),
                    "logo": "", "token_id": "hl-perp",
                })
        except Exception:  # noqa: BLE001
            pass

    # 4) vault positions (e.g. HLP liquidity vault)
    rows.extend(_vault_rows(address, wallet["name"]))

    return {"wallet": wallet["name"], "chain": CHAIN, "rows": rows,
            "total_usd": round(sum(r["usd"] for r in rows), 2)}
