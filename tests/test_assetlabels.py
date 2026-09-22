# -*- coding: utf-8 -*-
"""Asset labels (the "asset type" donut, the row tag picker and the rule engine)."""
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tracker import config, profiles  # noqa: E402
from tracker import assetlabels  # noqa: E402


def row(symbol, name="", price=0.0, chain="eth", token_id="", usd=0.0):
    return {"symbol": symbol, "name": name, "price": price, "chain": chain,
            "token_id": token_id, "usd": usd}


class ClassifyTest(unittest.TestCase):
    def setUp(self):
        # never touch the real profile files, and keep the rules file distinct from
        # the display-names file so one test cannot mask a bug in the other
        self._tmp = tempfile.mkdtemp()
        self._orig = profiles.asset_labels_file
        self._orig_legacy = profiles.legacy_asset_labels_file
        self._orig_labels = profiles.labels_file
        self._orig_active = profiles.active
        profiles.asset_labels_file = lambda: os.path.join(self._tmp, "asset_assetlabels.json")
        # no legacy file in the temp dir, so the migration stays out of the way
        profiles.legacy_asset_labels_file = lambda: os.path.join(self._tmp, "legacy_stablecoins.json")
        profiles.labels_file = lambda: os.path.join(self._tmp, "label_names.json")
        assetlabels.reset_cache()
        assetlabels.reset_names_cache()

    def tearDown(self):
        profiles.asset_labels_file = self._orig
        profiles.legacy_asset_labels_file = self._orig_legacy
        profiles.labels_file = self._orig_labels
        profiles.active = self._orig_active
        assetlabels.reset_cache()
        assetlabels.reset_names_cache()

    def test_stablecoin_wildcards_cover_bridged_forms(self):
        for sym in ("USDT", "USDC", "USDT.e", "USDC.e", "USDBC", "BUSD", "FDUSD",
                    "PYUSD", "USDe", "sUSDe", "crvUSD", "FRAX", "DAI", "DAI.e",
                    "GUSD", "LUSD", "TUSD", "USDP", "MIM", "DOLA"):
            with self.subTest(symbol=sym):
                self.assertEqual(assetlabels.classify(row(sym, price=1.0)), assetlabels.STABLE)

    def test_bitcoin_family(self):
        for sym in ("BTC", "WBTC", "cbBTC", "tBTC", "renBTC", "BTC.b", "LBTC"):
            with self.subTest(symbol=sym):
                self.assertEqual(assetlabels.classify(row(sym, price=63000)), assetlabels.BTC)

    def test_eth_sol_hype_are_detected(self):
        for sym, label in (("ETH", "eth"), ("WETH", "eth"), ("stETH", "eth"), ("wstETH", "eth"),
                           ("cbETH", "eth"), ("rETH", "eth"),
                           ("SOL", "sol"), ("WSOL", "sol"), ("mSOL", "sol"), ("jitoSOL", "sol"),
                           ("HYPE", "hype"), ("WHYPE", "hype"), ("kHYPE", "hype")):
            with self.subTest(symbol=sym):
                self.assertEqual(assetlabels.classify(row(sym, price=1.0)), label)

    def test_staked_positions_match_their_base_symbol(self):
        """Brokers name staked positions "SOL (staked)"; a plain glob never reached
        them, which left the largest positions of all sitting in "other"."""
        self.assertEqual(assetlabels.classify(row("SOL (staked)", price=150)), "sol")
        self.assertEqual(assetlabels.classify(row("HYPE (staked)", price=30)), "hype")
        self.assertEqual(assetlabels.classify(row("ETH (staked)", price=2500)), "eth")
        self.assertEqual(assetlabels.classify(row("SOL/ankr", price=150)), "sol")

    def test_other(self):
        for sym, price in (("JUP", 0.8), ("MAGIC", 1.0), ("DOGE", 0.2), ("PENDLE", 4.0)):
            with self.subTest(symbol=sym):
                self.assertEqual(assetlabels.classify(row(sym, price=price)), assetlabels.OTHER)

    def test_renaming_a_user_label_rewrites_its_rules(self):
        assetlabels.add_entry({"symbol": "PENX", "category": "pendle"})
        self.assertEqual(assetlabels.classify(row("PENX", price=4.0)), "pendle")
        kind, label = assetlabels.rename_label("pendle", "defi")
        self.assertEqual(kind, "renamed")
        self.assertEqual(label, "defi")
        self.assertEqual(assetlabels.classify(row("PENX", price=4.0)), "defi")
        self.assertNotIn("pendle", assetlabels.known_labels())
        self.assertIn("defi", assetlabels.known_labels())

    def test_renaming_a_builtin_label_only_changes_the_display(self):
        """A built-in id is what detection matches on, so it must survive a rename."""
        kind, label = assetlabels.rename_label("eth", "Ethereum")
        self.assertEqual((kind, label), ("display", "eth"))
        self.assertEqual(assetlabels.label_names().get("eth"), "Ethereum")
        # detection is untouched
        self.assertEqual(assetlabels.classify(row("WETH", price=2500)), "eth")
        self.assertIn("eth", assetlabels.known_labels())

    def test_deleting_a_user_label_drops_its_rules(self):
        assetlabels.add_entry({"symbol": "TMPX", "category": "temp"})
        self.assertEqual(assetlabels.classify(row("TMPX", price=9.0)), "temp")
        assetlabels.delete_label("temp")
        self.assertEqual(assetlabels.classify(row("TMPX", price=9.0)), "other")
        self.assertNotIn("temp", assetlabels.known_labels())

    def test_builtin_labels_cannot_be_deleted(self):
        for name in ("stable", "btc", "eth", "sol", "hype", "other"):
            with self.subTest(label=name):
                with self.assertRaises(ValueError):
                    assetlabels.delete_label(name)

    def test_rename_rejects_a_bad_name(self):
        for bad in ("", "   ", "x" * 25, "bad;name"):
            with self.subTest(name=bad):
                with self.assertRaises(ValueError):
                    assetlabels.rename_label("eth", bad)

    def test_a_row_carries_exactly_one_label(self):
        """Every token gets one label; a second rule for the same target replaces
        the first so the user's LAST choice is the one that sticks."""
        r = row("USDC", price=1.0, chain="sol", token_id="MINT1")
        self.assertEqual(assetlabels.classify(r), assetlabels.STABLE)
        assetlabels.add_entry({"category": "other", "action": "exclude",
                               "token_id": "MINT1", "chain": "sol"})
        self.assertEqual(assetlabels.classify(r), assetlabels.OTHER)
        # the user changes their mind: the stale exclude must not keep winning
        assetlabels.add_entry({"category": "stable", "action": "include",
                               "token_id": "MINT1", "chain": "sol"})
        self.assertEqual(assetlabels.classify(r), assetlabels.STABLE)
        self.assertEqual(len(assetlabels.user_entries()), 1)

    def test_a_user_label_overrides_a_builtin_wildcard(self):
        """A human decision has to beat a built-in glob. This used to fail: the
        built-ins were consulted first, so relabelling USDC (which the `*USD*`
        built-in claims) silently did nothing."""
        r = row("USDC", "USD Coin", price=1.0, chain="linea", token_id="0xLINEA")
        self.assertEqual(assetlabels.classify(r), assetlabels.STABLE)
        assetlabels.add_entry({"category": "defi", "action": "include",
                               "token_id": "0xLINEA", "chain": "linea"})
        self.assertEqual(assetlabels.classify(r), "defi")
        # ...without disturbing USDC on any other chain
        self.assertEqual(assetlabels.classify(row("USDC", price=1.0, chain="eth")),
                         assetlabels.STABLE)

    def test_user_defined_labels_are_first_class(self):
        assetlabels.add_entry({"symbol": "PENX", "category": "pendle"})
        self.assertEqual(assetlabels.classify(row("PENX", price=4.0)), "pendle")
        labels = assetlabels.known_labels()
        self.assertIn("pendle", labels)
        # auto-detected labels keep their order, a custom one slots in before "other"
        self.assertEqual(labels[-1], "other")
        self.assertLess(labels.index("stable"), labels.index("btc"))
        self.assertLess(labels.index("pendle"), labels.index("other"))

    def test_price_band_catches_unlisted_pegs_but_only_near_one_dollar(self):
        # A ticker no wildcard covers, whose NAME marks it as a dollar asset, is
        # picked up only while it actually trades near $1 (ZKL matches nothing).
        self.assertEqual(assetlabels.classify(row("ZKL", "Zekul USD", price=1.001)),
                         assetlabels.STABLE)
        self.assertEqual(assetlabels.classify(row("ZKL", "Zekul USD", price=0.42)),
                         assetlabels.OTHER)
        self.assertEqual(assetlabels.classify(row("ZKL", "Zekul USD", price=0.0)),
                         assetlabels.OTHER)
        # A named wildcard is authoritative: USDT is a stablecoin whatever it trades
        # at, because asset class is not the same question as "is the peg holding".
        self.assertEqual(assetlabels.classify(row("USDT", "Tether", price=0.0)),
                         assetlabels.STABLE)
        self.assertEqual(assetlabels.classify(row("XUSD", "Some Dollar", price=0.42)),
                         assetlabels.STABLE)   # matched by the *USD* wildcard
        # a $1 token with no dollar marker is not assumed to be a stablecoin
        self.assertEqual(assetlabels.classify(row("MAGIC", "Magic", price=1.0)),
                         assetlabels.OTHER)

    def test_scam_tokens_named_after_stablecoins_stay_out(self):
        # real rows from a live snapshot: phishing tokens name-drop tether/dai
        for sym, name, price in (
            ("$ U5DT [EVENT-STETHER.NET]", "Visit tetherv2.com", 0.0),
            ("iDAI", "Instadapp DAI", 0.0467),
            ("yvDAI", "Yearn DAI", 1.2677),
            ("xdai.firstchef.net", "claim rewards", 0.0),
        ):
            with self.subTest(symbol=sym):
                self.assertEqual(assetlabels.classify(row(sym, name, price)), assetlabels.OTHER)

    def test_user_include_and_exclude_rules(self):
        # include: an unknown ticker the user knows is a stablecoin
        assetlabels.add_entry({"symbol": "MYUSDX", "category": "stable"})
        self.assertEqual(assetlabels.classify(row("MYUSDX", price=0.5)), assetlabels.STABLE)
        # exclude: pin a wildcard false-positive back out
        assetlabels.add_entry({"symbol": "USDT*", "category": "other", "action": "exclude",
                               "chain": "tron"})
        self.assertEqual(assetlabels.classify(row("USDT", chain="tron", price=1.0)),
                         assetlabels.OTHER)
        # ...without disturbing the same symbol on another chain
        self.assertEqual(assetlabels.classify(row("USDT", chain="eth", price=1.0)),
                         assetlabels.STABLE)

    def test_invalid_rules_rejected(self):
        with self.assertRaises(ValueError):
            assetlabels.add_entry({"symbol": "X"})                       # no label
        with self.assertRaises(ValueError):
            assetlabels.add_entry({"symbol": "X", "category": "a" * 40})  # too long
        with self.assertRaises(ValueError):
            assetlabels.add_entry({"symbol": "X", "category": "bad;label"})
        with self.assertRaises(ValueError):
            assetlabels.add_entry({"category": "stable"})                # nothing to match
        with self.assertRaises(ValueError):
            assetlabels.add_entry({"symbol": "X", "category": "ok", "action": "sideways"})
        # an invented label IS allowed — labels are data, not an enum
        assetlabels.add_entry({"symbol": "OKX1", "category": "my label 1"})
        self.assertIn("my label 1", assetlabels.known_labels())

    def test_label_validation(self):
        for good in ("stable", "btc", "myLabel", "my label", "a-b_c.d", "L2"):
            self.assertTrue(assetlabels.valid_label(good), good)
        for bad in ("", " ", "x" * 25, "bad;x", "bad/x", "<script>"):
            self.assertFalse(assetlabels.valid_label(bad), bad)

    def test_annotate_and_category_totals_are_additive(self):
        rows = [row("USDC", price=1.0, usd=100.0), row("BTC", price=60000, usd=250.0),
                row("ETH", price=2500, usd=50.0), row("PEPE", price=0.001, usd=7.0)]
        ann = assetlabels.annotate(rows)
        self.assertEqual([r["cat"] for r in ann], ["stable", "btc", "eth", "other"])
        totals = assetlabels.category_totals(rows)
        self.assertEqual(totals[assetlabels.STABLE], 100.0)
        self.assertEqual(totals[assetlabels.BTC], 250.0)
        self.assertEqual(totals["eth"], 50.0)
        self.assertEqual(totals[assetlabels.OTHER], 7.0)
        self.assertEqual(sum(totals.values()), 407.0)   # nothing lost or double counted
        self.assertEqual(list(totals), assetlabels.known_labels())  # covers every label
        # annotate must not mutate the caller's rows
        self.assertNotIn("cat", rows[0])

    def test_user_rules_persist_and_hot_reload(self):
        assetlabels.add_entry({"symbol": "PERSISTX", "category": "btc"})
        path = profiles.asset_labels_file()
        self.assertTrue(os.path.exists(path))
        with open(path, encoding="utf-8") as fh:
            on_disk = json.load(fh)
        self.assertEqual(on_disk[0]["symbol"], "PERSISTX")
        assetlabels.reset_cache()
        self.assertEqual(len(assetlabels.user_entries()), 1)

    def test_builtin_list_covers_every_auto_label(self):
        cats = {e["category"] for e in assetlabels.builtin_entries()}
        self.assertEqual(cats, {"stable", "btc", "eth", "sol", "hype"})

    def test_builtin_list_has_no_catch_all_pattern(self):
        """A `*` built-in would classify every token as a stablecoin."""
        for entry in assetlabels.builtin_entries():
            self.assertNotEqual(entry.get("symbol"), "*",
                                "a catch-all pattern would swallow every token")


if __name__ == "__main__":
    unittest.main()
