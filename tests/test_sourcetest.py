# -*- coding: utf-8 -*-
"""Per-source "Test" buttons.

A test exists to name the failing thing before a refresh turns the dashboard into
error rows, so the contract is: any target answers with the same
`{ok, ms, message, detail}` shape, an unknown target is a *result* rather than an
exception, and the provider's own wording survives into `message`.
No network here: the fetchers are replaced.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tracker import cex, sourcetest  # noqa: E402


class SourceTestContractTest(unittest.TestCase):
    def test_an_unknown_target_is_a_result_not_an_exception(self):
        r = sourcetest.run_test("does-not-exist")
        self.assertFalse(r["ok"])
        self.assertIn("does-not-exist", r["message"])
        self.assertIn("ms", r)

    def test_a_missing_account_is_named(self):
        r = sourcetest.run_test("cex", "no_such_account")
        self.assertFalse(r["ok"])
        self.assertIn("no_such_account", r["message"])

    def test_every_result_has_the_same_shape(self):
        for target in ("nope", "cex"):
            r = sourcetest.run_test(target)
            self.assertEqual(sorted(r), ["detail", "message", "ms", "ok"])


class CexTestProbe(unittest.TestCase):
    def setUp(self):
        self._orig_fetch = cex.fetch_cex_accounts

    def tearDown(self):
        cex.fetch_cex_accounts = self._orig_fetch

    def test_a_healthy_account_reports_its_total(self):
        cex.fetch_cex_accounts = lambda accounts, native: [{
            "account": accounts[0], "error": None, "notes": [],
            "rows": [{"symbol": "USDT", "usd": 100.0}, {"symbol": "BTC", "usd": 50.0}],
            "total_usd": 150.0}]
        r = sourcetest.test_cex({"name": "x", "exchange": "binance"})
        self.assertTrue(r["ok"])
        self.assertEqual(r["detail"]["total_usd"], 150.0)
        self.assertEqual(r["detail"]["assets"], 2)
        self.assertEqual(r["detail"]["top"][0]["symbol"], "USDT")

    def test_a_failing_account_reports_the_exchange_message(self):
        cex.fetch_cex_accounts = lambda accounts, native: [{
            "account": accounts[0], "error": "Invalid API-key (HTTP 401)",
            "notes": [], "rows": [], "total_usd": 0.0}]
        r = sourcetest.test_cex({"name": "x", "exchange": "okx"})
        self.assertFalse(r["ok"])
        self.assertIn("Invalid API-key", r["message"])

    def test_tolerated_parts_travel_along_as_notes(self):
        cex.fetch_cex_accounts = lambda accounts, native: [{
            "account": accounts[0], "error": None,
            "notes": [{"part": "futures", "message": "Invalid API-key, IP, or permissions"}],
            "rows": [{"symbol": "USDT", "usd": 10.0}], "total_usd": 10.0}]
        r = sourcetest.test_cex({"name": "x", "exchange": "binance"})
        self.assertTrue(r["ok"])
        self.assertEqual(r["detail"]["notes"][0]["part"], "futures")

    def test_an_unknown_exchange_is_rejected(self):
        r = sourcetest.test_cex({"name": "x", "exchange": "ftx"})
        self.assertFalse(r["ok"])
        self.assertIn("ftx", r["message"])


class ProviderProbeTest(unittest.TestCase):
    def test_the_probe_path_is_derived_from_the_endpoint_origin(self):
        """Configured URLs are full endpoints (…/balance, …/api/v3/simple/price), so a
        probe must replace the path, not append to it."""
        self.assertEqual(sourcetest._origin("https://blockchain.info/balance"),
                         "https://blockchain.info")
        self.assertEqual(sourcetest._origin("https://api.coingecko.com/api/v3/simple/price"),
                         "https://api.coingecko.com")
        self.assertEqual(sourcetest._origin(""), "://")

    def test_an_unknown_provider_is_reported(self):
        r = sourcetest.test_provider("not-a-provider", "https://example.com/x")
        self.assertFalse(r["ok"])
        self.assertIn("not-a-provider", r["message"])


class ErrorMessageTest(unittest.TestCase):
    """The provider's own words, because "401" tells nobody which field to fix."""

    class _Resp(object):
        status_code = 401

        def __init__(self, payload, text=""):
            self._payload = payload
            self.text = text

        def json(self):
            if self._payload is None:
                raise ValueError("not json")
            return self._payload

    def test_a_json_error_field_is_used(self):
        import requests

        class Err(requests.exceptions.HTTPError):
            pass

        e = Err("401")
        e.response = self._Resp({"code": -2015, "msg": "Invalid API-key, IP, or permissions"})
        self.assertIn("Invalid API-key", sourcetest._explain(e))
        self.assertIn("401", sourcetest._explain(e))

    def test_a_non_json_body_falls_back_to_its_text(self):
        import requests

        e = requests.exceptions.HTTPError("500")
        e.response = self._Resp(None, text="upstream exploded")
        self.assertIn("upstream exploded", sourcetest._explain(e))

    def test_a_plain_exception_keeps_its_message(self):
        self.assertEqual(sourcetest._explain(RuntimeError("boom")), "boom")


if __name__ == "__main__":
    unittest.main()
