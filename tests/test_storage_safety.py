# -*- coding: utf-8 -*-
"""Durability and concurrency of the config files.

Two failure modes are covered here:

  * a crash between truncating a file and finishing the write — `open(path, "w")`
    destroys the previous contents, and nothing else holds a copy;
  * two writers interleaving a read-modify-write, which silently loses one of the
    updates (the scheduler thread and an HTTP request do exactly this).
"""
import json
import os
import sys
import tempfile
import threading
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tracker import atomicio, profiles, schedule, status  # noqa: E402


class AtomicWriteTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.path = os.path.join(self.tmp, "cfg.json")

    def test_writes_the_content_and_leaves_no_temp_file(self):
        atomicio.write_json(self.path, {"a": 1})
        self.assertEqual(json.load(open(self.path, encoding="utf-8")), {"a": 1})
        self.assertEqual(os.listdir(self.tmp), ["cfg.json"])

    def test_new_file_is_owner_only(self):
        """These files can hold API keys, so a fresh one must not be world-readable."""
        atomicio.write_text(self.path, "secret")
        self.assertEqual(os.stat(self.path).st_mode & 0o777, 0o600)

    def test_existing_mode_is_preserved(self):
        atomicio.write_text(self.path, "one")
        os.chmod(self.path, 0o644)
        atomicio.write_text(self.path, "two")
        self.assertEqual(os.stat(self.path).st_mode & 0o777, 0o644)
        self.assertEqual(open(self.path, encoding="utf-8").read(), "two")

    def test_a_failed_replace_leaves_the_old_file_untouched(self):
        """The crash case: if the swap never happens, the target must still hold the
        previous complete contents — not a truncated or half-written file."""
        atomicio.write_json(self.path, {"version": 1})
        before = open(self.path, "rb").read()

        real = os.replace
        os.replace = lambda *a, **k: (_ for _ in ()).throw(OSError("simulated crash"))
        try:
            with self.assertRaises(OSError):
                atomicio.write_json(self.path, {"version": 2})
        finally:
            os.replace = real

        self.assertEqual(open(self.path, "rb").read(), before)
        self.assertEqual(json.load(open(self.path, encoding="utf-8")), {"version": 1})
        self.assertEqual(os.listdir(self.tmp), ["cfg.json"], "temp file left behind")

    def test_a_reader_never_observes_a_torn_file(self):
        """A naive writer truncates in place, so a concurrent reader can parse a
        half-written file. With a sibling temp + rename it can only ever see a
        complete document."""
        payload_a = {"data": "a" * 200_000}
        payload_b = {"data": "b" * 200_000}
        atomicio.write_json(self.path, payload_a)
        stop = threading.Event()
        errors = []

        def writer():
            flip = False
            while not stop.is_set():
                atomicio.write_json(self.path, payload_b if flip else payload_a)
                flip = not flip

        def reader():
            while not stop.is_set():
                try:
                    with open(self.path, encoding="utf-8") as f:
                        doc = json.load(f)
                    if doc["data"][0] not in ("a", "b") or len(doc["data"]) != 200_000:
                        errors.append("partial document observed")
                except Exception as e:  # noqa: BLE001
                    errors.append(f"{type(e).__name__}: {e}")

        threads = [threading.Thread(target=writer), threading.Thread(target=reader),
                   threading.Thread(target=reader)]
        for t in threads:
            t.start()
        stop.wait(1.0)
        stop.set()
        for t in threads:
            t.join(timeout=5)
        self.assertEqual(errors, [], "reader saw an invalid document")


