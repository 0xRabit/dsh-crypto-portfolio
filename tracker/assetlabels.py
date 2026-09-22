# -*- coding: utf-8 -*-
"""Asset labels: the "asset type" donut, the row tag picker and the rule engine.

Every token row carries exactly ONE label. Built-ins the system detects on its own:

    stable   USDT / USDC and their bridged, wrapped or renamed forms
    btc      bitcoin and its wrapped forms (WBTC, tBTC, cbBTC, …)
    eth      ether and its staked / wrapped forms (WETH, stETH, rETH, …)
    sol      SOL and its staked / wrapped forms (mSOL, jitoSOL, …)
    hype     HYPE and its wrapped / staked forms
    other    the default — anything no rule claims

Labels are DATA, not an enum: a rule may use any short label string the user types,
and a user-defined label behaves exactly like a built-in one (it gets its own slice
in the donut and its own colour). Detection is three-layered:

  1. Glob rules. `symbol` is a case-insensitive glob (`USDT*`, `*USDC`, `WBTC*`),
     `name` a substring, `token_id` / `chain` pin a rule to one asset. Built-ins
     live in tracker/config.py; user rules in profiles/<name>/asset_labels.json.
  2. Price band. A token priced inside STABLECOIN_PRICE_BAND whose symbol or name
     carries a dollar marker counts as a stablecoin even with no rule naming it —
     this is what catches a pegged asset under an unfamiliar ticker.
  3. User rules win over everything: an `exclude` / `other` rule pins a token out,
     so a wildcard false positive can be corrected per token without touching the
     built-in list.

Because a row can only hold one label, the per-row control is a single-select.
"""
import fnmatch
import json
import re
import os
import threading

from . import config, profiles

_lock = threading.Lock()
_user_cache = {"mtime": None, "data": None}
_names_cache = {"mtime": None, "data": None}

STABLE, BTC, ETH, SOL, HYPE, OTHER = "stable", "btc", "eth", "sol", "hype", "other"
# donut / legend order for the auto-detected labels; user labels follow, `other` last
BUILTIN_LABELS = [STABLE, BTC, ETH, SOL, HYPE]
DEFAULT_LABEL = OTHER
_LABEL_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 _.-]{0,23}$")


def valid_label(value):
    """A label is free text, but must be short and shell-friendly."""
    return bool(_LABEL_RE.match(str(value or "").strip()))


def normalize_label(value):
    v = str(value or "").strip()
    return v if valid_label(v) else DEFAULT_LABEL


def _migrate_legacy_file():
    """One-time move of profiles/**/stablecoins.json -> asset_labels.json."""
    try:
        old, new = profiles.legacy_asset_labels_file(), profiles.asset_labels_file()
        if os.path.exists(old) and not os.path.exists(new):
            os.makedirs(os.path.dirname(new), exist_ok=True)
            os.replace(old, new)
    except OSError:
        pass


def _file_mtime():
    _migrate_legacy_file()
    try:
        f = profiles.asset_labels_file()
        return os.path.getmtime(f) if os.path.exists(f) else None
    except OSError:
        return None


def reset_cache():
    global _user_cache
    with _lock:
        _user_cache = {"mtime": None, "data": None}


def reset_names_cache():
    global _names_cache
    with _lock:
        _names_cache = {"mtime": None, "data": None}


def asset_labels_file():
    _migrate_legacy_file()
    return profiles.asset_labels_file()


