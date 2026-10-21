# -*- coding: utf-8 -*-
"""DeBank failure reporting, the source probe, and the Settings wiring.

Four defects conspired to make a perfectly valid DeBank AccessKey look broken:

  1. `_fetch_with_provider()` caught every per-chain failure internally, so a
     provider that failed on ALL chains still returned a "successful" empty
     result. `try_providers()` recorded it as a success: the documented public
     fallback never ran, and the wallet was reported as fetched with $0.
  2. `sourcetest.test_debank()` probed `{base_url}/chain/list` for both
     providers, but the Pro host only serves `/v1/...` — so its probe 404'd and
     said "debank-pro failed" no matter how correct the key was.
  3. `runSourceTest()` was defined and never bound to anything: every Test
     button was inert.
  4. The sources toolbar was the last child of `.panel-body`, where a sticky box
     is clamped by its containing block and can never stick.

1 and 2 are exercised against replaced fetchers (no network); 3 and 4 live in
static files, so those tests read the files.
"""
import os
import re
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tracker import debank, sources, sourcetest  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PRO = {"name": "debank-pro", "type": "pro", "key": "k",
       "base_url": "https://pro-openapi.debank.com", "enabled": True}
PUBLIC = {"name": "debank-public", "type": "public", "key": "",
          "base_url": "https://api.debank.com", "enabled": True}
# a published example address (the same one the public templates ship), never one of
# the author's — the privacy guard rejects real wallet addresses in this repo
WALLET = {"name": "w", "address": "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045"}


class ProviderLevelFailureTest(unittest.TestCase):
    """Defect 1: "every chain failed" must not look like "the wallet is empty"."""

    def setUp(self):
        self._pro = debank._fetch_pro_chain
        self._pub = debank._fetch_public_chain
        self._filter = debank.filter_rows
        self._get = sources.get_source
        debank.filter_rows = lambda rows: rows           # keep the test hermetic
        sources.get_source = lambda key: {"enabled": True, "providers": [PRO]}

    def tearDown(self):
        debank._fetch_pro_chain = self._pro
        debank._fetch_public_chain = self._pub
        debank.filter_rows = self._filter
        sources.get_source = self._get

    def test_every_chain_failing_raises_instead_of_returning_an_empty_wallet(self):
        def boom(provider, address, cid, session):
            raise RuntimeError("HTTP 401 Invalid AccessKey")
        debank._fetch_pro_chain = boom
        with self.assertRaises(RuntimeError) as ctx:
            debank._fetch_with_provider(PRO, WALLET, ["eth"], 2)
        msg = str(ctx.exception)
        self.assertIn("debank-pro", msg)
        self.assertIn("all 1 chains", msg)
        # the provider's own wording has to survive, that is what the user reads
        self.assertIn("HTTP 401", msg)

    def test_a_wallet_whose_only_provider_dies_is_reported_as_an_error(self):
        debank._fetch_pro_chain = lambda provider, address, cid, session: (_ for _ in ()).throw(
            RuntimeError("HTTP 401 Invalid AccessKey"))
        res = debank.fetch_evm_wallet(dict(WALLET), chains=["eth"])
        self.assertIn("error", res)
        self.assertIn("HTTP 401", res["error"])
        self.assertEqual(res["tokens"], [])
        self.assertEqual(res["chain_errors"], ["all-providers"])

    def test_a_genuinely_empty_wallet_still_returns_quietly(self):
        # an empty wallet answers with empty arrays, not exceptions — so the guard
        # must not fire and the wallet stays "ok with nothing in it"
        debank._fetch_pro_chain = lambda provider, address, cid, session: []
        res = debank.fetch_evm_wallet(dict(WALLET), chains=["eth"])
        self.assertNotIn("error", res)
        self.assertEqual(res["tokens"], [])
        self.assertEqual(res["total_usd"], 0.0)

    def test_a_partly_failing_wallet_keeps_the_chains_that_answered(self):
        def flaky(provider, address, cid, session):
            if cid == "eth":
                return [{"symbol": "ETH", "amount": 2.0, "price": 100.0, "id": "eth"}]
            raise RuntimeError("HTTP 500")
        debank._fetch_pro_chain = flaky
        res = debank.fetch_evm_wallet(dict(WALLET), chains=["eth", "bsc"])
        self.assertNotIn("error", res)
        self.assertEqual(res["total_usd"], 200.0)
        self.assertEqual([t["symbol"] for t in res["tokens"]], ["ETH"])
        self.assertEqual(res["chain_errors"], ["bsc"])

    def test_a_public_provider_that_fails_on_every_chain_also_raises(self):
        sources.get_source = lambda key: {"enabled": True, "providers": [PUBLIC]}

        def boom(provider, address, cid):
            raise RuntimeError("HTTP 429 rate limited")
        debank._fetch_public_chain = boom
        with self.assertRaises(RuntimeError):
            debank._fetch_with_provider(PUBLIC, WALLET, ["eth"], 2)


