# -*- coding: utf-8 -*-
"""The asset plan: tiers, the weekly buy, the ammo pool, goals and the rules.

The numbers asserted here are the workbook's own worked examples — BTC 80,422 sits
in T2 and ETH 2,353 in T3, so the week costs $160 + $280 + $100 = $540; a 4-year
double needs 18.92% a year (4.43% a quarter). Where the workbook and this code could
drift apart, the workbook wins and the test says so.

No network and no profile: storage, the wallet list and the config loader are all
replaced with fixtures.
"""
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tracker import plan  # noqa: E402

DATE = "2026-10-16"


def token(symbol, usd, amount=None, price=None, wallet="w1", cat="other", name=""):
    amount = amount if amount is not None else (usd / price if price else 1.0)
    return {"symbol": symbol, "name": name or symbol, "chain": "eth", "wallet": wallet,
            "amount": amount, "price": price if price is not None else (usd / amount if amount else 0),
            "usd": usd, "logo": "", "token_id": symbol.lower(), "cat": cat}


class FakeStorage:
    """A storage module whose three reads return whatever the test says."""

    def __init__(self, rows, total=None, history=None):
        self.rows = rows
        self.snapshot = {"date": DATE, "created_at": DATE + "T12:00:00",
                         "total_usd": total if total is not None else sum(r["usd"] for r in rows)}
        self.history = history or {"dates": [DATE], "totals": [self.snapshot["total_usd"]],
                                   "wallets": {}, "chains": {}}

    def get_tokens(self, date=None):
        return self.rows

    def get_snapshot(self, date=None):
        return self.snapshot

    def get_latest_snapshot(self):
        return self.snapshot

    def get_history(self, days=None):
        return self.history


class PlanCase(unittest.TestCase):
    """Base: swap storage/config/log for fixtures, restore afterwards."""

    def setUp(self):
        self._storage = plan.storage
        self._load = plan.load
        self._log_read = plan.log_read
        self._log_append = plan.log_append
        self._log_remove = plan.log_remove
        self._walletstore = plan.walletstore
        self.log = []
        plan.log_read = lambda limit=None: list(reversed(self.log))[:limit] if limit else list(reversed(self.log))
        plan.log_append = lambda entry: self.log.append(dict(entry, qty=0)) or self.log[-1]
        plan.log_remove = lambda index: True

    def tearDown(self):
        plan.storage = self._storage
        plan.load = self._load
        plan.log_read = self._log_read
        plan.log_append = self._log_append
        plan.log_remove = self._log_remove
        plan.walletstore = self._walletstore

    def install(self, rows, config=None, total=None, history=None, wallets=None):
        plan.storage = FakeStorage(rows, total=total, history=history)
        cfg = plan.defaults()
        if config:
            cfg = plan.normalize(dict(cfg, **config))
        plan.load = lambda: cfg
        plan.walletstore = type("W", (), {"all_wallets": staticmethod(lambda: wallets or [])})
        return plan.analyze(DATE)


