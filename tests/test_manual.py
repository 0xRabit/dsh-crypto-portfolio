# -*- coding: utf-8 -*-
"""Hand-registered protocol positions (tracker/manual.py).

Some protocols have no balance API, so the position is written down by hand. The
contract that matters: a registration is an estimate **with a date** — it never
follows the market, a refresh never overwrites it, and it counts from its own date
onwards so registering today cannot rewrite last month's history.

These tests pin the validation, the row shape the rest of the app consumes, and the
two integrations that make it visible: `views.view_of` (totals, wallet cards, chain
distribution, health) and `storage.get_tokens` / `get_history`.
"""
import json
import os
import shutil
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tracker import manual, profiles, storage, views  # noqa: E402

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
    return {"date": date, "created_at": date + "T00:00:00", "total_usd": 0.0,
            "by_chain": {}, "wallets": [
                {"wallet": name, "address": "0x" + name, "type": "evm", "total_usd": 0.0,
                 "tokens": [dict(t, wallet=name) for t in tokens]}
                for name, tokens in wallets]}


def token(symbol, usd, chain="eth"):
    return {"symbol": symbol, "name": symbol, "chain": chain, "usd": usd,
            "amount": usd, "price": 1.0, "token_id": "0x" + symbol.lower()}


class ManualCase(unittest.TestCase):
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
        manual.reset_cache()
        storage._schema_done.clear()
        storage.init_db()
        # the wallet list lives on disk; keep validation deterministic
        self._names = manual.wallet_names
        manual.wallet_names = lambda: ["evm-1", "binance_read"]

    def tearDown(self):
        manual.wallet_names = self._names

    def add(self, **kw):
        entry = {"wallet": "evm-1", "protocol": "Papertrade", "symbol": "PT",
                 "amount": 1000, "value_usd": 500, "date": "2026-10-18"}
        entry.update(kw)
        return manual.upsert(entry)


class ValidationTest(ManualCase):
    def test_a_position_needs_a_wallet_a_protocol_and_a_symbol(self):
        for field in ("wallet", "protocol", "symbol"):
            entry = {"wallet": "evm-1", "protocol": "P", "symbol": "S"}
            entry[field] = ""
            with self.assertRaises(ValueError, msg=field):
                manual.upsert(dict(entry))

    def test_an_unknown_wallet_is_rejected_and_the_known_ones_are_listed(self):
        with self.assertRaises(ValueError) as ctx:
            self.add(wallet="nope")
        self.assertIn("evm-1", str(ctx.exception))

    def test_a_bad_date_is_rejected(self):
        with self.assertRaises(ValueError):
            self.add(date="18/10/2026")

    def test_negative_numbers_are_rejected(self):
        with self.assertRaises(ValueError):
            self.add(amount=-1)
        with self.assertRaises(ValueError):
            self.add(value_usd=-5)

    def test_defaults_fill_in_the_name_the_date_and_an_id(self):
        row = manual.upsert({"wallet": "evm-1", "protocol": "Papertrade", "symbol": "PT"})
        self.assertEqual(row["name"], "Papertrade")
        self.assertEqual(len(row["id"]) >= 6, True)
        self.assertTrue(row["date"])                       # defaults to today

    def test_the_file_is_written_as_json(self):
        self.add()
        with open(manual.manual_file(), encoding="utf-8") as fh:
            data = json.load(fh)
        self.assertEqual(data["version"], 1)
        self.assertEqual(len(data["positions"]), 1)


class CrudTest(ManualCase):
    def test_add_then_list(self):
        self.add()
        rows = manual.positions()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["protocol"], "Papertrade")

    def test_upsert_with_an_id_replaces_instead_of_appending(self):
        first = self.add()
        second = manual.upsert({"id": first["id"], "wallet": "evm-1",
                                "protocol": "Papertrade", "symbol": "PT",
                                "amount": 1, "value_usd": 700, "date": "2026-10-18"})
        rows = manual.positions()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["value_usd"], 700.0)
        self.assertEqual(rows[0]["created_at"], first["created_at"])
        self.assertEqual(second["id"], first["id"])

    def test_remove(self):
        row = self.add()
        self.assertTrue(manual.remove(row["id"]))
        self.assertEqual(manual.positions(), [])
        self.assertFalse(manual.remove(row["id"]))

    def test_newest_registration_comes_first(self):
        self.add(date="2026-10-01", protocol="A")
        self.add(date="2026-10-18", protocol="B")
        self.assertEqual([p["protocol"] for p in manual.positions()], ["B", "A"])

    def test_duplicate_ids_in_a_file_are_repaired(self):
        row = self.add()
        with open(manual.manual_file(), encoding="utf-8") as fh:
            data = json.load(fh)
        data["positions"].append(dict(data["positions"][0]))
        with open(manual.manual_file(), "w", encoding="utf-8") as fh:
            json.dump(data, fh)
        manual.reset_cache()
        ids = [p["id"] for p in manual.positions()]
        self.assertEqual(len(ids), len(set(ids)), ids)
        self.assertIn(row["id"], ids)


