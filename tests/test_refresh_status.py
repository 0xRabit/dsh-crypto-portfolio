# -*- coding: utf-8 -*-
"""A failed refresh must leave a trace (tracker/server.py).

"刷新失败" with no reason anywhere was undebuggable: the progress panel hid it after
four seconds and the process only said "ending". Now the failure is kept in
`/api/status` (so the page can show it after a reload) and appended to
`profiles/<profile>/refresh.log`.

These tests drive the real handler method — the fake only stands in for the socket —
so the 500, the recorded state and the log line are all exercised together.
"""
import json
import os
import shutil
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tracker import portfolio, profiles, server  # noqa: E402

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


def handler_class():
    from tracker.server import Handler

    class Fake(Handler):
        def __init__(self):
            self.replies = []

        # the 429 path writes through _reply(), not _reply_json(): both are recorded
        def _reply(self, code, body, ctype):
            self.replies.append((code, json.loads(body.decode("utf-8"))))

        def _reply_json(self, data, code=200):
            self.replies.append((code, data))

    return Fake


class RefreshFailureTest(unittest.TestCase):
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
        server._refresh_state.update(running=False, stage="", done=0, total=0, msg="",
                                     last_error="", last_error_at="", last_error_stage="")
        server._last_refresh_at = 0.0
        self.handler = handler_class()()

    def _fail(self, exc):
        # each attempt must get past the 60 s cooldown the previous one armed
        server._last_refresh_at = 0.0
        with mock.patch.object(portfolio, "refresh_snapshot", side_effect=exc):
            self.handler._handle_refresh({})

    def test_a_crash_is_reported_and_recorded(self):
        self._fail(RuntimeError("boom"))
        code, body = self.handler.replies[-1]
        self.assertEqual(code, 500)
        self.assertEqual(body["error"], "RuntimeError: boom")
        self.assertEqual(server._refresh_state["last_error"], "RuntimeError: boom")
        self.assertTrue(server._refresh_state["last_error_at"])
        # the panel is closed again, whatever happened
        self.assertFalse(server._refresh_state["running"])

    def test_the_reason_lands_in_the_profile_log(self):
        self._fail(ValueError("no network"))
        path = os.path.join(profiles.profile_dir("default"), "refresh.log")
        self.assertTrue(os.path.exists(path))
        with open(path, encoding="utf-8") as fh:
            line = fh.read().rstrip("\n")      # keep the trailing empty field
        self.assertIn("ValueError: no network", line)
        self.assertEqual(len(line.split("\t")), 4, line)     # ts, stage, error, msg

    def test_two_failures_append_instead_of_overwriting(self):
        self._fail(RuntimeError("first"))
        self._fail(RuntimeError("second"))
        with open(os.path.join(profiles.profile_dir("default"), "refresh.log"),
                  encoding="utf-8") as fh:
            lines = [l for l in fh.read().splitlines() if l]
        self.assertEqual(len(lines), 2)
        self.assertIn("first", lines[0])
        self.assertIn("second", lines[1])

    def test_a_success_clears_the_record(self):
        self._fail(RuntimeError("boom"))
        self.assertTrue(server._refresh_state["last_error"])
        self.handler._snapshot_view = lambda data: {"date": "2026-10-30", "total_usd": 1.0}
        self.handler._reply_json = lambda data, code=200: self.handler.replies.append((code, data))
        server._last_refresh_at = 0.0
        with mock.patch.object(portfolio, "refresh_snapshot",
                               return_value=({"date": "2026-10-30"}, None)):
            self.handler._handle_refresh({})
        self.assertEqual(server._refresh_state["last_error"], "")
        self.assertEqual(self.handler.replies[-1][0], 200)

    def test_a_rate_limited_second_run_is_not_a_failure(self):
        server._last_refresh_at = __import__("time").time()
        self.handler._handle_refresh({})
        code, body = self.handler.replies[-1]
        self.assertEqual(code, 429)
        self.assertIn("rate-limited", body["error"])
        self.assertEqual(server._refresh_state["last_error"], "")

    def test_the_log_file_is_created_only_when_needed(self):
        path = os.path.join(profiles.profile_dir("default"), "refresh.log")
        self.assertFalse(os.path.exists(path))


if __name__ == "__main__":
    unittest.main()