class TiersAndWeeklyTest(PlanCase):
    def test_the_workbook_example_tiers_and_weekly_total(self):
        rows = [token("BTC", 35305.0, amount=0.439, price=80422.0, cat="btc"),
                token("ETH", 22118.0, amount=9.4, price=2353.0, cat="eth"),
                token("HYPE", 15419.0, amount=197.0, price=78.27, cat="hype")]
        d = self.install(rows, config={"manual_assets": []})
        self.assertEqual(d["tiers"]["BTC"]["tier"], "T2")
        self.assertEqual(d["tiers"]["ETH"]["tier"], "T3")
        # HYPE+SOL has no tier of its own: it follows BTC
        self.assertEqual(d["tiers"]["HYPE+SOL"]["tier"], "T2")
        weekly = {w["bucket"]: w["amount"] for w in d["weekly"]["rows"]}
        self.assertEqual(weekly, {"BTC": 160.0, "ETH": 280.0, "HYPE+SOL": 100.0})
        self.assertEqual(d["weekly"]["total"], 540.0)

    def test_tier_boundaries_are_inclusive_at_the_floor(self):
        b = {"t1_above": 100000.0, "t2_floor": 80000.0, "t3_floor": 60000.0}
        self.assertEqual(plan.tier_of(100000.1, b), "T1")
        self.assertEqual(plan.tier_of(100000.0, b), "T2")   # the ceiling is not exceeded
        self.assertEqual(plan.tier_of(80000.0, b), "T2")
        self.assertEqual(plan.tier_of(79999.9, b), "T3")
        self.assertEqual(plan.tier_of(60000.0, b), "T3")
        self.assertEqual(plan.tier_of(59999.9, b), "T4")
        self.assertIsNone(plan.tier_of(0, b))
        self.assertIsNone(plan.tier_of(None, b))

    def test_every_coin_is_judged_on_its_own_price(self):
        eth_b = {"t1_above": 3000.0, "t2_floor": 2500.0, "t3_floor": 1800.0}
        self.assertEqual(plan.tier_of(2500.0, eth_b), "T2")
        self.assertEqual(plan.tier_of(2499.0, eth_b), "T3")
        self.assertEqual(plan.tier_of(1799.0, eth_b), "T4")

    def test_spam_rows_with_no_value_cannot_poison_a_bucket_price(self):
        # airdropped junk reuses the ETH symbol with an absurd amount; the bucket price
        # must come from the real, priced holding instead of a weighted average
        rows = [token("ETH", 8840.0, amount=3.756, price=2353.33, cat="eth"),
                token("ETH", 0.0, amount=3.849e58, price=0.0, cat="other")]
        d = self.install(rows, config={"manual_assets": []})
        self.assertEqual(d["tiers"]["ETH"]["price"], 2353.33)
        self.assertEqual(d["tiers"]["ETH"]["tier"], "T3")
        weekly = {w["bucket"]: w["amount"] for w in d["weekly"]["rows"]}
        self.assertEqual(weekly["ETH"], 280.0)

    def test_a_missing_price_means_no_buy_for_that_coin(self):
        rows = [token("BTC", 35305.0, amount=0.439, price=80422.0, cat="btc")]
        d = self.install(rows, config={"manual_assets": []})
        eth = [w for w in d["weekly"]["rows"] if w["bucket"] == "ETH"][0]
        self.assertIsNone(eth["tier"])
        self.assertEqual(eth["amount"], 0.0)

    def test_the_t1_tier_stops_buying(self):
        rows = [token("BTC", 50000.0, amount=0.5, price=100001.0, cat="btc"),
                token("ETH", 30000.0, amount=10.0, price=3001.0, cat="eth")]
        d = self.install(rows, config={"manual_assets": []})
        self.assertEqual(d["tiers"]["BTC"]["tier"], "T1")
        self.assertEqual(d["weekly"]["total"], 0.0)
        keys = [a["key"] for a in d["advice"]]
        self.assertIn("advStopBuying", keys)
        self.assertNotIn("advWeekly", keys)


class PriceTileDT4Test(PlanCase):
    def test_t4_multiplies_the_weekly_amount_and_cancels_the_cap(self):
        rows = [token("BTC", 30000.0, amount=0.5, price=60000.0 * 0.9, cat="btc")]
        d = self.install(rows, config={"manual_assets": []})
        self.assertEqual(d["tiers"]["BTC"]["tier"], "T4")
        # the 1,500 tier budget applies to each coin that is in T4: BTC 40% + HYPE+SOL
        # 25% (no ETH price in this fixture, so no ETH leg)
        self.assertEqual(d["weekly"]["total"], 975.0)
        self.assertEqual(d["weekly"]["rows"][0]["weekly_base"], 1500.0)
        keys = [a["key"] for a in d["advice"]]
        self.assertIn("advT4Rush", keys)
        self.assertEqual([a for a in d["advice"] if a["key"] == "advT4Rush"][0]["params"]["weeks"], [6, 10])


