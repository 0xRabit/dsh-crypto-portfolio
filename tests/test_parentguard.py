# -*- coding: utf-8 -*-
"""The dashboard must not outlive the app that started it (tracker/parentguard.py).

If the desktop host is force-killed, no signal reaches this process: it kept port 8080,
served stale code to the next launch, and made the updater wait for a pipe that never
closed. The guard watches for the reparent instead.
"""
import os
import sys
import threading
import time
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tracker import parentguard  # noqa: E402


class GuardTest(unittest.TestCase):
    def test_it_is_off_unless_the_launcher_asks(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop(parentguard.ENV, None)
            self.assertFalse(parentguard.enabled())
            self.assertIsNone(parentguard.start(getppid=lambda: 1))
        for value in ("0", ""):
            with mock.patch.dict(os.environ, {parentguard.ENV: value}):
                self.assertFalse(parentguard.enabled())

    def test_it_is_on_when_the_plugin_sets_the_flag(self):
        with mock.patch.dict(os.environ, {parentguard.ENV: "1"}):
            self.assertTrue(parentguard.enabled())

    def test_it_fires_when_the_parent_changes(self):
        with mock.patch.dict(os.environ, {parentguard.ENV: "1"}):
            calls = []
            parents = iter([4242, 4242, 4242, 1, 1])
            guard = parentguard.start(interval=0.05, getppid=lambda: next(parents, 1),
                                      on_orphan=lambda: calls.append(1), log=lambda *_: None)
            self.assertIsNotNone(guard)
            for _ in range(60):
                if calls:
                    break
                time.sleep(0.05)
            self.assertEqual(len(calls), 1)

    def test_an_unchanged_parent_does_not_fire(self):
        with mock.patch.dict(os.environ, {parentguard.ENV: "1"}):
            calls = []
            guard = parentguard.start(interval=0.05, getppid=lambda: 4242,
                                      on_orphan=lambda: calls.append(1), log=lambda *_: None)
            time.sleep(0.4)
            self.assertTrue(guard.is_alive())
            self.assertEqual(calls, [])

    def test_a_vanished_parent_counts_as_orphaned(self):
        with mock.patch.dict(os.environ, {parentguard.ENV: "1"}):
            calls = []
            seen = []

            def flaky():
                seen.append(1)
                if len(seen) > 1:
                    raise OSError("no parent")
                return 4242

            parentguard.start(interval=0.05, getppid=flaky,
                              on_orphan=lambda: calls.append(1), log=lambda *_: None)
            for _ in range(40):
                if calls:
                    break
                time.sleep(0.05)
            self.assertEqual(len(calls), 1)


if __name__ == "__main__":
    unittest.main()
