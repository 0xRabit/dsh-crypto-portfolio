# -*- coding: utf-8 -*-
"""Asset plan — the rules of `asset_plan.xlsx`, evaluated against the live snapshot.

The workbook is a personal operating manual: price tiers decide how much to buy each
week, a pool of "ammo" (spot stablecoins, half a vault position, two equity ETFs)
funds it in a fixed order, drawdown and take-profit rules say when to stop buying and
when to sell, and a geometric quarterly path is the yardstick for "am I on track?".

This module is that manual in code. It runs off the data the dashboard already has, so
advice refreshes itself with the daily fetch and needs no second data source:

    storage.get_tokens(date)   the crypto side, blacklist-filtered and asset-labelled
    storage.get_history()      daily totals, for the drawdown peak and 币本位 tracking
    plan.json                  what only the owner knows: cash, equities, goal shape
    plan_log.jsonl             what was actually executed, so "ammo left" is real

`analyze()` returns one dict: totals, tiers, the weekly buy plan, the ammo pool, goal
progress, every rule that fires and the ordered advice list the Plan tab renders.

Wording lives in the frontend dictionary, not here: rules and advice carry an i18n
`key` plus the numbers the sentence needs (the same convention as
`health.suggestions`), so one analysis serves both languages.
"""
import datetime
import json
import math
import os
import threading

from . import atomicio, health, profiles, storage, walletstore

# ————————————————————————————————————————————————————————————————
# configuration (profiles/<active>/plan.json)
# ————————————————————————————————————————————————————————————————
DEFAULTS = {
    "enabled": True,
    "emergency_fund": 2500.0,
    # the yardstick: total assets at the moment the plan started
    "start": {"date": "", "total": 0.0},
    # how new money is split, from 总览!C41:C43
    "allocation": {"BTC": 0.40, "ETH": 0.35, "HYPE+SOL": 0.25},
    # weekly budget per tier, from 价格维度!D6:D9
    "weekly": {"T1": 0.0, "T2": 400.0, "T3": 800.0, "T4": 1500.0},
    # tier boundaries per coin, from 价格维度!C12:D14 (each coin is judged on its own)
    "tiers": {
        "BTC": {"t1_above": 100000.0, "t2_floor": 80000.0, "t3_floor": 60000.0},
        "ETH": {"t1_above": 3000.0, "t2_floor": 2500.0, "t3_floor": 1800.0},
    },
    # which symbols belong to which bucket. Staked and wrapped forms count as the
    # underlying asset — the workbook's ETH line includes stETH, HYPE includes the
    # staked position, and so on.
    "buckets": {
        "BTC": ["BTC", "WBTC", "BTCB", "renBTC"],
        "ETH": ["ETH", "WETH", "stETH", "wstETH", "rETH", "cbETH"],
        "HYPE": ["HYPE", "HYPE (staked)", "HYPE (staked)"],
        "SOL": ["SOL", "SOL (staked)", "JitoSOL", "mSOL", "jupSOL", "bSOL"],
    },
    "bucket_order": ["BTC", "ETH", "HYPE", "SOL"],
    "hype_sol_bucket": "HYPE+SOL",
    "hlp_symbols": ["HLP"],
    "core": ["BTC", "ETH", "HYPE", "SOL"],
    # share-of-core bands for the rebalancing rules R1–R3
    "bands": {"BTC": [0.40, 0.55], "ETH": [0.25, 0.35], "HYPE+SOL": [0.0, 0.30]},
    # the ammo pool, in the order it may be spent (总览!A32:E38)
    "ammo": [
        {"id": "stables", "label": "Spot stablecoins (minus the emergency fund)",
         "priority": 1, "formula": "stables_minus_emergency", "amount": 0.0,
         "round_to": 0.0, "condition": "as soon as BTC is below the T1 line"},
        {"id": "hlp", "label": "Half the vault position", "priority": 2,
         "formula": "hlp_half", "amount": 0.0, "round_to": 100.0,
         "condition": "once the stablecoins are spent"},
        {"id": "etf1", "label": "Index ETF #1 (example)", "priority": 3,
         "formula": "manual", "amount": 10000.0, "round_to": 0.0,
         "condition": "after the first two; sell into strength, in slices"},
        {"id": "etf2", "label": "Index ETF #2 (example)", "priority": 4,
         "formula": "manual", "amount": 10000.0, "round_to": 0.0,
         "condition": "last resort, or when BTC breaks the absolute floor"},
    ],
    # assets the tracker cannot see. Placeholders on purpose: these are someone's
    # net worth, so the shipped defaults are illustrative — edit them in Plan settings
    # (a profile that has saved a plan keeps its own numbers in plan.json).
    "manual_assets": [
        {"name": "Pre-IPO equity (example)", "value": 20000.0,
         "role": "long-term hold, not ammo", "ammo_id": ""},
        {"name": "Index ETF #1 (example)", "value": 10000.0,
         "role": "ammo — third in line", "ammo_id": "etf1"},
        {"name": "Index ETF #2 (example)", "value": 10000.0,
         "role": "ammo — fourth in line", "ammo_id": "etf2"},
    ],
    "goals": [
        {"id": "x2_4y", "label": "4年翻倍", "years": 4.0, "multiple": 2.0},
        {"id": "x4_8y", "label": "8年4倍", "years": 8.0, "multiple": 4.0},
    ],
    # quarterly deployment stages and caps, from 时间维度!A6:O38
    "phases": [
        {"from": "2026Q4", "to": "2027Q4", "cap": 7000.0, "stage": "accumulate"},
        {"from": "2028Q1", "to": "2028Q4", "cap": 4500.0, "stage": "halving"},
        {"from": "2029Q1", "to": "2030Q2", "cap": 0.0, "stage": "take_profit"},
        {"from": "2030Q3", "to": "2032Q4", "cap": 0.0, "stage": "rebuild"},
        {"from": "2033Q1", "to": "2034Q4", "cap": 0.0, "stage": "take_profit"},
    ],
    "deviation": {"bad": -0.20, "good": 0.20},
    "cold_wallet_threshold": 2000.0,
}

