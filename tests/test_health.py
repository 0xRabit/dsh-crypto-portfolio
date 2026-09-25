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


def w(name, usd, type_="evm", storage=None):
    row = {"wallet": name, "type": type_, "total_usd": usd}
    if storage:
        row["storage"] = storage
    return row


class TieringTest(unittest.TestCase):
    def test_wallets_are_split_btc_onchain_cex(self):
        t = health.tiering([w("btc-1", 500, "btc"), w("evm-1", 300), w("sol-1", 100, "sol"),
                            w("binance_read", 100, "cex")])
        tiers = t["tiers"]
        self.assertEqual(tiers["tier1"]["balance"], 500.0)
        self.assertEqual(tiers["tier2"]["balance"], 400.0)
        self.assertEqual(tiers["tier3"]["balance"], 100.0)
        self.assertEqual(t["total"], 1000.0)
        self.assertEqual(tiers["tier2"]["percent"], 40.0)

    def test_doge_and_ada_count_as_onchain_not_cex(self):
        t = health.tiering([w("doge-1", 100, "doge"), w("ada-1", 100, "ada")])
        self.assertEqual(t["tiers"]["tier2"]["balance"], 200.0)
        self.assertEqual(t["tiers"]["tier3"]["balance"], 0.0)

    def test_the_risk_level_tracks_the_onchain_share(self):
        # 59% / 60% / 69% / 70%: the two thresholds are inclusive lower bounds
        for pct, level in ((59.0, health.SAFE), (60.0, health.WARNING),
                           (69.9, health.WARNING), (70.0, health.HIGH_RISK)):
            tier2 = pct * 10
            rows = [w("btc-1", 1000 - tier2, "btc"), w("evm-1", tier2)]
            self.assertEqual(health.tiering(rows)["onChainRiskLevel"], level, pct)

    def test_an_empty_portfolio_is_safe_not_a_division_by_zero(self):
        t = health.tiering([])
        self.assertEqual(t["total"], 0.0)
        self.assertEqual(t["onChainRiskLevel"], health.SAFE)
        self.assertEqual(t["tiers"]["tier1"]["percent"], 0.0)

    def test_tier_members_are_listed_for_the_tooltip(self):
        t = health.tiering([w("btc-1", 10, "btc"), w("btc-2", 5, "btc")])
        self.assertEqual(sorted(t["tiers"]["tier1"]["wallets"]), ["btc-1", "btc-2"])
        # a wallet with no balance is still a member, it just adds nothing
        t2 = health.tiering([w("btc-1", 0, "btc")])
        self.assertEqual(t2["tiers"]["tier1"]["wallets"], [])


class ConcentrationTest(unittest.TestCase):
    def test_the_largest_wallet_sets_the_figure(self):
        c = health.concentration([w("a", 600), w("b", 400)])
        self.assertEqual(c["percent"], 60.0)
        self.assertEqual(c["maxWallet"], "a")
        self.assertEqual(c["level"], health.WARNING)

    def test_thresholds(self):
        for pct, level in ((49.0, health.SAFE), (50.0, health.WARNING),
                           (74.9, health.WARNING), (75.0, health.HIGH_RISK)):
            # the remainder is split so that "a" really is the largest wallet
            rest = (100 - pct) / 2
            c = health.concentration([w("a", pct), w("b", rest), w("c", rest)])
            self.assertEqual(c["percent"], pct, pct)
            self.assertEqual(c["level"], level, pct)

    def test_a_btc_heavy_wallet_is_flagged_as_btc(self):
        c = health.concentration([w("btc-1", 900, "btc"), w("evm-1", 100)])
        self.assertTrue(c["maxWalletIsBtc"])
        self.assertEqual(c["maxWalletType"], "btc")

    def test_non_btc_wallet_is_not_flagged_as_btc(self):
        c = health.concentration([w("evm-1", 900), w("btc-1", 100, "btc")])
        self.assertFalse(c["maxWalletIsBtc"])

    def test_an_empty_portfolio_reports_safe_with_no_wallet(self):
        c = health.concentration([])
        self.assertEqual(c["percent"], 0.0)
        self.assertIsNone(c["maxWallet"])
        self.assertEqual(c["level"], health.SAFE)

    def test_zero_balance_wallets_do_not_become_the_maximum(self):
        c = health.concentration([w("empty", 0), w("real", 10)])
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
        s = health.storage_security([w("ledger", 600, storage="cold"), w("hot-1", 400)])
        self.assertEqual(s["storage"]["cold"]["balance"], 600.0)
        self.assertEqual(s["storage"]["hot"]["balance"], 400.0)
        self.assertEqual(s["storage"]["cold"]["percent"], 60.0)
        self.assertEqual(s["securityLevel"], health.SAFE)

    def test_thresholds_are_inverted_because_more_cold_is_better(self):
        for pct, level in ((0.0, health.HIGH_RISK), (19.9, health.HIGH_RISK),
                           (20.0, health.WARNING), (49.9, health.WARNING),
                           (50.0, health.SAFE)):
            s = health.storage_security([w("cold", pct, storage="cold"),
                                         w("hot", 100 - pct)])
            self.assertEqual(s["securityLevel"], level, pct)

    def test_an_empty_portfolio_is_safe(self):
        """Nothing at risk is not the same as everything at risk."""
        self.assertEqual(health.storage_security([])["securityLevel"], health.SAFE)

    def test_wallet_names_are_kept_per_bucket(self):
        s = health.storage_security([w("a", 1, storage="cold"), w("b", 1),
                                     w("cex", 1, "cex")])
        self.assertEqual(s["storage"]["cold"]["wallets"], ["a"])
        self.assertEqual(s["storage"]["hot"]["wallets"], ["b"])
        self.assertEqual(s["storage"]["cex"]["wallets"], ["cex"])