class AmmoTest(PlanCase):
    def base_rows(self):
        return [token("BTC", 35305.0, amount=0.439, price=80422.0, cat="btc"),
                token("USDT", 10000.0, amount=10000.0, price=1.0, cat="stable"),
                token("HLP", 12000.0, amount=12000.0, price=1.0, cat="stable")]

    def test_formulas_from_the_workbook(self):
        d = self.install(self.base_rows(), config={"manual_assets": []})
        by = {a["id"]: a for a in d["ammo"]["rows"]}
        # spot stablecoins = all stablecoin-labelled rows minus the HLP vault, then
        # the emergency fund is held back
        # spot stablecoins 10,000 minus the default 2,500 emergency fund
        self.assertEqual(by["stables"]["planned"], 7500.0)
        self.assertEqual(by["hlp"]["planned"], 6000.0)          # half of 12,000
        self.assertEqual(by["etf1"]["planned"], 10000.0)        # manual (example default)
        self.assertEqual(d["ammo"]["planned"], 33500.0)   # 7,500 + 6,000 + 10,000 + 10,000

    def test_the_emergency_fund_is_held_back(self):
        d = self.install(self.base_rows(),
                         config={"manual_assets": [], "emergency_fund": 2500.0})
        by = {a["id"]: a for a in d["ammo"]["rows"]}
        self.assertEqual(by["stables"]["planned"], 7500.0)

    def test_the_log_reduces_what_is_left(self):
        self.log = [{"date": DATE, "asset": "BTC", "side": "buy", "amount": 160.0,
                     "source": "stables", "qty": 0.0019},
                    {"date": DATE, "asset": "ETH", "side": "buy", "amount": 280.0,
                     "source": "stables", "qty": 0.11},
                    {"date": DATE, "asset": "EQUITY", "side": "sell", "amount": 5000.0,
                     "source": "", "qty": 0}]
        d = self.install(self.base_rows(), config={"manual_assets": []})
        by = {a["id"]: a for a in d["ammo"]["rows"]}
        self.assertEqual(by["stables"]["used"], 440.0)
        self.assertEqual(by["stables"]["remaining"], 7060.0)
        # a sell carries no source, so it must not consume the pool
        self.assertEqual(d["ammo"]["used"], 440.0)

    def test_the_next_source_follows_the_tier_permission_list(self):
        d = self.install(self.base_rows(), config={"manual_assets": []})
        self.assertEqual(d["tiers"]["BTC"]["tier"], "T2")
        self.assertEqual(d["ammo"]["order"], ["stables"])       # T2 may only use cash
        self.assertEqual(d["ammo"]["next"]["id"], "stables")
        self.assertFalse([a for a in d["ammo"]["rows"] if a["id"] == "hlp"][0]["allowed"])

    def test_t3_unlocks_the_vault_and_the_first_equity(self):
        rows = [token("BTC", 35000.0, amount=0.5, price=70000.0, cat="btc"),
                token("USDT", 10000.0, amount=10000.0, price=1.0, cat="stable"),
                token("HLP", 12000.0, amount=12000.0, price=1.0, cat="stable")]
        d = self.install(rows, config={"manual_assets": []})
        self.assertEqual(d["tiers"]["BTC"]["tier"], "T3")
        self.assertEqual(d["ammo"]["order"], ["stables", "hlp", "etf1"])
        self.assertEqual(d["ammo"]["next"]["id"], "stables")

    def test_an_empty_pool_is_called_out(self):
        rows = [token("BTC", 35305.0, amount=0.439, price=80422.0, cat="btc")]
        d = self.install(rows, config={"manual_assets": []})
        self.assertIn("advNoAmmo", [a["key"] for a in d["advice"]])


