# -*- coding: utf-8 -*-
"""Unit tests for the DOGE / ADA balance fetchers and their wiring.

Runs with the stdlib only (no pytest required):

    python3 -m unittest discover -s tests -v

All network access is mocked — these tests are deterministic and offline.
Real-world response shapes were captured from live providers:
  - BlockCypher  GET  https://api.blockcypher.com/v1/doge/main/addrs/{addr}/balance
  - Koios        POST https://api.koios.rest/api/v1/address_info
                 POST https://api.koios.rest/api/v1/account_info
"""
import os
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tracker import ada, doge, prices, sources, walletstore  # noqa: E402

# Public example addresses (used only as test fixtures).
DOGE_ADDR = "DH5yaieqoZN36fDVciNyRueRGvGLR3mr7L"          # well-known DOGE address
DOGE_ADDR2 = "DBXu2kgc3xtvCUWFcxFE3r9hEYgmuaaCyD"
ADA_ADDR = "addr1qx2fxv2umyhttkxyxp8x0dlpdt3k6cwng5pxj3jhsydzer3n0d3vllmyqwsx5wktcd8cc3sq835lu7drv2xwl2wywfgse35a3x"
ADA_STAKE = "stake1uyehkck0lajq8gr28t9uxnuvgcqrc6070x3k9r8048z8y5gh6ffgw"

_TMP = None


def setUpModule():
    """Point profiles at a throwaway dir so the suite is hermetic.

    A fresh clone of the public repo has no profiles/ directory until the app
    seeds one at startup; these tests must not depend on that side effect.
    """
    global _TMP
    _TMP = tempfile.TemporaryDirectory()
    os.makedirs(os.path.join(_TMP.name, "default"), exist_ok=True)
    from tracker import profiles
    patcher = mock.patch.multiple(
        profiles,
        PROFILES_DIR=_TMP.name,
        ACTIVE_FILE=os.path.join(_TMP.name, ".active"),
    )
    patcher.start()
    sources.reset_failover()
    unittest.addModuleCleanup(patcher.stop)


def tearDownModule():
    global _TMP
    if _TMP is not None:
        _TMP.cleanup()
        _TMP = None


class DogeFetcherTest(unittest.TestCase):
    """BlockCypher returns `final_balance` in koinu (1 DOGE = 1e8 koinu)."""

    def test_converts_koinu_to_known_balance(self):
        # live capture: final_balance 6221159392701 koinu = 62211.59392701 DOGE
        payload = {"address": DOGE_ADDR, "final_balance": 6221159392701,
                   "total_received": 4385334471466759299, "n_tx": 1483}
        with mock.patch.object(doge, "http_get_json", return_value=payload) as m:
            out = doge.fetch_doge_koinu([DOGE_ADDR])
        self.assertEqual(out[DOGE_ADDR], 6221159392701)
        # url must carry the address
        self.assertIn(DOGE_ADDR, m.call_args[0][0])
        self.assertIn("doge/main", m.call_args[0][0])

    def test_multiple_addresses_and_zero_balance(self):
        payloads = {DOGE_ADDR: {"final_balance": 100000000},
                    DOGE_ADDR2: {"final_balance": 0}}

        def fake(url, **kw):
            for a, body in payloads.items():
                if a in url:
                    return body
            raise AssertionError("unexpected url " + url)

        with mock.patch.object(doge, "http_get_json", side_effect=fake):
            out = doge.fetch_doge_koinu([DOGE_ADDR, DOGE_ADDR2])
        self.assertEqual(out[DOGE_ADDR], 100000000)
        self.assertEqual(out[DOGE_ADDR2], 0)          # 0 is a valid balance, not None

    def test_unresolvable_address_is_none(self):
        with mock.patch.object(doge, "http_get_json", side_effect=RuntimeError("boom")):
            out = doge.fetch_doge_koinu([DOGE_ADDR])
        self.assertIsNone(out[DOGE_ADDR])

    def test_empty_input_returns_empty(self):
        self.assertEqual(doge.fetch_doge_koinu([]), {})
        self.assertEqual(doge.fetch_doge_koinu([None, ""]), {})

    def test_disabled_source_returns_none(self):
        with mock.patch.object(doge.sources, "get_source", return_value={"enabled": False}):
            out = doge.fetch_doge_koinu([DOGE_ADDR])
        self.assertIsNone(out[DOGE_ADDR])

    def test_koinu_divisor_matches_portfolio(self):
        # the dashboard divides by this to show whole DOGE
        self.assertEqual(doge.KOINU, 100_000_000)
        self.assertAlmostEqual(6221159392701 / doge.KOINU, 62211.59392701, places=8)


