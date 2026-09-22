# -*- coding: utf-8 -*-
"""Crash-safe writes for the small config files.

Every file written through here is tiny but hard to replace: `sources.json` holds
the API keys, `wallets.json` the wallet list, and an empty `.active` points the
whole dashboard at the wrong profile. `open(path, "w")` truncates the target
FIRST, so a crash, SIGKILL or power loss between the truncate and the flush leaves
a half-written or zero-byte file — and nothing else holds a copy.

`write_text` sidesteps that: it writes a sibling temporary file, flushes and
fsyncs it, then `os.replace()`s it over the target. A rename within one directory
is atomic, so a reader (or a restart) sees either the complete old file or the
complete new one, never a torn one.

Two details that matter:

* the temp file lives in the SAME directory, because `os.replace` is only atomic
  within a filesystem;
* a brand-new file is created mode 0600 instead of inheriting a permissive umask,
  since these files can carry API keys; an existing file keeps the mode it had.
"""
import json
import os
import tempfile

__all__ = ["write_text", "write_json"]

#: mode for a file we are creating for the first time (owner read/write only)
NEW_FILE_MODE = 0o600


def _fsync_dir(path):
    """Persist the rename itself. Best effort: some platforms refuse to fsync a
    directory, and losing this only costs durability of the *rename*, not data."""
    try:
        fd = os.open(path, os.O_RDONLY)
    except OSError:
        return
    try:
        os.fsync(fd)
    except OSError:
        pass
    finally:
        os.close(fd)


def write_text(path, text, mode=None):
    """Atomically replace `path` with `text` (utf-8). Returns the path written."""
    directory = os.path.dirname(os.path.abspath(path)) or "."
    os.makedirs(directory, exist_ok=True)

    if mode is None:
        try:
            mode = os.stat(path).st_mode & 0o777      # keep what the file already had
        except OSError:
            mode = NEW_FILE_MODE                     # new file: do not go world-readable

    fd, tmp = tempfile.mkstemp(dir=directory,
                               prefix="." + os.path.basename(path) + ".",
                               suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())        # data on disk BEFORE the rename is visible
        os.chmod(tmp, mode)
        os.replace(tmp, path)
        _fsync_dir(directory)
    except BaseException:
        # never leave a stray temp file behind, and never touch the target
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise
    return path


def write_json(path, data, indent=2, mode=None):
    """Atomically write `data` as JSON. Same guarantees as write_text."""
    return write_text(path, json.dumps(data, ensure_ascii=False, indent=indent), mode=mode)
