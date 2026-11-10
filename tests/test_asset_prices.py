# -*- coding: utf-8 -*-
"""Assets with a real quantity but no public quote.

A tokenised stock is the case that started this: Binance holds it in the funding
wallet as `EQ_TSLA` with `stockTicker: "TSLA"`, 12.5 units — and no exchange
ticker, no CoinGecko entry. Priced at $0 the row fell behind "hide zero" and the
holding was invisible; the quantity was never the problem, the price was.

So: the symbol loses its `EQ_` wrapper, and a *stated* price (Settings → Sources)
values anything the market cannot. These tests pin both, plus the config round-trip.
"""
import os
import shutil
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tracker import cex, profiles, sources  # noqa: E402

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


class _Case(unittest.TestCase):
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
        sources.load(force=True)


class AssetPriceConfigTest(_Case):
    def test_set_read_remove(self):
        self.assertEqual(sources.asset_prices(), {})
        prices = sources.set_asset_price("tsla", 150)
        self.assertEqual(prices, {"TSLA": 150.0})          # symbol is normalised
        self.assertEqual(sources.asset_prices(), {"TSLA": 150.0})
        prices = sources.set_asset_price("TSLA", 175.5)    # an edit replaces
        self.assertEqual(prices, {"TSLA": 175.5})
        self.assertEqual(sources.remove_asset_price("TSLA"), {})
        self.assertEqual(sources.asset_prices(), {})

    def test_a_bad_symbol_or_price_is_rejected(self):
        for bad in ("", "with space", "x" * 30, "TSLA;rm"):
            with self.assertRaises(ValueError, msg=bad):
                sources.set_asset_price(bad, 10)
        for bad in (0, -1, "abc", None):
            with self.assertRaises(ValueError, msg=repr(bad)):
                sources.set_asset_price("TSLA", bad)

    def test_a_corrupt_entry_does_not_break_reading(self):
        sources.save({"asset_prices": {"TSLA": 120, "BAD": "x", "ZERO": 0, "OK": "5"}})
        self.assertEqual(sources.asset_prices(), {"TSLA": 120.0, "OK": 5.0})

    def test_it_survives_a_reload(self):
        sources.set_asset_price("TSLA", 42)
        sources.load(force=True)
        self.assertEqual(sources.asset_prices(), {"TSLA": 42.0})


class StockSymbolTest(unittest.TestCase):
    def test_a_tokenised_stock_loses_the_eq_prefix(self):
        self.assertEqual(cex._asset_symbol({"asset": "EQ_TSLA", "stockTicker": "TSLA"}), "TSLA")
        # no stockTicker given: strip the wrapper anyway
        self.assertEqual(cex._asset_symbol({"asset": "EQ_TSLA"}), "TSLA")

    def test_ordinary_assets_are_untouched(self):
        for asset in ("USDT", "EQX", "LDBNB", "TSLAB"):
            self.assertEqual(cex._asset_symbol({"asset": asset}), asset)


class StatedPriceTest(_Case):
    """fetch_cex_accounts must use the stated price only when the market has none."""

    def _accounts(self, balances):
        return [{"name": "binance_read", "exchange": "binance", "enabled": True}]

    def test_a_priced_asset_is_counted(self):
        sources.set_asset_price("TSLA", 150)
        with mock.patch.object(cex, "_binance_balances",
                               return_value=({"TSLA": 12.5}, {}, [])), \
             mock.patch.object(cex, "_ticker_map", return_value={}):
            out = cex.fetch_cex_accounts(self._accounts(None), {})
        row = out[0]["rows"][0]
        self.assertEqual(row["symbol"], "TSLA")
        self.assertAlmostEqual(row["price"], 150.0)
        self.assertAlmostEqual(row["usd"], 12.5 * 150.0, places=5)

    def test_without_a_stated_price_it_stays_at_zero(self):
        with mock.patch.object(cex, "_binance_balances",
                               return_value=({"TSLA": 12.5}, {}, [])), \
             mock.patch.object(cex, "_ticker_map", return_value={}):
            out = cex.fetch_cex_accounts(self._accounts(None), {})
        self.assertEqual(out[0]["rows"][0]["usd"], 0.0)

    def test_the_market_price_wins_over_the_stated_one(self):
        sources.set_asset_price("TSLA", 150)
        with mock.patch.object(cex, "_binance_balances",
                               return_value=({"TSLA": 1}, {}, [])), \
             mock.patch.object(cex, "_ticker_map", return_value={"TSLA": 200.0}):
            out = cex.fetch_cex_accounts(self._accounts(None), {})
        self.assertAlmostEqual(out[0]["rows"][0]["price"], 200.0)

    def test_a_stablecoin_is_still_one_dollar(self):
        sources.set_asset_price("USDT", 7)          # nonsense, but must not win
        with mock.patch.object(cex, "_binance_balances",
                               return_value=({"USDT": 10}, {}, [])), \
             mock.patch.object(cex, "_ticker_map", return_value={}):
            out = cex.fetch_cex_accounts(self._accounts(None), {})
        self.assertAlmostEqual(out[0]["rows"][0]["price"], 1.0)


if __name__ == "__main__":
    unittest.main()
