# -*- coding: utf-8 -*-
"""S1/S2/S3/P2: secret masking, the cross-site write fence, refresh throttling
and snapshot retention."""
import importlib
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tracker import sources  # noqa: E402
from tracker import storage  # noqa: E402


class MaskingTest(unittest.TestCase):
    """S1 — secrets must not leave the API in the clear by default."""

    def test_mask_keeps_a_recognisable_stub(self):
        self.assertEqual(sources.mask_secret("0123456789abcdef0123456789abcdef01234567"),
                         "0123\u20264567")
        self.assertEqual(sources.mask_secret(""), "")
        self.assertEqual(sources.mask_secret(None), "")
        # too short to hint at without leaking most of it
        self.assertEqual(sources.mask_secret("abc"), sources.MASK)

    def test_mask_config_covers_nested_keys_and_url_secrets(self):
        cfg = {
            "debank": {"key": "0123456789abcdef0123456789abcdef01234567",
                       "providers": [{"name": "p", "key": "abcdef1234567890"}]},
            "solana": {"rpc": [{"name": "helius",
                                "url": "https://mainnet.helius-rpc.com/?api-key=00000000-1111-2222-3333-444444444444"}]},
            "cex": {"accounts": [{"name": "binance_read", "key": "K1234567890", "secret": "S1234567890"}]},
            "plain": "https://api.example.com/v3/simple/price",
        }
        masked = sources.mask_config(cfg)
        blob = json.dumps(masked)
        for secret in ("0123456789abcdef0123456789abcdef01234567", "abcdef1234567890",
                       "00000000-1111-2222-3333-444444444444", "K1234567890", "S1234567890"):
            self.assertNotIn(secret, blob, f"{secret} leaked through mask_config")
        # the masked URL still shows where it points
        self.assertIn("mainnet.helius-rpc.com", masked["solana"]["rpc"][0]["url"])
        # a non-secret URL is left alone
        self.assertEqual(masked["plain"], cfg["plain"])

    def test_round_trip_preserves_real_secrets(self):
        """The settings form posts back what it was given; that must not destroy keys."""
        cfg = {"debank": {"key": "realkey1234567890"},
               "solana": {"rpc": [{"url": "https://h/?api-key=abcdefghijklmnop"}]},
               "cex": {"accounts": [{"key": "K", "secret": "S"}]}}
        posted = sources.mask_config(cfg)          # what the browser round-trips
        merged = sources.merge_masked(posted, cfg)
        self.assertEqual(merged["debank"]["key"], "realkey1234567890")
        self.assertEqual(merged["solana"]["rpc"][0]["url"], "https://h/?api-key=abcdefghijklmnop")
        # a short secret masks to a bare ellipsis and must still survive a save
        self.assertEqual(merged["cex"]["accounts"][0]["key"], "K")
        self.assertEqual(merged["cex"]["accounts"][0]["secret"], "S")

    def test_a_genuinely_new_key_is_still_saved(self):
        current = {"debank": {"key": "oldkey1234567890"}}
        incoming = {"debank": {"key": "brandnewkey987654"}}
        self.assertEqual(sources.merge_masked(incoming, current)["debank"]["key"], "brandnewkey987654")
        # clearing a key on purpose still works
        self.assertEqual(sources.merge_masked({"debank": {"key": ""}}, current)["debank"]["key"], "")


class WriteGuardTest(unittest.TestCase):
    """S2 — a cross-site page must not be able to trigger a write."""

    def _guard(self, headers, is_post=True):
        from tracker.server import Handler

        class Fake(Handler):
            def __init__(self, hdrs):
                self.headers = hdrs
        return Fake(headers)._write_guard(is_post=is_post)

    def test_blocks_cross_site_requests(self):
        self.assertIsNotNone(self._guard({"Sec-Fetch-Site": "cross-site"}))
        self.assertIsNotNone(self._guard({"Sec-Fetch-Site": "CROSS-SITE"}))
        # DNS-rebinding / foreign origin
        self.assertIsNotNone(self._guard({"Origin": "http://evil.example", "Host": "127.0.0.1:8080"}))
        # an opaque origin is what a sandboxed iframe / data: page sends
        self.assertIsNotNone(self._guard({"Origin": "null", "Host": "127.0.0.1:8080"}))

    def test_allows_same_origin_and_non_browser_callers(self):
        # the dashboard itself
        self.assertIsNone(self._guard({"Sec-Fetch-Site": "same-origin",
                                       "Origin": "http://127.0.0.1:8080",
                                       "Host": "127.0.0.1:8080",
                                       "Content-Type": "application/json"}))
        # curl / the scheduler send neither header
        self.assertIsNone(self._guard({}))
        self.assertIsNone(self._guard({"Content-Type": "application/json"}))

    def test_post_body_must_be_json(self):
        hdrs = {"Content-Type": "text/plain", "Content-Length": "12"}
        self.assertIsNotNone(self._guard(hdrs))
        hdrs = {"Content-Type": "application/x-www-form-urlencoded", "Content-Length": "12"}
        self.assertIsNotNone(self._guard(hdrs))
        # an empty POST with no content type is fine
        self.assertIsNone(self._guard({}))


