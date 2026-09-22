# -*- coding: utf-8 -*-
"""Per-profile status: last successful run per data source, last refresh time.

Stored in profiles/<name>/status.json so the Sources panel can show, for each
source, when it last succeeded (and CEX per-exchange success dates).
"""
import json
import os
import threading
from datetime import datetime

from . import atomicio, profiles

# Every mark_* is a read-modify-write of the whole file, and a refresh marks one
# source at a time while the scheduler may be updating another profile.
_lock = threading.RLock()


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
    atomicio.write_json(status_file(profile), d)


def _now():
    return datetime.now().isoformat(timespec="seconds")


def mark_source_ok(source, when=None, profile=None):
    with _lock:
        d = _load(profile)
        last_ok = d.setdefault("last_ok", {})
        last_ok[source] = when or _now()
        _save(d, profile)


def mark_refresh(when=None, profile=None):
    with _lock:
        d = _load(profile)
        d["last_refresh"] = when or _now()
        _save(d, profile)


def set_detail(key, value, profile=None):
    with _lock:
        d = _load(profile)
        d[key] = value
        _save(d, profile)


def get_status(profile=None):
    return _load(profile)
