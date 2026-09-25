# -*- coding: utf-8 -*-
"""Asset health analysis (three indicators + suggestions).

The indicators are threshold-driven, so the tests pin the boundaries rather than
the arithmetic: a portfolio one dollar either side of 60/70, 50/75 and 50/20 %
must land on different levels. The suggestion list is what the user acts on, so
its suppression rules (a BTC-heavy portfolio is not told to buy BTC) are checked
too.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tracker import health  # noqa: E402

# the tests pin the maths, not the operator's settings: thresholds are injected
CFG = {"volatility": {"warning": 60.0, "danger": 70.0},
       "concentration": {"warning": 50.0, "danger": 75.0},
       "storage": {"safe": 50.0, "warning": 20.0}}


def lab(stable=0.0, btc=0.0, other=0.0):
    return {"stable": stable, "btc": btc, "other": other}


def w(name, usd, type_="evm", storage=None):
    row = {"wallet": name, "type": type_, "total_usd": usd}
    if storage:
        row["storage"] = storage
    return row


class VolatilityTest(unittest.TestCase):
    """Stablecoins / BTC / everything else, scored on the third bucket."""

    def test_the_three_buckets_are_totalled_and_shared(self):
        v = health.volatility(lab(stable=100, btc=300, other=600), CFG)
        self.assertEqual(v["buckets"]["stable"]["balance"], 100.0)
        self.assertEqual(v["buckets"]["btc"]["balance"], 300.0)
        self.assertEqual(v["buckets"]["other"]["balance"], 600.0)
        self.assertEqual(v["total"], 1000.0)
        self.assertEqual(v["buckets"]["other"]["percent"], 60.0)
        self.assertEqual(v["buckets"]["stable"]["percent"], 10.0)

    def test_the_risk_level_tracks_the_volatile_share(self):
        for pct, level in ((59.0, health.SAFE), (60.0, health.WARNING),
                           (69.9, health.WARNING), (70.0, health.HIGH_RISK)):
            v = health.volatility(lab(stable=100 - pct, other=pct), CFG)
            self.assertEqual(v["level"], level, pct)

    def test_stablecoins_and_btc_do_not_count_as_risk(self):
        """A portfolio that is all stablecoins and BTC is safe however large it is."""
        v = health.volatility(lab(stable=9_000_000, btc=1_000_000), CFG)
        self.assertEqual(v["buckets"]["other"]["percent"], 0.0)
        self.assertEqual(v["level"], health.SAFE)

    def test_an_empty_portfolio_is_safe_not_a_division_by_zero(self):
        v = health.volatility(lab(), CFG)
        self.assertEqual(v["total"], 0.0)
        self.assertEqual(v["level"], health.SAFE)
        self.assertEqual(v["buckets"]["other"]["percent"], 0.0)

    def test_missing_buckets_are_treated_as_zero(self):
        v = health.volatility({"other": 10}, CFG)
        self.assertEqual(v["total"], 10.0)
        self.assertEqual(v["buckets"]["stable"]["balance"], 0.0)

    def test_junk_values_do_not_crash_the_card(self):
        v = health.volatility({"stable": None, "btc": "x", "other": 5}, CFG)
        self.assertEqual(v["total"], 5.0)

    def test_the_thresholds_are_returned_for_the_gauge(self):
        v = health.volatility(lab(other=1), {"volatility": {"warning": 30, "danger": 40}})
        self.assertEqual(v["thresholds"], {"warning": 30, "danger": 40})

    def test_whole_wallets_are_a_documented_fallback(self):
        """Without token labels a BTC wallet counts as BTC and the rest as volatile."""
        split = health.wallet_volatility([
            {"wallet": "btc-1", "type": "btc", "total_usd": 100},
            {"wallet": "evm-1", "type": "evm", "total_usd": 20}])
        self.assertEqual(split, {"stable": 0.0, "btc": 100.0, "other": 20.0})


class ConcentrationTest(unittest.TestCase):
    def test_the_largest_wallet_sets_the_figure(self):
        c = health.concentration([w("a", 600), w("b", 400)], CFG)
        self.assertEqual(c["percent"], 60.0)
        self.assertEqual(c["maxWallet"], "a")
        self.assertEqual(c["level"], health.WARNING)

    def test_thresholds(self):
        for pct, level in ((49.0, health.SAFE), (50.0, health.WARNING),
                           (74.9, health.WARNING), (75.0, health.HIGH_RISK)):
            # the remainder is split so that "a" really is the largest wallet
            rest = (100 - pct) / 2
            c = health.concentration([w("a", pct), w("b", rest), w("c", rest)], CFG)
            self.assertEqual(c["percent"], pct, pct)
            self.assertEqual(c["level"], level, pct)

    def test_a_btc_heavy_wallet_is_flagged_as_btc(self):
        c = health.concentration([w("btc-1", 900, "btc"), w("evm-1", 100)], CFG)
        self.assertTrue(c["maxWalletIsBtc"])
        self.assertEqual(c["maxWalletType"], "btc")

    def test_non_btc_wallet_is_not_flagged_as_btc(self):
        c = health.concentration([w("evm-1", 900), w("btc-1", 100, "btc")], CFG)
        self.assertFalse(c["maxWalletIsBtc"])

    def test_an_empty_portfolio_reports_safe_with_no_wallet(self):
        c = health.concentration([], CFG)
        self.assertEqual(c["percent"], 0.0)
        self.assertIsNone(c["maxWallet"])
        self.assertEqual(c["level"], health.SAFE)

    def test_zero_balance_wallets_do_not_become_the_maximum(self):
        c = health.concentration([w("empty", 0), w("real", 10)], CFG)
        self.assertEqual(c["maxWallet"], "real")
        self.assertEqual(c["percent"], 100.0)


class StorageTest(unittest.TestCase):
    def test_cex_type_wins_over_the_stored_preference(self):
        """An exchange account is custody by definition; the field cannot make it cold."""
        self.assertEqual(health.storage_kind({"type": "cex", "storage": "cold"}), "cex")

    def test_missing_field_means_hot(self):
        self.assertEqual(health.storage_kind({"type": "evm"}), "hot")
        self.assertEqual(health.storage_kind({"type": "evm", "storage": ""}), "hot")

    def test_an_unknown_value_is_treated_as_hot(self):
        self.assertEqual(health.storage_kind({"type": "evm", "storage": "vault"}), "hot")

    def test_cold_and_hot_are_read_from_the_field(self):
        s = health.storage_security([w("ledger", 600, storage="cold"), w("hot-1", 400)], CFG)
        self.assertEqual(s["storage"]["cold"]["balance"], 600.0)
        self.assertEqual(s["storage"]["hot"]["balance"], 400.0)
        self.assertEqual(s["storage"]["cold"]["percent"], 60.0)
        self.assertEqual(s["securityLevel"], health.SAFE)

    def test_thresholds_are_inverted_because_more_cold_is_better(self):
        for pct, level in ((0.0, health.HIGH_RISK), (19.9, health.HIGH_RISK),
                           (20.0, health.WARNING), (49.9, health.WARNING),
                           (50.0, health.SAFE)):
            s = health.storage_security([w("cold", pct, storage="cold"),
                                         w("hot", 100 - pct)], CFG)
            self.assertEqual(s["securityLevel"], level, pct)

    def test_an_empty_portfolio_is_safe(self):
        """Nothing at risk is not the same as everything at risk."""
        self.assertEqual(health.storage_security([], CFG)["securityLevel"], health.SAFE)

    def test_wallet_names_are_kept_per_bucket(self):
        s = health.storage_security([w("a", 1, storage="cold"), w("b", 1),
                                     w("cex", 1, "cex")], CFG)
        self.assertEqual(s["storage"]["cold"]["wallets"], ["a"])
        self.assertEqual(s["storage"]["hot"]["wallets"], ["b"])
        self.assertEqual(s["storage"]["cex"]["wallets"], ["cex"])


class SuggestionTest(unittest.TestCase):
    def test_a_healthy_portfolio_gets_one_all_clear(self):
        rows = [w("btc-1", 600, "btc", storage="cold"), w("evm-1", 100),
                w("binance_read", 300, "cex")]
        out = health.analyze(rows, lab(btc=600, other=400), CFG)["suggestions"]
        self.assertEqual([s["key"] for s in out], ["healthOk"])
        self.assertEqual(out[0]["level"], health.SAFE)

    def test_each_failing_indicator_contributes_one_line(self):
        rows = [w("evm-big", 800), w("btc-1", 100, "btc"), w("cex-1", 100, "cex")]
        out = health.analyze(rows, lab(btc=100, other=900), CFG)["suggestions"]
        keys = [s["key"] for s in out]
        self.assertIn("healthVolatilityRisk", keys)
        self.assertIn("healthStorageAdvice", keys)
        self.assertNotIn("healthOk", keys)

    def test_a_concentrated_btc_portfolio_is_not_told_to_buy_btc(self):
        rows = [w("btc-1", 600, "btc", storage="cold"), w("evm-1", 250),
                w("cex-1", 150, "cex")]
        health_data = health.analyze(rows, lab(btc=600, other=400), CFG)
        self.assertEqual(health_data["concentration"]["level"], health.WARNING)
        self.assertTrue(health_data["concentration"]["maxWalletIsBtc"])
        keys = [s["key"] for s in health_data["suggestions"]]
        self.assertNotIn("healthConcentration", keys)
        self.assertEqual(keys, ["healthOk"])

    def test_a_concentrated_non_btc_portfolio_is(self):
        rows = [w("evm-1", 900, storage="cold"), w("btc-1", 100, "btc")]
        keys = [s["key"] for s in health.analyze(rows, lab(btc=100, other=900), CFG)["suggestions"]]
        self.assertIn("healthConcentrationAdvice", keys)

    def test_a_suggestion_carries_the_numbers_its_sentence_needs(self):
        rows = [w("evm-1", 800), w("btc-1", 200, "btc")]
        out = health.analyze(rows, lab(btc=100, other=900), CFG)["suggestions"]
        vol = next(s for s in out if s["key"] == "healthVolatilityRisk")
        self.assertEqual(vol["pct"], 90.0)
        conc = next(s for s in out if s["key"] == "healthConcentrationAdvice")
        self.assertEqual(conc["pct"], 80.0)
        self.assertEqual(conc["wallet"], "evm-1")


class AnalyzeTest(unittest.TestCase):
    def test_the_report_has_all_three_indicators(self):
        data = health.analyze([w("btc-1", 100, "btc")], lab(btc=100), CFG)
        self.assertEqual(sorted(data), ["concentration", "storage", "suggestions",
                                        "total", "volatility"])
        self.assertEqual(data["total"], 100.0)

    def test_the_fallback_split_is_used_when_no_labels_are_given(self):
        data = health.analyze([w("btc-1", 100, "btc"), w("evm-1", 100)])
        self.assertEqual(data["volatility"]["buckets"]["btc"]["balance"], 100.0)
        self.assertEqual(data["volatility"]["buckets"]["other"]["balance"], 100.0)

    def test_junk_rows_are_ignored(self):
        data = health.analyze([None, "x", 5, w("btc-1", 100, "btc")], lab(btc=100), CFG)
        self.assertEqual(data["total"], 100.0)

    def test_a_missing_total_is_treated_as_zero(self):
        data = health.analyze([{"wallet": "x", "type": "evm"}], lab(), CFG)
        self.assertEqual(data["total"], 0.0)


if __name__ == "__main__":
    unittest.main()