class DebankProbeTest(unittest.TestCase):
    """Defect 2: the probe must hit the endpoint a refresh actually calls."""

    def setUp(self):
        self._get = sourcetest.http_get_json
        self._wallet = sourcetest._first_wallet
        sourcetest._first_wallet = lambda wtype: WALLET["address"]
        self.seen = []

    def tearDown(self):
        sourcetest.http_get_json = self._get
        sourcetest._first_wallet = self._wallet

    def _probe(self, reply):
        def fake(url, headers=None, params=None, timeout=None, retries=None):
            self.seen.append({"url": url, "params": params or {}, "headers": headers or {}})
            return reply
        sourcetest.http_get_json = fake
        return sourcetest.test_debank({"providers": [PRO, PUBLIC]})

    def test_the_pro_provider_is_probed_where_a_refresh_reads_tokens(self):
        r = self._probe([{"symbol": "ETH"}])
        self.assertTrue(r["ok"])
        self.assertEqual(self.seen[0]["url"], "https://pro-openapi.debank.com/v1/user/token_list")
        self.assertEqual(self.seen[0]["params"]["id"], WALLET["address"])
        self.assertEqual(self.seen[0]["headers"]["AccessKey"], "k")
        # the path that made every valid key look broken
        self.assertNotIn("/chain/list", self.seen[0]["url"])

    def test_the_keyless_provider_uses_its_own_shape(self):
        self._probe({"data": {"chains": [{"id": "eth"}, {"id": "bsc"}]}})
        urls = [s["url"] for s in self.seen]
        self.assertEqual(urls[1], "https://api.debank.com/token/balance_list")
        self.assertEqual(self.seen[1]["params"]["user"], WALLET["address"])
        self.assertEqual(self.seen[1]["headers"], {})

    def test_a_bare_array_and_a_wrapped_chain_list_are_both_counted(self):
        r = self._probe([{"symbol": "ETH"}, {"symbol": "USDT"}])
        self.assertEqual(r["detail"]["providers"][0]["chains"], 2)
        self.assertTrue(r["detail"]["providers"][0]["key_used"])

    def test_without_an_evm_wallet_it_falls_back_to_a_chain_list(self):
        sourcetest._first_wallet = lambda wtype: None
        r = self._probe({"data": {"chains": [{"id": "eth"}]}})
        self.assertTrue(r["ok"])
        self.assertEqual(self.seen[0]["url"], "https://pro-openapi.debank.com/v1/chain/list")
        self.assertEqual(self.seen[0]["params"], {})

    def test_an_empty_answer_is_a_failure_not_a_pass(self):
        r = self._probe([])
        self.assertFalse(r["ok"])
        self.assertIn("debank-pro", r["message"])


class SettingsWiringTest(unittest.TestCase):
    """Defects 3 and 4: the two front-end fixes are static, so read the files."""

    def read(self, rel):
        with open(os.path.join(ROOT, rel), encoding="utf-8") as fh:
            return fh.read()

    def test_the_test_button_is_actually_bound(self):
        js = self.read("static/app.js")
        self.assertIn('$("sourcesBody").addEventListener("click"', js)
        self.assertIn("button[data-test-target]", js)
        # definition + the delegated call: one occurrence was the dead-code state
        self.assertGreaterEqual(js.count("runSourceTest"), 2)

    def test_the_sources_toolbar_sits_above_the_list_it_acts_on(self):
        html = self.read("static/index.html")
        self.assertLess(html.index("sticky-toolbar"), html.index('id="sourcesBody"'))
        # the inline margin-top would fight the pinned offset
        self.assertNotIn('class="toolbar" style="margin-top:12px"', html)

    def test_the_sticky_rule_exists_and_pins_below_the_header_stack(self):
        css = self.read("static/style.css")
        rule = css.split(".sticky-toolbar", 1)[1].split("}", 1)[0]
        self.assertIn("position: sticky", rule)
        self.assertIn("top: 102px", rule)
        self.assertIn("margin: 0 ", rule)          # zero top margin: no gap while pinned

    def test_the_assets_are_cache_busted(self):
        # both files carry an explicit ?v= so a stale cache cannot serve last week's
        # script against this week's markup. The number itself is bumped by hand, so
        # only its presence is asserted here.
        html = self.read("static/index.html")
        for asset in ("/static/app.js?v=", "/static/style.css?v="):
            m = re.search(re.escape(asset) + r"(\d+)", html)
            self.assertIsNotNone(m, asset + " is missing from index.html")
            self.assertGreaterEqual(int(m.group(1)), 1)


if __name__ == "__main__":
    unittest.main()
