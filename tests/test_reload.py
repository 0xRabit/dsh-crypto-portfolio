# -*- coding: utf-8 -*-
"""Auto-restart on code change (tracker/reload.py).

The dashboard is a long-lived child process, and Python imports a module once. The
point of this module is that editing `tracker/*.py` must not mean restarting all of
DSH: the process watches its own sources and re-executes itself (same PID, same
argv, same env). These tests pin the fingerprint, the change detection, the opt-out
and the exec call itself — plus one real watcher run on a temporary tree.
"""
import os
import sys
import tempfile
import threading
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tracker import reload as reload_mod  # noqa: E402


def make_tree(root):
    """A miniature package: run.py + tracker/*.py + noise that must be ignored."""
    os.makedirs(os.path.join(root, "tracker"), exist_ok=True)
    for name in ("run.py", "fetch.py"):
        with open(os.path.join(root, name), "w", encoding="utf-8") as fh:
            fh.write("# %s\n" % name)
    for name in ("server.py", "views.py"):
        with open(os.path.join(root, "tracker", name), "w", encoding="utf-8") as fh:
            fh.write("# %s\n" % name)


class FingerprintTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = self.tmp.name
        make_tree(self.root)

    def tearDown(self):
        self.tmp.cleanup()

    def test_it_covers_the_sources_and_nothing_else(self):
        fp = reload_mod.fingerprint(self.root)
        names = sorted(os.path.basename(p) for p in fp)
        self.assertEqual(names, ["fetch.py", "run.py", "server.py", "views.py"])

    def test_user_data_and_caches_are_ignored(self):
        # a snapshot write must never restart the server that wrote it
        os.makedirs(os.path.join(self.root, "profiles", "default"), exist_ok=True)
        with open(os.path.join(self.root, "profiles", "default", "portfolio.db"), "w") as fh:
            fh.write("x")
        with open(os.path.join(self.root, "tracker", "views.cpython-39.pyc"), "w") as fh:
            fh.write("x")
        fp = reload_mod.fingerprint(self.root)
        self.assertFalse([p for p in fp if "profiles" in p or p.endswith(".pyc")])

    def test_a_touch_changes_the_fingerprint(self):
        before = reload_mod.fingerprint(self.root)
        path = os.path.join(self.root, "tracker", "views.py")
        os.utime(path, ns=(1, 1))
        after = reload_mod.fingerprint(self.root)
        self.assertTrue(reload_mod.changed(before, after))

    def test_adding_a_module_counts_as_a_change(self):
        before = reload_mod.fingerprint(self.root)
        with open(os.path.join(self.root, "tracker", "newmod.py"), "w") as fh:
            fh.write("# new\n")
        self.assertTrue(reload_mod.changed(before, reload_mod.fingerprint(self.root)))

    def test_an_unchanged_tree_is_not_a_change(self):
        before = reload_mod.fingerprint(self.root)
        self.assertFalse(reload_mod.changed(before, reload_mod.fingerprint(self.root)))

    def test_a_missing_directory_is_not_an_error(self):
        self.assertEqual(reload_mod.fingerprint(os.path.join(self.root, "nope")), {})


class RestartTest(unittest.TestCase):
    def test_restart_reexecutes_the_same_command_line(self):
        calls = []
        reload_mod.restart(argv=["run.py", "--port", "8099"],
                           execv=lambda exe, argv: calls.append((exe, argv)))
        self.assertEqual(len(calls), 1)
        exe, argv = calls[0]
        self.assertEqual(exe, sys.executable)
        self.assertEqual(argv, [sys.executable, "run.py", "--port", "8099"])

    def test_the_env_var_disables_the_watcher(self):
        with mock.patch.dict(os.environ, {"PORTFOLIO_NO_RELOAD": "1"}):
            self.assertFalse(reload_mod.enabled())
            self.assertIsNone(reload_mod.start(tempfile.gettempdir()))

    def test_it_is_enabled_by_default(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("PORTFOLIO_NO_RELOAD", None)
            self.assertTrue(reload_mod.enabled())


class WatcherTest(unittest.TestCase):
    """One real watcher loop: touch a file, expect the callback."""

    def test_an_edit_triggers_the_callback(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        make_tree(tmp.name)
        fired = threading.Event()
        with mock.patch.dict(os.environ, {"PORTFOLIO_RELOAD_INTERVAL": "0.2"}):
            thread = reload_mod.start(tmp.name, debounce=0.05,
                                      on_change=fired.set)
        self.assertIsNotNone(thread)
        path = os.path.join(tmp.name, "tracker", "server.py")
        os.utime(path, ns=(2, 2))
        self.assertTrue(fired.wait(5.0), "the watcher did not notice the edit")

    def test_it_survives_a_callback_that_raises(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        make_tree(tmp.name)
        calls = []

        def boom():
            calls.append(1)
            raise RuntimeError("nope")

        with mock.patch.dict(os.environ, {"PORTFOLIO_RELOAD_INTERVAL": "0.2"}):
            reload_mod.start(tmp.name, debounce=0.05, on_change=boom)
        os.utime(os.path.join(tmp.name, "tracker", "server.py"), ns=(3, 3))
        for _ in range(50):
            if calls:
                break
            threading.Event().wait(0.1)
        self.assertEqual(len(calls), 1)          # raised once, thread stayed alive


if __name__ == "__main__":
    unittest.main()
