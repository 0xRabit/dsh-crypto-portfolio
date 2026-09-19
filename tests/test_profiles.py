# -*- coding: utf-8 -*-
"""Unit tests for profile management (create / rename / delete / active).

Runs with the stdlib only:

    python3 -m unittest discover -s tests -v

Everything happens inside a throwaway PROFILES_DIR, so the operator's real
profiles are never touched.
"""
import json
import os
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tracker import profiles  # noqa: E402

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


class InterruptedRefreshRecoveryTest(unittest.TestCase):
    """The scheduler switches the active profile while it refreshes, then
    switches back in a `finally`. A hard kill skips that, so startup must be
    able to put the user's chosen profile back."""

    def setUp(self):
        for d in os.listdir(_TMP.name):
            p = os.path.join(_TMP.name, d)
            if os.path.isdir(p):
                import shutil
                shutil.rmtree(p)
        try:
            os.remove(os.path.join(_TMP.name, ".active"))
        except OSError:
            pass
        profiles.clear_restore_target()
        profiles.create_profile("default", from_template=False)
        profiles.create_profile("mine")
        profiles.set_active("mine")

    def test_marker_records_and_restores_the_users_profile(self):
        # simulate: user is on "mine", scheduler switches to "default" and dies
        profiles.mark_restore_target(profiles.active())   # "mine"
        profiles.set_active("default")                    # scheduler switch
        self.assertEqual(profiles.active(), "default")
        # next startup recovers
        restored = profiles.recover_active()
        self.assertEqual(restored, "mine")
        self.assertEqual(profiles.active(), "mine")

    def test_marker_is_cleared_after_recovery(self):
        profiles.mark_restore_target("mine")
        profiles.set_active("default")
        profiles.recover_active()
        self.assertIsNone(profiles.recover_active())      # nothing left to do
        self.assertEqual(profiles.active(), "mine")

    def test_clean_shutdown_leaves_nothing_to_recover(self):
        profiles.mark_restore_target("mine")
        profiles.set_active("default")
        profiles.set_active("mine")
        profiles.clear_restore_target()                   # normal finally path
        self.assertIsNone(profiles.recover_active())
        self.assertEqual(profiles.active(), "mine")

    def test_marker_for_a_deleted_profile_is_ignored(self):
        profiles.mark_restore_target("ghost")
        profiles.set_active("default")
        self.assertIsNone(profiles.recover_active())
        self.assertEqual(profiles.active(), "default")


class ProfileRenameTest(unittest.TestCase):

    def setUp(self):
        # fresh sandbox per test
        for d in os.listdir(_TMP.name):
            p = os.path.join(_TMP.name, d)
            if os.path.isdir(p):
                import shutil
                shutil.rmtree(p)
        try:
            os.remove(os.path.join(_TMP.name, ".active"))
        except OSError:
            pass
        profiles.create_profile("default", from_template=False)
        profiles.create_profile("alpha")
        # give alpha some content that must survive the rename
        with open(os.path.join(profiles.profile_dir("alpha"), "wallets.json"), "w",
                  encoding="utf-8") as f:
            json.dump([{"name": "w1", "type": "doge", "address": "D..."}], f)
        with open(os.path.join(profiles.profile_dir("alpha"), "portfolio.db"), "wb") as f:
            f.write(b"SQLite format 3\x00fake")

    def test_rename_moves_config_and_db(self):
        profiles.rename_profile("alpha", "beta")
        self.assertFalse(profiles.exists("alpha"))
        self.assertTrue(profiles.exists("beta"))
        self.assertTrue(os.path.exists(os.path.join(profiles.profile_dir("beta"), "wallets.json")))
        self.assertTrue(os.path.exists(os.path.join(profiles.profile_dir("beta"), "portfolio.db")))

    def test_rename_keeps_wallet_content(self):
        profiles.rename_profile("alpha", "beta")
        with open(os.path.join(profiles.profile_dir("beta"), "wallets.json"), encoding="utf-8") as f:
            data = json.load(f)
        self.assertEqual(data[0]["name"], "w1")
        self.assertEqual(data[0]["type"], "doge")

    def test_renaming_active_profile_updates_active(self):
        profiles.set_active("alpha")
        self.assertEqual(profiles.active(), "alpha")
        profiles.rename_profile("alpha", "beta")
        self.assertEqual(profiles.active(), "beta")
        # and the per-profile file helpers now resolve into the renamed dir
        self.assertIn("beta", profiles.wallets_file())

    def test_rename_inactive_profile_leaves_active_alone(self):
        profiles.set_active("default")
        profiles.rename_profile("alpha", "beta")
        self.assertEqual(profiles.active(), "default")

    def test_rename_to_existing_name_is_rejected(self):
        with self.assertRaises(ValueError):
            profiles.rename_profile("alpha", "default")

    def test_rename_missing_profile_is_rejected(self):
        with self.assertRaises(ValueError):
            profiles.rename_profile("nope", "whatever")

    def test_default_profile_cannot_be_renamed(self):
        with self.assertRaises(ValueError):
            profiles.rename_profile("default", "mine")

    def test_rename_to_same_name_is_noop(self):
        self.assertEqual(profiles.rename_profile("alpha", "alpha"), "alpha")
        self.assertTrue(profiles.exists("alpha"))

    def test_rename_rejects_path_traversal(self):
        for bad in ("../evil", "a/b", "a\\b", "", ".", "..", "x:y"):
            with self.assertRaises(ValueError, msg=f"{bad!r} should be rejected"):
                profiles.rename_profile("alpha", bad)
        self.assertTrue(profiles.exists("alpha"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