class SuggestionTest(unittest.TestCase):
    def test_a_healthy_portfolio_gets_one_all_clear(self):
        rows = [w("btc-1", 600, "btc", storage="cold"), w("evm-1", 100),
                w("binance_read", 300, "cex")]
        out = health.analyze(rows)["suggestions"]
        self.assertEqual([s["key"] for s in out], ["healthOk"])
        self.assertEqual(out[0]["level"], health.SAFE)

    def test_each_failing_indicator_contributes_one_line(self):
        rows = [w("evm-big", 800), w("btc-1", 100, "btc"), w("cex-1", 100, "cex")]
        out = health.analyze(rows)["suggestions"]
        keys = [s["key"] for s in out]
        self.assertIn("healthOnChainRisk", keys)
        self.assertIn("healthStorageAdvice", keys)
        self.assertNotIn("healthOk", keys)

    def test_a_concentrated_btc_portfolio_is_not_told_to_buy_btc(self):
        rows = [w("btc-1", 600, "btc", storage="cold"), w("evm-1", 250),
                w("cex-1", 150, "cex")]
        health_data = health.analyze(rows)
        self.assertEqual(health_data["concentration"]["level"], health.WARNING)
        self.assertTrue(health_data["concentration"]["maxWalletIsBtc"])
        keys = [s["key"] for s in health_data["suggestions"]]
        self.assertNotIn("healthConcentration", keys)
        self.assertEqual(keys, ["healthOk"])

    def test_a_concentrated_non_btc_portfolio_is(self):
        rows = [w("evm-1", 900, storage="cold"), w("btc-1", 100, "btc")]
        keys = [s["key"] for s in health.analyze(rows)["suggestions"]]
        self.assertIn("healthConcentration", keys)

    def test_a_suggestion_carries_the_numbers_its_sentence_needs(self):
        rows = [w("evm-1", 800), w("btc-1", 200, "btc")]
        out = health.analyze(rows)["suggestions"]
        onchain = next(s for s in out if s["key"] == "healthOnChainRisk")
        self.assertEqual(onchain["pct"], 80.0)
        conc = next(s for s in out if s["key"] == "healthConcentration")
        self.assertEqual(conc["pct"], 80.0)
        self.assertEqual(conc["wallet"], "evm-1")


class AnalyzeTest(unittest.TestCase):
    def test_the_report_has_all_three_indicators(self):
        data = health.analyze([w("btc-1", 100, "btc")])
        self.assertEqual(sorted(data), ["concentration", "storage", "suggestions",
                                        "tiering", "total"])
        self.assertEqual(data["total"], 100.0)

    def test_junk_rows_are_ignored(self):
        data = health.analyze([None, "x", 5, w("btc-1", 100, "btc")])
        self.assertEqual(data["total"], 100.0)

    def test_a_missing_total_is_treated_as_zero(self):
        data = health.analyze([{"wallet": "x", "type": "evm"}])
        self.assertEqual(data["total"], 0.0)


if __name__ == "__main__":
    unittest.main()
