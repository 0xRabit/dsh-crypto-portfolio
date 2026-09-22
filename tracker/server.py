# -*- coding: utf-8 -*-
"""Stdlib HTTP server: serves the dashboard + JSON API."""
import json
import os
import re
import threading
import time
import urllib.parse
from datetime import date, datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from . import config, portfolio, storage
from . import blacklist as bl
from . import cex
from . import profiles
from . import schedule as sched
from . import sources
from . import stablecoins
from . import status
from . import walletstore
from .debank import chain_names
from .views import view_of

_HERE = os.path.dirname(os.path.abspath(__file__))
_STATIC = os.path.join(os.path.dirname(_HERE), "static")

MIME = {
    ".html": "text/html; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".png": "image/png",
    ".svg": "image/svg+xml",
    ".ico": "image/x-icon",
    ".json": "application/json; charset=utf-8",
}

_refresh_state = {"running": False, "stage": "", "done": 0, "total": 0, "msg": ""}
_state_lock = threading.Lock()

# A full fetch hits DeBank/Binance/CoinGecko and takes tens of seconds. Without a
# floor, anything that can reach this port (including a cross-site page, see
# _write_guard) could loop refresh and burn the upstream API quotas.
REFRESH_COOLDOWN_SECONDS = float(os.environ.get("PORTFOLIO_REFRESH_COOLDOWN", "60"))
_last_refresh_at = 0.0
# Cooperative cancel: checked from the progress callback between wallets.
_refresh_cancel = threading.Event()


class RefreshCancelled(Exception):
    """Raised from the progress callback to abort an in-flight refresh."""

_chain_name_cache = None
_chain_name_lock = threading.Lock()


def get_chain_names():
    global _chain_name_cache
    with _chain_name_lock:
        if _chain_name_cache is None:
            try:
                names = chain_names()
            except Exception:  # noqa: BLE001
                names = {}
            names["hyperliquid"] = "Hyperliquid L1"
            names["binance"] = "Binance"
            names["bybit"] = "Bybit"
            names["backpack"] = "Backpack"
            _chain_name_cache = names
        return _chain_name_cache


def _json(data, code=200):
    body = json.dumps(data, ensure_ascii=False).encode("utf-8")
    return code, body


