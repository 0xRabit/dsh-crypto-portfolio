# -*- coding: utf-8 -*-
"""Binance reads every sub-account, and a rejected request explains itself.

Two real incidents are pinned here:

1. A blanket `$0` for a funded account. The refresh had failed with
   "HTTPError: 400 Client Error: Bad Request" — Binance's actual answer was
   `-1021 Timestamp for this request is outside of the recvWindow`, because a proxy
   held the signed request for longer than the 5 s window. The body is now read, one
   retry with a fresh timestamp happens, and the window is 60 s.
2. Under-reporting. `/api/v3/account` shows the spot wallet only, so money in Earn,
   Funding, margin or futures was invisible. Earn also writes an `LDxxx` receipt into
   spot for the same position, and that receipt has no ticker (it prices at 0), so
   the underlying position must be counted instead of the receipt — once.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tracker import cex  # noqa: E402

ACC = {"key": "test-key", "secret": "test-secret"}


class _FakeBinance(object):
    """Replaces _signed_request: routes by path and records what was asked for."""

    def __init__(self):
        self.calls = []
        self.replies = {}
        self.raise_first = {}

    def __call__(self, url, headers, method):
        path = url.split("?")[0].split(".com", 1)[1]
        self.calls.append((method, path))
        if path in self.raise_first and self.raise_first[path]:
            self.raise_first[path] -= 1
            raise cex._BinanceRetry("timestamp rejected (code -1021)")
        reply = self.replies.get(path)
        if reply is None:
            raise RuntimeError("no reply configured for %s" % path)
        if isinstance(reply, Exception):
            raise reply
        return reply


class BinanceSubAccountsTest(unittest.TestCase):
    def setUp(self):
        self.fake = _FakeBinance()
        self._orig = cex._signed_request
        cex._signed_request = self.fake
        # every SubAccount call is optional except spot: default them to empty
        self.fake.replies = {
            "/api/v3/account": {"balances": []},
            "/sapi/v1/simple-earn/flexible/position": {"rows": []},
            "/sapi/v1/simple-earn/locked/position": {"rows": []},
            "/sapi/v1/asset/get-funding-asset": [],
            "/sapi/v1/margin/account": {"userAssets": []},
            "/fapi/v2/balance": [],
        }

    def tearDown(self):
        cex._signed_request = self._orig

    def set(self, path, reply):
        self.fake.replies[path] = reply

    def test_spot_free_and_locked_are_both_counted(self):
        self.set("/api/v3/account", {"balances": [
            {"asset": "USDT", "free": "810.65", "locked": "2826.65"},
            {"asset": "BTC", "free": "0.016", "locked": "0"}]})
        balances, _prices, notes = cex._binance_balances(ACC)
        self.assertAlmostEqual(balances["USDT"], 3637.30, places=2)
        self.assertAlmostEqual(balances["BTC"], 0.016)
        self.assertEqual(notes, [])

    def test_earn_positions_are_counted_at_the_underlying_coin(self):
        """The LDxxx receipt in spot has no ticker; the underlying position does."""
        self.set("/api/v3/account", {"balances": [
            {"asset": "LDBNB", "free": "0.5", "locked": "0"}]})
        self.set("/sapi/v1/simple-earn/flexible/position", {"rows": [
            {"asset": "BNB", "totalAmount": "0.5"}]})
        balances, _prices, _notes = cex._binance_balances(ACC)
        self.assertAlmostEqual(balances["BNB"], 0.5)
        self.assertNotIn("LDBNB", balances)      # the receipt is the same position

    def test_an_earn_position_is_not_double_counted(self):
        self.set("/api/v3/account", {"balances": [
            {"asset": "LDUSDT", "free": "100", "locked": "0"}]})
        self.set("/sapi/v1/simple-earn/flexible/position", {"rows": [
            {"asset": "USDT", "totalAmount": "100"}]})
        balances, _prices, _notes = cex._binance_balances(ACC)
        self.assertAlmostEqual(balances["USDT"], 100.0)

    def test_locked_earn_positions_are_included_too(self):
        self.set("/sapi/v1/simple-earn/locked/position", {"rows": [
            {"asset": "ETH", "amount": "1.5", "rewards": "0.25"}]})
        balances, _prices, _notes = cex._binance_balances(ACC)
        self.assertAlmostEqual(balances["ETH"], 1.75)

    def test_a_receipt_without_a_position_is_kept(self):
        """LDxxx for something the Earn endpoint did not report must not be dropped."""
        self.set("/api/v3/account", {"balances": [
            {"asset": "LDSTRK", "free": "3", "locked": "0"}]})
        balances, _prices, _notes = cex._binance_balances(ACC)
        self.assertAlmostEqual(balances["LDSTRK"], 3.0)

    def test_funding_account_is_added(self):
        self.set("/api/v3/account", {"balances": [
            {"asset": "USDT", "free": "10", "locked": "0"}]})
        self.set("/sapi/v1/asset/get-funding-asset", [
            {"asset": "USDT", "free": "5", "freeze": "1", "locked": "2", "withdrawing": "0"}])
        balances, _prices, _notes = cex._binance_balances(ACC)
        self.assertAlmostEqual(balances["USDT"], 18.0)

    def test_margin_net_asset_is_added(self):
        self.set("/sapi/v1/margin/account", {"userAssets": [
            {"asset": "USDT", "netAsset": "250"},
            {"asset": "ETH", "netAsset": "0"}]})       # zero rows are ignored
        balances, _prices, _notes = cex._binance_balances(ACC)
        self.assertAlmostEqual(balances["USDT"], 250.0)
        self.assertNotIn("ETH", balances)

    def test_futures_balance_is_added(self):
        self.set("/fapi/v2/balance", [
            {"asset": "USDT", "balance": "1000", "availableBalance": "1000"}])
        balances, _prices, notes = cex._binance_balances(ACC)
        self.assertAlmostEqual(balances["USDT"], 1000.0)
        self.assertEqual(notes, [])

    def test_a_key_without_futures_permission_degrades_to_a_note(self):
        """-2015 on /fapi is normal for a spot-only key: the rest of the account must
        still be reported, with the gap named."""
        self.set("/api/v3/account", {"balances": [
            {"asset": "USDT", "free": "100", "locked": "0"}]})
        self.set("/fapi/v2/balance", RuntimeError(
            "Invalid API-key, IP, or permissions for action (HTTP 401)"))
        balances, _prices, notes = cex._binance_balances(ACC)
        self.assertAlmostEqual(balances["USDT"], 100.0)
        self.assertEqual([n["part"] for n in notes], ["futures"])
        self.assertIn("permissions", notes[0]["message"])

    def test_a_failing_optional_call_does_not_lose_the_spot_balance(self):
        self.set("/api/v3/account", {"balances": [
            {"asset": "USDT", "free": "100", "locked": "0"}]})
        self.set("/sapi/v1/asset/get-funding-asset", RuntimeError("boom"))
        self.set("/sapi/v1/margin/account", RuntimeError("boom"))
        balances, _prices, notes = cex._binance_balances(ACC)
        self.assertAlmostEqual(balances["USDT"], 100.0)
        self.assertEqual(sorted(n["part"] for n in notes), ["funding", "margin"])

    def test_every_sub_account_is_queried(self):
        cex._binance_balances(ACC)
        paths = [p for _m, p in self.fake.calls]
        for expected in ("/api/v3/account", "/sapi/v1/simple-earn/flexible/position",
                         "/sapi/v1/simple-earn/locked/position",
                         "/sapi/v1/asset/get-funding-asset", "/sapi/v1/margin/account",
                         "/fapi/v2/balance"):
            self.assertIn(expected, paths)
        # funding is a POST endpoint; asking with GET is answered with -1000
        self.assertIn(("POST", "/sapi/v1/asset/get-funding-asset"), self.fake.calls)


class BinanceRetryTest(unittest.TestCase):
    def setUp(self):
        self.fake = _FakeBinance()
        self._orig = cex._signed_request
        cex._signed_request = self.fake

    def tearDown(self):
        cex._signed_request = self._orig

    def test_a_timestamp_rejection_is_retried_once_with_a_fresh_timestamp(self):
        self.fake.replies = {"/api/v3/account": {"balances": [
            {"asset": "USDT", "free": "1", "locked": "0"}]}}
        self.fake.raise_first = {"/api/v3/account": 1}
        d = cex._binance_signed(ACC, "/api/v3/account")
        self.assertEqual(d["balances"][0]["asset"], "USDT")
        self.assertEqual(len(self.fake.calls), 2)          # failed once, then retried

    def test_a_second_rejection_surfaces_as_an_error(self):
        self.fake.replies = {}
        self.fake.raise_first = {"/api/v3/account": 5}
        with self.assertRaises(RuntimeError) as cm:
            cex._binance_signed(ACC, "/api/v3/account")
        self.assertIn("timestamp", str(cm.exception))

    def test_a_non_timestamp_error_is_not_retried(self):
        self.fake.replies = {"/api/v3/account": RuntimeError("Invalid API-key (HTTP 401)")}
        with self.assertRaises(RuntimeError):
            cex._binance_signed(ACC, "/api/v3/account")
        self.assertEqual(len(self.fake.calls), 1)

    def test_the_signed_query_carries_a_sixty_second_window(self):
        seen = {}

        def capture(url, headers, method):
            seen["url"] = url
            return {"balances": []}
        cex._signed_request = capture
        cex._binance_signed(ACC, "/api/v3/account")
        self.assertIn("recvWindow=60000", seen["url"])
        self.assertIn("signature=", seen["url"])


class BinanceErrorBodyTest(unittest.TestCase):
    """A rejected request must report Binance's own wording, not "400 Bad Request"."""

    def test_the_json_body_is_read(self):
        import requests

        class Resp(object):
            status_code = 400
            text = '{"code":-1021,"msg":"Timestamp for this request is outside of the recvWindow."}'

            def json(self):
                return {"code": -1021, "msg": "Timestamp for this request is outside of the recvWindow."}

        class Session(object):
            def get(self, *a, **kw):
                return Resp()

            def post(self, *a, **kw):
                return Resp()

        orig = requests.get
        requests.get = Session().get
        try:
            with self.assertRaises(cex._BinanceRetry):
                cex._signed_request("https://api.binance.com/api/v3/account?x=1", {}, "GET")
        finally:
            requests.get = orig

    def test_a_permission_error_is_a_plain_error_with_the_message(self):
        import requests

        class Resp(object):
            status_code = 401
            text = '{"code":-2015,"msg":"Invalid API-key, IP, or permissions for action"}'

            def json(self):
                return {"code": -2015, "msg": "Invalid API-key, IP, or permissions for action"}

        orig = requests.get
        requests.get = lambda *a, **kw: Resp()
        try:
            with self.assertRaises(RuntimeError) as cm:
                cex._signed_request("https://fapi.binance.com/fapi/v2/balance?x=1", {}, "GET")
            self.assertIn("permissions", str(cm.exception))
            self.assertIn("401", str(cm.exception))
        finally:
            requests.get = orig


if __name__ == "__main__":
    unittest.main()