def _load_user_entries():
    _migrate_legacy_file()
    try:
        with open(profiles.asset_labels_file(), "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except FileNotFoundError:
        return []
    except Exception:  # noqa: BLE001
        return []


def _save_user_entries(entries):
    path = profiles.asset_labels_file()
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
    if not valid_label(clean.get("category")):
        raise ValueError("category must be 1-24 chars: letters, digits, space, _ . -")
    if clean.get("action") not in (None, "", "include", "exclude"):
        raise ValueError("action must be include or exclude")
    if not (clean.get("symbol") or clean.get("name") or clean.get("token_id")):
        raise ValueError("at least one of symbol / name / token_id is required")
    clean["category"] = normalize_label(clean["category"])
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
        # a row carries exactly one label, so a new rule for the same target
        # replaces whatever was there before — last choice wins, no stale exclude
        def _target(e):
            return (_norm(e.get("token_id")), _norm(e.get("chain")), _norm(e.get("symbol")))
        keep = [e for e in entries if _target(e) != _target(clean)]
        keep.append(clean)
        entries = keep
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
    """Built-in glob rules. These are MATCHING rules — the price band is not one of
    them (a `symbol: "*"` row would swallow every token), so keep it out."""
    sets = ((STABLE, config.STABLECOIN_SYMBOLS), (BTC, config.BITCOIN_SYMBOLS),
            (ETH, config.ETHEREUM_SYMBOLS), (SOL, config.SOLANA_SYMBOLS),
            (HYPE, config.HYPE_SYMBOLS))
    return [{"symbol": pat, "category": cat, "action": "include", "builtin": True}
            for cat, pats in sets for pat in pats]


def matching_entries():
    """Everything consulted when classifying a row, in precedence order.

    User rules come FIRST. Until this was ordered, a built-in wildcard always beat
    a human decision, so relabelling "USDC" (which matches the `*USD*` built-in)
    silently did nothing — the user could only pin a token out, never relabel it.
    """
    user = user_entries()
    return ([e for e in user if e.get("action") == "exclude"]
            + [e for e in user if e.get("action") != "exclude"]
            + builtin_entries())


def all_entries():
    """Rules plus the informational auto-detect row, purely for the UI listing."""
    return builtin_entries() + user_entries() + [{
        "symbol": "", "category": STABLE, "action": "auto", "builtin": True, "auto": True,
        "price_band": list(config.STABLECOIN_PRICE_BAND),
        "note": "auto: priced inside the band with a USD/DAI/FRAX marker in symbol or name",
    }]


def _norm(value):
    return str(value if value is not None else "").strip().lower()


def _base_symbol(symbol):
    """Strip the qualifier staked positions carry: "SOL (staked)" -> "sol",
    "HYPE (staked)" -> "hype", "ETH/ankr" -> "eth". Without this a plain glob can
    never reach them and sizeable positions sit in "other" forever."""
    s = _norm(symbol)
    for sep in (" (", "(", "/", " -", ":"):
        i = s.find(sep)
        if i > 0:
            s = s[:i]
    return s.strip()


def _symbol_variants(symbol):
    full = _norm(symbol)
    base = _base_symbol(symbol)
    return [full] if base == full else [full, base]


def _rule_matches(entry, row):
    """A rule matches when every field it specifies agrees with the row."""
    if entry.get("chain") and _norm(entry["chain"]) != _norm(row.get("chain")):
        return False
    if entry.get("token_id") and _norm(entry["token_id"]) != _norm(row.get("token_id")):
        return False
    if entry.get("symbol"):
        pattern = _norm(entry["symbol"])
        if not any(fnmatch.fnmatchcase(v, pattern) for v in _symbol_variants(row.get("symbol"))):
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
            return DEFAULT_LABEL
    for entry in entries:
        if entry.get("action") == "exclude":
            continue
        if _rule_matches(entry, row):
            return normalize_label(entry.get("category"))
    return STABLE if _price_says_stable(row) else DEFAULT_LABEL


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
                cat = DEFAULT_LABEL
                break
        if cat is None:
            for e in inclusions:
                if _rule_matches(e, row):
                    cat = normalize_label(e.get("category"))
                    break
        if cat is None:
            cat = STABLE if _price_says_stable(row) else DEFAULT_LABEL
        row["cat"] = cat
        out.append(row)
    return out


def category_totals(rows):
    """USD per bucket — used by the asset-type donut when computed server-side."""
    totals = {label: 0.0 for label in known_labels()}
    for row in annotate(rows):
        totals[row["cat"]] = totals.get(row["cat"], 0.0) + float(row.get("usd") or 0.0)
    return totals


def known_labels(include_empty=True):
    """Every label that can appear: auto-detected ones first, then any label the
    user invented, with `other` always last."""
    extra = []
    for e in user_entries():
        cat = str(e.get("category") or "").strip()
        if valid_label(cat) and cat not in BUILTIN_LABELS and cat != DEFAULT_LABEL:
            if cat not in extra:
                extra.append(cat)
    out = BUILTIN_LABELS + extra + [DEFAULT_LABEL]
    return out if include_empty else [x for x in out if x != DEFAULT_LABEL]

# ————————————————————————————————————————————————————————————————
# display names
#
# A label id is what the rules match on, so a built-in id (stable/btc/eth/…) must
# keep its name or detection breaks. Renaming a built-in therefore stores a DISPLAY
# name instead, and renaming a user-created label rewrites its rules — either way
# the user gets the "rename a tag" behaviour without breaking classification.
# ————————————————————————————————————————————————————————————————


def _names_mtime():
    try:
        f = profiles.labels_file()
        return os.path.getmtime(f) if os.path.exists(f) else None
    except OSError:
        return None


def label_names():
    """{label id: display name} for labels the user renamed."""
    global _names_cache
    with _lock:
        mtime = _names_mtime()
        if _names_cache["data"] is None or _names_cache["mtime"] != mtime:
            data = {}
            try:
                with open(profiles.labels_file(), "r", encoding="utf-8") as f:
                    raw = json.load(f)
                if isinstance(raw, dict) and isinstance(raw.get("names"), dict):
                    data = {k: str(v) for k, v in raw["names"].items() if valid_label(k)}
            except FileNotFoundError:
                pass
            except Exception:  # noqa: BLE001
                data = {}
            _names_cache = {"mtime": mtime, "data": data}
        return dict(_names_cache["data"])


def _save_names(names):
    global _names_cache
    path = profiles.labels_file()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"names": names}, f, ensure_ascii=False, indent=2)
    _names_cache = {"mtime": _names_mtime(), "data": dict(names)}


