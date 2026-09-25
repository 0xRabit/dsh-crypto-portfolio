# -*- coding: utf-8 -*-
"""Wallet store: the tracked wallet list of the ACTIVE profile.

Wallets live in profiles/<active>/wallets.json (per-profile). Removing a wallet
only stops future fetching; historical snapshots already stored in the profile
DB are never touched.
"""
import json
import os
import threading

from . import atomicio, profiles

VALID_TYPES = ("evm", "btc", "sol", "doge", "ada")
# Where the keys live. "cex" is not listed: an exchange account is custody by
# definition, and health.py derives that from the wallet type instead.
VALID_STORAGE = ("hot", "cold")
DEFAULT_STORAGE = "hot"

_lock = threading.Lock()
_user_cache = {"mtime": None, "data": None}


def wallets_file():
    return profiles.wallets_file()


def _file_mtime():
    try:
        return os.path.getmtime(profiles.wallets_file()) if os.path.exists(profiles.wallets_file()) else None
    except OSError:
        return None


def _load_user_wallets():
    try:
        with open(profiles.wallets_file(), "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except FileNotFoundError:
        return []
    except Exception:  # noqa: BLE001
        return []


def _save_user_wallets(entries):
    d = os.path.dirname(profiles.wallets_file())
    os.makedirs(d, exist_ok=True)
    atomicio.write_json(profiles.wallets_file(), entries)


def user_wallets():
    """Wallets of the active profile; hot-reloads when the file changes."""
    global _user_cache
    with _lock:
        mtime = _file_mtime()
        if _user_cache["data"] is None or _user_cache["mtime"] != mtime:
            _user_cache = {"mtime": mtime, "data": _load_user_wallets()}
        return list(_user_cache["data"])


def all_wallets():
    """Wallets of the active profile only (no built-in merge)."""
    return user_wallets()


def normalize_storage(value):
    """`hot` unless the caller said otherwise; an unknown value is rejected."""
    kind = str(value if value is not None else DEFAULT_STORAGE).strip().lower()
    if kind not in VALID_STORAGE:
        raise ValueError(f"storage must be one of {'/'.join(VALID_STORAGE)}")
    return kind


def add_wallet(wallet):
    """Add a wallet to the active profile. wallet: {name, type, address, storage?}."""
    global _user_cache
    name = str(wallet.get("name") or "").strip()
    wtype = str(wallet.get("type") or "").strip().lower()
    address = str(wallet.get("address") or "").strip()
    if not name:
        raise ValueError("wallet name is required")
    if wtype not in VALID_TYPES:
        raise ValueError(f"type must be one of {'/'.join(VALID_TYPES)}")
    if not address:
        raise ValueError("address is required")
    storage = normalize_storage(wallet.get("storage"))
    with _lock:
        entries = _load_user_wallets()
        for w in entries:
            if w.get("address", "").lower() == address.lower() and w.get("type") == wtype:
                raise ValueError("address already in the wallet list")
        entries.append({"name": name, "type": wtype, "address": address,
                        "storage": storage})
        _save_user_wallets(entries)
        _user_cache = {"mtime": _file_mtime(), "data": entries}
        return list(entries)


def set_storage(index, kind):
    """Set the storage class of one wallet. Returns the new wallet list."""
    global _user_cache
    kind = normalize_storage(kind)
    with _lock:
        entries = _load_user_wallets()
        if not (0 <= index < len(entries)):
            raise ValueError("invalid index")
        entries[index]["storage"] = kind
        _save_user_wallets(entries)
        _user_cache = {"mtime": _file_mtime(), "data": entries}
        return list(entries)


def remove_wallet(index):
    """Remove a wallet from the active profile by index."""
    global _user_cache
    with _lock:
        entries = _load_user_wallets()
        if not (0 <= index < len(entries)):
            return False
        del entries[index]
        _save_user_wallets(entries)
        _user_cache = {"mtime": _file_mtime(), "data": entries}
        return True


def save_all(entries):
    """Overwrite the active profile's wallets (used by config import)."""
    global _user_cache
    with _lock:
        entries = [e for e in entries if isinstance(e, dict)]
        _save_user_wallets(entries)
        _user_cache = {"mtime": _file_mtime(), "data": entries}


def reset_cache():
    global _user_cache
    with _lock:
        _user_cache = {"mtime": None, "data": None}