# numeric thresholds of 止盈与再平衡规则, kept in code: they are the workbook's wording,
# not personal inputs. Every rule below cites its sheet id.
RULES = {
    "P2": {"btc_low": 120000.0, "btc_high": 150000.0, "sell_hype_sol": 0.20,
           "step": 0.10, "batches": "3-4"},
    "P3": {"btc_min": 150000.0, "sell_hype_sol": 0.30, "core_sell": [0.10, 0.15],
           "step_usd": 25000.0, "step_sell": 0.05, "btc_core_keep": 0.70},
    "P4": {"lead": 0.30, "lock": [0.10, 0.15]},
    "P5": {"lock": [0.25, 0.30]},
    "P6": {"single_max": 0.20, "trim_to": 0.15},
    "R2": {"drift_pp": 0.05},
    "R4": {"stables_min": 0.05, "target": [0.10, 0.20]},
    "R5": {"idle_usd": 2000.0},
    "D3": {"btc": 60000.0, "weeks": [6, 10]},
    "D4": {"drawdown": 0.60},
}

# how many sources a tier may spend, counting down the priority order (价格维度!H6:H9:
# T1 buys nothing, T2 only cash, T3 adds the vault and the first equity, T4 all of it).
# Counted by rank rather than by id, so renaming a source cannot silently disable it.
TIER_SOURCES = {"T1": 0, "T2": 1, "T3": 3, "T4": 4}
# HYPE+SOL has no tier of its own: it follows BTC (价格维度!C20)
TIER_FOLLOWS = {"HYPE+SOL": "BTC"}

_lock = threading.RLock()
_cache = {"mtime": None, "data": None}


def plan_file():
    return profiles.plan_file()


def log_file():
    return profiles.plan_log_file()


# ————————————————————————————————————————————————————————————————
# config
# ————————————————————————————————————————————————————————————————
def defaults():
    return json.loads(json.dumps(DEFAULTS))


def _num(value, where, minimum=None, maximum=None):
    try:
        n = float(value)
    except (TypeError, ValueError):
        raise ValueError("%s must be a number" % where)
    if n != n or n in (float("inf"), float("-inf")):
        raise ValueError("%s must be a finite number" % where)
    if minimum is not None and n < minimum:
        raise ValueError("%s must be at least %s" % (where, minimum))
    if maximum is not None and n > maximum:
        raise ValueError("%s must be at most %s" % (where, maximum))
    return n


def _tier_bounds(raw, coin):
    out = {}
    base = DEFAULTS["tiers"][coin]
    for key in base:
        out[key] = _num((raw or {}).get(key, base[key]), "%s.%s" % (coin, key), minimum=0.0)
    if not (out["t3_floor"] < out["t2_floor"] < out["t1_above"]):
        raise ValueError("%s: floors must rise (t3 < t2 < t1)" % coin)
    return out


