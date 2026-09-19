# -*- coding: utf-8 -*-
"""Per-profile schedule tests.

The scheduler runs per profile (profiles/<name>/schedule.json), so editing one
profile's schedule must never touch another's. Runs with the stdlib only:

    python3 -m unittest discover -s tests -v
"""
import json
import os
import shutil
import sys
import tempfile
import unittest
from datetime import datetime
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tracker import profiles, schedule as sched  # noqa: E402

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


class PerProfileScheduleTest(unittest.TestCase):

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
        profiles.create_profile("alpha")
        profiles.create_profile("beta")
        profiles.set_active("alpha")

    def test_defaults_are_disabled(self):
        for n in ("default", "alpha", "beta"):
            s = sched.get_schedule(n)
            self.assertFalse(s["enabled"], n)
            self.assertEqual(s["time"], sched.DEFAULT_TIME)

    def test_setting_one_profile_does_not_touch_others(self):
        sched.set_schedule(True, "07:15", "beta")
        self.assertTrue(sched.get_schedule("beta")["enabled"])
        self.assertEqual(sched.get_schedule("beta")["time"], "07:15")
        # the others stay untouched
        self.assertFalse(sched.get_schedule("alpha")["enabled"])
        self.assertFalse(sched.get_schedule("default")["enabled"])

    def test_each_profile_keeps_its_own_file(self):
        sched.set_schedule(True, "06:00", "alpha")
        sched.set_schedule(True, "22:30", "beta")
        with open(os.path.join(profiles.profile_dir("alpha"), "schedule.json"), encoding="utf-8") as f:
            a = json.load(f)
        with open(os.path.join(profiles.profile_dir("beta"), "schedule.json"), encoding="utf-8") as f:
            b = json.load(f)
        self.assertEqual(a["time"], "06:00")
        self.assertEqual(b["time"], "22:30")

    def test_explicit_profile_write_does_not_change_active(self):
        sched.set_schedule(True, "11:11", "beta")
        self.assertEqual(profiles.active(), "alpha")

    def test_none_profile_targets_the_active_one(self):
        sched.set_schedule(True, "05:45")           # no profile -> active (alpha)
        self.assertEqual(sched.get_schedule("alpha")["time"], "05:45")
        self.assertFalse(sched.get_schedule("beta")["enabled"])

    def test_is_due_is_scoped_per_profile(self):
        sched.set_schedule(True, "10:00", "beta")
        now = datetime(2026, 9, 19, 10, 0)
        self.assertTrue(sched.is_due("beta", now))
        self.assertFalse(sched.is_due("alpha", now))   # alpha has no schedule
        self.assertFalse(sched.is_due("default", now))

    def test_disabled_profile_is_never_due(self):
        now = datetime(2026, 9, 19, 10, 0)
        sched.set_schedule(False, "10:00", "beta")
        self.assertFalse(sched.is_due("beta", now))

    def test_saving_resets_the_once_per_day_marker(self):
        sched.set_schedule(True, "10:00", "beta")
        sched.mark_run(profile="beta")
        self.assertIsNotNone(sched.get_schedule("beta")["last_run_date"])
        sched.set_schedule(True, "10:00", "beta")     # re-save clears it
        self.assertIsNone(sched.get_schedule("beta")["last_run_date"])

    def test_renaming_a_profile_carries_its_schedule(self):
        sched.set_schedule(True, "13:05", "beta")
        profiles.rename_profile("beta", "gamma")
        s = sched.get_schedule("gamma")
        self.assertTrue(s["enabled"])
        self.assertEqual(s["time"], "13:05")


if __name__ == "__main__":
    unittest.main(verbosity=2)
