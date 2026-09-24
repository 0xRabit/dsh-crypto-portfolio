# -*- coding: utf-8 -*-
"""Backpack balance merging.

Backpack reports a balance across two signed views, and the exchange UI's
"US Dollar" row is USDC in the futures collateral account — not a spot balance.
Reading only /api/v1/capital hid the largest position in the account, and the two
views overlap (a pledged spot balance appears in both with the same quantity), so
this needs a test rather than trust.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tracker import cex  # noqa: E402


def _spot(**assets):
    return {a: {"available": str(v), "locked": "0", "staked": "0"} for a, v in assets.items()}


def _collateral(entries):
    return {"assetsValue": "0", "collateral": entries}


def _entry(symbol, qty, mark):
    return {"symbol": symbol, "totalQuantity": str(qty), "assetMarkPrice": str(mark)}


class BackpackMergeTest(unittest.TestCase):
    def setUp(self):
        self.calls = []

        def fake_sign(_acc):
            def call(instruction, path):
                self.calls.append((instruction, path))
                if instruction == "balanceQuery":
                    if self.spot_fails:
                        raise RuntimeError("spot unavailable")
                    return self.spot
                if self.collateral_fails:
                    raise RuntimeError("collateral unavailable")
                return self.coll
            return call
        self._orig = cex._backpack_sign
        cex._backpack_sign = fake_sign
        self.spot = {}
        self.coll = {}
        self.spot_fails = False
        self.collateral_fails = False

    def tearDown(self):
        cex._backpack_sign = self._orig

    def test_it_queries_both_balance_views(self):
        cex._backpack_state({"key": "k", "secret": "s"})
        self.assertEqual(self.calls, [("balanceQuery", "/api/v1/capital"),
                                      ("collateralQuery", "/api/v1/capital/collateral")])

    def test_a_collateral_only_balance_is_included(self):
        """This is the reported bug: the exchange UI's "US Dollar" is collateral
        USDC and the spot endpoint never mentions it."""
        self.spot = _spot(BP=350.0)
        self.coll = _collateral([_entry("USDC", 1492.4796, 1)])
        balances, prices = cex._backpack_state({"key": "k", "secret": "s"})
        self.assertAlmostEqual(balances["USDC"], 1492.4796)
        self.assertAlmostEqual(balances["BP"], 350.0)
        self.assertEqual(prices["USDC"], 1.0)

    def test_an_overlapping_asset_is_not_double_counted(self):
        """A pledged spot balance is reported identically in both views; summing the
        two responses would have doubled GOOGL.US."""
        self.spot = _spot(**{"GOOGL.US": 1.44986})
        self.coll = _collateral([_entry("GOOGL.US", 1.44986, 339.09)])
        balances, prices = cex._backpack_state({"key": "k", "secret": "s"})
        self.assertAlmostEqual(balances["GOOGL.US"], 1.44986)
        self.assertEqual(prices["GOOGL.US"], 339.09)

    def test_the_larger_of_the_two_quantities_wins(self):
        # e.g. lent-out quantity only shows up in the collateral view
        self.spot = _spot(SOL=0.01)
        self.coll = _collateral([_entry("SOL", 0.0195, 116.0)])
        balances, _ = cex._backpack_state({"key": "k", "secret": "s"})
        self.assertAlmostEqual(balances["SOL"], 0.0195)

    def test_points_are_not_treated_as_an_asset(self):
        """1838 Backpack points have no price and are absent from the UI's list."""
        self.spot = _spot(POINTS=1838.2, BP=1.0)
        self.coll = _collateral([_entry("POINTS", 500, 0)])
        balances, _ = cex._backpack_state({"key": "k", "secret": "s"})
        self.assertNotIn("POINTS", balances)
        self.assertIn("BP", balances)

    def test_zero_quantities_are_dropped(self):
        self.spot = _spot(BP=0, TRUMP=0.02)
        self.coll = _collateral([_entry("SEI", 0, 0.06)])
        balances, _ = cex._backpack_state({"key": "k", "secret": "s"})
        self.assertEqual(sorted(balances), ["TRUMP"])

    def test_a_spot_only_key_still_yields_spot_balances(self):
        self.spot = _spot(BP=350.0)
        self.collateral_fails = True
        balances, prices = cex._backpack_state({"key": "k", "secret": "s"})
        self.assertAlmostEqual(balances["BP"], 350.0)
        self.assertEqual(prices, {})


class PriceOfTest(unittest.TestCase):
    def test_stables_and_native_symbols(self):
        self.assertEqual(cex._price_of("USDC", {}, {}), 1.0)
        self.assertEqual(cex._price_of("BTC", {"bitcoin": 84000}, {}), 84000)

    def test_a_missing_native_price_falls_back_to_the_exchange(self):
        """Reporting a holding as worth nothing because the on-chain price pipeline
        is down is worse than using the exchange's own price."""
        self.assertEqual(cex._price_of("BTC", {}, {"BTC": 84500}), 84500)
        self.assertEqual(cex._price_of("BTC", {"bitcoin": 0}, {"BTC": 84500}), 84500)

    def test_tokenised_stock_price_comes_from_the_ticker_map(self):
        self.assertEqual(cex._price_of("GOOGL.US", {}, {"GOOGL.US": 339.09}), 339.09)

    def test_an_unpriceable_asset_is_zero(self):
        self.assertEqual(cex._price_of("FRAG", {}, {}), 0.0)


if __name__ == "__main__":
    unittest.main()
