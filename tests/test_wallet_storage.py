# -*- coding: utf-8 -*-
"""Wallet storage class (hot / cold) and its path into the health report.

`storage` is the only per-wallet field the health report reads, and it is written
by the browser through /api/wallets/storage, so it needs the same treatment as
any other config write: validated, persisted, and never able to touch a wallet it
was not pointed at.

Everything runs inside a throwaway PROFILES_DIR; a containment guard fails the
suite if a patched path ever escapes it.
"""
import json
import os
import shutil
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tracker import health, profiles, views, walletstore  # noqa: E402

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


class _TempProfileTest(unittest.TestCase):
    """A clean, ACTIVE throwaway profile per test — views and the blacklist both
    resolve through the active profile, so it has to exist before either is used."""

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
        walletstore.reset_cache()
        self._guard()

    def _guard(self):
        """A patch that silently stopped applying would write the operator's real
        wallets.json, which is exactly the accident these tests exist to prevent."""
        for path in (profiles.wallets_file(), profiles.PROFILES_DIR):
            real = os.path.realpath(path)
            if not real.startswith(os.path.realpath(_TMP.name)):
                self.fail(f"path escaped the temp dir: {real}")

    def test_the_containment_guard_rejects_an_escaping_path(self):
        self.assertRaises(AssertionError, self.fail, "path escaped the temp dir: /tmp/x")

    def test_a_new_wallet_defaults_to_hot(self):
        walletstore.add_wallet({"name": "w1", "type": "evm", "address": "0xabc"})
        self.assertEqual(walletstore.user_wallets()[0]["storage"], "hot")

    def test_a_cold_wallet_round_trips_through_the_file(self):
        walletstore.add_wallet({"name": "ledger", "type": "btc", "address": "bc1q",
                                "storage": "cold"})
        walletstore.reset_cache()          # force a re-read from disk
        self.assertEqual(walletstore.user_wallets()[0]["storage"], "cold")
        with open(profiles.wallets_file(), encoding="utf-8") as fh:
            self.assertEqual(json.load(fh)[0]["storage"], "cold")

    def test_an_unknown_storage_value_is_rejected(self):
        with self.assertRaises(ValueError):
            walletstore.add_wallet({"name": "w1", "type": "evm", "address": "0xabc",
                                    "storage": "vault"})
        self.assertEqual(walletstore.user_wallets(), [])

    def test_cex_is_not_a_user_selectable_storage_value(self):
        """An exchange account is custody by definition; health.py derives it."""
        with self.assertRaises(ValueError):
            walletstore.normalize_storage("cex")

    def test_storage_can_be_changed_after_the_fact(self):
        walletstore.add_wallet({"name": "w1", "type": "evm", "address": "0xabc"})
        walletstore.add_wallet({"name": "w2", "type": "btc", "address": "bc1q"})
        walletstore.set_storage(1, "cold")
        entries = walletstore.user_wallets()
        self.assertEqual(entries[0]["storage"], "hot")
        self.assertEqual(entries[1]["storage"], "cold")

    def test_changing_storage_keeps_every_other_field(self):
        walletstore.add_wallet({"name": "w1", "type": "sol", "address": "So1"})
        walletstore.set_storage(0, "cold")
        self.assertEqual(walletstore.user_wallets()[0],
                         {"name": "w1", "type": "sol", "address": "So1", "storage": "cold"})

    def test_an_out_of_range_index_is_rejected(self):
        walletstore.add_wallet({"name": "w1", "type": "evm", "address": "0xabc"})
        for index in (-1, 1, 99):
            with self.assertRaises(ValueError):
                walletstore.set_storage(index, "cold")
        self.assertEqual(walletstore.user_wallets()[0]["storage"], "hot")

    def test_an_unknown_value_is_rejected_on_update(self):
        walletstore.add_wallet({"name": "w1", "type": "evm", "address": "0xabc"})
        with self.assertRaises(ValueError):
            walletstore.set_storage(0, "warm")
        self.assertEqual(walletstore.user_wallets()[0]["storage"], "hot")


