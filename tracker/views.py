# -*- coding: utf-8 -*-
"""Blacklist-filtered view of a snapshot (single source of truth).

Totals (wallet / total / by-chain) are always recomputed from the filtered
token rows, so blacklist changes apply to every historical snapshot, not only
newly fetched ones.
"""
from .blacklist import is_blacklisted


def view_of(snap):
    wallets = []
    total = 0.0
    by_chain = {}
    for w in snap.get("wallets", []):
        tokens = [t for t in w.get("tokens", []) if not is_blacklisted(t)]
        wt = round(sum(float(t.get("usd", 0.0)) for t in tokens), 2)
        total += wt
        for t in tokens:
            c = t.get("chain") or ""
            if t.get("usd"):
                by_chain[c] = round(by_chain.get(c, 0.0) + float(t["usd"]), 2)
        wallets.append({"wallet": w.get("wallet") or w.get("name", ""),
                        "address": w.get("address", ""), "type": w.get("type", ""),
                        "total_usd": wt, "token_count": len(tokens)})
    return {"date": snap.get("date", ""), "created_at": snap.get("created_at"),
            "total_usd": round(total, 2), "by_chain": by_chain,
            "wallets": wallets, "token_count": sum(w["token_count"] for w in wallets)}