class AdaFetcherTest(unittest.TestCase):
    """Koios answers payment addresses and stake addresses on two endpoints."""

    def test_payment_address_balance(self):
        # live capture: balance "1000000" lovelace = 1.0 ADA
        resp = [{"address": ADA_ADDR, "balance": "1000000",
                 "stake_address": ADA_STAKE, "script_address": False}]
        with mock.patch.object(ada, "http_post_json", return_value=resp) as m:
            out = ada.fetch_ada_lovelace([ADA_ADDR])
        self.assertEqual(out[ADA_ADDR], 1000000)
        body = m.call_args.kwargs.get("json_body") or m.call_args[1]["json_body"]
        self.assertEqual(body, {"_addresses": [ADA_ADDR]})

    def test_stake_address_uses_account_endpoint(self):
        resp = [{"stake_address": ADA_STAKE, "total_balance": "2400000", "status": "registered"}]
        with mock.patch.object(ada, "http_post_json", return_value=resp) as m:
            out = ada.fetch_ada_lovelace([ADA_STAKE])
        self.assertEqual(out[ADA_STAKE], 2400000)
        url = m.call_args[0][0]
        self.assertIn("account_info", url)
        body = m.call_args[1]["json_body"]
        self.assertEqual(body, {"_stake_addresses": [ADA_STAKE]})

    def test_mixed_payment_and_stake_are_routed(self):
        def fake(url, **kw):
            body = kw.get("json_body", {})
            if "_addresses" in body:
                return [{"address": ADA_ADDR, "balance": "5000000"}]
            return [{"stake_address": ADA_STAKE, "total_balance": "7000000"}]

        with mock.patch.object(ada, "http_post_json", side_effect=fake):
            out = ada.fetch_ada_lovelace([ADA_ADDR, ADA_STAKE])
        self.assertEqual(out[ADA_ADDR], 5000000)
        self.assertEqual(out[ADA_STAKE], 7000000)

    def test_unknown_address_is_none(self):
        # Koios answers [] for an address it does not know
        with mock.patch.object(ada, "http_post_json", return_value=[]):
            out = ada.fetch_ada_lovelace([ADA_ADDR])
        self.assertIsNone(out[ADA_ADDR])

    def test_failure_is_none_and_empty_input(self):
        with mock.patch.object(ada, "http_post_json", side_effect=RuntimeError("boom")):
            out = ada.fetch_ada_lovelace([ADA_ADDR])
        self.assertIsNone(out[ADA_ADDR])
        self.assertEqual(ada.fetch_ada_lovelace([]), {})

    def test_stake_detection(self):
        self.assertTrue(ada._is_stake(ADA_STAKE))
        self.assertTrue(ada._is_stake("stake_test1xyz"))
        self.assertFalse(ada._is_stake(ADA_ADDR))


