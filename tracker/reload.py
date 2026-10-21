# -*- coding: utf-8 -*-
"""Restart the dashboard when its own code changes.

The plugin runs the tracker as a long-lived child process, and Python imports a
module once — so every edit used to mean restarting all of DSH just to load it.
That is the wrong trade for a personal tool: the *plugin* is the thing that owns
this process, so the plugin's process should be able to pick the change up alone.

So the process watches its own sources and, when they change, re-executes itself:

    python3 run.py ...   ->   os.execv(sys.executable, [sys.executable] + sys.argv)

Same PID, same arguments, same environment — the parent (DSH, a terminal, launchd)
sees nothing, the port is rebound, and the new code is live within a couple of
seconds. Only Python sources are watched: `static/` is read from disk on every
request already, and `profiles/` is user data that must never trigger a restart.

    PORTFOLIO_NO_RELOAD=1     disable the watcher (a frozen install does not need it)
    PORTFOLIO_RELOAD_INTERVAL seconds between stat sweeps (default 1.5)
"""
import os
import sys
import threading
import time

# watched on every sweep: first-party Python only.
_WATCH_FILES = ("run.py", "fetch.py")
_WATCH_DIR = "tracker"
_RELOAD_ENV = "PORTFOLIO_NO_RELOAD"
_INTERVAL_ENV = "PORTFOLIO_RELOAD_INTERVAL"


def enabled():
    return not (os.environ.get(_RELOAD_ENV) or "").strip()


def fingerprint(root):
    """{path: (mtime_ns, size)} over the files that matter.

    Deliberately not a walk of `profiles/`: writing a snapshot would otherwise
    restart the server that just wrote it. `.pyc` caches are ignored for the same
    reason (they change because of the reload, not because of an edit).
    """
    out = {}
    paths = [os.path.join(root, name) for name in _WATCH_FILES]
    package = os.path.join(root, _WATCH_DIR)
    try:
        entries = os.listdir(package)
    except OSError:
        entries = []
    paths += [os.path.join(package, name) for name in entries
              if name.endswith(".py") and not name.startswith(".")]
    for path in paths:
        try:
            st = os.stat(path)
        except OSError:
            continue
        out[path] = (st.st_mtime_ns, st.st_size)
    return out


def changed(old, new):
    """True when a watched file appeared, disappeared or was rewritten."""
    if set(old) != set(new):
        return True
    return any(old[p] != new[p] for p in old)


def restart(argv=None, execv=None):
    """Replace this process with a fresh one (same command line, same PID)."""
    argv = list(argv or sys.argv)
    execv = execv or os.execv
    print("[reload] code changed — restarting the dashboard", flush=True)
    sys.stdout.flush()
    sys.stderr.flush()
    execv(sys.executable, [sys.executable] + argv)


def start(root, interval=None, debounce=1.0, on_change=None):
    """Watch the sources in a daemon thread; returns the thread (or None).

    `on_change` exists so a test (or a future "restart" button) can observe the
    trigger without replacing the process.
    """
    if not enabled():
        return None
    try:
        interval = float(os.environ.get(_INTERVAL_ENV) or interval or 1.5)
    except ValueError:
        interval = 1.5
    interval = max(0.2, interval)
    on_change = on_change or (lambda: restart())
    base = fingerprint(root)

    def loop():
        state = dict(base)
        while True:
            time.sleep(interval)
            try:
                current = fingerprint(root)
            except Exception:                            # noqa: BLE001
                continue
            if not changed(state, current):
                continue
            # an editor writes in two steps (truncate, then content): look again
            # after a beat so the reload sees the finished file
            time.sleep(max(0.1, debounce))
            try:
                state = fingerprint(root)
            except Exception:                            # noqa: BLE001
                continue
            try:
                on_change()
            except SystemExit:
                raise
            except Exception as exc:                     # noqa: BLE001
                print("[reload] restart failed: %s" % exc, flush=True)

    thread = threading.Thread(target=loop, name="code-reload", daemon=True)
    thread.start()
    print("[reload] watching %s/*.py + %s (every %.1fs; %s=1 disables)"
          % (_WATCH_DIR, " + ".join(_WATCH_FILES), interval, _RELOAD_ENV), flush=True)
    return thread
