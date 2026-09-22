# -*- coding: utf-8 -*-
"""Asset-type classification (the "asset type" donut and the stablecoin tag)."""
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tracker import config, profiles, stablecoins  # noqa: E402


def row(symbol, name="", price=0.0, chain="eth", token_id="", usd=0.0):
    return {"symbol": symbol, "name": name, "price": price, "chain": chain,
            "token_id": token_id, "usd": usd}


class ClassifyTest(unittest.TestCase):
    def setUp(self):
        # never touch the real profile file
        self._tmp = tempfile.mkdtemp()
        self._orig = profiles.stablecoins_file
        self._orig_active = profiles.active
        profiles.stablecoins_file = lambda: os.path.join(self._tmp, "stablecoins.json")
        stablecoins.reset_cache()

    def tearDown(self):
        profiles.stablecoins_file = self._orig
        profiles.active = self._orig_active
        stablecoins.reset_cache()

    def test_stablecoin_wildcards_cover_bridged_forms(self):
        for sym in ("USDT", "USDC", "USDT.e", "USDC.e", "USDBC", "BUSD", "FDUSD",
                    "PYUSD", "USDe", "sUSDe", "crvUSD", "FRAX", "DAI", "DAI.e",
                    "GUSD", "LUSD", "TUSD", "USDP", "MIM", "DOLA"):
            with self.subTest(symbol=sym):
                self.assertEqual(stablecoins.classify(row(sym, price=1.0)), stablecoins.STABLE)

    def test_bitcoin_family(self):
        for sym in ("BTC", "WBTC", "cbBTC", "tBTC", "renBTC", "BTC.b", "LBTC"):
            with self.subTest(symbol=sym):
                self.assertEqual(stablecoins.classify(row(sym, price=63000)), stablecoins.BTC)

    def test_other(self):
        for sym, price in (("ETH", 2500), ("SOL", 150), ("JUP", 0.8), ("HYPE", 30)):
            with self.subTest(symbol=sym):
                self.assertEqual(stablecoins.classify(row(sym, price=price)), stablecoins.OTHER)

    def test_price_band_catches_unlisted_pegs_but_only_near_one_dollar(self):
        # A ticker no wildcard covers, whose NAME marks it as a dollar asset, is
        # picked up only while it actually trades near $1 (ZKL matches nothing).
        self.assertEqual(stablecoins.classify(row("ZKL", "Zekul USD", price=1.001)),
                         stablecoins.STABLE)
        self.assertEqual(stablecoins.classify(row("ZKL", "Zekul USD", price=0.42)),
                         stablecoins.OTHER)
        self.assertEqual(stablecoins.classify(row("ZKL", "Zekul USD", price=0.0)),
                         stablecoins.OTHER)
        # A named wildcard is authoritative: USDT is a stablecoin whatever it trades
        # at, because asset class is not the same question as "is the peg holding".
        self.assertEqual(stablecoins.classify(row("USDT", "Tether", price=0.0)),
                         stablecoins.STABLE)
        self.assertEqual(stablecoins.classify(row("XUSD", "Some Dollar", price=0.42)),
                         stablecoins.STABLE)   # matched by the *USD* wildcard
        # a $1 token with no dollar marker is not assumed to be a stablecoin
        self.assertEqual(stablecoins.classify(row("MAGIC", "Magic", price=1.0)),
                         stablecoins.OTHER)

    def test_scam_tokens_named_after_stablecoins_stay_out(self):
        # real rows from a live snapshot: phishing tokens name-drop tether/dai
        for sym, name, price in (
            ("$ U5DT [EVENT-STETHER.NET]", "Visit tetherv2.com", 0.0),
            ("iDAI", "Instadapp DAI", 0.0467),
            ("yvDAI", "Yearn DAI", 1.2677),
            ("xdai.firstchef.net", "claim rewards", 0.0),
        ):
            with self.subTest(symbol=sym):
                self.assertEqual(stablecoins.classify(row(sym, name, price)), stablecoins.OTHER)

    def test_user_include_and_exclude_rules(self):
        # include: an unknown ticker the user knows is a stablecoin
        stablecoins.add_entry({"symbol": "MYUSDX", "category": "stable"})
        self.assertEqual(stablecoins.classify(row("MYUSDX", price=0.5)), stablecoins.STABLE)
        # exclude: pin a wildcard false-positive back out
        stablecoins.add_entry({"symbol": "USDT*", "category": "other", "action": "exclude",
                               "chain": "tron"})
        self.assertEqual(stablecoins.classify(row("USDT", chain="tron", price=1.0)),
                         stablecoins.OTHER)
        # ...without disturbing the same symbol on another chain
        self.assertEqual(stablecoins.classify(row("USDT", chain="eth", price=1.0)),
                         stablecoins.STABLE)

    def test_duplicate_and_invalid_rules_rejected(self):
        stablecoins.add_entry({"symbol": "DUPX", "category": "stable"})
        with self.assertRaises(ValueError):
            stablecoins.add_entry({"symbol": "DUPX", "category": "stable"})
        with self.assertRaises(ValueError):
            stablecoins.add_entry({"symbol": "X", "category": "nonsense"})
        with self.assertRaises(ValueError):
            stablecoins.add_entry({"category": "stable"})   # nothing to match on

    def test_annotate_and_category_totals_are_additive(self):
        rows = [row("USDC", price=1.0, usd=100.0), row("BTC", price=60000, usd=250.0),
                row("ETH", price=2500, usd=50.0)]
        ann = stablecoins.annotate(rows)
        self.assertEqual([r["cat"] for r in ann], ["stable", "btc", "other"])
        totals = stablecoins.category_totals(rows)
        self.assertEqual(totals[stablecoins.STABLE], 100.0)
        self.assertEqual(totals[stablecoins.BTC], 250.0)
        self.assertEqual(totals[stablecoins.OTHER], 50.0)
        self.assertEqual(sum(totals.values()), 400.0)   # nothing lost or double counted
        # annotate must not mutate the caller's rows
        self.assertNotIn("cat", rows[0])

    def test_user_rules_persist_and_hot_reload(self):
        stablecoins.add_entry({"symbol": "PERSISTX", "category": "btc"})
        path = profiles.stablecoins_file()
        self.assertTrue(os.path.exists(path))
        with open(path, encoding="utf-8") as fh:
            on_disk = json.load(fh)
        self.assertEqual(on_disk[0]["symbol"], "PERSISTX")
        stablecoins.reset_cache()
        self.assertEqual(len(stablecoins.user_entries()), 1)

    def test_builtin_list_has_no_catch_all_pattern(self):
        """A `*` built-in would classify every token as a stablecoin."""
        for entry in stablecoins.builtin_entries():
            self.assertNotEqual(entry.get("symbol"), "*",
                                "a catch-all pattern would swallow every token")


if __name__ == "__main__":
    unittest.main()
