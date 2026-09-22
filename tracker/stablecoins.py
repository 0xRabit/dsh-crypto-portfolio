# -*- coding: utf-8 -*-
"""Asset-type classification for the "asset type" donut and the token table tag.

Every token row is classified into exactly one of three buckets:

    stable   stablecoins — USDT / USDC and their bridged, wrapped or renamed
             forms, on any venue
    btc      bitcoin and its wrapped forms (WBTC, tBTC, cbBTC, …)
    other    everything else

Two detection layers, both editable:

  1. Glob rules. `symbol` is a case-insensitive glob (`USDT*`, `*USDC`, `WBTC*`),
     `name` is a substring, and `token_id` / `chain` pin a rule to one asset.
     Built-ins live in tracker/config.py; user rules in
     profiles/<name>/stablecoins.json (managed from the dashboard).
  2. Price band. A token priced inside STABLECOIN_PRICE_BAND whose symbol or name
     carries a dollar marker is treated as a stablecoin even when no rule names
     it — this is what catches a pegged asset under an unfamiliar ticker.

User rules win over everything: an `exclude` entry pins a token OUT of a bucket,
so a wildcard false positive (a leveraged token called "USD…") can be corrected
from the table without touching the built-in list.
"""
import fnmatch
import json
import os
import threading

from . import config, profiles

_lock = threading.Lock()
_user_cache = {"mtime": None, "data": None}

STABLE, BTC, OTHER = "stable", "btc", "other"


def _file_mtime():
    try:
        f = profiles.stablecoins_file()
        return os.path.getmtime(f) if os.path.exists(f) else None
    except OSError:
        return None


def reset_cache():
    global _user_cache
    with _lock:
        _user_cache = {"mtime": None, "data": None}


def stablecoins_file():
    return profiles.stablecoins_file()