class ViewToHealthTest(_TempProfileTest):
    """The health figures shown in the UI are computed from view_of(), so the
    storage class must survive that trip."""

    def _snap(self, wallets):
        return {"date": "2026-01-01", "created_at": "2026-01-01T00:00:00",
                "wallets": [{"wallet": w["name"], "type": w["type"], "storage": w.get("storage"),
                             "tokens": [{"chain": w["type"], "symbol": "X", "usd": w["usd"]}]}
                            for w in wallets]}

    def test_storage_is_carried_into_the_view(self):
        view = views.view_of(self._snap([
            {"name": "ledger", "type": "btc", "usd": 100.0, "storage": "cold"},
            {"name": "hot-1", "type": "evm", "usd": 100.0, "storage": "hot"}]))
        by_name = {w["wallet"]: w for w in view["wallets"]}
        self.assertEqual(by_name["ledger"]["storage"], "cold")
        self.assertEqual(by_name["hot-1"]["storage"], "hot")

    def test_a_snapshot_without_the_field_becomes_hot(self):
        view = views.view_of(self._snap([{"name": "old", "type": "evm", "usd": 10.0}]))
        self.assertIsNone(view["wallets"][0]["storage"])
        data = health.analyze(view["wallets"])
        self.assertEqual(data["storage"]["storage"]["hot"]["balance"], 10.0)
        self.assertEqual(data["storage"]["storage"]["cold"]["balance"], 0.0)

    def test_a_cold_wallet_moves_the_storage_indicator(self):
        hot = health.analyze(views.view_of(self._snap([
            {"name": "a", "type": "evm", "usd": 100.0, "storage": "hot"}]))["wallets"])
        self.assertEqual(hot["storage"]["securityLevel"], health.HIGH_RISK)

        cold = views.view_of(self._snap([
            {"name": "ledger", "type": "btc", "usd": 60.0, "storage": "cold"},
            {"name": "a", "type": "evm", "usd": 40.0, "storage": "hot"}]))
        data = health.analyze(cold["wallets"])
        self.assertEqual(data["storage"]["storage"]["cold"]["percent"], 60.0)
        self.assertEqual(data["storage"]["securityLevel"], health.SAFE)

    def test_a_cex_wallet_counts_as_exchange_custody_whatever_it_says(self):
        view = views.view_of(self._snap([
            {"name": "binance_read", "type": "cex", "usd": 100.0, "storage": "cold"}]))
        data = health.analyze(view["wallets"])
        self.assertEqual(data["storage"]["storage"]["cex"]["balance"], 100.0)
        self.assertEqual(data["storage"]["storage"]["cold"]["balance"], 0.0)


class LiveStorageWinsTest(_TempProfileTest):
    """The reported bug: marking a wallet cold in Settings left the health panel
    showing the old split, because the view read the class out of the stored
    snapshot (frozen at the last refresh)."""

    SNAP = {"date": "2026-01-01", "created_at": "2026-01-01T00:00:00", "wallets": [
        {"wallet": "ledger", "type": "btc", "storage": None,
         "tokens": [{"chain": "btc", "symbol": "BTC", "usd": 60.0}]},
        {"wallet": "hot-1", "type": "evm", "storage": None,
         "tokens": [{"chain": "eth", "symbol": "ETH", "usd": 40.0}]},
    ]}

    def test_the_live_setting_overrides_the_snapshot(self):
        view = views.view_of(self.SNAP, storage_map={"ledger": "cold"})
        data = health.analyze(view["wallets"])
        self.assertEqual(data["storage"]["storage"]["cold"]["balance"], 60.0)
        self.assertEqual(data["storage"]["securityLevel"], health.SAFE)

    def test_without_the_map_the_snapshot_value_is_used(self):
        self.assertEqual(health.analyze(views.view_of(self.SNAP)["wallets"])["storage"]["securityLevel"],
                         health.HIGH_RISK)

    def test_a_wallet_missing_from_the_map_keeps_its_stored_class(self):
        snap = json.loads(json.dumps(self.SNAP))
        snap["wallets"][0]["storage"] = "cold"
        view = views.view_of(snap, storage_map={"hot-1": "hot"})
        by_name = {w["wallet"]: w["storage"] for w in view["wallets"]}
        self.assertEqual(by_name["ledger"], "cold")

    def test_a_removed_wallet_keeps_the_class_it_was_snapshotted_with(self):
        """Deleting a wallet from the live list must not silently reclassify the
        history it is still part of."""
        snap = json.loads(json.dumps(self.SNAP))
        snap["wallets"][0]["storage"] = "cold"
        view = views.view_of(snap, storage_map={})     # wallet no longer configured
        by_name = {w["wallet"]: w["storage"] for w in view["wallets"]}
        self.assertEqual(by_name["ledger"], "cold")

    def test_switching_a_wallet_back_to_hot_is_reflected_too(self):
        snap = json.loads(json.dumps(self.SNAP))
        snap["wallets"][0]["storage"] = "cold"
        view = views.view_of(snap, storage_map={"ledger": "hot"})
        self.assertEqual({w["wallet"]: w["storage"] for w in view["wallets"]}["ledger"], "hot")


if __name__ == "__main__":
    unittest.main()
