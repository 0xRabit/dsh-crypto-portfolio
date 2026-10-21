# -*- coding: utf-8 -*-
"""Manually registered protocol positions — for assets no API can read.

A new protocol (Papertrade is the example that started this) often has no public
balance endpoint: there is nothing to fetch, so the only honest way to count it is
to write it down. A registration is therefore **a snapshot of your own estimate**:

    protocol + wallet + symbol + amount + value (USD) + the date you registered it

It never follows the market. The dashboard keeps showing exactly that number and
that date until you register it again, which is the point — a stale manual position
should look stale, not silently drift.

Rows are shaped like fetched tokens, so everything downstream (totals, wallet cards,
chain distribution, token table, health report, plan) handles them identically; the
only differences are the ``manual: true`` flag, the registration ``date`` and the
``protocol`` it belongs to.

A position only counts from its registration date onwards: registering today must
not rewrite last month's history. Historical snapshots simply have fewer rows.
"""
import datetime
import json
import os
import threading
import uuid

from . import atomicio, profiles, walletstore

CHAIN = "manual"          # chain id used for grouping/display: "manual" / 手动登记
DEFAULT_LABEL = None      # labels come from the normal asset-label engine

_lock = threading.RLock()
_cache = {"mtime": None, "data": None}


def manual_file():
    return profiles.manual_file()


# ————————————————————————————————————————————————————————————————
# validation
# ————————————————————————————————————————————————————————————————
def _text(value, where, maximum=200, required=True):
    out = str(value or "").strip()
    if required and not out:
        raise ValueError("%s is required" % where)
    if len(out) > maximum:
        raise ValueError("%s must be at most %d characters" % (where, maximum))
    return out


def _number(value, where, minimum=0.0):
    try:
        n = float(value)
    except (TypeError, ValueError):
        raise ValueError("%s must be a number" % where)
    if n != n or n in (float("inf"), float("-inf")):
        raise ValueError("%s must be a finite number" % where)
    if n < minimum:
        raise ValueError("%s must be at least %s" % (where, minimum))
    return n


def _date(value, where="date"):
    text = str(value or "").strip()
    if not text:
        return datetime.date.today().isoformat()
    try:
        datetime.date.fromisoformat(text)
    except ValueError:
        raise ValueError("%s must be YYYY-MM-DD" % where)
    return text


def wallet_names():
    """Wallet names a position may be attached to (live list, user + CEX)."""
    try:
        return [w.get("name") for w in walletstore.all_wallets() if w.get("name")]
    except Exception:                                        # noqa: BLE001
        return []


def normalize(raw, known_wallets=None):
    """Validate one registration. `known_wallets=None` skips the wallet check."""
    if not isinstance(raw, dict):
        raise ValueError("a position must be a JSON object")
    wallets = known_wallets if known_wallets is not None else wallet_names()
    wallet = _text(raw.get("wallet"), "wallet", 80)
    if wallets and wallet not in wallets:
        raise ValueError("wallet %r is not configured (known: %s)"
                         % (wallet, ", ".join(wallets)))
    protocol = _text(raw.get("protocol"), "protocol", 60)
    symbol = _text(raw.get("symbol"), "symbol", 20)
    amount = _number(raw.get("amount", 0.0), "amount")
    value = _number(raw.get("value_usd", raw.get("usd", 0.0)), "value_usd")
    name = _text(raw.get("name"), "name", 120, required=False)
    return {
        "id": _text(raw.get("id"), "id", 64, required=False) or uuid.uuid4().hex[:12],
        "date": _date(raw.get("date")),
        "wallet": wallet,
        "protocol": protocol,
        "symbol": symbol,
        "name": name or protocol,
        "amount": amount,
        "value_usd": round(value, 2),
        "note": _text(raw.get("note"), "note", 200, required=False),
        "created_at": str(raw.get("created_at") or "").strip()
                      or datetime.datetime.now().isoformat(timespec="seconds"),
        "updated_at": datetime.datetime.now().isoformat(timespec="seconds"),
    }


def normalize_all(raw):
    """Validate a whole file: {version, positions:[…]}. Unknown keys are dropped."""
    if raw is None:
        return {"version": 1, "positions": []}
    if isinstance(raw, list):
        raw = {"version": 1, "positions": raw}
    if not isinstance(raw, dict):
        raise ValueError("manual positions must be a JSON object")
    positions = raw.get("positions")
    if positions is None:
        positions = []
    if not isinstance(positions, list):
        raise ValueError("positions must be a list")
    wallets = wallet_names()
    out, seen = [], set()
    for i, item in enumerate(positions):
        try:
            row = normalize(item, known_wallets=wallets)
        except ValueError as exc:
            raise ValueError("position %d: %s" % (i + 1, exc))
        if row["id"] in seen:                    # duplicate id would break remove/edit
            row["id"] = uuid.uuid4().hex[:12]
        seen.add(row["id"])
        out.append(row)
    return {"version": 1, "positions": out}