class GoalTest(PlanCase):
    def rows(self):
        return [token("BTC", 100000.0, amount=1.0, price=100000.0, cat="btc")]

    def test_a_four_year_double_needs_18_92_percent_a_year(self):
        rows = [token("BTC", 50000.0, amount=1.0, price=50000.0, cat="btc")]
        d = self.install(rows, config={"manual_assets": [],
                                       "start": {"date": "2026-10-16", "total": 100000.0}})
        g = [g for g in d["goals"] if g["label"] == "4年翻倍"][0]
        self.assertEqual(g["required_cagr"], 0.1892)          # 18.92% a year
        self.assertEqual(g["required_quarterly"], 0.0443)      # 4.43% a quarter
        self.assertEqual(g["target"], 200000.0)
        self.assertEqual(g["deadline"], "2030-10-16")

    def test_an_eight_year_quadruple_needs_the_same_rate(self):
        d = self.install(self.rows(), config={"manual_assets": [],
                                              "start": {"date": "2026-10-16", "total": 100000.0}})
        g = [g for g in d["goals"] if g["label"] == "8年4倍"][0]
        self.assertEqual(g["required_cagr"], 0.1892)
        self.assertEqual(g["target"], 400000.0)

    def test_deviation_decides_the_status(self):
        rows = [token("BTC", 79000.0, amount=1.0, price=79000.0, cat="btc")]
        d = self.install(rows, config={"manual_assets": [],
                                       "start": {"date": "2026-07-16", "total": 100000.0}})
        g = d["goals"][0]
        # one quarter of the path has elapsed, so the target line sits above the start
        self.assertGreater(g["path"], 100000.0)
        self.assertLess(g["deviation"], 0)        # …and the portfolio is under it
        self.assertIn(g["status"], ("behind", "on_track"))

    def test_the_start_falls_back_to_the_oldest_snapshot(self):
        history = {"dates": ["2026-08-01", DATE], "totals": [120000.0, 100000.0],
                   "wallets": {}, "chains": {}}
        d = self.install(self.rows(), config={"manual_assets": []}, history=history)
        self.assertEqual(d["start"]["source"], "history")
        self.assertEqual(d["start"]["total"], 120000.0)
        self.assertEqual(d["start"]["date"], "2026-08-01")


class QuarterTest(PlanCase):
    def rows(self):
        return [token("BTC", 35305.0, amount=0.439, price=80422.0, cat="btc")]

    def test_the_accumulation_phase_caps_a_quarter_at_7000(self):
        d = self.install(self.rows(), config={"manual_assets": [],
                                              "start": {"date": "2026-09-01", "total": 170000.0}})
        self.assertEqual(d["quarter"]["label"], "2026Q4")
        self.assertEqual(d["quarter"]["cap"], 7000.0)
        self.assertEqual(d["quarter"]["stage"], "accumulate")

    def test_2029_is_a_take_profit_window_with_no_new_cap(self):
        storage = FakeStorage(self.rows())
        storage.snapshot = {"date": "2029-05-01", "created_at": "2029-05-01T12:00:00",
                            "total_usd": 100000.0}
        plan.storage = storage
        plan.load = lambda: plan.normalize({"manual_assets": [],
                                           "start": {"date": "2026-09-01", "total": 170000.0}})
        plan.walletstore = type("W", (), {"all_wallets": staticmethod(lambda: [])})
        d = plan.analyze("2029-05-01")
        self.assertEqual(d["quarter"]["stage"], "take_profit")
        self.assertEqual(d["quarter"]["cap"], 0.0)

    def test_spending_this_quarter_comes_from_the_log(self):
        self.log = [{"date": DATE, "asset": "BTC", "side": "buy", "amount": 500.0,
                     "source": "stables"},
                    {"date": "2026-09-30", "asset": "BTC", "side": "buy", "amount": 900.0,
                     "source": "stables"}]
        d = self.install(self.rows(), config={"manual_assets": []})
        self.assertEqual(d["quarter"]["spent"], 500.0)          # only this quarter counts
        self.assertEqual(d["quarter"]["remaining"], 6500.0)