class Handler(BaseHTTPRequestHandler):
    server_version = "PortfolioTracker/1.0"

    def log_message(self, fmt, *args):  # silence request log
        pass

    def do_GET(self):  # noqa: N802
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        qs = urllib.parse.parse_qs(parsed.query)

        try:
            if path == "/":
                self._serve_file("index.html")
            elif path.startswith("/static/"):
                self._serve_file(path[len("/static/"):], subdir=_STATIC)
            elif path == "/api/wallets":
                code, body = _json(self._wallet_view())
                self._reply(code, body, "application/json; charset=utf-8")
            elif path == "/api/refresh":
                # kept for curl/CLI compatibility; the dashboard POSTs. Either way
                # this is a write, so the cross-site fence applies.
                denied = self._write_guard(is_post=False)
                if denied:
                    self._reply(403, json.dumps({"error": denied}).encode(), "application/json")
                else:
                    self._handle_refresh(qs)
            elif path == "/api/current":
                snap = storage.get_latest_snapshot()
                if not snap:
                    code, body = _json({"error": "No snapshot yet - click Refresh"}, 404)
                else:
                    code, body = _json(self._snapshot_view(snap))
                self._reply(code, body, "application/json; charset=utf-8")
            elif path == "/api/snapshot":
                d = qs.get("date", [None])[0]
                snap = storage.get_snapshot(d) if d else storage.get_latest_snapshot()
                if not snap:
                    code, body = _json({"error": f"没有 {d or '任何'} 快照"}, 404)
                else:
                    code, body = _json(self._snapshot_view(snap))
                self._reply(code, body, "application/json; charset=utf-8")
            elif path == "/api/history":
                days = int(qs.get("days", ["0"])[0] or 0) or None
                code, body = _json(storage.get_history(days))
                self._reply(code, body, "application/json; charset=utf-8")
            elif path == "/api/tokens":
                d = qs.get("date", [None])[0] or storage.get_latest_snapshot()
                d = d["date"] if isinstance(d, dict) else d
                code, body = _json({"date": d, "tokens": storage.get_tokens(d),
                                    "labels": stablecoins.known_labels()})
                self._reply(code, body, "application/json; charset=utf-8")
            elif path == "/api/status":
                code, body = _json(dict(_refresh_state))
                self._reply(code, body, "application/json; charset=utf-8")
            elif path == "/api/snapshots":
                code, body = _json(storage.get_snapshot_dates())
                self._reply(code, body, "application/json; charset=utf-8")
            elif path == "/api/stablecoins":
                code, body = _json(self._stablecoins_view())
                self._reply(code, body, "application/json; charset=utf-8")
            elif path == "/api/blacklist":
                code, body = _json(self._blacklist_view())
                self._reply(code, body, "application/json; charset=utf-8")
            elif path == "/api/sources":
                # secrets are masked unless the caller explicitly asks to reveal
                reveal = (qs.get("reveal") or ["0"])[0] in ("1", "true")
                cfg = sources.load()
                code, body = _json({
                    "file": sources.sources_file(),
                    "config": cfg if reveal else sources.mask_config(cfg),
                    "masked": not reveal,
                    "last_ok": sources.failover_state(),
                    "status": status.get_status(),
                })
                self._reply(code, body, "application/json; charset=utf-8")
            elif path == "/api/schedule":
                # per-profile: ?profile=<name> (defaults to the active profile)
                prof = (qs.get("profile") or [None])[0]
                if prof and not profiles.exists(prof):
                    raise ValueError(f"profile {prof!r} does not exist")
                code, body = _json(sched.get_schedule(prof))
                self._reply(code, body, "application/json; charset=utf-8")
            elif path == "/api/config/export":
                code, body = _json(self._config_export())
                self._reply(code, body, "application/json; charset=utf-8")
            elif path == "/api/profiles":
                code, body = _json(self._profiles_view())
                self._reply(code, body, "application/json; charset=utf-8")
            else:
                self._reply(404, json.dumps({"error": "not found"}).encode(), "application/json")
        except Exception as e:  # noqa: BLE001
            self._reply(500, json.dumps({"error": f"{type(e).__name__}: {e}"}).encode(),
                        "application/json")

    def _config_export(self):
        import datetime as _dt
        return {
            "format": "portfolio-config",
            "version": 1,
            "exported_at": _dt.datetime.now().isoformat(timespec="seconds"),
            "sources": sources.load(),
            "wallets": walletstore.user_wallets(),
            "blacklist": bl.user_entries(),
            "stablecoins": stablecoins.user_entries(),
            "note": "sources/wallets/blacklist 配置文件备份；导入后点「刷新数据」生效",
        }

    def _config_import(self, cfg):
        src = (cfg or {}).get("sources")
        if isinstance(src, dict):
            sources.save(src)
        wallets = (cfg or {}).get("wallets")
        if isinstance(wallets, list):
            walletstore.save_all(wallets)
        blacklist_entries = (cfg or {}).get("blacklist")
        if isinstance(blacklist_entries, list):
            bl.save_all(blacklist_entries)
        stable_rules = (cfg or {}).get("stablecoins")
        if isinstance(stable_rules, list):
            stablecoins.save_all(stable_rules)
        sources.reset_failover()
        return self._config_export()

    def _write_guard(self, is_post):
        """Reject cross-site writes; returns an error string, or None when allowed.

        A browser lets a page issue a "simple" cross-site POST (text/plain, or a
        form encoding) to a loopback URL with no CORS preflight: the attacker
        cannot read the response, but the side effect still runs. The same applies
        to a GET with side effects, which is reachable from a bare <img> tag. Two
        independent fences:

          * Sec-Fetch-Site is set by the browser itself and page script cannot
            forge it, so `cross-site` is refused outright.
          * If an Origin is present it must match the Host we were reached on.

        Non-browser callers (curl, the scheduler, tests) send neither header and
        pass both checks, which is what keeps the CLI usable.
        """
        if (self.headers.get("Sec-Fetch-Site") or "").strip().lower() == "cross-site":
            return "cross-site request refused"
        origin = (self.headers.get("Origin") or "").strip()
        if origin:
            host = (self.headers.get("Host") or "").strip()
            if origin == "null":
                # opaque origin: sandboxed iframe / data: document / file:// page
                return "opaque origin refused"
            origin_host = urllib.parse.urlparse(origin).netloc
            if origin_host and host and origin_host != host:
                return "origin does not match host"
        if is_post:
            ctype = (self.headers.get("Content-Type") or "").split(";", 1)[0].strip().lower()
            # Empty-body POSTs (no content-type) are allowed; anything with a body
            # must be JSON so a simple cross-site POST is forced into a preflight
            # this server never answers.
            length = int(self.headers.get("Content-Length") or 0)
            if ctype != "application/json" and (length > 0 or ctype):
                return "content type must be application/json"
        return None

    def do_POST(self):  # noqa: N802
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        denied = self._write_guard(is_post=True)
        if denied:
            code = 403 if "refused" in denied or "origin" in denied else 415
            self._reply(code, json.dumps({"error": denied}).encode(), "application/json")
            return
        try:
            body = self._read_body()
            if path == "/api/blacklist":
                entry = (body or {}).get("entry") or {}
                if not isinstance(entry, dict):
                    raise ValueError("entry must be a JSON object")
                bl.add_entry({k: (v or "") for k, v in entry.items()})
                self._reply_json(self._blacklist_view())
            elif path == "/api/blacklist/remove":
                index = int((body or {}).get("index", -1))
                if not bl.remove_entry(index):
                    raise ValueError("invalid index or built-in entry cannot be removed")
                self._reply_json(self._blacklist_view())
            elif path == "/api/stablecoins":
                entry = (body or {}).get("entry") or {}
                if not isinstance(entry, dict):
                    raise ValueError("entry must be a JSON object")
                stablecoins.add_entry(entry)
                self._reply_json(self._stablecoins_view())
            elif path == "/api/stablecoins/remove":
                index = int((body or {}).get("index", -1))
                if not stablecoins.remove_entry(index):
                    raise ValueError("invalid index")
                self._reply_json(self._stablecoins_view())
            elif path == "/api/wallets":
                wallet = (body or {}).get("wallet") or {}
                if not isinstance(wallet, dict):
                    raise ValueError("wallet must be a JSON object")
                walletstore.add_wallet(wallet)
                self._reply_json(self._wallet_view())
            elif path == "/api/wallets/remove":
                index = int((body or {}).get("index", -1))
                if not walletstore.remove_wallet(index):
                    raise ValueError("invalid index or built-in wallet cannot be removed")
                self._reply_json(self._wallet_view())
            elif path == "/api/sources":
                cfg = (body or {}).get("config")
                if not isinstance(cfg, dict):
                    raise ValueError("config must be a JSON object")
                # the form round-trips masked stubs; swap them back for the real
                # secrets before writing, or a save would destroy every key
                cfg = sources.merge_masked(cfg, sources.load())
                sources.save(cfg)
                sources.reset_failover()
                self._reply_json({"file": sources.sources_file(),
                                  "config": sources.mask_config(sources.load()),
                                  "masked": True,
                                  "last_ok": sources.failover_state()})
            elif path == "/api/refresh/cancel":
                _refresh_cancel.set()
                self._reply_json({"cancel_requested": True})
            elif path == "/api/refresh":
                # POST form: a GET with side effects is reachable from a bare <img>
                # tag, so the dashboard uses POST (still guarded by _write_guard).
                self._handle_refresh({})
            elif path == "/api/config/import":
                cfg = (body or {}).get("config") or {}
                self._reply_json(self._config_import(cfg))
            elif path == "/api/schedule":
                enabled = bool((body or {}).get("enabled", False))
                time_val = str((body or {}).get("time") or "").strip()
                # per-profile: an explicit profile lets the UI edit any profile's
                # schedule, not only the active one
                prof = str((body or {}).get("profile") or "").strip() or None
                if prof and not profiles.exists(prof):
                    raise ValueError(f"profile {prof!r} does not exist")
                self._reply_json(sched.set_schedule(enabled, time_val, prof))
            elif path == "/api/profiles":
                action = (body or {}).get("action")
                name = str((body or {}).get("name") or "").strip()
                if action == "switch":
                    if not name or not profiles.exists(name):
                        raise ValueError("profile does not exist")
                    profiles.set_active(name)
                    self._switch_profile()
                    self._reply_json(self._profiles_view())
                elif action == "create":
                    profiles.create_profile(
                        name, from_template=(body or {}).get("from_template", False),
                        copy_from=(body or {}).get("copy_from") or None)
                    self._reply_json(self._profiles_view())
                elif action == "rename":
                    new_name = str((body or {}).get("new_name") or "").strip()
                    if not new_name:
                        raise ValueError("new_name is required")
                    renamed_active = (profiles.active() == name)
                    profiles.rename_profile(name, new_name)
                    if renamed_active:
                        self._switch_profile()
                    self._reply_json(self._profiles_view())
                elif action == "delete":
                    profiles.delete_profile(name)
                    self._reply_json(self._profiles_view())
                else:
                    raise ValueError("action must be switch/create/rename/delete")
            else:
                self._reply_json({"error": "not found"}, 404)
        except Exception as e:  # noqa: BLE001
            self._reply_json({"error": f"{type(e).__name__}: {e}"}, 400)

    def _wallet_view(self):
        wallets = [dict(w, source="user", index=i)
                   for i, w in enumerate(walletstore.user_wallets())]
        cex_wallets = [{"name": a["name"], "type": "cex", "source": "cex",
                        "address": str(a.get("exchange") or "")}
                       for a in cex.cex_accounts()]
        return {"wallets": wallets + cex_wallets,
                "chains": get_chain_names(),
                "profile": profiles.active(),
                "file": walletstore.wallets_file()}

    def _profiles_view(self):
        """Profile list. Each entry carries its own schedule, because the
        scheduler runs per profile (profiles/<name>/schedule.json)."""
        out = []
        for n in profiles.list_profiles():
            s = sched.get_schedule(n)
            out.append({"name": n, "is_active": n == profiles.active(),
                        "is_default": n == "default",
                        "has_db": os.path.exists(os.path.join(profiles.profile_dir(n), "portfolio.db")),
                        "schedule": {"enabled": s["enabled"], "time": s["time"],
                                     "last_run_date": s.get("last_run_date")}})
        return {"active": profiles.active(), "profiles": out,
                "dir": profiles.profiles_dir()}

    def _switch_profile(self):
        """Re-point all config modules at the newly active profile and make
        sure the new profile's database schema exists."""
        bl.reset_cache()
        stablecoins.reset_cache()
        walletstore.reset_cache()
        sources.load(force=True)
        sources.reset_failover()
        storage.init_db()   # creates tables for the new profile's DB if missing

    def _read_body(self):
        length = int(self.headers.get("Content-Length") or 0)
        if length <= 0:
            return {}
        raw = self.rfile.read(length)
        try:
            return json.loads(raw.decode("utf-8"))
        except Exception:  # noqa: BLE001
            return {}

    def _stablecoins_view(self):
        """Rules for the asset-type donut. `index` counts USER rules only (built-ins
        cannot be deleted), plus one informational auto-detect row."""
        builtin = stablecoins.builtin_entries()
        user = stablecoins.user_entries()
        return {"file": stablecoins.stablecoins_file(),
                "builtin": builtin,
                "user": [dict(e, index=i) for i, e in enumerate(user)],
                "labels": stablecoins.known_labels(),
                "auto": {"price_band": list(config.STABLECOIN_PRICE_BAND),
                         "note": "priced inside the band with a USD/DAI/FRAX marker"}}

    def _blacklist_view(self):
        config_entries = [dict(e, source="config") for e in config.TOKEN_BLACKLIST]
        user_entries = [dict(e, source="user", index=i)
                        for i, e in enumerate(bl.user_entries())]
        return {"entries": config_entries + user_entries,
                "file": bl.blacklist_file()}

    # -- helpers -----------------------------------------------------------

    def _view_of(self, snap):
        """Snapshot view with blacklisted (phishing/fake) tokens excluded."""
        return view_of(snap)

    def _snapshot_view(self, snap):
        view = self._view_of(snap)
        # change vs previous day snapshot (previous day also blacklist-filtered)
        prev = storage.get_snapshot_dates()
        prev_dates = [p["date"] for p in prev if p["date"] < snap["date"]]
        if prev_dates:
            pv = self._view_of(storage.get_snapshot(prev_dates[-1]))
            view["prev_date"] = pv["date"]
            view["prev_total"] = pv["total_usd"]
            base = pv["total_usd"]
            view["change_usd"] = round(view["total_usd"] - base, 2)
            view["change_pct"] = round((view["change_usd"] / base * 100), 2) if base else None
        else:
            view["prev_date"] = None
            view["change_usd"] = None
            view["change_pct"] = None
        return view

    def _handle_refresh(self, qs):
        global _last_refresh_at
        dry = qs.get("dry", ["0"])[0] in ("1", "true")
        now = time.time()
        with _state_lock:
            if _refresh_state["running"]:
                self._reply(429, json.dumps({"error": "Refresh already in progress"}).encode(),
                            "application/json")
                return
            wait = REFRESH_COOLDOWN_SECONDS - (now - _last_refresh_at)
            if _last_refresh_at and wait > 0:
                self._reply(429, json.dumps({
                    "error": f"Refresh rate-limited, retry in {int(wait) + 1}s",
                    "retry_after": int(wait) + 1,
                }).encode(), "application/json")
                return
            _refresh_state["running"] = True
            _last_refresh_at = now
        _refresh_cancel.clear()

        def progress(stage, done, total, msg):
            if _refresh_cancel.is_set():
                raise RefreshCancelled()
            with _state_lock:
                _refresh_state.update(stage=stage, done=done, total=total, msg=msg)

        try:
            if dry:
                data = portfolio.fetch_all(progress=progress)
                view = {"date": data["date"], "total_usd": data["total_usd"],
                        "by_chain": data["by_chain"], "wallets": [
                            {"wallet": w["wallet"], "address": w.get("address", ""),
                             "type": w.get("type", ""), "total_usd": w.get("total_usd", 0.0),
                             "token_count": len(w.get("tokens", []))} for w in data["wallets"]]}
                view["token_count"] = sum(w["token_count"] for w in view["wallets"])
            else:
                data, prev = portfolio.refresh_snapshot(progress=progress)
                view = self._snapshot_view(data)
                if prev:
                    pv = self._view_of(prev)
                    view["prev_date"] = pv["date"]
                    view["prev_total"] = pv["total_usd"]
                    view["change_usd"] = round(view["total_usd"] - pv["total_usd"], 2)
                    base = pv["total_usd"]
                    view["change_pct"] = round(view["change_usd"] / base * 100, 2) if base else None
            self._reply_json(view)
        except RefreshCancelled:
            # nothing was written: the snapshot is only saved once the fetch ends
            self._reply_json({"cancelled": True})
        except Exception as e:  # noqa: BLE001
            self._reply_json({"error": f"{type(e).__name__}: {e}"}, 500)
        finally:
            _refresh_cancel.clear()
            with _state_lock:
                _refresh_state.update(running=False, stage="", done=0, total=0, msg="")

    def _reply_json(self, data, code=200):
        self._reply(code, json.dumps(data, ensure_ascii=False).encode("utf-8"),
                    "application/json; charset=utf-8")

    def _reply(self, code, body, ctype):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        try:
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def _serve_file(self, name, subdir=None):
        root = subdir or _STATIC
        if ".." in name or name.startswith("/"):
            self._reply(403, b"forbidden", "text/plain")
            return
        fp = os.path.join(root, name)
        if not os.path.isfile(fp):
            self._reply(404, b"not found", "text/plain")
            return
        ext = os.path.splitext(fp)[1].lower()
        with open(fp, "rb") as f:
            self._reply(200, f.read(), MIME.get(ext, "application/octet-stream"))


