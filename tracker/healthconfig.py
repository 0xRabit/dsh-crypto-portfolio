# -*- coding: utf-8 -*-
"""Health-report thresholds (per profile).

The three checks in `tracker/health.py` are only as useful as their thresholds:
"60 % of the portfolio is on-chain" is alarming for one investor and normal for
another, and the numbers that make sense depend on the currency you think in and
how much risk you are willing to carry. So they are configuration, stored in
profiles/<active>/health.json, editable in Settings, and validated on the way in.

Each pair is a *share of the portfolio in percent*:

    volatility     warning/danger : share that is neither a stablecoin nor BTC
    concentration  warning/danger : share held in the single largest wallet
    storage        safe/warning   : share in cold storage — inverted, because
                                    more cold is better, so `safe` > `warning`

Every file is per profile: the numbers that fit a small test portfolio are not the
ones that fit a seven-figure one.
"""
import json
import os
import threading

from . import atomicio, profiles

DEFAULTS = {
    "volatility": {"warning": 60.0, "danger": 70.0},
    "concentration": {"warning": 50.0, "danger": 75.0},
    "storage": {"safe": 50.0, "warning": 20.0},
}

# key -> (must be increasing?) for the ordered pairs
_ORDERED = (("volatility", "warning", "danger"),
            ("concentration", "warning", "danger"),
            ("storage", "warning", "safe"))

_lock = threading.RLock()
_cache = {"mtime": None, "data": None}


def health_file():
    return profiles.health_file()


def _mtime():
    try:
        path = health_file()
        return os.path.getmtime(path) if os.path.exists(path) else None
    except OSError:
        return None


def defaults():
    return {k: dict(v) for k, v in DEFAULTS.items()}


def _number(value, where):
    try:
        n = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"{where} must be a number")
    if n != n or n in (float("inf"), float("-inf")):   # NaN / infinity
        raise ValueError(f"{where} must be a finite number")
    if not (0.0 <= n <= 100.0):
        raise ValueError(f"{where} must be between 0 and 100")
    return round(n, 1)


def normalize(raw):
    """Validate a partial config and merge it over the defaults.

    A partial update is the normal case (the settings form may only send one
    group), so missing groups fall back to the defaults rather than erroring.
    """
    if raw is not None and not isinstance(raw, dict):
        raise ValueError("thresholds must be a JSON object")
    out = defaults()
    for group, fields in DEFAULTS.items():
        given = (raw or {}).get(group)
        if given is None:
            continue
        if not isinstance(given, dict):
            raise ValueError(f"{group} must be a JSON object")
        for field in fields:
            if field in given:
                out[group][field] = _number(given[field], f"{group}.{field}")
    for group, low, high in _ORDERED:
        if out[group][low] >= out[group][high]:
            raise ValueError(
                f"{group}: {low} ({out[group][low]}) must be below {high} ({out[group][high]})")
    return out


def load():
    """Thresholds of the active profile; hot-reloads when the file changes.

    Falls back to the defaults whenever the profile or the file cannot be read —
    a missing config must never take the health report down with it.
    """
    global _cache
    try:
        return _load()
    except Exception:  # noqa: BLE001
        return defaults()


def _load():
    global _cache
    with _lock:
        mtime = _mtime()
        if _cache["data"] is None or _cache["mtime"] != mtime:
            raw = None
            path = health_file()
            if os.path.exists(path):
                try:
                    with open(path, "r", encoding="utf-8") as fh:
                        raw = json.load(fh)
                except Exception:  # noqa: BLE001
                    raw = None      # a corrupt file falls back to the defaults
            try:
                data = normalize(raw)
            except ValueError:
                data = defaults()
            _cache = {"mtime": mtime, "data": data}
        return {k: dict(v) for k, v in _cache["data"].items()}


def save(raw):
    """Validate and persist; returns the stored (normalized) config."""
    global _cache
    data = normalize(raw)
    with _lock:
        atomicio.write_json(health_file(), data)
        _cache = {"mtime": _mtime(), "data": data}
        return {k: dict(v) for k, v in data.items()}


def reset_cache():
    global _cache
    with _lock:
        _cache = {"mtime": None, "data": None}
