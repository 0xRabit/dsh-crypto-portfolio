# -*- coding: utf-8 -*-
"""Stdlib HTTP server: serves the dashboard + JSON API."""
import json
import os
import re
import threading
import urllib.parse
from datetime import date
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from . import config, portfolio, storage
from . import blacklist as bl
from . import cex
from . import profiles
from . import sources
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
                code, body = _json({"date": d, "tokens": storage.get_tokens(d)})
                self._reply(code, body, "application/json; charset=utf-8")
            elif path == "/api/status":
                code, body = _json(dict(_refresh_state))
                self._reply(code, body, "application/json; charset=utf-8")
            elif path == "/api/snapshots":
                code, body = _json(storage.get_snapshot_dates())
                self._reply(code, body, "application/json; charset=utf-8")
            elif path == "/api/blacklist":
                code, body = _json(self._blacklist_view())
                self._reply(code, body, "application/json; charset=utf-8")
            elif path == "/api/sources":
                code, body = _json({
                    "file": sources.sources_file(),
                    "config": sources.load(),
                    "last_ok": sources.failover_state(),
                })
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
        sources.reset_failover()
        return self._config_export()

    def do_POST(self):  # noqa: N802
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
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
                sources.save(cfg)
                sources.reset_failover()
                self._reply_json({"file": sources.sources_file(),
                                  "config": sources.load(),
                                  "last_ok": sources.failover_state()})
            elif path == "/api/config/import":
                cfg = (body or {}).get("config") or {}
                self._reply_json(self._config_import(cfg))
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
                elif action == "delete":
                    profiles.delete_profile(name)
                    self._reply_json(self._profiles_view())
                else:
                    raise ValueError("action must be switch/create/delete")
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
        return {"active": profiles.active(),
                "profiles": [{"name": n, "is_active": n == profiles.active(),
                              "is_default": n == "default",
                              "has_db": os.path.exists(os.path.join(profiles.profile_dir(n), "portfolio.db"))}
                             for n in profiles.list_profiles()],
                "dir": profiles.profiles_dir()}

    def _switch_profile(self):
        """Re-point all config modules at the newly active profile and make
        sure the new profile's database schema exists."""
        bl.reset_cache()
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
        dry = qs.get("dry", ["0"])[0] in ("1", "true")
        with _state_lock:
            if _refresh_state["running"]:
                self._reply(429, json.dumps({"error": "Refresh already in progress"}).encode(),
                            "application/json")
                return
            _refresh_state["running"] = True

        def progress(stage, done, total, msg):
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
        except Exception as e:  # noqa: BLE001
            self._reply_json({"error": f"{type(e).__name__}: {e}"}, 500)
        finally:
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


def run(port=None, host="127.0.0.1", profile=None):
    port = port or config.DEFAULT_PORT
    profiles.ensure_profiles()
    if profile:
        profiles.set_active(profile)
    sources.ensure_file()
    storage.init_db()
    print(f"[profiles] active: {profiles.active()}")
    server = ThreadingHTTPServer((host, port), Handler)
    print(f"Portfolio Tracker running at http://{host}:{port}")
    print("Open the page and click Refresh to pull all wallet balances.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped")
        server.shutdown()