class RuleTest(PlanCase):
    def analyze_btc(self, price, hype=0.0, **cfg):
        rows = [token("BTC", 30000.0, amount=30000.0 / price, price=price, cat="btc")]
        if hype:
            rows.append(token("HYPE", hype, amount=hype / 78.27, price=78.27, cat="hype"))
        conf = {"manual_assets": []}
        conf.update(cfg)
        return self.install(rows, config=conf)

    def keys(self, d):
        return [r["key"] for r in d["rules"]]

    def test_p1_fires_above_the_accumulation_ceiling(self):
        self.assertIn("ruleP1", self.keys(self.analyze_btc(110000.0)))

    def test_p2_fires_in_the_120k_band(self):
        d = self.analyze_btc(130000.0, hype=20000.0)
        self.assertIn("ruleP2", self.keys(d))
        r = [r for r in d["rules"] if r["key"] == "ruleP2"][0]
        self.assertEqual(r["severity"], "act")
        self.assertEqual(r["params"]["step_pct"], 0.10)

    def test_p3_fires_from_150k(self):
        self.assertIn("ruleP3", self.keys(self.analyze_btc(160000.0, hype=20000.0)))

    def test_p2_stays_quiet_with_nothing_to_sell(self):
        # "sell 20% of HYPE+SOL" is noise when the position is empty
        self.assertNotIn("ruleP2", self.keys(self.analyze_btc(130000.0)))

    def test_r4_flags_thin_stablecoins_in_t1(self):
        d = self.analyze_btc(110000.0, emergency_fund=0.0)
        self.assertIn("ruleR4", self.keys(d))

    def test_r5_flags_crypto_left_on_an_exchange(self):
        rows = [token("BTC", 5000.0, amount=0.06, price=80422.0, cat="btc", wallet="binance_read")]
        d = self.install(rows, config={"manual_assets": []},
                         wallets=[{"name": "binance_read", "type": "cex"}])
        self.assertIn("ruleR5", self.keys(d))
        self.assertEqual([r for r in d["rules"] if r["key"] == "ruleR5"][0]["params"]["usd"], 5000.0)

    def test_r5_ignores_a_cold_wallet(self):
        rows = [token("BTC", 5000.0, amount=0.06, price=80422.0, cat="btc", wallet="btc-cold")]
        d = self.install(rows, config={"manual_assets": []},
                         wallets=[{"name": "btc-cold", "type": "btc", "storage": "cold"}])
        self.assertNotIn("ruleR5", self.keys(d))

    def test_p6_trims_a_single_coin_over_20_percent_of_core(self):
        rows = [token("BTC", 1000.0, amount=0.0124, price=80422.0, cat="btc"),
                token("HYPE", 3000.0, amount=38.0, price=78.27, cat="hype")]
        d = self.install(rows, config={"manual_assets": []})
        self.assertIn("ruleP6", self.keys(d))

    def test_d3_fires_below_the_absolute_floor(self):
        d = self.analyze_btc(55000.0)
        self.assertIn("ruleD3", self.keys(d))
        self.assertIn("advT4Rush", [a["key"] for a in d["advice"]])

    def test_d4_fires_when_ammo_is_gone_and_the_drawdown_is_deep(self):
        history = {"dates": ["2026-08-01", DATE], "totals": [300000.0, 100000.0],
                   "wallets": {}, "chains": {}}
        rows = [token("BTC", 100000.0, amount=1.0, price=50000.0, cat="btc")]
        d = self.install(rows, config={"manual_assets": [], "ammo": []}, history=history)
        self.assertIn("ruleD4", self.keys(d))

    def test_d1_fires_on_a_shallow_drawdown(self):
        history = {"dates": ["2026-08-01", DATE], "totals": [125000.0, 100000.0],
                   "wallets": {}, "chains": {}}
        rows = [token("BTC", 100000.0, amount=1.0, price=100000.0, cat="btc")]
        d = self.install(rows, config={"manual_assets": []}, history=history)
        self.assertIn("ruleD1", self.keys(d))