class TemplateWalletsTest(unittest.TestCase):
    """The public default template must ship valid DOGE/ADA example wallets
    (these are public example addresses — never the operator's own)."""

    @classmethod
    def setUpClass(cls):
        import json
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        with open(os.path.join(root, "templates", "portfolio_wallets.json"),
                  encoding="utf-8") as f:
            cls.tpl = json.load(f)

    def _of_type(self, t):
        return [w for w in self.tpl if w.get("type") == t]

    def test_every_entry_has_name_type_address(self):
        for w in self.tpl:
            for k in ("name", "type", "address"):
                self.assertTrue(w.get(k), f"{w} missing {k}")

    def test_doge_example_present_and_wellformed(self):
        rows = self._of_type("doge")
        self.assertTrue(rows, "no doge wallet in the default template")
        for w in rows:
            self.assertTrue(w["address"].startswith("D"), w["address"])
            self.assertNotIn("{", w["address"])

    def test_ada_example_present_and_wellformed(self):
        rows = self._of_type("ada")
        self.assertTrue(rows, "no ada wallet in the default template")
        for w in rows:
            self.assertTrue(w["address"].startswith("addr1"), w["address"])

    def test_templates_carry_no_secrets(self):
        # a public template must never contain a key-like field
        for w in self.tpl:
            self.assertNotIn("key", w)
            self.assertNotIn("secret", w)


class SourceConfigTest(unittest.TestCase):
    """The new sources ship enabled defaults so a fresh install works."""

    def test_doge_and_ada_defaults_exist(self):
        d = sources._DEFAULTS
        self.assertIn("doge", d)
        self.assertIn("ada", d)
        self.assertTrue(d["doge"]["enabled"])
        self.assertTrue(d["ada"]["enabled"])
        # DOGE: per-address provider carrying {addr}
        prov = d["doge"]["providers"][0]
        self.assertIn("{addr}", prov["url"])
        self.assertIn("blockcypher", prov["name"])
        # ADA: batch provider + stake endpoint
        adap = d["ada"]["providers"][0]
        self.assertIn("koios", adap["name"])
        self.assertIn("address_info", adap["url"])
        self.assertIn("account_info", adap["stake_url"])

    def test_wallet_types_accept_new_coins(self):
        for t in ("doge", "ada"):
            self.assertIn(t, walletstore.VALID_TYPES)


class PriceMappingTest(unittest.TestCase):
    """Both coins must be priceable through every exchange provider."""

    def test_ids_and_symbols(self):
        self.assertIn("dogecoin", prices.NATIVE_IDS)
        self.assertIn("cardano", prices.NATIVE_IDS)
        self.assertEqual(prices.EXCHANGE_SYMBOLS["dogecoin"], "DOGE")
        self.assertEqual(prices.EXCHANGE_SYMBOLS["cardano"], "ADA")


class PortfolioWiringTest(unittest.TestCase):
    """_chain_rows converts smallest units and flags unresolvable wallets."""

    def _rows(self, balances, price=1.0, divisor=1e8, wtype="doge", sym="DOGE"):
        from tracker import portfolio
        wallets = [{"name": "w1", "type": wtype, "address": "A1"},
                   {"name": "w2", "type": wtype, "address": "A2"}]
        with mock.patch.object(portfolio, "_wallet_subset", return_value=wallets):
            return portfolio._chain_rows(wtype, sym, "Test", divisor, balances, price,
                                         wtype, "")

    def test_doge_row_math(self):
        rows = self._rows({"A1": 6221159392701, "A2": 0}, price=0.08726)
        r1 = next(r for r in rows if r["wallet"] == "w1")
        self.assertAlmostEqual(r1["amount"], 62211.59392701, places=8)
        self.assertAlmostEqual(r1["usd"], 62211.59392701 * 0.08726, places=4)
        self.assertEqual(r1["chain"], "doge")
        self.assertEqual(r1["symbol"], "DOGE")

    def test_unresolved_wallet_is_error_row(self):
        rows = self._rows({"A1": None, "A2": None})
        self.assertTrue(all(r["error"] for r in rows))
        self.assertTrue(all(r["usd"] == 0.0 for r in rows))

    def test_ada_row_uses_million_divisor(self):
        rows = self._rows({"A1": 2400000, "A2": 1000000}, price=0.2187,
                          divisor=1e6, wtype="ada", sym="ADA")
        r1 = next(r for r in rows if r["wallet"] == "w1")
        self.assertAlmostEqual(r1["amount"], 2.4, places=9)
        self.assertAlmostEqual(r1["usd"], 2.4 * 0.2187, places=6)
        self.assertEqual(r1["chain"], "ada")


if __name__ == "__main__":
    unittest.main(verbosity=2)
