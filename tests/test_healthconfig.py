# -*- coding: utf-8 -*-
"""Health thresholds (per profile) and the volatility split they score.

The thresholds are the one part of the health report the user edits, so the tests
cover the validation edges (range, ordering, junk values, a corrupt file) rather
than just the happy path — a bad threshold must never take the report down, and a
partial update from the settings form must merge instead of wiping the other two
groups.

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

from tracker import health, healthconfig, profiles, views  # noqa: E402

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
        healthconfig.reset_cache()
        self.guard()

    def guard(self):
        real = os.path.realpath(healthconfig.health_file())
        if not real.startswith(os.path.realpath(_TMP.name)):
            self.fail(f"path escaped the temp dir: {real}")


class ThresholdValidationTest(unittest.TestCase):
    def test_defaults_are_complete(self):
        cfg = healthconfig.defaults()
        self.assertEqual(sorted(cfg), ["concentration", "storage", "volatility"])
        for group in cfg:
            self.assertEqual(sorted(cfg[group]), sorted(healthconfig.DEFAULTS[group]))

    def test_a_partial_update_merges_over_the_defaults(self):
        cfg = healthconfig.normalize({"concentration": {"warning": 30}})
        self.assertEqual(cfg["concentration"]["warning"], 30.0)
        self.assertEqual(cfg["concentration"]["danger"], 75.0)   # untouched
        self.assertEqual(cfg["volatility"], healthconfig.DEFAULTS["volatility"])

    def test_values_are_clamped_to_a_percentage_range(self):
        for bad in (-1, 101, 1e9):
            with self.assertRaises(ValueError):
                healthconfig.normalize({"volatility": {"warning": bad}})

    def test_junk_values_are_rejected(self):
        for bad in ("abc", None, [], {}, float("nan"), float("inf")):
            with self.assertRaises(ValueError):
                healthconfig.normalize({"volatility": {"danger": bad}})

    def test_the_pair_must_be_ordered(self):
        with self.assertRaises(ValueError):
            healthconfig.normalize({"volatility": {"warning": 80, "danger": 70}})
        with self.assertRaises(ValueError):
            healthconfig.normalize({"volatility": {"warning": 70, "danger": 70}})

    def test_storage_is_inverted_because_more_cold_is_better(self):
        with self.assertRaises(ValueError):
            healthconfig.normalize({"storage": {"safe": 10, "warning": 40}})
        ok = healthconfig.normalize({"storage": {"safe": 60, "warning": 30}})
        self.assertEqual(ok["storage"]["safe"], 60.0)

    def test_a_wrong_shape_is_rejected(self):
        with self.assertRaises(ValueError):
            healthconfig.normalize("nope")
        with self.assertRaises(ValueError):
            healthconfig.normalize({"volatility": 5})

    def test_values_are_rounded_to_one_decimal(self):
        cfg = healthconfig.normalize({"volatility": {"warning": 59.456}})
        self.assertEqual(cfg["volatility"]["warning"], 59.5)

    def test_an_unknown_group_is_ignored_not_stored(self):
        cfg = healthconfig.normalize({"nonsense": {"x": 1}})
        self.assertNotIn("nonsense", cfg)


class ThresholdStoreTest(_TempProfileTest):
    def test_a_fresh_profile_reports_the_defaults(self):
        self.assertEqual(healthconfig.load(), healthconfig.DEFAULTS)

    def test_save_then_load_round_trips(self):
        healthconfig.save({"concentration": {"warning": 40, "danger": 60}})
        healthconfig.reset_cache()          # force a re-read from disk
        cfg = healthconfig.load()
        self.assertEqual(cfg["concentration"], {"warning": 40.0, "danger": 60.0})

    def test_the_file_is_written_under_the_profile(self):
        healthconfig.save({"volatility": {"warning": 10, "danger": 20}})
        with open(healthconfig.health_file(), encoding="utf-8") as fh:
            self.assertEqual(json.load(fh)["volatility"], {"warning": 10.0, "danger": 20.0})

    def test_a_corrupt_file_falls_back_to_the_defaults(self):
        with open(healthconfig.health_file(), "w", encoding="utf-8") as fh:
            fh.write("{not json")
        healthconfig.reset_cache()
        self.assertEqual(healthconfig.load(), healthconfig.DEFAULTS)

    def test_out_of_range_values_on_disk_fall_back_to_the_defaults(self):
        with open(healthconfig.health_file(), "w", encoding="utf-8") as fh:
            json.dump({"volatility": {"warning": -5, "danger": 999}}, fh)
        healthconfig.reset_cache()
        self.assertEqual(healthconfig.load()["volatility"],
                         healthconfig.DEFAULTS["volatility"])

    def test_thresholds_are_per_profile(self):
        healthconfig.save({"volatility": {"warning": 10, "danger": 20}})
        profiles.create_profile("second", from_template=False)
        profiles.set_active("second")
        healthconfig.reset_cache()
        self.assertEqual(healthconfig.load(), healthconfig.DEFAULTS)
        profiles.set_active("default")
        healthconfig.reset_cache()
        self.assertEqual(healthconfig.load()["volatility"]["warning"], 10.0)


class ThresholdsDriveTheReportTest(_TempProfileTest):
    """The point of the setting: the same portfolio re-grades when it changes."""

    # 40 % volatile: comfortable under the defaults, uncomfortable if you say so
    WALLETS = [{"wallet": "evm-1", "type": "evm", "storage": "hot", "total_usd": 100.0}]
    LABELS = {"stable": 30.0, "btc": 30.0, "other": 40.0}

    def test_the_default_thresholds_call_this_safe(self):
        data = health.analyze(self.WALLETS, self.LABELS)
        self.assertEqual(data["volatility"]["level"], health.SAFE)

    def test_lowering_the_threshold_re_grades_the_same_portfolio(self):
        healthconfig.save({"volatility": {"warning": 30, "danger": 50}})
        data = health.analyze(self.WALLETS, self.LABELS)
        self.assertEqual(data["volatility"]["level"], health.WARNING)
        self.assertIn("healthVolatilityRisk",
                      [s["key"] for s in data["suggestions"]])

    def test_raising_it_clears_the_warning_again(self):
        healthconfig.save({"volatility": {"warning": 95, "danger": 99}})
        data = health.analyze(self.WALLETS, self.LABELS)
        self.assertEqual(data["volatility"]["level"], health.SAFE)
        self.assertNotIn("healthVolatilityRisk",
                         [s["key"] for s in data["suggestions"]])

    def test_the_gauge_receives_the_configured_thresholds(self):
        healthconfig.save({"concentration": {"warning": 20, "danger": 30}})
        data = health.analyze(self.WALLETS, self.LABELS)
        self.assertEqual(data["concentration"]["thresholds"], {"warning": 20.0, "danger": 30.0})


class VolatilityTotalsTest(_TempProfileTest):
    SNAP = {"date": "2026-01-01", "wallets": [
        {"wallet": "w1", "type": "evm", "tokens": [
            {"chain": "eth", "symbol": "USDC", "usd": 500.0},
            {"chain": "eth", "symbol": "ETH", "usd": 300.0},
        ]},
        {"wallet": "btc-1", "type": "btc", "tokens": [
            {"chain": "btc", "symbol": "BTC", "usd": 200.0},
        ]},
    ]}

    def test_tokens_are_split_into_the_three_buckets(self):
        totals = views.volatility_totals(self.SNAP)
        self.assertEqual(totals["stable"], 500.0)
        self.assertEqual(totals["btc"], 200.0)
        self.assertEqual(totals["other"], 300.0)

    def test_the_view_carries_the_split(self):
        view = views.view_of(self.SNAP)
        self.assertEqual(view["by_volatility"], {"stable": 500.0, "btc": 200.0, "other": 300.0})

    def test_a_blacklisted_row_is_not_counted(self):
        snap = json.loads(json.dumps(self.SNAP))
        snap["wallets"][0]["tokens"][1]["symbol"] = "ETHG"      # on the built-in blacklist
        totals = views.volatility_totals(snap)
        self.assertEqual(totals["other"], 0.0)
        self.assertEqual(totals["stable"], 500.0)

    def test_a_zero_usd_row_is_ignored(self):
        snap = json.loads(json.dumps(self.SNAP))
        snap["wallets"][0]["tokens"].append({"chain": "eth", "symbol": "JUNK", "usd": 0})
        self.assertEqual(views.volatility_totals(snap)["other"], 300.0)

    def test_exchange_holdings_land_in_their_token_bucket(self):
        snap = {"date": "x", "wallets": [{"wallet": "binance_read", "type": "cex", "tokens": [
            {"chain": "binance", "symbol": "USDT", "usd": 1000.0},
            {"chain": "binance", "symbol": "BTC", "usd": 100.0},
        ]}]}
        totals = views.volatility_totals(snap)
        self.assertEqual(totals["stable"], 1000.0)
        self.assertEqual(totals["btc"], 100.0)
        self.assertEqual(totals["other"], 0.0)

    def test_an_empty_snapshot_yields_zeroes(self):
        self.assertEqual(views.volatility_totals({}),
                         {"stable": 0.0, "btc": 0.0, "other": 0.0})


if __name__ == "__main__":
    unittest.main()