def is_builtin_label(label):
    return label in BUILTIN_LABELS or label == DEFAULT_LABEL


def rename_label(old, new):
    """Rename a label.

    User-created label -> every rule using it is rewritten (ids are data).
    Built-in label      -> the id must not change (detection depends on it), so this
                           stores a display name and leaves matching alone.
    Returns (kind, label) where kind is "renamed" or "display".
    """
    old = str(old or "").strip()
    new = str(new or "").strip()
    if not valid_label(new):
        raise ValueError("label must be 1-24 chars: letters, digits, space, _ . -")
    if old == new:
        return "renamed", new
    if is_builtin_label(old):
        names = label_names()
        names[old] = new
        # a renamed custom label that already carried this display name is dropped
        _save_names(names)
        return "display", old
    if not valid_label(old):
        raise ValueError("unknown label")
    global _user_cache
    with _lock:
        entries = _load_user_entries()
        n = 0
        for e in entries:
            if _norm(e.get("category")) == _norm(old):
                e["category"] = new
                n += 1
        if not n:
            raise ValueError(f"label {old!r} is not in use")
        _save_user_entries(entries)
        _user_cache = {"mtime": _file_mtime(), "data": entries}
    return "renamed", new


def delete_label(label):
    """Remove a user-created label: its rules go, so its tokens fall back to `other`."""
    label = str(label or "").strip()
    if is_builtin_label(label):
        raise ValueError(f"{label!r} is built in and cannot be deleted")
    global _user_cache
    with _lock:
        entries = _load_user_entries()
        keep = [e for e in entries if _norm(e.get("category")) != _norm(label)]
        if len(keep) == len(entries):
            raise ValueError(f"label {label!r} is not in use")
        _save_user_entries(keep)
        _user_cache = {"mtime": _file_mtime(), "data": keep}
    names = label_names()
    if label in names:
        names.pop(label)
        _save_names(names)
    return True