class RowsTest(ManualCase):
    def test_a_position_looks_like_a_token_row(self):
        self.add(amount=1000, value_usd=500, date="2026-10-18")
        row = manual.rows("2026-10-18")[0]
        self.assertEqual(row["wallet"], "evm-1")
        self.assertEqual(row["chain"], "manual")
        self.assertEqual(row["symbol"], "PT")
        self.assertEqual(row["usd"], 500.0)
        self.assertEqual(row["amount"], 1000.0)
        self.assertAlmostEqual(row["price"], 0.5)          # implied unit price
        self.assertTrue(row["manual"])
        self.assertEqual(row["date"], "2026-10-18")
        self.assertEqual(row["protocol"], "Papertrade")
        self.assertTrue(row["token_id"].startswith("manual:"))

    def test_no_amount_means_no_implied_price(self):
        self.add(amount=0, value_usd=250)
        row = manual.rows("2026-10-18")[0]
        self.assertEqual(row["price"], 0.0)
        self.assertEqual(row["usd"], 250.0)

    def test_it_counts_from_its_own_date_onwards_only(self):
        self.add(date="2026-10-18")
        self.assertEqual(manual.rows("2026-10-17"), [])
        self.assertEqual(len(manual.rows("2026-10-18")), 1)
        self.assertEqual(len(manual.rows("2026-11-01")), 1)

    def test_totals_per_date_and_per_wallet(self):
        self.add(date="2026-10-18", value_usd=500)
        self.add(date="2026-10-20", value_usd=300, protocol="Other", symbol="OT")
        dates = ["2026-10-17", "2026-10-18", "2026-10-21"]
        self.assertEqual(manual.totals_by_date(dates),
                         {"2026-10-17": 0.0, "2026-10-18": 500.0, "2026-10-21": 800.0})
        self.assertEqual(manual.wallet_totals_by_date(dates)["evm-1"],
                         {"2026-10-18": 500.0, "2026-10-21": 800.0})


class ViewIntegrationTest(ManualCase):
    def test_the_total_wallet_card_and_chain_distribution_include_it(self):
        self.add(value_usd=500, date="2026-10-18")
        view = views.view_of(snapshot("2026-10-18", [
            ("evm-1", [token("BTC", 1000)]),
        ]))
        self.assertEqual(view["total_usd"], 1500.0)
        wallet = [w for w in view["wallets"] if w["wallet"] == "evm-1"][0]
        self.assertEqual(wallet["total_usd"], 1500.0)
        self.assertEqual(wallet["token_count"], 2)
        self.assertEqual(view["by_chain"]["manual"], 500.0)

    def test_a_wallet_that_only_holds_a_registration_still_shows_up(self):
        self.add(wallet="evm-1", value_usd=500, date="2026-10-18")
        view = views.view_of(snapshot("2026-10-18", [("binance_read", [token("USDT", 100)])]))
        names = [w["wallet"] for w in view["wallets"]]
        self.assertIn("evm-1", names)
        self.assertTrue([w for w in view["wallets"] if w["wallet"] == "evm-1"][0]["manual_only"])
        self.assertEqual(view["total_usd"], 600.0)

    def test_a_later_registration_does_not_touch_an_earlier_snapshot(self):
        self.add(value_usd=500, date="2026-10-18")
        view = views.view_of(snapshot("2026-10-17", [("evm-1", [token("BTC", 1000)])]))
        self.assertEqual(view["total_usd"], 1000.0)

    def test_the_health_report_sees_it_too(self):
        # a manual stablecoin counts as a stablecoin, so the volatility figure moves
        self.add(symbol="USDT", value_usd=500, date="2026-10-18")
        totals = views.volatility_totals(snapshot("2026-10-18", [
            ("evm-1", [token("HYPE", 500)]),
        ]))
        self.assertEqual(totals["stable"], 500.0)
        self.assertEqual(totals["other"], 500.0)


class StorageIntegrationTest(ManualCase):
    def test_the_token_table_lists_it_with_its_label(self):
        storage.save_snapshot(snapshot("2026-10-18", [("evm-1", [token("BTC", 1000)])]))
        self.add(symbol="PT", value_usd=500, date="2026-10-18")
        rows = storage.get_tokens("2026-10-18")
        manual_rows = [r for r in rows if r.get("manual")]
        self.assertEqual(len(manual_rows), 1)
        self.assertEqual(manual_rows[0]["symbol"], "PT")
        self.assertEqual(manual_rows[0]["usd"], 500.0)
        self.assertIn("cat", manual_rows[0])
        # and it sorts with everything else, by value
        self.assertEqual(rows[0]["symbol"], "BTC")

    def test_the_trend_adds_it_from_its_date_on(self):
        storage.save_snapshot(snapshot("2026-10-17", [("evm-1", [token("BTC", 1000)])]))
        storage.save_snapshot(snapshot("2026-10-18", [("evm-1", [token("BTC", 1000)])]))
        self.add(value_usd=500, date="2026-10-18")
        history = storage.get_history()
        by_date = dict(zip(history["dates"], history["totals"]))
        self.assertEqual(by_date["2026-10-17"], 1000.0)
        self.assertEqual(by_date["2026-10-18"], 1500.0)
        self.assertEqual(history["wallets"]["evm-1"][-1], 1500.0)


if __name__ == "__main__":
    unittest.main()
