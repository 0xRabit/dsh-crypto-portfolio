# -*- coding: utf-8 -*-
"""OKX and Bitget balance fetchers.

Both sign every request, and a signature that is one character off looks exactly
like a wrong key from the outside — so the prehash shape (header names, timestamp
format, query inclusion) is pinned here instead of being trusted.

Bitget also splits a portfolio across the spot account and up to four futures
accounts, and an API key may be scoped to only some of them; a read-only key that
can see spot but not futures must still produce a balance.
"""
import base64
import hashlib
import hmac
import os
import re
import sys
import unittest
import urllib.parse

import requests
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tracker import cex  # noqa: E402


class _Recorder(object):
    """Replaces http_get_json; records (url, headers) and replays canned payloads.

    Both new fetchers inline their query into the path (the signature covers the
    path), so `params` here re-parses that query back out for the fake replies.
    """

    def __init__(self):
        self.calls = []

    def __call__(self, url, params=None, headers=None, **kw):
        merged = dict(params or {})
        if "?" in url:
            merged.update(urllib.parse.parse_qsl(url.split("?", 1)[1]))
        self.calls.append({"url": url, "params": merged, "headers": headers or {}})
        return self.reply(url, merged)


class OkxTest(unittest.TestCase):
    def setUp(self):
        self.rec = _Recorder()
        self.rec.reply = lambda url, params: self.payload
        self.payload = {}
        self._orig = cex.http_get_json
        cex.http_get_json = self.rec
        self.acc = {"key": "okx-key", "secret": "okx-secret", "passphrase": "okx-pass"}

    def tearDown(self):
        cex.http_get_json = self._orig

    def test_the_signature_is_over_timestamp_method_and_path(self):
        cex._okx_request(self.acc, "GET", "/api/v5/account/balance")
        h = self.rec.calls[0]["headers"]
        ts = h["OK-ACCESS-TIMESTAMP"]
        expected = base64.b64encode(hmac.new(
            b"okx-secret", (ts + "GET" + "/api/v5/account/balance").encode(),
            hashlib.sha256).digest()).decode()
        self.assertEqual(h["OK-ACCESS-SIGN"], expected)
        self.assertEqual(h["OK-ACCESS-KEY"], "okx-key")
        self.assertEqual(h["OK-ACCESS-PASSPHRASE"], "okx-pass")

    def test_the_timestamp_is_iso8601_with_milliseconds(self):
        """OKX rejects a plain epoch timestamp; the format itself is the contract."""
        cex._okx_request(self.acc, "GET", "/api/v5/account/balance")
        ts = self.rec.calls[0]["headers"]["OK-ACCESS-TIMESTAMP"]
        self.assertRegex(ts, r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$")
        # and it must be UTC, not local time
        now = datetime.now(timezone.utc)
        self.assertEqual(ts[:10], now.strftime("%Y-%m-%d"))

    def test_the_query_string_is_part_of_the_prehash(self):
        cex._okx_request(self.acc, "GET", "/api/v5/account/balance", {"ccy": "BTC"})
        call = self.rec.calls[0]
        self.assertTrue(call["url"].endswith("/api/v5/account/balance?ccy=BTC"))
        # http_get_json is handed the bare path; the query must be inlined by us so
        # that the URL and the signature can never disagree
        self.assertNotIn("params", call["headers"])
        h = call["headers"]
        expected = base64.b64encode(hmac.new(
            b"okx-secret",
            (h["OK-ACCESS-TIMESTAMP"] + "GET" + "/api/v5/account/balance?ccy=BTC").encode(),
            hashlib.sha256).digest()).decode()
        self.assertEqual(h["OK-ACCESS-SIGN"], expected)

    def test_balances_come_from_equity_with_an_implied_price(self):
        """OKX gives no per-currency price, only eqUsd, so the price is eqUsd/eq."""
        self.payload = {"code": "0", "data": [{"details": [
            {"ccy": "BTC", "eq": "0.5", "eqUsd": "42000"},
            {"ccy": "USDT", "eq": "1200.5", "eqUsd": "1200.5"},
        ]}]}
        balances, prices = cex._okx_balances(self.acc)
        self.assertAlmostEqual(balances["BTC"], 0.5)
        self.assertAlmostEqual(balances["USDT"], 1200.5)
        self.assertAlmostEqual(prices["BTC"], 84000.0)
        self.assertAlmostEqual(prices["USDT"], 1.0)

    def test_zero_and_negative_equity_is_dropped(self):
        # a currency with a borrow shows up with a negative equity
        self.payload = {"code": "0", "data": [{"details": [
            {"ccy": "BTC", "eq": "0", "eqUsd": "0"},
            {"ccy": "USDC", "eq": "-12", "eqUsd": "-12"},
            {"ccy": "ETH", "eq": "1.5", "eqUsd": "3000"},
        ]}]}
        balances, prices = cex._okx_balances(self.acc)
        self.assertEqual(sorted(balances), ["ETH"])
        self.assertEqual(sorted(prices), ["ETH"])

    def test_a_nonzero_code_raises_with_the_exchange_message(self):
        self.payload = {"code": "50111", "msg": "Invalid API Key"}
        with self.assertRaises(RuntimeError) as cm:
            cex._okx_balances(self.acc)
        self.assertIn("Invalid API Key", str(cm.exception))

    def test_a_missing_optional_field_does_not_crash(self):
        self.payload = {"code": "0", "data": [{"details": [{"ccy": "BTC", "eq": "1"}]}]}
        balances, prices = cex._okx_balances(self.acc)
        self.assertAlmostEqual(balances["BTC"], 1.0)
        self.assertEqual(prices, {})


class OkxFundingTest(unittest.TestCase):
    """OKX keeps deposits in a separate funding sub-account.

    Reading only /account/balance silently hides everything the user parked in
    funding — which is exactly where a deposit lands before it is traded.
    """

    def setUp(self):
        self.rec = _Recorder()
        self.rec.reply = self._reply
        self.trading = {"code": "0", "data": [{"details": []}]}
        self.funding = {"code": "0", "data": []}
        self.funding_fails = False
        self._orig = cex.http_get_json
        cex.http_get_json = self.rec
        self.acc = {"key": "k", "secret": "s", "passphrase": "p"}

    def tearDown(self):
        cex.http_get_json = self._orig

    def _reply(self, url, params):
        if "/asset/balances" in url:
            if self.funding_fails:
                raise RuntimeError("no funding permission")
            return self.funding
        return self.trading

    def test_both_sub_accounts_are_queried(self):
        cex._okx_balances(self.acc)
        urls = [c["url"] for c in self.rec.calls]
        self.assertEqual(len(urls), 2)
        self.assertTrue(any("/account/balance" in u for u in urls))
        self.assertTrue(any("/asset/balances" in u for u in urls))

    def test_a_funding_only_balance_is_included(self):
        self.trading = {"code": "0", "data": [{"details": [
            {"ccy": "USDC", "eq": "60", "eqUsd": "60"}]}]}
        self.funding = {"code": "0", "data": [
            {"ccy": "USDT", "bal": "8.327524", "availBal": "8.327524"}]}
        balances, _ = cex._okx_balances(self.acc)
        self.assertAlmostEqual(balances["USDC"], 60.0)
        self.assertAlmostEqual(balances["USDT"], 8.327524)

    def test_the_same_coin_in_both_is_summed_not_overwritten(self):
        """Trading and funding are distinct balances, so they add up; the exchange's
        own total assets does the same."""
        self.trading = {"code": "0", "data": [{"details": [
            {"ccy": "USDT", "eq": "100", "eqUsd": "100"}]}]}
        self.funding = {"code": "0", "data": [{"ccy": "USDT", "bal": "25"}]}
        balances, prices = cex._okx_balances(self.acc)
        self.assertAlmostEqual(balances["USDT"], 125.0)
        self.assertAlmostEqual(prices["USDT"], 1.0)

    def test_zero_funding_rows_are_ignored(self):
        self.funding = {"code": "0", "data": [{"ccy": "BTC", "bal": "0"}]}
        balances, _ = cex._okx_balances(self.acc)
        self.assertEqual(balances, {})

    def test_a_missing_funding_permission_is_not_fatal(self):
        self.funding_fails = True
        self.trading = {"code": "0", "data": [{"details": [
            {"ccy": "BTC", "eq": "0.5", "eqUsd": "42000"}]}]}
        balances, _ = cex._okx_balances(self.acc)
        self.assertAlmostEqual(balances["BTC"], 0.5)


class OkxTickerTest(unittest.TestCase):
    def setUp(self):
        self.rec = _Recorder()
        self.rec.reply = lambda url, params: self.payload
        self.payload = {}
        self._orig = cex.http_get_json
        cex.http_get_json = self.rec

    def tearDown(self):
        cex.http_get_json = self._orig

    def test_spot_tickers_are_mapped_by_base_currency(self):
        self.payload = {"code": "0", "data": [
            {"instId": "BTC-USDT", "last": "84195.6"},
            {"instId": "ETH-USDC", "last": "2680"},   # not a USDT pair
            {"instId": "BTC-USDC", "last": "84190"},
            {"instId": "SOL-USDT", "last": "116.52"},
        ]}
        prices = cex._ticker_map("okx", ["BTC", "SOL"])
        self.assertEqual(prices, {"BTC": 84195.6, "SOL": 116.52})

    def test_a_broken_response_is_swallowed(self):
        def boom(url, params=None, **kw):
            raise RuntimeError("network down")
        cex.http_get_json = boom
        self.assertEqual(cex._ticker_map("okx", ["BTC"]), {})


class BitgetTest(unittest.TestCase):
    """`reply` is keyed by URL so a test can make one endpoint fail independently."""

    def setUp(self):
        self.rec = _Recorder()
        self.rec.reply = self._reply
        self.spot_payload = {"code": "00000", "data": []}
        self.mix = {}
        self.spot_fails = False
        self._orig = cex.http_get_json
        cex.http_get_json = self.rec
        self.acc = {"key": "bg-key", "secret": "bg-secret", "passphrase": "bg-pass"}

    def tearDown(self):
        cex.http_get_json = self._orig

    def _reply(self, url, params):
        if "/spot/account/assets" in url:
            if self.spot_fails:
                raise RuntimeError("spot denied")
            return self.spot_payload
        product = params.get("productType")
        return self.mix.get(product, {"code": "00000", "data": []})

    def test_the_signature_is_over_timestamp_method_and_path(self):
        cex._bitget_request(self.acc, "GET", "/api/v2/spot/account/assets")
        h = self.rec.calls[0]["headers"]
        ts = h["ACCESS-TIMESTAMP"]
        self.assertTrue(ts.isdigit() and len(ts) == 13)   # milliseconds
        expected = base64.b64encode(hmac.new(
            b"bg-secret", (ts + "GET" + "/api/v2/spot/account/assets").encode(),
            hashlib.sha256).digest()).decode()
        self.assertEqual(h["ACCESS-SIGN"], expected)
        self.assertEqual(h["ACCESS-KEY"], "bg-key")
        self.assertEqual(h["ACCESS-PASSPHRASE"], "bg-pass")

    def test_the_query_is_signed_in_key_order(self):
        cex._bitget_request(self.acc, "GET", "/api/v2/mix/account/accounts",
                            {"productType": "USDT-FUTURES", "marginCoin": "USDT"})
        call = self.rec.calls[0]
        self.assertTrue(call["url"].endswith(
            "/api/v2/mix/account/accounts?marginCoin=USDT&productType=USDT-FUTURES"))
        h = call["headers"]
        expected = base64.b64encode(hmac.new(
            b"bg-secret",
            (h["ACCESS-TIMESTAMP"] + "GET" +
             "/api/v2/mix/account/accounts?marginCoin=USDT&productType=USDT-FUTURES").encode(),
            hashlib.sha256).digest()).decode()
        self.assertEqual(h["ACCESS-SIGN"], expected)

    def test_spot_freezes_and_locks_are_included(self):
        """A limit order's funds are frozen, not available — ignoring that field
        would report the balance as lower than the exchange UI shows."""
        self.spot_payload = {"code": "00000", "data": [
            {"coin": "BTC", "available": "0.1", "frozen": "0.02", "locked": "0.005"},
            {"coin": "USDT", "available": "500", "frozen": "0", "locked": "0"},
        ]}
        balances, _ = cex._bitget_balances(self.acc)
        self.assertAlmostEqual(balances["BTC"], 0.125)
        self.assertAlmostEqual(balances["USDT"], 500.0)

    def test_futures_equity_is_added_to_the_same_coin(self):
        self.spot_payload = {"code": "00000", "data": [
            {"coin": "USDT", "available": "500", "frozen": "0", "locked": "0"}]}
        self.mix = {"USDT-FUTURES": {"code": "00000", "data": [
            {"marginCoin": "USDT", "accountEquity": "1800.25"}]}}
        balances, _ = cex._bitget_balances(self.acc)
        self.assertAlmostEqual(balances["USDT"], 2300.25)

    def test_only_the_real_futures_accounts_are_queried(self):
        """A real read-only key answers on the S-prefixed demo products too, with a
        3000 play-money balance each — counting those would invent $6000."""
        cex._bitget_balances(self.acc)
        products = [c["params"].get("productType") for c in self.rec.calls
                    if "/mix/account/accounts" in c["url"]]
        self.assertEqual(products, ["USDT-FUTURES", "USDC-FUTURES", "COIN-FUTURES"])
        for p in products:
            self.assertFalse(p.startswith("S"), p)

    def test_a_simulated_product_balance_never_reaches_the_result(self):
        self.mix = {p: {"code": "00000", "data": [
            {"marginCoin": "USDT", "accountEquity": "3000"}]}
            for p in ("SUSDT-FUTURES", "SUSDC-FUTURES")}
        balances, _ = cex._bitget_balances(self.acc)
        self.assertEqual(balances, {})

    def test_a_spot_only_key_still_yields_a_balance(self):
        """A key scoped to spot answers 40006 on the futures endpoints; that must not
        turn the whole account into an error."""
        self.spot_payload = {"code": "00000", "data": [
            {"coin": "BTC", "available": "0.25", "frozen": "0", "locked": "0"}]}
        self.mix = {p: {"code": "40006", "msg": "Not authorized"}
                    for p in ("USDT-FUTURES", "USDC-FUTURES", "COIN-FUTURES")}
        balances, _ = cex._bitget_balances(self.acc)
        self.assertAlmostEqual(balances["BTC"], 0.25)

    def test_a_futures_only_key_still_yields_a_balance(self):
        self.spot_fails = True
        self.mix = {"USDT-FUTURES": {"code": "00000", "data": [
            {"marginCoin": "USDT", "accountEquity": "900"}]}}
        balances, _ = cex._bitget_balances(self.acc)
        self.assertAlmostEqual(balances["USDT"], 900.0)

    def test_a_failing_spot_reply_alone_raises(self):
        self.spot_payload = {"code": "40001", "msg": "signature error"}
        with self.assertRaises(RuntimeError) as cm:
            cex._bitget_balances(self.acc)
        self.assertIn("signature error", str(cm.exception))

    def test_zero_balances_are_dropped(self):
        self.spot_payload = {"code": "00000", "data": [
            {"coin": "ETH", "available": "0", "frozen": "0", "locked": "0"},
            {"coin": "SOL", "available": "2", "frozen": "0", "locked": "0"}]}
        balances, _ = cex._bitget_balances(self.acc)
        self.assertEqual(sorted(balances), ["SOL"])

    def test_tickers_are_mapped_by_base_currency(self):
        self.rec.reply = lambda url, params: {"code": "00000", "data": [
            {"symbol": "BTCUSDT", "lastPr": "84100"},
            {"symbol": "BTCUSDC", "lastPr": "84090"},
            {"symbol": "SOLUSDT", "lastPr": "116.4"},
        ]}
        self.assertEqual(cex._ticker_map("bitget", ["BTC", "SOL"]),
                         {"BTC": 84100.0, "SOL": 116.4})


class SignedGetTest(unittest.TestCase):
    """A rejected key must surface the exchange's own wording.

    OKX answers 401 with the reason only in the JSON body; passing requests'
    "HTTPError: 401 Client Error" through would tell the user nothing about which of
    the three credential fields is wrong.
    """

    class _Resp(object):
        def __init__(self, payload, raises=False):
            self._payload = payload
            self._raises = raises

        def json(self):
            if self._raises:
                raise ValueError("not json")
            return self._payload

    def setUp(self):
        self._orig = cex.http_get_json

    def tearDown(self):
        cex.http_get_json = self._orig

    def _raise(self, resp):
        def boom(*a, **kw):
            err = requests.exceptions.HTTPError("401 Client Error")
            err.response = resp
            raise err
        cex.http_get_json = boom

    def test_an_error_body_is_returned_as_data(self):
        self._raise(self._Resp({"code": "50111", "msg": "Invalid API Key"}))
        out = cex._signed_get("https://example.invalid", {})
        self.assertEqual(out["msg"], "Invalid API Key")

    def test_a_non_json_error_body_still_raises(self):
        self._raise(self._Resp(None, raises=True))
        with self.assertRaises(requests.exceptions.HTTPError):
            cex._signed_get("https://example.invalid", {})

    def test_a_transport_error_is_not_swallowed(self):
        def boom(*a, **kw):
            raise requests.exceptions.ConnectionError("no route")
        cex.http_get_json = boom
        with self.assertRaises(requests.exceptions.ConnectionError):
            cex._signed_get("https://example.invalid", {})


class DispatchTest(unittest.TestCase):
    """The exchange name in sources.json is what selects the fetcher."""

    def test_every_declared_exchange_has_a_fetcher(self):
        for name in cex.EXCHANGES:
            self.assertTrue(hasattr(cex, "_%s_balances" % name) or
                            hasattr(cex, "_%s_state" % name) or
                            hasattr(cex, "_%s_signed_get" % name), name)

    def test_an_unknown_exchange_reports_the_supported_list(self):
        res = cex.fetch_cex_accounts([{"name": "x", "exchange": "ftx",
                                       "key": "k", "secret": "s"}], {})
        self.assertIn("未知交易所", res[0]["error"])
        for name in cex.EXCHANGES:
            self.assertIn(name, res[0]["error"])

    def test_okx_and_bitget_declare_a_passphrase(self):
        src = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                           "tracker", "cex.py")
        with open(src, encoding="utf-8") as fh:
            head = fh.read(1200)
        self.assertRegex(head, r'"okx"\|"bitget"')


if __name__ == "__main__":
    unittest.main()
