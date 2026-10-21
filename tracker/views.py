# -*- coding: utf-8 -*-
"""Blacklist-filtered view of a snapshot (single source of truth).

Totals (wallet / total / by-chain) are always recomputed from the filtered
token rows, so blacklist changes apply to every historical snapshot, not only
newly fetched ones. The health report is built on top of this view, so its
numbers can never disagree with the dashboard.
"""
from . import assetlabels, manual
from .blacklist import is_blacklisted


def view_of(snap, storage_map=None):
    """`storage_map` is {wallet name: hot|cold} from the live wallet list.

    How a wallet is held is a property of the wallet, not a market fact, so the
    live setting wins over whatever the snapshot recorded: marking a wallet cold in
    Settings must move the health panel straight away instead of waiting for the
    next refresh. The snapshot's own value stays as the fallback, which is what
    keeps the class of a wallet that has since been removed.
    """
    # Manually registered positions (tracker/manual.py) count on the snapshot's own
    # date and later — registering one today must not rewrite last month's history.
    manual_by_wallet = manual.by_wallet(snap.get("date"))
    wallets = []
    total = 0.0
    by_chain = {}
    seen = set()
    for w in snap.get("wallets", []):
        name = w.get("wallet") or w.get("name", "")
        seen.add(name)
        # a manual row is subject to the same blacklist as a fetched one
        tokens = [t for t in w.get("tokens", []) if not is_blacklisted(t)]
        tokens += [t for t in manual_by_wallet.get(name, []) if not is_blacklisted(t)]
        wt = round(sum(float(t.get("usd", 0.0)) for t in tokens), 2)
        total += wt
        for t in tokens:
            c = t.get("chain") or ""
            if t.get("usd"):
                by_chain[c] = round(by_chain.get(c, 0.0) + float(t["usd"]), 2)
        wallets.append({"wallet": name,
                        "address": w.get("address", ""), "type": w.get("type", ""),
                        # a wallet that failed to fetch must be markable in the UI:
                        # without this an error reads as "this wallet holds nothing"
                        "error": w.get("error") or None,
                        "notes": w.get("notes") or [],
                        # storage class (cold/hot/cex) drives the health report; a
                        # snapshot taken before this field existed simply has none
                        "storage": (storage_map or {}).get(name) or w.get("storage"),
                        "total_usd": wt, "token_count": len(tokens)})
    for name, rows_ in manual_by_wallet.items():
        if name in seen:
            continue
        tokens = [t for t in rows_ if not is_blacklisted(t)]
        wt = round(sum(float(t.get("usd", 0.0)) for t in tokens), 2)
        total += wt
        for t in tokens:
            c = t.get("chain") or ""
            if t.get("usd"):
                by_chain[c] = round(by_chain.get(c, 0.0) + float(t["usd"]), 2)
        wallets.append({"wallet": name, "address": "", "type": "manual",
                        "error": None, "notes": [], "manual_only": True,
                        "storage": (storage_map or {}).get(name),
                        "total_usd": wt, "token_count": len(tokens)})
    return {"date": snap.get("date", ""), "created_at": snap.get("created_at"),
            "total_usd": round(total, 2), "by_chain": by_chain,
            "by_volatility": volatility_totals(snap),
            "wallets": wallets, "token_count": sum(w["token_count"] for w in wallets)}


def volatility_totals(snap):
    """{"stable": usd, "btc": usd, "other": usd} over the blacklist-filtered rows.

    The volatility card needs the *token* labels — one wallet can hold both a
    stablecoin and an alt — so the rows go through the same label engine the token
    table uses. "other" is everything that is neither a stablecoin nor BTC: the
    part of the portfolio whose price actually swings.
    """
    out = {assetlabels.STABLE: 0.0, assetlabels.BTC: 0.0, assetlabels.OTHER: 0.0}

    def add(t):
        if is_blacklisted(t):
            return
        usd = float(t.get("usd") or 0.0)
        if not usd:
            return
        label = assetlabels.classify(t)
        if label in (assetlabels.STABLE, assetlabels.BTC):
            out[label] = round(out[label] + usd, 2)
        else:
            out[assetlabels.OTHER] = round(out[assetlabels.OTHER] + usd, 2)

    for w in snap.get("wallets", []):
        for t in w.get("tokens", []):
            add(t)
    for row in manual.rows(snap.get("date")):
        add(row)
    return out