# ————————————————————————————————————————————————————————————————
# storage
# ————————————————————————————————————————————————————————————————
def _mtime():
    try:
        path = manual_file()
        return os.path.getmtime(path) if os.path.exists(path) else None
    except OSError:
        return None


def load():
    """Validated file contents; a missing or corrupt file reads as "no positions"."""
    global _cache
    try:
        with _lock:
            mtime = _mtime()
            if _cache["data"] is None or _cache["mtime"] != mtime:
                raw = None
                path = manual_file()
                if os.path.exists(path):
                    try:
                        with open(path, "r", encoding="utf-8") as fh:
                            raw = json.load(fh)
                    except Exception:                        # noqa: BLE001
                        raw = None
                try:
                    data = normalize_all(raw)
                except ValueError:
                    data = {"version": 1, "positions": []}
                _cache = {"mtime": mtime, "data": data}
            return json.loads(json.dumps(_cache["data"]))
    except Exception:                                        # noqa: BLE001
        return {"version": 1, "positions": []}


def save(positions):
    """Validate and persist the whole list; returns the stored file contents."""
    global _cache
    data = normalize_all({"version": 1, "positions": positions})
    with _lock:
        atomicio.write_json(manual_file(), data)
        _cache = {"mtime": _mtime(), "data": data}
        return json.loads(json.dumps(data))


def positions():
    """Registrations, newest first (the UI lists them in that order)."""
    rows = load()["positions"]
    rows.sort(key=lambda p: (p.get("date") or "", p.get("protocol") or "",
                             p.get("symbol") or ""), reverse=True)
    return rows


def upsert(entry):
    """Add a registration, or replace one when the entry carries its id."""
    rows = positions()
    row = normalize(entry)
    for i, old in enumerate(rows):
        if old["id"] == row["id"]:
            row["created_at"] = old.get("created_at") or row["created_at"]
            rows[i] = row
            break
    else:
        rows.append(row)
    save(rows)
    return row


def remove(position_id):
    rows = positions()
    keep = [p for p in rows if p["id"] != position_id]
    if len(keep) == len(rows):
        return False
    save(keep)
    return True


def reset_cache():
    global _cache
    with _lock:
        _cache = {"mtime": None, "data": None}


# ————————————————————————————————————————————————————————————————
# token-shaped rows
# ————————————————————————————————————————————————————————————————
def row_of(position):
    """One registration as a token row (the shape `views` and `storage` speak)."""
    amount = float(position.get("amount") or 0.0)
    value = float(position.get("value_usd") or 0.0)
    protocol = position.get("protocol") or "manual"
    symbol = position.get("symbol") or "?"
    return {
        "wallet": position.get("wallet") or "",
        "chain": CHAIN,
        "token_id": "manual:%s" % position.get("id"),
        "symbol": symbol,
        "name": position.get("name") or "%s · %s" % (protocol, symbol),
        "amount": amount,
        # a registration stores a *value*, not a price feed: show the implied unit
        # price so the table can keep one column layout
        "price": round(value / amount, 8) if amount else 0.0,
        "usd": round(value, 2),
        "logo": "",
        "manual": True,
        "date": position.get("date"),
        "protocol": protocol,
        "note": position.get("note") or "",
    }


def _cutoff(date):
    """A usable comparison date, or None when the given one is not a date.

    A snapshot with a corrupt date must not take the dashboard down, and it must not
    silently gain manual positions either — so an unparseable date means "no overlay".
    """
    if not date:
        return datetime.date.today().isoformat()
    try:
        return datetime.date.fromisoformat(str(date)).isoformat()
    except ValueError:
        return None


def rows(date=None):
    """Rows that count on `date` (default today): registered on or before it."""
    cut = _cutoff(date)
    if cut is None:
        return []
    return [row_of(p) for p in positions() if (p.get("date") or "") <= cut]


def total(date=None):
    return round(sum(float(r["usd"]) for r in rows(date)), 2)


def by_wallet(date=None):
    """{wallet name: [rows]} for one date — what `views.view_of` merges in."""
    out = {}
    for row in rows(date):
        out.setdefault(row["wallet"], []).append(row)
    return out


def totals_by_date(dates):
    """{date: manual total} for a list of snapshot dates (the trend overlay)."""
    positions_list = positions()
    out = {}
    for d in dates:
        out[d] = round(sum(float(p.get("value_usd") or 0.0) for p in positions_list
                           if (p.get("date") or "") <= d), 2)
    return out


def wallet_totals_by_date(dates):
    """{wallet: {date: manual total}} so the per-wallet trend lines agree too."""
    positions_list = positions()
    out = {}
    for p in positions_list:
        wallet = p.get("wallet") or ""
        series = out.setdefault(wallet, {})
        for d in dates:
            if (p.get("date") or "") <= d:
                series[d] = round(series.get(d, 0.0) + float(p.get("value_usd") or 0.0), 2)
    return out
