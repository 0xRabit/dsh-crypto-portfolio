# -*- coding: utf-8 -*-
"""SQLite storage: daily snapshots (last result of each day) + token/wallet detail rows."""
import json
import os
import sqlite3
import threading
from datetime import datetime, timedelta

from . import config, profiles
from .blacklist import filter_rows
from . import stablecoins
from .views import view_of

_here = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_here)

SCHEMA = """
CREATE TABLE IF NOT EXISTS snapshots (
    date         TEXT PRIMARY KEY,
    created_at   TEXT NOT NULL,
    total_usd    REAL NOT NULL DEFAULT 0,
    by_chain     TEXT NOT NULL DEFAULT '{}',
    raw          TEXT NOT NULL DEFAULT '{}'
);
CREATE TABLE IF NOT EXISTS wallet_totals (
    date   TEXT NOT NULL,
    wallet TEXT NOT NULL,
    usd    REAL NOT NULL DEFAULT 0,
    PRIMARY KEY (date, wallet)
);
CREATE TABLE IF NOT EXISTS tokens (
    date        TEXT NOT NULL,
    wallet      TEXT NOT NULL,
    chain       TEXT NOT NULL,
    token_id    TEXT NOT NULL DEFAULT '',
    symbol      TEXT NOT NULL DEFAULT '',
    name        TEXT NOT NULL DEFAULT '',
    amount      REAL NOT NULL DEFAULT 0,
    price       REAL NOT NULL DEFAULT 0,
    usd         REAL NOT NULL DEFAULT 0,
    logo        TEXT NOT NULL DEFAULT '',
    PRIMARY KEY (date, wallet, chain, token_id)
);
CREATE INDEX IF NOT EXISTS idx_tokens_date ON tokens(date);
CREATE INDEX IF NOT EXISTS idx_wt_date ON wallet_totals(date);
"""

_lock = threading.RLock()


def _db_path():
    return config.DB_PATH or profiles.db_path()


def _connect():
    conn = sqlite3.connect(_db_path(), timeout=30)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with _lock:
        conn = _connect()
        try:
            conn.executescript(SCHEMA)
            conn.commit()
        finally:
            conn.close()


def save_snapshot(data):
    """Upsert today's snapshot (last result of the day wins) + detail rows."""
    with _lock:
        conn = _connect()
        try:
            date = data["date"]
            now = datetime.now().isoformat(timespec="seconds")
            conn.execute(
                "INSERT OR REPLACE INTO snapshots(date, created_at, total_usd, by_chain, raw) "
                "VALUES (?,?,?,?,?)",
                (date, now, data.get("total_usd", 0.0),
                 json.dumps(data.get("by_chain", {})), json.dumps(data, ensure_ascii=False)),
            )
            conn.execute("DELETE FROM wallet_totals WHERE date=?", (date,))
            for w in data.get("wallets", []):
                conn.execute(
                    "INSERT INTO wallet_totals(date, wallet, usd) VALUES (?,?,?)",
                    (date, w["wallet"], w.get("total_usd", 0.0)))
            conn.execute("DELETE FROM tokens WHERE date=?", (date,))
            for w in data.get("wallets", []):
                for t in w.get("tokens", []):
                    conn.execute(
                        "INSERT INTO tokens(date,wallet,chain,token_id,symbol,name,amount,price,usd,logo) "
                        "VALUES (?,?,?,?,?,?,?,?,?,?)",
                        (date, t["wallet"], t.get("chain", ""), t.get("token_id", ""),
                         t.get("symbol", ""), t.get("name", ""), t.get("amount", 0.0),
                         t.get("price", 0.0), t.get("usd", 0.0), t.get("logo", "")))
            conn.commit()
        finally:
            conn.close()


def get_snapshot(date):
    with _lock:
        conn = _connect()
        try:
            row = conn.execute("SELECT * FROM snapshots WHERE date=?", (date,)).fetchone()
            if not row:
                return None
            snap = json.loads(row["raw"])
            snap["created_at"] = row["created_at"]
            return snap
        finally:
            conn.close()


def get_latest_snapshot():
    with _lock:
        conn = _connect()
        try:
            row = conn.execute("SELECT date FROM snapshots ORDER BY date DESC LIMIT 1").fetchone()
            if not row:
                return None
            return get_snapshot(row["date"])
        finally:
            conn.close()


def get_snapshot_dates():
    with _lock:
        conn = _connect()
        try:
            rows = conn.execute("SELECT date, created_at, total_usd FROM snapshots ORDER BY date").fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()