class ConcurrentUpdateTest(unittest.TestCase):
    """Read-modify-write on one file from several threads must not lose updates."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        # Patch EVERY path the code under test can reach. `set_active` writes through
        # the module-level ACTIVE_FILE constant rather than through profile_dir(), so
        # patching only the helpers is not enough — that mistake once wrote to the
        # operator's real profiles/.active.
        self._orig = dict(
            PROFILES_DIR=profiles.PROFILES_DIR, ACTIVE_FILE=profiles.ACTIVE_FILE,
            profile_dir=profiles.profile_dir, active=profiles.active,
            asset_labels_file=profiles.asset_labels_file,
            legacy_asset_labels_file=profiles.legacy_asset_labels_file,
            labels_file=profiles.labels_file,
        )
        profiles.PROFILES_DIR = self.tmp
        profiles.ACTIVE_FILE = os.path.join(self.tmp, ".active")
        profiles.profile_dir = lambda name=None: self.tmp
        profiles.active = lambda: "test"
        profiles.asset_labels_file = lambda: os.path.join(self.tmp, "asset_labels.json")
        profiles.legacy_asset_labels_file = lambda: os.path.join(self.tmp, "legacy.json")
        profiles.labels_file = lambda: os.path.join(self.tmp, "label_names.json")
        self._assert_contained()

    def _assert_contained(self):
        """Fail loudly rather than silently writing into the real data directory."""
        for label, value in (("ACTIVE_FILE", profiles.ACTIVE_FILE),
                             ("PROFILES_DIR", profiles.PROFILES_DIR),
                             ("profile_dir()", profiles.profile_dir("x")),
                             ("asset_labels_file()", profiles.asset_labels_file()),
                             ("labels_file()", profiles.labels_file())):
            self.assertTrue(
                os.path.abspath(str(value)).startswith(os.path.abspath(self.tmp)),
                f"{label} still points outside the temp dir: {value}")

    def tearDown(self):
        for name, value in self._orig.items():
            setattr(profiles, name, value)

    def _hammer(self, fn, n=24):
        barrier = threading.Barrier(n)
        errors = []

        def run(i):
            try:
                barrier.wait(timeout=5)
                fn(i)
            except Exception as e:  # noqa: BLE001
                errors.append(f"{type(e).__name__}: {e}")

        threads = [threading.Thread(target=run, args=(i,)) for i in range(n)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)
        return errors

    def test_the_containment_guard_rejects_an_escaping_path(self):
        """The guard exists because patching profile_dir() alone is not enough:
        set_active() writes through the module-level ACTIVE_FILE. If a future edit
        leaves any of these pointing at the real data dir, setUp must fail loudly
        instead of writing to the operator's live profile."""
        real = profiles.ACTIVE_FILE
        try:
            profiles.ACTIVE_FILE = os.path.join(os.path.dirname(self.tmp), ".active")
            with self.assertRaises(AssertionError):
                self._assert_contained()
        finally:
            profiles.ACTIVE_FILE = real

    def test_every_source_mark_survives(self):
        """Each mark_* rewrites the whole status file; without a lock, one thread's
        read-modify-write clobbers another's and sources go missing."""
        errors = self._hammer(lambda i: status.mark_source_ok(f"src{i}", profile="test"))
        self.assertEqual(errors, [])
        last_ok = status.get_status("test").get("last_ok", {})
        missing = [f"src{i}" for i in range(24) if f"src{i}" not in last_ok]
        self.assertEqual(missing, [], f"lost updates: {missing}")
        with open(os.path.join(self.tmp, "status.json"), encoding="utf-8") as fh:
            json.load(fh)

    def test_schedule_stays_valid_under_concurrent_writes(self):
        errors = self._hammer(
            lambda i: (schedule.set_schedule(True, f"{i % 24:02d}:00", profile="test")
                       if i % 2 else schedule.mark_run(profile="test")))
        self.assertEqual(errors, [])
        with open(os.path.join(self.tmp, "schedule.json"), encoding="utf-8") as fh:
            doc = json.load(fh)
        self.assertIn("enabled", doc)
        self.assertTrue(doc["time"].count(":") == 1)

    def test_active_pointer_is_never_left_empty(self):
        """An empty .active sends the dashboard to the wrong profile.

        This one must go through the REAL `active()` (the base class patches it out),
        because reading the 11-byte pointer back is the whole point.
        """
        os.makedirs(self.tmp, exist_ok=True)
        for name in ("alpha", "beta"):
            os.makedirs(os.path.join(self.tmp, name), exist_ok=True)
        # exercise the real reader/writer against the temp pointer
        profiles.active = self._orig["active"]
        profiles.profile_dir = lambda name=None: os.path.join(self.tmp, name or "alpha")
        errors = self._hammer(lambda i: profiles.set_active("alpha" if i % 2 else "beta"))
        self.assertEqual(errors, [])
        values = set()
        for _ in range(200):
            values.add(profiles.active())
        self.assertTrue(values <= {"alpha", "beta"}, f"unexpected pointer value: {values}")
        self.assertNotIn("", values)
        # and the file on disk holds a complete profile name, never a fragment
        with open(os.path.join(self.tmp, ".active"), encoding="utf-8") as fh:
            self.assertIn(fh.read().strip(), ("alpha", "beta"))


if __name__ == "__main__":
    unittest.main()
