# -*- coding: utf-8 -*-
"""Live Binance read: what can *this* key actually do?

Skipped by default — it talks to the real API and needs real credentials. Run it
deliberately when a wallet reports "did not update":

    PORTFOLIO_LIVE_CEX=1 python3 -m unittest tests.test_binance_live -v
    PORTFOLIO_LIVE_CEX=1 BINANCE_TEST_KEY=... BINANCE_TEST_SECRET=... python3 -m unittest tests.test_binance_live -v

Credentials come from the environment, or — with no env vars — from the ACTIVE
profile's own sources file, which is where the dashboard reads them anyway. Nothing
is hardcoded here, so the file stays publishable.

The useful part is not "the call worked": it is asking Binance which *permissions* the
key has (`/sapi/v1/account/apiRestrictions`) and then checking that the tracker's
behaviour matches them. A key with `enableFutures: false` must yield a futures *note*
(the spot side is complete), never a silent `$0` and never an error row.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tracker import cex, sources  # noqa: E402

LIVE = (os.environ.get("PORTFOLIO_LIVE_CEX") or "").strip() == "1"


def live_account():
    """(account, origin): env first, then the active profile's binance entry."""
    key = (os.environ.get("BINANCE_TEST_KEY") or "").strip()
    secret = (os.environ.get("BINANCE_TEST_SECRET") or "").strip()
    if key and secret:
        return {"exchange": "binance", "name": "env", "key": key, "secret": secret}, "environment"
    try:
        cfg = sources.load()
    except Exception:                                        # noqa: BLE001
        return None, "no config"
    accounts = ((cfg or {}).get("cex", {}) or {}).get("accounts", [])
    acc = next((a for a in accounts if a.get("exchange") == "binance"
                and a.get("key") and a.get("secret")), None)
    return acc, "profiles/<active>/portfolio_sources.json"


@unittest.skipUnless(LIVE, "live Binance test: set PORTFOLIO_LIVE_CEX=1 to run it")
class BinanceLiveReadTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.acc, cls.origin = live_account()
        if not cls.acc:
            raise unittest.SkipTest("no Binance credentials in the environment or the profile")
        print("\n  credentials from: %s (%s)"
              % (cls.origin, str(cls.acc.get("key", "")).split(":")[0] or "-"))
        # the permission list is the single most useful fact: it names the knob
        cls.perms = cex._binance_signed(cls.acc, "/sapi/v1/account/apiRestrictions")

    def test_the_key_can_read(self):
        """Reading must be on; withdrawals must be off on a key this tool uses."""
        self.assertTrue(self.perms.get("enableReading"), "enableReading is off: the key cannot read")
        self.assertFalse(self.perms.get("enableWithdrawals"),
                         "enableWithdrawals is ON — a tracker key must never be able to move funds")
        print("  ipRestrict=%s enableFutures=%s enableMargin=%s"
              % (self.perms.get("ipRestrict"), self.perms.get("enableFutures"),
                 self.perms.get("enableMargin")))

    def test_the_spot_balance_is_visible(self):
        spot = cex._binance_signed(self.acc, "/api/v3/account")
        held = [b for b in spot.get("balances", [])
                if float(b.get("free") or 0) + float(b.get("locked") or 0) > 0]
        print("  spot: %d asset(s) -> %s" % (len(held), ", ".join(
            "%s %s" % (b["asset"], round(float(b["free"]) + float(b["locked"]), 4))
            for b in held[:8])))
        self.assertTrue(held, "the spot wallet reads but holds nothing")

    def test_the_wallet_matches_the_key_permissions(self):
        """Futures is counted only when the key may see it — and says so when it may not."""
        balances, _prices, notes = cex._binance_balances(self.acc)
        parts = [n.get("part") for n in notes]
        self.assertTrue(balances, "no balance at all: the account read returned nothing")
        if self.perms.get("enableFutures"):
            self.assertNotIn("futures", parts, "futures is permitted but the read failed")
            print("  futures: permitted and read")
        else:
            self.assertIn("futures", parts, "futures is NOT permitted, so the tracker must note it")
            message = next(n["message"] for n in notes if n["part"] == "futures")
            self.assertIn("Enable Futures", message, "the note must say what to change")
            print("  futures: NOT permitted (enableFutures=false) -> noted, spot still counted")
            print("           fix: Binance → API Management → this key → Enable Futures,")
            print("                or untick \"futures\" for this account in Settings → Sources")


if __name__ == "__main__":
    unittest.main()