class ConfigTest(unittest.TestCase):
    def test_a_partial_update_keeps_the_rest_of_the_defaults(self):
        cfg = plan.normalize({"emergency_fund": 5000})
        self.assertEqual(cfg["emergency_fund"], 5000.0)
        self.assertEqual(cfg["weekly"]["T2"], 400.0)
        self.assertEqual(cfg["allocation"]["BTC"], 0.40)

    def test_allocation_must_add_up(self):
        with self.assertRaises(ValueError):
            plan.normalize({"allocation": {"BTC": 0.5, "ETH": 0.35, "HYPE+SOL": 0.25}})

    def test_tier_floors_must_rise(self):
        with self.assertRaises(ValueError):
            plan.normalize({"tiers": {"BTC": {"t1_above": 10, "t2_floor": 80000,
                                              "t3_floor": 60000}}})

    def test_negative_money_is_rejected(self):
        with self.assertRaises(ValueError):
            plan.normalize({"emergency_fund": -1})

    def test_an_unknown_ammo_formula_is_rejected(self):
        with self.assertRaises(ValueError):
            plan.normalize({"ammo": [{"id": "x", "label": "x", "formula": "magic"}]})

    def test_a_broken_start_date_is_rejected(self):
        with self.assertRaises(ValueError):
            plan.normalize({"start": {"date": "16/10/2026", "total": 1}})

    def test_normalize_is_idempotent(self):
        once = plan.normalize({})
        twice = plan.normalize(once)
        self.assertEqual(once, twice)


class LogTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self._file = plan.log_file
        plan.log_file = lambda: os.path.join(self.tmp, "plan_log.jsonl")

    def tearDown(self):
        plan.log_file = self._file

    def test_quantity_is_derived_from_price_and_amount(self):
        row = plan.log_append({"date": DATE, "asset": "BTC", "price": 80000, "amount": 160})
        self.assertAlmostEqual(row["qty"], 0.002, places=10)
        self.assertEqual(plan.log_read()[0]["amount"], 160.0)

    def test_a_zero_amount_is_rejected(self):
        with self.assertRaises(ValueError):
            plan.log_append({"asset": "BTC", "amount": 0})

    def test_a_bad_date_is_rejected(self):
        with self.assertRaises(ValueError):
            plan.log_append({"asset": "BTC", "amount": 10, "date": "today"})

    def test_an_asset_is_required(self):
        with self.assertRaises(ValueError):
            plan.log_append({"amount": 10})

    def test_newest_first_and_removable(self):
        plan.log_append({"date": "2026-10-01", "asset": "BTC", "amount": 100})
        plan.log_append({"date": "2026-10-08", "asset": "ETH", "amount": 200})
        self.assertEqual([r["asset"] for r in plan.log_read()], ["ETH", "BTC"])
        self.assertTrue(plan.log_remove(0))
        self.assertEqual([r["asset"] for r in plan.log_read()], ["BTC"])
        self.assertFalse(plan.log_remove(5))

    def test_a_sell_keeps_its_direction(self):
        row = plan.log_append({"asset": "EQUITY", "amount": 5000, "side": "sell"})
        self.assertEqual(row["side"], "sell")


class NoSnapshotTest(PlanCase):
    def test_analyze_says_so_instead_of_guessing(self):
        plan.storage = type("S", (), {"get_latest_snapshot": staticmethod(lambda: None),
                                      "get_snapshot": staticmethod(lambda d=None: None)})()
        plan.load = lambda: plan.defaults()
        d = plan.analyze()
        self.assertFalse(d["ok"])
        self.assertEqual(d["error"], "no-snapshot")


if __name__ == "__main__":
    unittest.main()