def normalize(raw):
    """Validate a partial config and merge it over the defaults."""
    if raw is not None and not isinstance(raw, dict):
        raise ValueError("plan config must be a JSON object")
    raw = raw or {}
    out = defaults()

    out["enabled"] = bool(raw.get("enabled", out["enabled"]))
    out["emergency_fund"] = _num(raw.get("emergency_fund", out["emergency_fund"]),
                                 "emergency_fund", minimum=0.0)

    start = raw.get("start")
    if isinstance(start, dict):
        date = str(start.get("date") or "").strip()
        if date:
            try:
                datetime.date.fromisoformat(date)
            except ValueError:
                raise ValueError("start.date must be YYYY-MM-DD")
        out["start"] = {"date": date,
                        "total": _num(start.get("total", 0.0), "start.total", minimum=0.0)}

    for key, label in (("BTC", "BTC"), ("ETH", "ETH"), ("HYPE+SOL", "HYPE+SOL")):
        if isinstance(raw.get("allocation"), dict) and key in raw["allocation"]:
            out["allocation"][key] = _num(raw["allocation"][key], "allocation.%s" % key,
                                          minimum=0.0, maximum=1.0)
    total_alloc = sum(out["allocation"].values())
    if abs(total_alloc - 1.0) > 1e-6:
        raise ValueError("allocation must add up to 100%% (currently %.1f%%)"
                         % (total_alloc * 100))

    for tier in out["weekly"]:
        if isinstance(raw.get("weekly"), dict) and tier in raw["weekly"]:
            out["weekly"][tier] = _num(raw["weekly"][tier], "weekly.%s" % tier, minimum=0.0)
    if not any(out["weekly"].values()):
        raise ValueError("at least one tier must have a weekly amount")

    for coin in ("BTC", "ETH"):
        if isinstance(raw.get("tiers"), dict) and coin in raw["tiers"]:
            out["tiers"][coin] = _tier_bounds(raw["tiers"][coin], coin)

    if isinstance(raw.get("buckets"), dict):
        for key, symbols in raw["buckets"].items():
            if key not in out["buckets"]:
                continue
            if not isinstance(symbols, list):
                raise ValueError("buckets.%s must be a list of symbols" % key)
            out["buckets"][key] = [str(s).strip() for s in symbols if str(s).strip()]

    if isinstance(raw.get("hlp_symbols"), list):
        out["hlp_symbols"] = [str(s).strip() for s in raw["hlp_symbols"] if str(s).strip()]

    if isinstance(raw.get("manual_assets"), list):
        assets = []
        for i, item in enumerate(raw["manual_assets"]):
            if not isinstance(item, dict):
                raise ValueError("manual_assets[%d] must be an object" % i)
            name = str(item.get("name") or "").strip()
            if not name:
                raise ValueError("manual_assets[%d].name is required" % i)
            assets.append({"name": name,
                           "value": _num(item.get("value", 0.0),
                                         "manual_assets[%d].value" % i, minimum=0.0),
                           "role": str(item.get("role") or "").strip(),
                           "ammo_id": str(item.get("ammo_id") or "").strip()})
        out["manual_assets"] = assets

    if isinstance(raw.get("ammo"), list) and raw["ammo"]:
        ammo = []
        for i, item in enumerate(raw["ammo"]):
            if not isinstance(item, dict):
                raise ValueError("ammo[%d] must be an object" % i)
            formula = str(item.get("formula") or "manual").strip()
            if formula not in ("manual", "stables_minus_emergency", "hlp_half"):
                raise ValueError("ammo[%d].formula must be manual / stables_minus_emergency"
                                 " / hlp_half" % i)
            ammo.append({"id": str(item.get("id") or "ammo%d" % i).strip(),
                         "label": str(item.get("label") or item.get("id") or "").strip(),
                         "priority": int(_num(item.get("priority", i + 1),
                                              "ammo[%d].priority" % i, minimum=1)),
                         "formula": formula,
                         "amount": _num(item.get("amount", 0.0), "ammo[%d].amount" % i,
                                        minimum=0.0),
                         "round_to": _num(item.get("round_to", 0.0) or 0.0,
                                          "ammo[%d].round_to" % i, minimum=0.0),
                         "condition": str(item.get("condition") or "").strip()})
        out["ammo"] = sorted(ammo, key=lambda a: a["priority"])

    if isinstance(raw.get("goals"), list) and raw["goals"]:
        goals = []
        for i, item in enumerate(raw["goals"]):
            if not isinstance(item, dict):
                raise ValueError("goals[%d] must be an object" % i)
            goals.append({"id": str(item.get("id") or "goal%d" % i).strip(),
                          "label": str(item.get("label") or item.get("id") or "").strip(),
                          "years": _num(item.get("years", 4), "goals[%d].years" % i,
                                        minimum=0.25, maximum=60),
                          "multiple": _num(item.get("multiple", 2), "goals[%d].multiple" % i,
                                           minimum=1.01, maximum=1000)})
        out["goals"] = goals

    if isinstance(raw.get("phases"), list) and raw["phases"]:
        phases = []
        for i, item in enumerate(raw["phases"]):
            if not isinstance(item, dict):
                raise ValueError("phases[%d] must be an object" % i)
            phases.append({"from": str(item.get("from") or "").strip(),
                           "to": str(item.get("to") or "").strip(),
                           "cap": _num(item.get("cap", 0.0), "phases[%d].cap" % i, minimum=0.0),
                           "stage": str(item.get("stage") or "accumulate").strip()})
        out["phases"] = sorted(phases, key=lambda p: _quarter_key(p["from"]))

    dev = raw.get("deviation")
    if isinstance(dev, dict):
        out["deviation"] = {"bad": _num(dev.get("bad", out["deviation"]["bad"]),
                                        "deviation.bad", maximum=0.0),
                            "good": _num(dev.get("good", out["deviation"]["good"]),
                                         "deviation.good", minimum=0.0)}

    out["cold_wallet_threshold"] = _num(
        raw.get("cold_wallet_threshold", out["cold_wallet_threshold"]),
        "cold_wallet_threshold", minimum=0.0)
    return out


def _mtime():
    try:
        path = plan_file()
        return os.path.getmtime(path) if os.path.exists(path) else None
    except OSError:
        return None


def load():
    """Config of the active profile; falls back to the defaults on any problem."""
    global _cache
    try:
        with _lock:
            mtime = _mtime()
            if _cache["data"] is None or _cache["mtime"] != mtime:
                raw = None
                path = plan_file()
                if os.path.exists(path):
                    try:
                        with open(path, "r", encoding="utf-8") as fh:
                            raw = json.load(fh)
                    except Exception:                            # noqa: BLE001
                        raw = None
                try:
                    data = normalize(raw)
                except ValueError:
                    data = defaults()
                _cache = {"mtime": mtime, "data": data}
            return json.loads(json.dumps(_cache["data"]))
    except Exception:                                            # noqa: BLE001
        return defaults()


def save(raw):
    global _cache
    data = normalize(raw)
    with _lock:
        atomicio.write_json(plan_file(), data)
        _cache = {"mtime": _mtime(), "data": data}
        return json.loads(json.dumps(data))


def reset_cache():
    global _cache
    with _lock:
        _cache = {"mtime": None, "data": None}


# ————————————————————————————————————————————————————————————————
# execution log (profiles/<active>/plan_log.jsonl)
# ————————————————————————————————————————————————————————————————
LOG_FIELDS = ("date", "asset", "side", "price", "amount", "qty", "source", "note")


