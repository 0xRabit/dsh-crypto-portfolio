# -*- coding: utf-8 -*-
"""Orchestration: fetch every wallet, price everything, build unified snapshot data."""
import threading
from datetime import date, datetime

from . import config, storage
from . import walletstore
from .blacklist import filter_rows
from .btc import fetch_btc_satoshis
from .cex import cex_accounts, fetch_cex_accounts
from .debank import fetch_evm_wallet
from .etherscan import fetch_etherscan
from .hyperliquid import fetch_hyperliquid_wallet
from .prices import get_native_prices
from .solana import birdeye_wallet_prices, fetch_solana_wallet, get_sol_token_prices
from . import status

_refresh_lock = threading.Lock()


def today_str():
    return date.today().isoformat()


def _wallet_subset(wtype):
    return [w for w in walletstore.all_wallets() if w["type"] == wtype]


def _btc_rows(satoshis, btc_usd):
    rows = []
    for w in _wallet_subset("btc"):
        sats = satoshis.get(w["address"])
        if sats is None:
            rows.append({"wallet": w["name"], "chain": "btc", "symbol": "BTC", "name": "Bitcoin",
                         "amount": None, "price": btc_usd or 0, "usd": 0.0,
                         "logo": "https://assets.coingecko.com/coins/images/1/small/bitcoin.png",
                         "token_id": "btc", "error": True})
            continue
        amount = sats / 1e8
        rows.append({"wallet": w["name"], "chain": "btc", "symbol": "BTC", "name": "Bitcoin",
                     "amount": amount, "price": btc_usd or 0, "usd": round(amount * (btc_usd or 0), 6),
                     "logo": "https://assets.coingecko.com/coins/images/1/small/bitcoin.png",
                     "token_id": "btc"})
    return rows


def _sol_rows(sol_data_list, sol_usd, prices):
    """sol_data_list: [{wallet, sol_lamports, staked_lamports, tokens:[...]}]"""
    rows = []
    for data in sol_data_list:
        wname = data["wallet"]
        sol_amount = data["sol_lamports"] / 1e9
        rows.append({"wallet": wname, "chain": "sol", "symbol": "SOL", "name": "Solana",
                     "amount": sol_amount, "price": sol_usd or 0, "usd": round(sol_amount * (sol_usd or 0), 6),
                     "logo": "https://assets.coingecko.com/coins/images/4128/small/solana.png",
                     "token_id": "sol"})
        staked = data.get("staked_lamports", 0) / 1e9
        if staked > 0:
            rows.append({"wallet": wname, "chain": "sol", "symbol": "SOL (staked)",
                         "name": "Solana native staked", "amount": staked,
                         "price": sol_usd or 0, "usd": round(staked * (sol_usd or 0), 6),
                         "logo": "", "token_id": "sol-staked"})
        for t in data["tokens"]:
            price = prices.get(t["mint"], 0)
            rows.append({"wallet": wname, "chain": "sol", "symbol": t["mint"][:6] + "...",
                         "name": t["mint"], "amount": t["amount"], "price": price,
                         "usd": round(t["amount"] * price, 6), "logo": "",
                         "token_id": t["mint"]})
    return rows


def _wallet_from_rows(rows):
    total = round(sum(r["usd"] for r in rows), 2)
    return {"wallet": rows[0]["wallet"], "tokens": rows, "total_usd": total}