class RetentionTest(unittest.TestCase):
    """P2 — the database must not grow without bound."""

    def test_recent_window_is_kept_whole_and_the_tail_is_thinned(self):
        import datetime
        today = "2026-09-20"
        days, d = [], datetime.date(2025, 8, 1)
        while d.isoformat() <= today:
            days.append(d.isoformat())
            d += datetime.timedelta(days=1)
        keep, drop = storage.plan_retention(days, today=today, keep_days=90, keep_monthly=12)
        # exhaustive and disjoint: nothing silently disappears
        self.assertEqual(sorted(keep + drop), sorted(set(days)))
        self.assertEqual(set(keep) & set(drop), set())
        # the dense window is exactly keep_days long, and today always survives
        self.assertEqual(len([k for k in keep if k >= "2026-06-23"]), 90)
        self.assertIn(today, keep)
        # the tail keeps a single representative per month
        tail = [k for k in keep if k < "2026-06-23"]
        self.assertEqual(len(tail), len({t[:7] for t in tail}))

    def test_edge_cases(self):
        self.assertEqual(storage.plan_retention([], today="2026-09-20"), ([], []))
        self.assertEqual(storage.plan_retention(["2026-09-20"], today="2026-09-20"),
                         (["2026-09-20"], []))
        # keep_monthly=0 drops the whole tail but still keeps the dense window
        keep, drop = storage.plan_retention(["2026-01-01", "2026-09-20"],
                                            today="2026-09-20", keep_days=30, keep_monthly=0)
        self.assertEqual(keep, ["2026-09-20"])
        self.assertEqual(drop, ["2026-01-01"])

    def test_prune_deletes_rows_from_every_table(self):
        tmp = tempfile.mkdtemp()
        old_db = storage._db_path
        try:
            db = os.path.join(tmp, "t.db")
            storage._db_path = lambda: db
            storage.init_db()
            with storage._lock:
                conn = storage._connect()
                for date in ("2020-01-01", "2026-09-20"):
                    conn.execute("INSERT INTO snapshots(date,created_at,total_usd,by_chain,raw) "
                                 "VALUES (?,?,?,?,?)", (date, "x", 1.0, "{}", "{}"))
                    conn.execute("INSERT INTO wallet_totals(date,wallet,usd) VALUES (?,?,?)",
                                 (date, "w", 1.0))
                    conn.execute("INSERT INTO tokens(date,wallet,chain,token_id,symbol,name,amount,"
                                 "price,usd,logo) VALUES (?,?,?,?,?,?,?,?,?,?)",
                                 (date, "w", "eth", "t", "SYM", "N", 1.0, 1.0, 1.0, ""))
                conn.commit()
                conn.close()
            summary = storage.prune_snapshots(today="2026-09-20", keep_days=30, keep_monthly=0)
            self.assertEqual(summary["dropped"], 1)
            self.assertEqual(summary["dropped_dates"], ["2020-01-01"])
            with storage._lock:
                conn = storage._connect()
                for table in ("snapshots", "wallet_totals", "tokens"):
                    left = conn.execute(f"SELECT DISTINCT date FROM {table}").fetchall()
                    self.assertEqual([r[0] for r in left], ["2026-09-20"], f"{table} not pruned")
                conn.close()
        finally:
            storage._db_path = old_db


if __name__ == "__main__":
    unittest.main()