_scheduler_stop = threading.Event()


def _run_scheduled(profile):
    prev = profiles.active()
    # survive a hard kill mid-refresh: a marker lets the next startup restore
    # the profile the user actually selected
    profiles.mark_restore_target(prev)
    try:
        profiles.set_active(profile)
        with _state_lock:
            if _refresh_state["running"]:
                return
        for attempt in range(3):
            try:
                data, _prev = portfolio.refresh_snapshot()
                sched.mark_run(profile=profile)
                print(f"[scheduler] {profile}: auto-refresh done (${data.get('total_usd')})", flush=True)
                return
            except Exception as e:  # noqa: BLE001
                print(f"[scheduler] {profile}: attempt {attempt + 1} failed: {e}", flush=True)
                _scheduler_stop.wait(60)
    finally:
        try:
            profiles.set_active(prev)
        except Exception:  # noqa: BLE001
            pass
        profiles.clear_restore_target()


def _scheduler_loop():
    while not _scheduler_stop.wait(30):
        try:
            now = datetime.now()
            for p in profiles.list_profiles():
                if sched.is_due(p, now):
                    _run_scheduled(p)
        except Exception as e:  # noqa: BLE001
            print(f"[scheduler] loop error: {e}", flush=True)


def run(port=None, host="127.0.0.1", profile=None):
    port = port or config.DEFAULT_PORT
    profiles.ensure_profiles()
    # undo a scheduled refresh that was interrupted by a hard kill
    recovered = profiles.recover_active()
    if recovered:
        print(f"[profiles] recovered interrupted refresh; active restored to {recovered}", flush=True)
    if profile:
        profiles.set_active(profile)
    sources.ensure_file()
    storage.init_db()
    print(f"[profiles] active: {profiles.active()}", flush=True)
    scheduler = threading.Thread(target=_scheduler_loop, daemon=True)
    scheduler.start()
    print("[scheduler] daily auto-refresh thread started", flush=True)
    server = ThreadingHTTPServer((host, port), Handler)
    print(f"Portfolio Tracker running at http://{host}:{port}")
    print("Open the page and click Refresh to pull all wallet balances.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped")
        _scheduler_stop.set()
        server.shutdown()
