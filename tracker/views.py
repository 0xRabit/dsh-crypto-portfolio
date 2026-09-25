# -*- coding: utf-8 -*-
"""Blacklist-filtered view of a snapshot (single source of truth).

Totals (wallet / total / by-chain) are always recomputed from the filtered
token rows, so blacklist changes apply to every historical snapshot, not only
newly fetched ones. The health report is built on top of this view, so its
numbers can never disagree with the dashboard.
"""
from .blacklist import is_blacklisted


def view_of(snap, storage_map=None):
    """`storage_map` is {wallet name: hot|cold} from the live wallet list.

    How a wallet is held is a property of the wallet, not a market fact, so the
    live setting wins over whatever the snapshot recorded: marking a wallet cold in
    Settings must move the health panel straight away instead of waiting for the
    next refresh. The snapshot's own value stays as the fallback, which is what
    keeps the class of a wallet that has since been removed.
    """
    wallets = []
    total = 0.0
    by_chain = {}
    for w in snap.get("wallets", []):
        name = w.get("wallet") or w.get("name", "")
        tokens = [t for t in w.get("tokens", []) if not is_blacklisted(t)]
        wt = round(sum(float(t.get("usd", 0.0)) for t in tokens), 2)
        total += wt
        for t in tokens:
            c = t.get("chain") or ""
            if t.get("usd"):
                by_chain[c] = round(by_chain.get(c, 0.0) + float(t["usd"]), 2)
        wallets.append({"wallet": name,
                        "address": w.get("address", ""), "type": w.get("type", ""),
                        # storage class (cold/hot/cex) drives the health report; a
                        # snapshot taken before this field existed simply has none
                        "storage": (storage_map or {}).get(name) or w.get("storage"),
                        "total_usd": wt, "token_count": len(tokens)})
    return {"date": snap.get("date", ""), "created_at": snap.get("created_at"),
            "total_usd": round(total, 2), "by_chain": by_chain,
            "wallets": wallets, "token_count": sum(w["token_count"] for w in wallets)}