def fetch_all(progress=None):
    """Fetch all wallets and return unified snapshot data (does NOT save).

    progress: optional callable(stage, done, total, msg) for UI feedback.
    """
    def tick(stage, done, total, msg=""):
        if progress:
            progress(stage, done, total, msg)

    result = {"date": today_str(), "created_at": datetime.now().isoformat(timespec="seconds"),
              "wallets": [], "total_usd": 0.0, "by_chain": {}}

    # 1) native prices (one CoinGecko call)
    tick("prices", 0, 1, "Fetching BTC/ETH/SOL/HYPE prices…")
    native = get_native_prices()
    btc_usd = native.get("bitcoin")
    sol_usd = native.get("solana")
    tick("prices", 1, 1, "Prices fetched")
    if native:
        status.mark_source_ok("prices")

    # 2) BTC wallets
    sats = {}
    btc_wallets = _wallet_subset("btc")
    if btc_wallets:
        tick("btc", 0, 1, "Fetching BTC balances…")
        sats = fetch_btc_satoshis([w["address"] for w in btc_wallets])
        tick("btc", 1, 1, "BTC balances fetched")
        status.mark_source_ok("btc")

    # 3) EVM wallets (DeBank all chains + Hyperliquid native L1)
    evm_wallets = _wallet_subset("evm")
    evm_results = []
    if evm_wallets:
        total_steps = len(evm_wallets)
        for i, w in enumerate(evm_wallets):
            tick("evm", i, total_steps, f"Fetching {w['name']} (DeBank all chains + Hyperliquid L1)…")
            ew = fetch_evm_wallet(w)
            try:
                hl = fetch_hyperliquid_wallet(w, native.get("hyperliquid"),
                                              native.get("bitcoin"), native.get("ethereum"))
                ew["tokens"].extend(hl["rows"])
                status.mark_source_ok("hyperliquid")
            except Exception:  # noqa: BLE001
                pass
            evm_results.append(ew)
        tick("evm", total_steps, total_steps, "EVM/Hyperliquid fetched")
        status.mark_source_ok("debank")

    # 4) Solana wallets
    sol_wallets = _wallet_subset("sol")
    sol_rows_all = []
    if sol_wallets:
        tick("sol", 0, 3, "Fetching Solana tokens…")
        sol_data_list = [fetch_solana_wallet(w) for w in sol_wallets]
        sol_mints = [t["mint"] for d in sol_data_list for t in d["tokens"] if t["amount"] > 0]
        tick("sol", 1, 3, "Fetching SPL token prices…")
        spl_prices = get_sol_token_prices(sol_mints)
        tick("sol", 2, 3, "Birdeye price enrichment (if configured)…")
        birdeye_prices = {}
        birdeye_sol = None
        for w in sol_wallets:
            bp, bs = birdeye_wallet_prices(w["address"])
            if bp:
                birdeye_prices.update(bp)
            if bs:
                birdeye_sol = bs
        if birdeye_prices:
            spl_prices = {**spl_prices, **birdeye_prices}
        eff_sol_usd = birdeye_sol or sol_usd
        sol_rows_all = _sol_rows(sol_data_list, eff_sol_usd, spl_prices)
        tick("sol", 3, 3, "Solana fetched")
        status.mark_source_ok("solana")

    # 5) CEX accounts (Binance / Bybit / Backpack)
    # Etherscan reference source: native balances, surfaced in Settings, not merged
    try:
        esc_detail, _esc_err = fetch_etherscan(evm_wallets, native)
        if esc_detail:
            status.mark_source_ok("etherscan")
            status.set_detail("etherscan_native", esc_detail)
    except Exception:  # noqa: BLE001
        pass

    tick("cex", 0, 1, "Fetching CEX balances (Binance/Bybit/Backpack)…")
    cex_results = fetch_cex_accounts(cex_accounts(), native)
    tick("cex", 1, 1, "CEX fetched")
    for _r in cex_results:
        if _r["error"] is None:
            status.mark_source_ok(f"cex:{_r['account'].get('exchange')}")
    status.mark_source_ok("cex")

    # 6) assemble — every wallet's tokens pass through the blacklist; all totals
    #    (wallet / chain / total) are recomputed from the filtered token rows.
    btc_rows_all = filter_rows(_btc_rows(sats, btc_usd))
    sol_rows_all = filter_rows(sol_rows_all)

    wallet_objs = []
    for w in walletstore.all_wallets():
        obj = {"wallet": w["name"], "address": w["address"], "type": w["type"],
               "tokens": [], "total_usd": 0.0}
        if w["type"] == "btc":
            obj["tokens"] = [r for r in btc_rows_all if r["wallet"] == w["name"]]
        elif w["type"] == "evm":
            ew = next((e for e in evm_results if e["wallet"] == w["name"]), None)
            if ew:
                obj["tokens"] = ew["tokens"]
        elif w["type"] == "sol":
            obj["tokens"] = [r for r in sol_rows_all if r["wallet"] == w["name"]]
        obj["tokens"] = filter_rows(obj["tokens"])
        obj["total_usd"] = round(sum(r["usd"] for r in obj["tokens"]), 2)
        for r in obj["tokens"]:
            if r.get("usd"):
                c = r.get("chain") or ""
                result["by_chain"][c] = round(result["by_chain"].get(c, 0.0) + r["usd"], 2)
        wallet_objs.append(obj)

    for res in cex_results:
        acc = res["account"]
        obj = {"wallet": acc["name"], "address": str(acc.get("exchange") or ""),
               "type": "cex", "tokens": filter_rows(res["rows"]),
               "total_usd": round(sum(r["usd"] for r in res["rows"]), 2),
               "error": res["error"]}
        if res["error"]:
            obj["tokens"] = [{"wallet": acc["name"], "chain": str(acc.get("exchange") or "cex"),
                              "symbol": "CEX-Error", "name": res["error"],
                              "amount": 0, "price": 0, "usd": 0.0, "logo": "",
                              "token_id": f"cex-err-{acc['name']}"}]
        for r in obj["tokens"]:
            if r.get("usd"):
                result["by_chain"][r["chain"]] = round(result["by_chain"].get(r["chain"], 0.0) + r["usd"], 2)
        wallet_objs.append(obj)

    for wo in wallet_objs:
        wo["tokens"] = sorted(wo["tokens"], key=lambda r: -r["usd"])
        result["total_usd"] = round(result["total_usd"] + wo["total_usd"], 2)

    result["wallets"] = wallet_objs
    status.mark_refresh()
    return result


def refresh_snapshot(progress=None):
    """Fetch everything and save today's snapshot. Returns (data, prev_latest)."""
    with _refresh_lock:
        prev = storage.get_latest_snapshot()
        data = fetch_all(progress=progress)
        storage.save_snapshot(data)
        return data, prev