def get_history(days=None):
    """Trend data: dates, total per day, per-wallet and per-chain series.

    Computed from each snapshot's raw token rows through the blacklist-filtered
    view, so historical totals always match the current blacklist.
    """
    with _lock:
        conn = _connect()
        try:
            sql = "SELECT date FROM snapshots ORDER BY date DESC"
            args = []
            if days:
                sql += " LIMIT ?"
                args.append(days)
            dates = [r["date"] for r in conn.execute(sql, args).fetchall()]
            dates.reverse()
            if not dates:
                return {"dates": [], "totals": [], "wallets": {}, "chains": {}}
            totals = []
            wallets = {}
            chains = {}
            for d in dates:
                raw = conn.execute("SELECT raw FROM snapshots WHERE date=?", (d,)).fetchone()
                snap = json.loads(raw["raw"]) if raw else {"date": d, "wallets": []}
                snap["date"] = d
                v = view_of(snap)
                totals.append(v["total_usd"])
                for w in v["wallets"]:
                    wallets.setdefault(w["wallet"], {})[d] = w["total_usd"]
                for c, val in v["by_chain"].items():
                    chains.setdefault(c, {})[d] = val
            return {
                "dates": dates,
                "totals": totals,
                "wallets": {w: [series.get(d, 0.0) for d in dates]
                            for w, series in wallets.items()},
                "chains": {c: [series.get(d, 0.0) for d in dates]
                           for c, series in chains.items()},
            }
        finally:
            conn.close()


def get_tokens(date):
    with _lock:
        conn = _connect()
        try:
            rows = conn.execute(
                "SELECT wallet,chain,token_id,symbol,name,amount,price,usd,logo FROM tokens WHERE date=? "
                "ORDER BY usd DESC", (date,)).fetchall()
            # classification is applied at read time, so editing the rules also
            # reclassifies every historical snapshot
            return stablecoins.annotate(filter_rows([dict(r) for r in rows]))
        finally:
            conn.close()


# ————————————————————————————————————————————————————————————————
# retention
#
# Every snapshot keeps a copy of every token row, so a profile grows by roughly
# 0.75 MB per day (a 12-wallet profile reaches ~280 MB/year) with nothing ever
# removed. Keep a dense recent window for the trend chart, and thin anything older
# down to one snapshot per month so long-range history still works.
# ————————————————————————————————————————————————————————————————
KEEP_DAILY_DAYS = int(os.environ.get("PORTFOLIO_KEEP_DAILY_DAYS", "90"))
KEEP_MONTHLY = int(os.environ.get("PORTFOLIO_KEEP_MONTHLY", "24"))


def plan_retention(dates, today=None, keep_days=None, keep_monthly=None):
    """Split dated snapshots into (keep, drop).

    `dates` is any iterable of 'YYYY-MM-DD'. The newest `keep_days` calendar days
    are all kept; older dates are thinned to the last snapshot of each month, of
    which the newest `keep_monthly` months survive. Pure so it can be tested
    without a database.
    """
    keep_days = KEEP_DAILY_DAYS if keep_days is None else keep_days
    keep_monthly = KEEP_MONTHLY if keep_monthly is None else keep_monthly
    days = sorted({str(d)[:10] for d in dates})
    if not days:
        return [], []
    if today is None:
        today = datetime.now().date().isoformat()
    cutoff = (datetime.fromisoformat(today).date() - timedelta(days=keep_days - 1)).isoformat()

    keep, older = [], []
    for d in days:
        (keep if d >= cutoff else older).append(d)

    # one representative per month for the tail: the last snapshot in that month
    by_month = {}
    for d in older:
        by_month[d[:7]] = d
    # One representative per month for the tail: the last snapshot in that month.
    # A month already present in the dense window contributes nothing extra, so the
    # chart never ends up with two points a few days apart.
    represented = {d[:7] for d in keep}
    tail_months = [m for m in sorted(by_month) if m not in represented]
    keep_months = tail_months[-keep_monthly:] if keep_monthly > 0 else []
    tail_keep = {by_month[m] for m in keep_months}
    keep.extend(sorted(tail_keep))
    # every older date that is not a chosen representative goes; deriving this from
    # `older` rather than from the month map is what makes the split exhaustive
    drop = [d for d in older if d not in tail_keep]
    return sorted(keep), sorted(drop)


def prune_snapshots(today=None, keep_days=None, keep_monthly=None):
    """Delete snapshots outside the retention window; returns a summary."""
    with _lock:
        conn = _connect()
        try:
            dates = [r["date"] for r in conn.execute("SELECT date FROM snapshots").fetchall()]
            keep, drop = plan_retention(dates, today=today, keep_days=keep_days,
                                        keep_monthly=keep_monthly)
            for d in drop:
                conn.execute("DELETE FROM tokens WHERE date=?", (d,))
                conn.execute("DELETE FROM wallet_totals WHERE date=?", (d,))
                conn.execute("DELETE FROM snapshots WHERE date=?", (d,))
            if drop:
                conn.commit()
            return {"kept": len(keep), "dropped": len(drop), "dropped_dates": drop}
        finally:
            conn.close()
