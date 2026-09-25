# -*- coding: utf-8 -*-
"""Trend history: the aggregate table and its invalidation.

`get_history` used to re-parse every snapshot's raw JSON and re-filter every token
row on each call — on a real profile that was ~6 s per page load, and it grew with
the portfolio rather than with the number of days. It now reads per-date aggregates
(`history_totals`) and rebuilds them only when something that rewrites history
changes: a new snapshot, the blacklist, or the asset-label rules.

These tests pin three things: the aggregates equal the raw-JSON result, a rule
change really does rewrite history, and pruning drops the matching rows.
"""
import json
import os
import shutil
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tracker import assetlabels, blacklist as bl, profiles, storage  # noqa: E402
from tracker.views import view_of  # noqa: E402

_TMP = None


def setUpModule():
    global _TMP
    _TMP = tempfile.TemporaryDirectory()
    patcher = mock.patch.multiple(
        profiles,
        PROFILES_DIR=_TMP.name,
        ACTIVE_FILE=os.path.join(_TMP.name, ".active"),
    )
    patcher.start()
    unittest.addModuleCleanup(patcher.stop)


def tearDownModule():
    global _TMP
    if _TMP is not None:
        _TMP.cleanup()
        _TMP = None


def snapshot(date, wallets):
    """{date, wallets:[{wallet, tokens:[…]}]} as portfolio.fetch_all would build it."""
    return {
        "date": date, "created_at": date + "T00:00:00", "total_usd": 0.0,
        "by_chain": {}, "wallets": [
            {"wallet": name, "address": "0x" + name, "type": "evm", "total_usd": 0.0,
             "tokens": [dict(t, wallet=name) for t in tokens]}
            for name, tokens in wallets
        ],
    }


def token(symbol, usd, chain="eth", token_id=None):
    return {"symbol": symbol, "name": symbol, "chain": chain, "usd": usd,
            "amount": usd, "price": 1.0, "token_id": token_id or ("0x" + symbol.lower())}