def _load_user_entries():
    try:
        with open(profiles.stablecoins_file(), "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except FileNotFoundError:
        return []
    except Exception:  # noqa: BLE001
        return []


def _save_user_entries(entries):
    path = profiles.stablecoins_file()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(entries, f, ensure_ascii=False, indent=2)


def user_entries():
    """User rules; hot-reloads when the file changes on disk."""
    global _user_cache
    with _lock:
        mtime = _file_mtime()
        if _user_cache["data"] is None or _user_cache["mtime"] != mtime:
            _user_cache = {"mtime": mtime, "data": _load_user_entries()}
        return list(_user_cache["data"])


def save_all(entries):
    """Overwrite the user rules (used by config import)."""
    global _user_cache
    with _lock:
        entries = [e for e in entries if isinstance(e, dict)]
        _save_user_entries(entries)
        _user_cache = {"mtime": _file_mtime(), "data": entries}


def add_entry(entry):
    """Add a user rule; returns the updated list."""
    global _user_cache
    clean = {k: str(v).strip() for k, v in (entry or {}).items() if v not in (None, "")}
    if clean.get("category") not in (STABLE, BTC, OTHER):
        raise ValueError("category must be stable/btc/other")
    if clean.get("action") not in (None, "", "include", "exclude"):
        raise ValueError("action must be include or exclude")
    if not (clean.get("symbol") or clean.get("name") or clean.get("token_id")):
        raise ValueError("at least one of symbol / name / token_id is required")
    clean.setdefault("action", "include")
    with _lock:
        entries = _load_user_entries()
        for e in entries:
            same = (e.get("symbol", "").lower() == clean.get("symbol", "").lower()
                    and e.get("token_id", "").lower() == clean.get("token_id", "").lower()
                    and e.get("chain", "").lower() == clean.get("chain", "").lower()
                    and e.get("category") == clean.get("category")
                    and e.get("action", "include") == clean.get("action", "include"))
            if same:
                raise ValueError("identical rule already exists")
        entries.append(clean)
        _save_user_entries(entries)
        _user_cache = {"mtime": _file_mtime(), "data": entries}
        return list(entries)


def remove_entry(index):
    """Remove a user rule by index."""
    global _user_cache
    with _lock:
        entries = _load_user_entries()
        if not (0 <= index < len(entries)):
            return False
        del entries[index]
        _save_user_entries(entries)
        _user_cache = {"mtime": _file_mtime(), "data": entries}
        return True


def builtin_entries():
    """Built-in glob rules. These are MATCHING rules — the price band is not one
    of them (a `symbol: "*"` row would swallow every token), so keep it out."""
    out = [{"symbol": p, "category": STABLE, "action": "include", "builtin": True}
           for p in config.STABLECOIN_SYMBOLS]
    out += [{"symbol": p, "category": BTC, "action": "include", "builtin": True}
            for p in config.BITCOIN_SYMBOLS]
    return out


def matching_entries():
    """Everything consulted when classifying a row."""
    return builtin_entries() + user_entries()


def all_entries():
    """Rules plus the informational auto-detect row, purely for the UI listing."""
    return builtin_entries() + user_entries() + [{
        "symbol": "", "category": STABLE, "action": "auto", "builtin": True, "auto": True,
        "price_band": list(config.STABLECOIN_PRICE_BAND),
        "note": "auto: priced inside the band with a USD/DAI/FRAX marker in symbol or name",
    }]


def _norm(value):
    return str(value if value is not None else "").strip().lower()


def _rule_matches(entry, row):
    """A rule matches when every field it specifies agrees with the row."""
    if entry.get("chain") and _norm(entry["chain"]) != _norm(row.get("chain")):
        return False
    if entry.get("token_id") and _norm(entry["token_id"]) != _norm(row.get("token_id")):
        return False
    if entry.get("symbol"):
        pattern = _norm(entry["symbol"])
        if not (fnmatch.fnmatchcase(_norm(row.get("symbol")), pattern)
                or _norm(row.get("symbol")) == pattern):
            return False
    if entry.get("name") and _norm(entry["name"]) not in _norm(row.get("name")):
        return False
    return bool(entry.get("symbol") or entry.get("name") or entry.get("token_id"))


def _price_says_stable(row):
    """Peg heuristic: near $1 *and* a dollar marker in the ticker or name."""
    try:
        price = float(row.get("price") or 0)
    except (TypeError, ValueError):
        return False
    lo, hi = config.STABLECOIN_PRICE_BAND
    if not (lo <= price <= hi):
        return False
    hay = (_norm(row.get("symbol")) + " " + _norm(row.get("name")))
    return any(marker in hay for marker in ("usd", "dai", "frax", "cusd", "vai", "dola"))


def classify(row):
    """Return 'stable' | 'btc' | 'other' for one token row.

    User rules are consulted first and an `exclude` wins outright, so a human
    decision always beats a wildcard or the price heuristic.
    """
    entries = matching_entries()
    for entry in entries:
        if entry.get("action") == "exclude" and _rule_matches(entry, row):
            return OTHER
    for entry in entries:
        if entry.get("action") == "exclude":
            continue
        if _rule_matches(entry, row):
            return entry.get("category", OTHER)
    return STABLE if _price_says_stable(row) else OTHER


def annotate(rows):
    """Return rows with a `cat` field added (classification is per-request, so
    editing the rules reclassifies historical snapshots too)."""
    if not rows:
        return rows
    entries = matching_entries()
    exclusions = [e for e in entries if e.get("action") == "exclude"]
    inclusions = [e for e in entries if e.get("action") != "exclude"]
    out = []
    for row in rows:
        row = dict(row)
        cat = None
        for e in exclusions:
            if _rule_matches(e, row):
                cat = OTHER
                break
        if cat is None:
            for e in inclusions:
                if _rule_matches(e, row):
                    cat = e.get("category", OTHER)
                    break
        if cat is None:
            cat = STABLE if _price_says_stable(row) else OTHER
        row["cat"] = cat
        out.append(row)
    return out


def category_totals(rows):
    """USD per bucket — used by the asset-type donut when computed server-side."""
    totals = {STABLE: 0.0, BTC: 0.0, OTHER: 0.0}
    for row in annotate(rows):
        totals[row["cat"]] = totals.get(row["cat"], 0.0) + float(row.get("usd") or 0.0)
    return totals
