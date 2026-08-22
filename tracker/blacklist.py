# -*- coding: utf-8 -*-
"""Token blacklist filtering (phishing / fake tokens).

Two sources are merged:
  - built-in entries from tracker/config.py (TOKEN_BLACKLIST)
  - user-added entries persisted in portfolio_blacklist.json (editable from the UI)

Each entry may have any of:
  token_id  exact contract/mint address match (case-insensitive)
  symbol    case-insensitive: exact symbol match, or symbol appears in the row symbol
  name      case-insensitive substring of the token name
  chain     optional: restrict the entry to one chain

Filtering is applied BOTH at fetch time (so totals never include blacklisted
tokens) and at read time (so historical snapshots are filtered too).
"""
import json
import os
import threading

from . import config, profiles

_lock = threading.Lock()
_user_cache = {"mtime": None, "data": None}


def _file_mtime():
    try:
        return os.path.getmtime(profiles.blacklist_file()) if os.path.exists(profiles.blacklist_file()) else None
    except OSError:
        return None


def reset_cache():
    global _user_cache
    with _lock:
        _user_cache = {"mtime": None, "data": None}


def save_all(entries):
    """Overwrite the user blacklist file (used by config import)."""
    global _user_cache
    with _lock:
        entries = [e for e in entries if isinstance(e, dict)]
        _save_user_entries(entries)
        _user_cache = {"mtime": _file_mtime(), "data": entries}


def blacklist_file():
    return profiles.blacklist_file()


def _load_user_entries():
    try:
        with open(profiles.blacklist_file(), "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except FileNotFoundError:
        return []
    except Exception:  # noqa: BLE001
        return []


def _save_user_entries(entries):
    with open(profiles.blacklist_file(), "w", encoding="utf-8") as f:
        json.dump(entries, f, ensure_ascii=False, indent=2)


def user_entries():
    """User-added entries (persisted in portfolio_blacklist.json); hot-reloads
    when the file changes on disk."""
    global _user_cache
    with _lock:
        mtime = _file_mtime()
        if _user_cache["data"] is None or _user_cache["mtime"] != mtime:
            _user_cache = {"mtime": mtime, "data": _load_user_entries()}
        return list(_user_cache["data"])


def all_entries():
    return list(config.TOKEN_BLACKLIST) + user_entries()


def add_entry(entry):
    """Add a user blacklist entry; returns updated user entries."""
    global _user_cache
    clean = {k: str(v).strip() for k, v in entry.items() if v not in (None, "")}
    if not (clean.get("token_id") or clean.get("symbol") or clean.get("name")):
        raise ValueError("至少需要 token_id / symbol / name 之一")
    with _lock:
        entries = _load_user_entries()
        # avoid exact duplicates
        for e in entries:
            if e.get("token_id") and clean.get("token_id") \
                    and e["token_id"].lower() == clean["token_id"].lower():
                raise ValueError("该合约地址已在黑名单中")
        entries.append(clean)
        _save_user_entries(entries)
        _user_cache = {"mtime": _file_mtime(), "data": entries}
        return list(entries)


def remove_entry(index):
    """Remove a user entry by index (into the user entries list)."""
    global _user_cache
    with _lock:
        entries = _load_user_entries()
        if not (0 <= index < len(entries)):
            return False
        del entries[index]
        _save_user_entries(entries)
        _user_cache = {"mtime": _file_mtime(), "data": entries}
        return True


def _entry_matches(entry, row):
    if entry.get("chain") and entry.get("chain") != row.get("chain"):
        return False
    if entry.get("token_id"):
        if str(entry["token_id"]).lower() == str(row.get("token_id", "")).lower():
            return True
    if entry.get("symbol"):
        sym = str(entry["symbol"]).lower()
        row_sym = str(row.get("symbol", "")).lower()
        if row_sym == sym or sym in row_sym:
            return True
    if entry.get("name"):
        if entry["name"].lower() in str(row.get("name", "")).lower():
            return True
    return False


def is_blacklisted(row):
    for entry in all_entries():
        if _entry_matches(entry, row):
            return True
    return False


def filter_rows(rows):
    """Return rows with blacklisted tokens removed."""
    if not all_entries():
        return rows
    return [r for r in rows if not is_blacklisted(r)]