def log_read(limit=None):
    """Newest-first list of executed operations."""
    path = log_file()
    if not os.path.exists(path):
        return []
    rows = []
    try:
        with open(path, "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    rows.append(json.loads(line))
                except ValueError:
                    continue
    except OSError:
        return []
    rows.reverse()
    return rows[:limit] if limit else rows


def log_append(entry):
    """Record one buy/sell. `qty` is derived when a price is given."""
    if not isinstance(entry, dict):
        raise ValueError("entry must be a JSON object")
    date = str(entry.get("date") or datetime.date.today().isoformat()).strip()
    try:
        datetime.date.fromisoformat(date)
    except ValueError:
        raise ValueError("date must be YYYY-MM-DD")
    amount = _num(entry.get("amount", 0.0), "amount", minimum=0.0)
    if amount <= 0:
        raise ValueError("amount must be greater than 0")
    price = _num(entry.get("price", 0.0) or 0.0, "price", minimum=0.0)
    row = {
        "date": date,
        "asset": str(entry.get("asset") or "").strip(),
        "side": "sell" if str(entry.get("side") or "buy").lower() == "sell" else "buy",
        "price": price,
        "amount": amount,
        "qty": round(amount / price, 10) if price > 0 else _num(entry.get("qty", 0.0) or 0.0,
                                                               "qty", minimum=0.0),
        "source": str(entry.get("source") or "").strip(),
        "note": str(entry.get("note") or "").strip()[:200],
    }
    if not row["asset"]:
        raise ValueError("asset is required")
    with _lock:
        path = log_file()
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
            fh.flush()
            os.fsync(fh.fileno())
    return row


def log_remove(index):
    """Delete entry #index as listed (newest first). Returns True when it existed."""
    with _lock:
        rows = log_read()
        if index < 0 or index >= len(rows):
            return False
        rows.pop(index)
        rows.reverse()                                  # back to oldest-first on disk
        atomicio.write_text(log_file(),
                            "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
    return True


# ————————————————————————————————————————————————————————————————
# calendar helpers
# ————————————————————————————————————————————————————————————————
def quarter_label(date):
    """'2026Q4' for a date or ISO string."""
    if isinstance(date, str):
        date = datetime.date.fromisoformat(date)
    return "%dQ%d" % (date.year, (date.month - 1) // 3 + 1)


def _quarter_key(label):
    """'2026Q4' -> 20264, so quarters sort and index arithmetically."""
    try:
        year, q = str(label).upper().split("Q")
        return int(year) * 10 + int(q)
    except Exception:                                        # noqa: BLE001
        return 0


def quarter_index(label, start_label):
    """How many quarters after `start_label` this one is (0 for the start)."""
    return (_quarter_key(label) // 10 - _quarter_key(start_label) // 10) * 4 + \
           (_quarter_key(label) % 10 - _quarter_key(start_label) % 10)


def phase_for(label, phases):
    """The deployment phase a quarter belongs to, or the last one as a fallback."""
    key = _quarter_key(label)
    for p in phases:
        if _quarter_key(p.get("from")) <= key <= _quarter_key(p.get("to")):
            return p
    first = _quarter_key(phases[0]["from"]) if phases else 0
    return phases[0] if (phases and key < first) else (phases[-1] if phases else
                                                       {"cap": 0.0, "stage": "accumulate"})


# ————————————————————————————————————————————————————————————————
# market helpers
# ————————————————————————————————————————————————————————————————
def tier_of(price, bounds):
    """T1 (above the accumulation ceiling) … T4 (below the absolute floor)."""
    if price is None or price <= 0:
        return None
    if price > bounds["t1_above"]:
        return "T1"
    if price >= bounds["t2_floor"]:
        return "T2"
    if price >= bounds["t3_floor"]:
        return "T3"
    return "T4"


def _bucket_rows(rows, symbols):
    wanted = {s.lower() for s in symbols}
    return [r for r in rows if str(r.get("symbol") or "").strip().lower() in wanted]


def _usd(rows):
    return round(sum(float(r.get("usd") or 0.0) for r in rows), 2)


def _price(rows, symbols):
    """Market price of a bucket.

    Deliberately not a value-weighted average: airdropped spam regularly reuses a
    real symbol — this profile carries a fake `ETH` with 3.8e58 units and no price —
    and one worthless row would drag any average to zero. The largest *priced*
    holding sets the bucket price instead, and rows worth nothing are ignored.
    """
    wanted = {s.lower() for s in symbols}
    live = [r for r in rows
            if str(r.get("symbol") or "").strip().lower() in wanted
            and float(r.get("usd") or 0.0) > 0
            and float(r.get("amount") or 0.0) > 0
            and float(r.get("price") or 0.0) > 0]
    if live:
        biggest = max(live, key=lambda r: float(r.get("usd") or 0.0))
        return round(float(biggest["price"]), 8)
    # nothing held (or nothing priced): still read the feed if a row reports a price
    for symbol in [s.lower() for s in symbols]:
        for r in rows:
            if (str(r.get("symbol") or "").strip().lower() == symbol
                    and float(r.get("price") or 0.0) > 0
                    and float(r.get("amount") or 0.0) > 0):
                return round(float(r["price"]), 8)
    return None


def _round_to(value, step):
    if not step or step <= 0:
        return round(value, 2)
    return round(round(value / step) * step, 2)


def _pct(part, whole):
    return round(part / whole * 100.0, 2) if whole else 0.0


# ————————————————————————————————————————————————————————————————
# the analysis
# ————————————————————————————————————————————————————————————————
def _start_of(cfg, history, manual_total):
    """Effective plan start: the configured one, else the oldest snapshot on record."""
    start = cfg.get("start") or {}
    if start.get("date") and float(start.get("total") or 0) > 0:
        return {"date": start["date"], "total": round(float(start["total"]), 2),
                "source": "config"}
    dates = history.get("dates") or []
    totals = history.get("totals") or []
    if dates:
        return {"date": dates[0], "total": round(float(totals[0] or 0.0) + manual_total, 2),
                "source": "history"}
    return {"date": datetime.date.today().isoformat(), "total": round(manual_total, 2),
            "source": "default"}


def _denominated(history, rows, total_now, btc_symbols, eth_symbols, start_date):
    """Total assets expressed in BTC / ETH, and how that compares with the start."""
    def qty_on(date):
        total = None
        for i, d in enumerate(history.get("dates") or []):
            if d == date:
                total = float((history.get("totals") or [])[i] or 0.0)
                break
        if total is None:
            return None
        day_rows = storage.get_tokens(date)
        out = {}
        for key, symbols in (("btc", btc_symbols), ("eth", eth_symbols)):
            price = _price(day_rows, symbols)
            out[key] = round(total / price, 8) if price else None
        return out

    base = qty_on(start_date) or {}
    out = {}
    for key, symbols in (("btc", btc_symbols), ("eth", eth_symbols)):
        price = _price(rows, symbols)
        qty = round(total_now / price, 8) if price else None
        b = base.get(key)
        out[key] = {"price": price, "qty": qty, "baseline": b,
                    "delta": (round(qty / b - 1, 4) if qty and b else None)}
    return out


def analyze(date=None, now=None):
    """Everything the Plan tab shows, for one snapshot (default: the newest)."""
    cfg = load()
    snapshot = storage.get_snapshot(date) if date else storage.get_latest_snapshot()
    if not snapshot:
        return {"ok": False, "error": "no-snapshot", "config": cfg}
    date = snapshot["date"]
    rows = storage.get_tokens(date)

    # ---- totals -------------------------------------------------------
    bucket_values, bucket_prices, bucket_rows = {}, {}, {}
    for key in cfg["bucket_order"]:
        symbols = cfg["buckets"].get(key) or []
        sel = _bucket_rows(rows, symbols)
        bucket_rows[key] = sel
        bucket_values[key] = _usd(sel)
        bucket_prices[key] = _price(rows, symbols)
    hlp_rows = _bucket_rows(rows, cfg["hlp_symbols"])
    hlp_value = _usd(hlp_rows)
    labelled_stables = [r for r in rows if r.get("cat") == "stable"]
    stable_value = _usd(labelled_stables)
    spot_stables = round(max(0.0, stable_value - hlp_value), 2)
    crypto_total = round(sum(float(r.get("usd") or 0.0) for r in rows), 2)
    manual = [{"name": a["name"], "value": round(float(a["value"]), 2),
               "role": a.get("role", ""), "ammo_id": a.get("ammo_id", "")}
              for a in cfg["manual_assets"]]
    manual_total = round(sum(a["value"] for a in manual), 2)
    total = round(crypto_total + manual_total, 2)
    core_value = round(sum(bucket_values.get(k, 0.0) for k in cfg["core"]), 2)
    hype_sol = round(bucket_values.get("HYPE", 0.0) + bucket_values.get("SOL", 0.0), 2)

    # ---- history: peak for the drawdown rules, oldest total for the start ----
    history = storage.get_history()
    totals = [float(t or 0.0) for t in (history.get("totals") or [])]
    peak_crypto = max(totals) if totals else crypto_total
    peak_total = round(peak_crypto + manual_total, 2)
    drawdown = round(total / peak_total - 1, 4) if peak_total > 0 else 0.0
    start = _start_of(cfg, history, manual_total)

    # ---- tiers and the weekly plan ------------------------------------
    tiers, weekly_rows = {}, []
    weekly_total = 0.0
    for key in cfg["bucket_order"]:
        price = bucket_prices.get(key)
        bounds = cfg["tiers"].get(key)
        tier = tier_of(price, bounds) if bounds else None
        entry = {"bucket": key, "price": price, "tier": tier, "bounds": bounds,
                 "value": bucket_values.get(key, 0.0)}
        tiers[key] = entry
    hys_tier = tiers.get("BTC", {}).get("tier")          # HYPE+SOL follows BTC
    tiers["HYPE+SOL"] = {"bucket": "HYPE+SOL", "price": None, "tier": hys_tier,
                         "bounds": cfg["tiers"].get("BTC"), "follows": "BTC",
                         "value": hype_sol}
    for key in ("BTC", "ETH", "HYPE+SOL"):
        entry = tiers[key]
        tier = entry.get("tier")
        base = float(cfg["weekly"].get(tier, 0.0)) if tier else 0.0
        share = float(cfg["allocation"].get(key, 0.0))
        amount = round(base * share, 2)
        weekly_rows.append({"bucket": key, "tier": tier, "weekly_base": base,
                            "share": share, "amount": amount,
                            "qty": (round(amount / entry["price"], 10)
                                    if amount and entry.get("price") else None),
                            "price": entry.get("price")})
        weekly_total += amount
    weekly_total = round(weekly_total, 2)

    # ---- ammo pool -----------------------------------------------------
    log = log_read()
    used_by_source = {}
    for r in log:
        if r.get("side") == "buy" and r.get("source"):
            used_by_source[r["source"]] = round(
                used_by_source.get(r["source"], 0.0) + float(r.get("amount") or 0.0), 2)
    rank = TIER_SOURCES.get(tiers.get("BTC", {}).get("tier") or "T2", 1)
    ammo_rows, ammo_total = [], {"planned": 0.0, "used": 0.0, "remaining": 0.0}
    for a in sorted(cfg["ammo"], key=lambda x: x["priority"]):
        if a["formula"] == "stables_minus_emergency":
            planned = round(max(0.0, spot_stables - float(cfg["emergency_fund"])), 2)
        elif a["formula"] == "hlp_half":
            planned = _round_to(max(0.0, hlp_value / 2.0), a.get("round_to") or 0.0)
        else:
            planned = round(float(a.get("amount") or 0.0), 2)
        used = used_by_source.get(a["id"], 0.0)
        remaining = round(max(0.0, planned - used), 2)
        ammo_rows.append({"id": a["id"], "label": a["label"], "priority": a["priority"],
                          "formula": a["formula"], "planned": planned, "used": used,
                          "remaining": remaining, "condition": a.get("condition", ""),
                          "allowed": False})
        ammo_total["planned"] += planned
        ammo_total["used"] += used
        ammo_total["remaining"] += remaining
    # the tier decides how deep into the queue this week's money may reach
    allowed = [a["id"] for a in ammo_rows[:max(0, int(rank))]]
    for a in ammo_rows:
        a["allowed"] = a["id"] in allowed
    ammo_total = {k: round(v, 2) for k, v in ammo_total.items()}
    ammo_total["used_pct"] = _pct(ammo_total["used"], ammo_total["planned"])
    runnable = [a for a in ammo_rows if a["allowed"] and a["remaining"] > 0]
    next_source = runnable[0] if runnable else None
    runway_weeks = (round(ammo_total["remaining"] / weekly_total, 1)
                    if weekly_total > 0 else None)

    # ---- calendar: quarter, cap, stage ---------------------------------
    today = now or datetime.date.today()
    try:
        snap_date = datetime.date.fromisoformat(date)
    except ValueError:
        snap_date = today
    q_label = quarter_label(snap_date)
    phase = phase_for(q_label, cfg["phases"])
    start_label = quarter_label(datetime.date.fromisoformat(start["date"])) \
        if start.get("date") else q_label
    q_index = max(0, quarter_index(q_label, start_label))
    spent_this_quarter = round(sum(float(r.get("amount") or 0.0) for r in log
                                   if r.get("side") == "buy"
                                   and quarter_label(r.get("date") or q_label) == q_label), 2)
    cap = float(phase.get("cap") or 0.0)
    quarter = {"label": q_label, "index": q_index, "stage": phase.get("stage"),
               "cap": cap, "spent": spent_this_quarter,
               "remaining": round(max(0.0, cap - spent_this_quarter), 2),
               "capped": cap > 0 and weekly_total > 0
               and spent_this_quarter + weekly_total > cap}

    # ---- goals ---------------------------------------------------------
    elapsed_years = None
    if start.get("date"):
        try:
            elapsed_years = max(0.0, (snap_date - datetime.date.fromisoformat(start["date"])
                                      ).days / 365.25)
        except ValueError:
            elapsed_years = None
    goals = []
    for g in cfg["goals"]:
        years = float(g["years"])
        multiple = float(g["multiple"])
        required = multiple ** (1.0 / years) - 1.0
        quarterly = multiple ** (1.0 / (years * 4)) - 1.0
        target = round(start["total"] * multiple, 2)
        quarters_elapsed = max(0, quarter_index(q_label, start_label))
        path = round(start["total"] * (1.0 + quarterly) ** quarters_elapsed, 2)
        deviation = round(total / path - 1.0, 4) if path > 0 else 0.0
        current = None
        on_pace = None
        if elapsed_years and elapsed_years > 0 and start["total"] > 0:
            current = round((total / start["total"]) ** (1.0 / elapsed_years) - 1.0, 4)
            on_pace = current >= required
        if deviation < cfg["deviation"]["bad"]:
            status = "behind"
        elif deviation > cfg["deviation"]["good"]:
            status = "ahead"
        else:
            status = "on_track"
        goals.append({"id": g["id"], "label": g["label"], "years": years,
                      "multiple": multiple, "target": target, "path": path,
                      "required_cagr": round(required, 4),
                      "required_quarterly": round(quarterly, 4),
                      "current_cagr": current, "on_pace": on_pace,
                      "progress": round(total / target, 4) if target else 0.0,
                      "deviation": deviation, "status": status,
                      "deadline": (datetime.date.fromisoformat(start["date"])
                                   .replace(year=datetime.date.fromisoformat(start["date"]).year
                                            + int(years))).isoformat()
                      if start.get("date") else None})

    # ---- 币本位 ---------------------------------------------------------
    denominated = _denominated(history, rows, total, cfg["buckets"]["BTC"],
                               cfg["buckets"]["ETH"], start["date"])

    # ---- core mix (R1–R3) ------------------------------------------------
    core_mix = []
    for key in ("BTC", "ETH", "HYPE+SOL"):
        value = bucket_values.get(key, 0.0) if key != "HYPE+SOL" else hype_sol
        share = value / core_value if core_value else 0.0
        band = cfg["bands"].get(key) or [0.0, 1.0]
        status = "ok"
        if share > band[1] + RULES["R2"]["drift_pp"]:
            status = "high"
        elif share < band[0] - RULES["R2"]["drift_pp"]:
            status = "low"
        core_mix.append({"bucket": key, "value": round(value, 2), "share": round(share, 4),
                         "band": band, "status": status})

    # ---- R5: idle crypto sitting on an exchange --------------------------
    kinds = {}
    try:
        kinds = {w.get("name"): health.storage_kind(w) for w in walletstore.all_wallets()}
    except Exception:                                        # noqa: BLE001
        kinds = {}
    idle_exchange = 0.0
    for key in ("BTC", "ETH"):
        for r in bucket_rows.get(key, []):
            if kinds.get(r.get("wallet")) == "cex":
                idle_exchange += float(r.get("usd") or 0.0)
    idle_exchange = round(idle_exchange, 2)

    ctx = {"cfg": cfg, "date": date, "total": total, "crypto_total": crypto_total,
           "core_value": core_value, "hype_sol": hype_sol, "stable_value": stable_value,
           "spot_stables": spot_stables, "hlp_value": hlp_value, "manual_total": manual_total,
           "bucket_values": bucket_values, "bucket_prices": bucket_prices,
           "tiers": tiers, "weekly_rows": weekly_rows, "weekly_total": weekly_total,
           "ammo_rows": ammo_rows, "ammo_total": ammo_total, "next_source": next_source,
           "runway_weeks": runway_weeks, "quarter": quarter, "goals": goals,
           "drawdown": drawdown, "peak_total": peak_total, "start": start,
           "core_mix": core_mix, "idle_exchange": idle_exchange,
           "denominated": denominated, "log": log}

    rules = _rules(ctx)
    advice = _advice(ctx, rules)

    return {
        "ok": True,
        "date": date,
        "file": plan_file(),
        "log_file": log_file(),
        "created_at": snapshot.get("created_at"),
        "generated_at": datetime.datetime.now().isoformat(timespec="seconds"),
        "stale_days": (today - snap_date).days,
        "config": cfg,
        "start": start,
        "totals": {"crypto": crypto_total, "manual": manual_total, "total": total,
                   "core": core_value, "hype_sol": hype_sol, "stables": stable_value,
                   "spot_stables": spot_stables, "hlp": hlp_value,
                   "peak": peak_total, "drawdown": drawdown},
        "manual_assets": manual,
        "buckets": [dict(tiers[k], **{"value": bucket_values.get(k, 0.0)})
                    for k in cfg["bucket_order"]],
        "tiers": tiers,
        "weekly": {"rows": weekly_rows, "total": weekly_total,
                   "runway_weeks": runway_weeks,
                   "sources": TIER_SOURCES.get(tiers.get("BTC", {}).get("tier") or "", [])},
        "ammo": {"rows": ammo_rows, "planned": ammo_total["planned"],
                 "used": ammo_total["used"], "remaining": ammo_total["remaining"],
                 "used_pct": ammo_total["used_pct"],
                 "next": next_source, "order": allowed},
        "quarter": quarter,
        "goals": goals,
        "core_mix": core_mix,
        "denominated": denominated,
        "rules": rules,
        "advice": advice,
        "log": log[:50],
    }


# ————————————————————————————————————————————————————————————————
# rules from 止盈与再平衡规则
# ————————————————————————————————————————————————————————————————
def _rule(key, group, severity, **params):
    return {"key": key, "group": group, "severity": severity, "params": params}


def _rules(ctx):
    """Every rule from the workbook that currently fires, newest severity first."""
    cfg = ctx["cfg"]
    out = []
    btc_price = ctx["bucket_prices"].get("BTC")
    eth_price = ctx["bucket_prices"].get("ETH")
    btc_tier = ctx["tiers"].get("BTC", {}).get("tier")
    p2, p3 = RULES["P2"], RULES["P3"]

    # --- take profit (P1–P6) ------------------------------------------
    if btc_tier == "T1" or (eth_price and cfg["tiers"]["ETH"]
                            and eth_price > cfg["tiers"]["ETH"]["t1_above"]):
        out.append(_rule("ruleP1", "take_profit", "watch",
                         btc=btc_price, eth=eth_price,
                         btc_line=cfg["tiers"]["BTC"]["t1_above"],
                         eth_line=cfg["tiers"]["ETH"]["t1_above"]))
    if btc_price and p2["btc_low"] <= btc_price < p2["btc_high"] and ctx["hype_sol"] > 0:
        out.append(_rule("ruleP2", "take_profit", "act",
                         btc=btc_price, pct=p2["sell_hype_sol"],
                         amount=round(ctx["hype_sol"] * p2["sell_hype_sol"], 2),
                         step_pct=p2["step"], batches=p2["batches"]))
    if btc_price and btc_price >= p3["btc_min"]:
        out.append(_rule("ruleP3", "take_profit", "act",
                         btc=btc_price, pct=p3["sell_hype_sol"],
                         amount=round(ctx["hype_sol"] * p3["sell_hype_sol"], 2),
                         core_pct=p3["core_sell"], step=p3["step_usd"],
                         step_pct=p3["step_sell"], keep=p3["btc_core_keep"]))
    for g in ctx["goals"]:
        if g["status"] == "ahead" and g["deviation"] >= RULES["P4"]["lead"]:
            out.append(_rule("ruleP4", "take_profit", "watch", label=g["label"],
                             deviation=g["deviation"], lock=RULES["P4"]["lock"],
                             amount=round(ctx["total"] * RULES["P4"]["lock"][0], 2)))
        if g["progress"] >= 1.0 and g["years"] >= 4:
            out.append(_rule("ruleP5", "take_profit", "watch", label=g["label"],
                             lock=RULES["P5"]["lock"],
                             amount=round(ctx["total"] * RULES["P5"]["lock"][0], 2)))
    for key in ("HYPE", "SOL"):
        value = ctx["bucket_values"].get(key, 0.0)
        share = value / ctx["core_value"] if ctx["core_value"] else 0.0
        if share > RULES["P6"]["single_max"]:
            out.append(_rule("ruleP6", "take_profit", "watch", bucket=key,
                             share=round(share, 4), max_share=RULES["P6"]["single_max"],
                             trim_to=RULES["P6"]["trim_to"],
                             amount=round(value - ctx["core_value"] * RULES["P6"]["trim_to"], 2)))

    # --- rebalancing (R1–R5) ------------------------------------------
    for row in ctx["core_mix"]:
        if row["status"] == "ok":
            continue
        key = "ruleR3" if btc_tier == "T1" else "ruleR2"
        out.append(_rule(key, "rebalance", "act" if btc_tier == "T1" else "watch",
                         bucket=row["bucket"], share=row["share"],
                         band=row["band"], drift=RULES["R2"]["drift_pp"]))
    stable_share = ctx["stable_value"] / ctx["total"] if ctx["total"] else 0.0
    if btc_tier == "T1" and stable_share < RULES["R4"]["stables_min"]:
        out.append(_rule("ruleR4", "rebalance", "act", share=round(stable_share, 4),
                         minimum=RULES["R4"]["stables_min"], target=RULES["R4"]["target"]))
    if ctx["idle_exchange"] > RULES["R5"]["idle_usd"]:
        out.append(_rule("ruleR5", "rebalance", "watch", usd=ctx["idle_exchange"],
                         threshold=RULES["R5"]["idle_usd"]))

    # --- drawdown (D1–D4); D5/D6 are judgement calls and stay as standing notes ---
    dd = ctx["drawdown"]
    if dd <= -RULES["D4"]["drawdown"]:
        out.append(_rule("ruleD4", "drawdown", "watch", drawdown=dd,
                         ammo=ctx["ammo_total"]["remaining"]))
    elif btc_price and btc_price < RULES["D3"]["btc"]:
        out.append(_rule("ruleD3", "drawdown", "act", btc=btc_price,
                         line=RULES["D3"]["btc"], weeks=RULES["D3"]["weeks"],
                         remaining=ctx["ammo_total"]["remaining"]))
    elif dd <= -0.30:
        out.append(_rule("ruleD2", "drawdown", "watch", drawdown=dd))
    elif dd <= -0.20:
        out.append(_rule("ruleD1", "drawdown", "info", drawdown=dd,
                         remaining=ctx["ammo_total"]["remaining"]))
    if ctx["hlp_value"] > 0:
        out.append(_rule("ruleD5", "drawdown", "info", usd=ctx["hlp_value"]))

    order = {"act": 0, "watch": 1, "info": 2}
    out.sort(key=lambda r: (order.get(r["severity"], 3), r["key"]))
    return out


# ————————————————————————————————————————————————————————————————
# the advice the tab leads with
# ————————————————————————————————————————————————————————————————
def _advice(ctx, rules):
    """Ordered actions for this snapshot: what to do, with what money, and why."""
    cfg = ctx["cfg"]
    week = ctx["weekly_rows"]
    btc_tier = ctx["tiers"].get("BTC", {}).get("tier")
    quarter = ctx["quarter"]
    nxt = ctx["next_source"]
    out = []

    if quarter["stage"] == "take_profit":
        out.append({"key": "advStageTakeProfit", "severity": "watch",
                    "params": {"stage": quarter["stage"]}})
    elif quarter["stage"] == "halving":
        out.append({"key": "advStageHalving", "severity": "info",
                    "params": {"stage": quarter["stage"]}})
    elif quarter["stage"] == "rebuild":
        out.append({"key": "advStageRebuild", "severity": "info",
                    "params": {"stage": quarter["stage"]}})

    if ctx["weekly_total"] > 0:
        by = {r["bucket"]: r for r in week}
        params = {"total": ctx["weekly_total"],
                  "btc": (by.get("BTC") or {}).get("amount", 0.0),
                  "eth": (by.get("ETH") or {}).get("amount", 0.0),
                  "hys": (by.get("HYPE+SOL") or {}).get("amount", 0.0),
                  "tier_btc": (by.get("BTC") or {}).get("tier"),
                  "tier_eth": (by.get("ETH") or {}).get("tier")}
        out.append({"key": "advWeekly", "severity": "act", "params": params})
        if nxt:
            out.append({"key": "advSource", "severity": "act",
                        "params": {"source": nxt["label"], "left": nxt["remaining"],
                                   "used": nxt["used"], "planned": nxt["planned"]}})
        else:
            out.append({"key": "advNoAmmo", "severity": "watch", "params": {}})
        if quarter["capped"]:
            out.append({"key": "advQuarterCap", "severity": "watch",
                        "params": {"spent": quarter["spent"], "cap": quarter["cap"],
                                   "weekly": ctx["weekly_total"],
                                   "room": quarter["remaining"]}})
        elif quarter["cap"] > 0:
            out.append({"key": "advQuarterRoom", "severity": "info",
                        "params": {"spent": quarter["spent"], "cap": quarter["cap"],
                                   "remaining": quarter["remaining"]}})
        if ctx["runway_weeks"] is not None:
            out.append({"key": "advRunway", "severity": "info",
                        "params": {"weeks": ctx["runway_weeks"],
                                   "months": round(ctx["runway_weeks"] / 4.33, 1),
                                   "tier": btc_tier}})
    else:
        out.append({"key": "advStopBuying", "severity": "act",
                    "params": {"tier": btc_tier,
                               "btc": ctx["bucket_prices"].get("BTC"),
                               "line": cfg["tiers"]["BTC"]["t1_above"]}})

    if btc_tier == "T4":
        out.append({"key": "advT4Rush", "severity": "act",
                    "params": {"remaining": ctx["ammo_total"]["remaining"],
                               "weeks": RULES["D3"]["weeks"],
                               "btc": ctx["bucket_prices"].get("BTC")}})
    if ctx["idle_exchange"] > cfg["cold_wallet_threshold"]:
        out.append({"key": "advColdWallet", "severity": "act",
                    "params": {"usd": ctx["idle_exchange"],
                               "threshold": ctx["cfg"]["cold_wallet_threshold"]}})
    if any(v > 0 for k, v in ctx["bucket_values"].items() if k in ("HYPE", "SOL")):
        out.append({"key": "advStake", "severity": "info", "params": {}})
    out.append({"key": "advDiscipline", "severity": "info",
                "params": {"sources": [r["label"] for r in ctx["ammo_rows"]]}})
    out.append({"key": "advBottomLine", "severity": "info",
                "params": {"emergency": cfg["emergency_fund"]}})

    order = {"act": 0, "watch": 1, "info": 2}
    rank = {"advT4Rush": -1, "advColdWallet": 1}
    out.sort(key=lambda a: (order.get(a["severity"], 3), rank.get(a["key"], 0)))
    return out
