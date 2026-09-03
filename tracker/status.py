# -*- coding: utf-8 -*-
"""Per-profile status: last successful run per data source, last refresh time.

Stored in profiles/<name>/status.json so the Sources panel can show, for each
source, when it last succeeded (and CEX per-exchange success dates).
"""
import json
import os
from datetime import datetime

from . import profiles


def status_file(profile=None):
    profile = profile or profiles.active()
    return os.path.join(profiles.profile_dir(profile), "status.json")


def _load(profile=None):
    try:
        with open(status_file(profile), "r", encoding="utf-8") as f:
            d = json.load(f)
        return d if isinstance(d, dict) else {}
    except Exception:  # noqa: BLE001
        return {}


def _save(d, profile=None):
    p = status_file(profile)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=2)


def _now():
    return datetime.now().isoformat(timespec="seconds")


def mark_source_ok(source, when=None, profile=None):
    d = _load(profile)
    last_ok = d.setdefault("last_ok", {})
    last_ok[source] = when or _now()
    _save(d, profile)


def mark_refresh(when=None, profile=None):
    d = _load(profile)
    d["last_refresh"] = when or _now()
    _save(d, profile)


def set_detail(key, value, profile=None):
    d = _load(profile)
    d[key] = value
    _save(d, profile)


def get_status(profile=None):
    return _load(profile)
