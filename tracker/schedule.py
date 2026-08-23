# -*- coding: utf-8 -*-
"""Per-profile scheduled daily refresh.

Each profile may enable a daily auto-refresh at a local time ("HH:MM").
The last-run date is tracked per profile so a profile is refreshed at most
once per day even if the scheduler restarts.
"""
import json
import os
from datetime import date, datetime

from . import profiles

DEFAULT_TIME = "09:00"


def schedule_file(profile=None):
    profile = profile or profiles.active()
    return os.path.join(profiles.profile_dir(profile), "schedule.json")


def _load(profile=None):
    try:
        with open(schedule_file(profile), "r", encoding="utf-8") as f:
            d = json.load(f)
        return d if isinstance(d, dict) else {}
    except Exception:  # noqa: BLE001
        return {}


def _save(d, profile=None):
    p = schedule_file(profile)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=2)


def get_schedule(profile=None):
    d = _load(profile)
    return {
        "enabled": bool(d.get("enabled", False)),
        "time": d.get("time") or DEFAULT_TIME,
        "last_run_date": d.get("last_run_date"),
    }


def set_schedule(enabled, time, profile=None):
    d = _load(profile)
    d["enabled"] = bool(enabled)
    if time:
        d["time"] = str(time).strip()
    # reset the once-per-day marker: a newly saved time can fire the same day
    # (if the time is still in the future; past times fire again tomorrow)
    d.pop("last_run_date", None)
    _save(d, profile)
    return get_schedule(profile)


def mark_run(when=None, profile=None):
    d = _load(profile)
    if isinstance(when, str):   # defensive: caller passed profile by position
        when = None
    d["last_run_date"] = (when or datetime.now()).date().isoformat()
    _save(d, profile)


def is_due(profile, now=None):
    """True when the profile's schedule is enabled and the current local time
    matches the configured HH:MM, and it has not run yet today."""
    s = get_schedule(profile)
    if not s["enabled"]:
        return False
    now = now or datetime.now()
    if now.strftime("%H:%M") != s["time"]:
        return False
    return s.get("last_run_date") != now.date().isoformat()