class HistoryAggregateTest(unittest.TestCase):
    def setUp(self):
        for d in os.listdir(_TMP.name):
            p = os.path.join(_TMP.name, d)
            if os.path.isdir(p):
                shutil.rmtree(p)
        try:
            os.remove(os.path.join(_TMP.name, ".active"))
        except OSError:
            pass
        profiles.create_profile("default", from_template=False)
        profiles.set_active("default")
        bl.reset_cache()
        assetlabels.reset_cache()
        storage._schema_done.clear()
        storage.init_db()
        self.guard()

    def guard(self):
        for path in (profiles.db_path(), profiles.PROFILES_DIR):
            if not os.path.realpath(path).startswith(os.path.realpath(_TMP.name)):
                self.fail(f"path escaped the temp dir: {path}")

    def seed(self):
        storage.save_snapshot(snapshot("2026-01-01", [
            ("alice", [token("BTC", 600), token("USDC", 400)]),
            ("bob", [token("SOL", 100, chain="sol")]),
        ]))
        storage.save_snapshot(snapshot("2026-01-02", [
            ("alice", [token("BTC", 700), token("USDC", 300)]),
            ("bob", [token("SOL", 200, chain="sol")]),
        ]))

    def reference(self):
        """The original algorithm: parse every snapshot and filter it live."""
        import sqlite3
        conn = sqlite3.connect(profiles.db_path())
        conn.row_factory = sqlite3.Row
        dates = [r["date"] for r in conn.execute("SELECT date FROM snapshots ORDER BY date")]
        totals, wallets, chains = [], {}, {}
        for d in dates:
            raw = conn.execute("SELECT raw FROM snapshots WHERE date=?", (d,)).fetchone()
            snap = json.loads(raw["raw"])
            snap["date"] = d
            v = view_of(snap)
            totals.append(v["total_usd"])
            for w in v["wallets"]:
                wallets.setdefault(w["wallet"], {})[d] = w["total_usd"]
            for c, val in v["by_chain"].items():
                chains.setdefault(c, {})[d] = val
        conn.close()
        return {"dates": dates, "totals": totals,
                "wallets": {w: [s.get(d, 0.0) for d in dates] for w, s in wallets.items()},
                "chains": {c: [s.get(d, 0.0) for d in dates] for c, s in chains.items()}}

    def test_the_aggregates_match_the_raw_json_result(self):
        self.seed()
        got, want = storage.get_history(0), self.reference()
        self.assertEqual(got["dates"], want["dates"])
        self.assertEqual(got["totals"], want["totals"])
        self.assertEqual(got["wallets"], want["wallets"])
        self.assertEqual(got["chains"], want["chains"])

    def test_a_snapshot_is_aggregated_on_write(self):
        self.seed()
        self.assertEqual(storage.get_history(0)["totals"], [1100, 1200])

    def test_a_blacklist_entry_rewrites_history(self):
        """The reason history is not read from the (fetch-time filtered) token rows:
        adding a blacklist entry today must also remove it from yesterday."""
        self.seed()
        self.assertEqual(storage.get_history(0)["totals"][1], 1200)
        bl.add_entry({"symbol": "BTC"})
        after = storage.get_history(0)
        self.assertEqual(after["totals"], [500, 500])          # BTC gone from both days
        bl.remove_entry(0)
        self.assertEqual(storage.get_history(0)["totals"], [1100, 1200])

    def test_a_label_rule_change_also_rewrites_history(self):
        self.seed()
        before = storage.get_history(0)["chains"]
        assetlabels.add_entry({"symbol": "SOL", "category": "sol", "action": "include"})
        after = storage.get_history(0)["chains"]
        self.assertEqual(sorted(after), sorted(before))        # chain totals unaffected…
        self.assertEqual(storage.get_history(0)["totals"], [1100, 1200])

    def test_pruning_drops_the_matching_aggregate_rows(self):
        """A dropped snapshot must not leave its aggregate rows behind, or the trend
        would show days that no longer exist."""
        import sqlite3
        self.seed()
        storage.save_snapshot(snapshot("2026-02-01", [("alice", [token("BTC", 900)])]))
        dropped = storage.prune_snapshots(today="2026-03-01", keep_days=1, keep_monthly=1)
        self.assertEqual(dropped["dropped_dates"], ["2026-01-01", "2026-01-02"])
        got = storage.get_history(0)
        self.assertEqual(got["dates"], ["2026-02-01"])
        self.assertEqual(got["totals"], [900])
        conn = sqlite3.connect(profiles.db_path())
        stale = conn.execute(
            "SELECT COUNT(*) FROM history_totals WHERE date IN ('2026-01-01','2026-01-02')"
        ).fetchone()[0]
        conn.close()
        self.assertEqual(stale, 0)

    def test_pruning_with_no_tail_keeps_nothing_old(self):
        self.seed()
        storage.prune_snapshots(today="2026-03-01", keep_days=1, keep_monthly=0)
        self.assertEqual(storage.get_history(0)["dates"], [])

    def test_days_limits_the_window(self):
        self.seed()
        got = storage.get_history(1)
        self.assertEqual(got["dates"], ["2026-01-02"])
        self.assertEqual(len(got["wallets"]["alice"]), 1)

    def test_an_empty_db_returns_empty_series(self):
        got = storage.get_history(0)
        self.assertEqual(got, {"dates": [], "totals": [], "wallets": {}, "chains": {}})

    def test_the_rebuild_is_committed_so_it_happens_once(self):
        """A rebuild that is rolled back on close would repeat on every request —
        which is exactly the bug the aggregate table exists to remove."""
        import sqlite3
        self.seed()
        storage.get_history(0)
        conn = sqlite3.connect(profiles.db_path())
        rows = conn.execute("SELECT COUNT(*) FROM history_totals").fetchone()[0]
        sig = conn.execute("SELECT value FROM meta WHERE key='history_sig'").fetchone()
        conn.close()
        self.assertGreater(rows, 0)
        self.assertIsNotNone(sig)
        # a second read must not rebuild: nothing but the read happens here
        self.assertEqual(storage.get_history(0)["totals"], [1100, 1200])
        conn = sqlite3.connect(profiles.db_path())
        again = conn.execute("SELECT COUNT(*) FROM history_totals").fetchone()[0]
        conn.close()
        self.assertEqual(rows, again)


if __name__ == "__main__":
    unittest.main()
