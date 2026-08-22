# -*- coding: utf-8 -*-
"""Profile management — multiple named portfolio configs.

Each profile is a directory under profiles/ holding its own:
  sources.json   (API URLs + keys)
  wallets.json   (wallets tracked)
  blacklist.json (blacklisted tokens)
  portfolio.db   (daily snapshots history)

The default profile is seeded from templates/ (public example wallets, empty
API keys). Private configs (the user's own wallets/keys) belong to a named
profile of their choosing and are never part of any published artifact.

The active profile is persisted in profiles/.active; switching it re-points
every config file and the SQLite database.
"""
import json
import os
import shutil

from . import config

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROFILES_DIR = os.path.join(_ROOT, "profiles")
ACTIVE_FILE = os.path.join(PROFILES_DIR, ".active")
TEMPLATES_DIR = os.path.join(_ROOT, "templates")

_BAD = set('/\\:\x00')


def _valid_name(name):
    name = str(name or "").strip()
    if not name or name in (".", "..") or any(c in _BAD for c in name):
        raise ValueError(f"invalid profile name: {name!r}")
    return name


def profiles_dir():
    return PROFILES_DIR


def list_profiles():
    if not os.path.isdir(PROFILES_DIR):
        return []
    return sorted(d for d in os.listdir(PROFILES_DIR)
                  if os.path.isdir(os.path.join(PROFILES_DIR, d)) and not d.startswith("."))


def profile_dir(name):
    return os.path.join(PROFILES_DIR, _valid_name(name))


def exists(name):
    return os.path.isdir(profile_dir(name))


def active():
    try:
        with open(ACTIVE_FILE, "r", encoding="utf-8") as f:
            name = f.read().strip()
        if name and exists(name):
            return name
    except Exception:  # noqa: BLE001
        pass
    return "default" if exists("default") else (list_profiles() or [None])[0]


def set_active(name):
    _valid_name(name)
    if not exists(name):
        raise ValueError(f"profile {name!r} does not exist")
    os.makedirs(PROFILES_DIR, exist_ok=True)
    with open(ACTIVE_FILE, "w", encoding="utf-8") as f:
        f.write(name)


# per-profile file locations -------------------------------------------------
def sources_file():
    return os.path.join(profile_dir(active()), "sources.json")


def wallets_file():
    return os.path.join(profile_dir(active()), "wallets.json")


def blacklist_file():
    return os.path.join(profile_dir(active()), "blacklist.json")


def db_path():
    return os.path.join(profile_dir(active()), "portfolio.db")


# lifecycle ------------------------------------------------------------------
def create_profile(name, from_template=False, copy_from=None, wallets_seed=None):
    """Create a profile directory.

    from_template: seed sources.json+wallets.json from templates/ (public).
    copy_from:     copy an existing profile's config files (not its DB).
    wallets_seed:  optional wallet list to write into wallets.json.
    """
    name = _valid_name(name)
    if exists(name):
        raise ValueError(f"profile {name!r} already exists")
    d = profile_dir(name)
    os.makedirs(d, exist_ok=True)
    if from_template:
        for f in ("sources.json", "wallets.json"):
            src = os.path.join(TEMPLATES_DIR, "portfolio_" + f)
            if os.path.exists(src):
                shutil.copyfile(src, os.path.join(d, f))
    elif copy_from:
        src_dir = profile_dir(copy_from)
        for f in ("sources.json", "wallets.json", "blacklist.json"):
            src = os.path.join(src_dir, f)
            if os.path.exists(src):
                shutil.copyfile(src, os.path.join(d, f))
    if wallets_seed is not None:
        with open(os.path.join(d, "wallets.json"), "w", encoding="utf-8") as f:
            json.dump(wallets_seed, f, ensure_ascii=False, indent=2)
    return name


def delete_profile(name):
    name = _valid_name(name)
    if name == "default":
        raise ValueError("cannot delete the default profile")
    if name == active():
        raise ValueError("cannot delete the active profile")
    shutil.rmtree(profile_dir(name), ignore_errors=True)


def ensure_profiles():
    """Create the default (public template) profile; migrate legacy root-level
    configs (old single-profile layout) into a profile named 'private'."""
    os.makedirs(PROFILES_DIR, exist_ok=True)
    if not exists("default"):
        create_profile("default", from_template=True)

    legacy = [("portfolio_sources.json", "sources.json"),
              ("portfolio_wallets.json", "wallets.json"),
              ("portfolio_blacklist.json", "blacklist.json"),
              ("portfolio.db", "portfolio.db")]
    if any(os.path.exists(os.path.join(_ROOT, src)) for src, _ in legacy) and not exists("private"):
        create_profile("private")
        pd = profile_dir("private")
        for src_name, dst_name in legacy:
            src = os.path.join(_ROOT, src_name)
            if os.path.exists(src):
                shutil.move(src, os.path.join(pd, dst_name))
        # seed wallets from config.py built-ins when the migrated list is empty
        wp = os.path.join(pd, "wallets.json")
        try:
            with open(wp, "r", encoding="utf-8") as f:
                wallets = json.load(f)
        except Exception:  # noqa: BLE001
            wallets = []
        if not wallets and config.WALLETS:
            with open(wp, "w", encoding="utf-8") as f:
                json.dump(config.WALLETS, f, ensure_ascii=False, indent=2)
        set_active("private")
        print("[profiles] migrated legacy configs into profile 'private' (active)")

    if not exists(active()):
        set_active("default")
    return active()
