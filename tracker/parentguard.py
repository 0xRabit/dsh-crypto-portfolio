# -*- coding: utf-8 -*-
"""Exit when the process that started us is gone.

The desktop app runs the dashboard as a grandchild: Electron → host → this server. If the
host is force-killed, nothing tells the child to stop — it kept port 8080 alive, served
stale code to the next launch, and made the app updater wait for a pipe that never
closed. Signals cannot be trusted for that (a SIGKILL sends none), but a child *can*
notice that it was reparented: once the parent is gone, `getppid()` stops being the
process that started us (it becomes 1 / launchd on macOS).

Only enabled when the launcher asks for it (`PORTFOLIO_PARENT_GUARD=1`, which the DSH
plugin sets), so a deliberate standalone `python3 run.py` is never surprised.
"""
import os
import threading
import time

ENV = "PORTFOLIO_PARENT_GUARD"


def enabled():
    return (os.environ.get(ENV) or "").strip() not in ("", "0")


def start(interval=3.0, getppid=None, on_orphan=None, log=print):
    """Watch the parent; return the thread (or None when disabled).

    `getppid` / `on_orphan` are injectable so the decision can be tested without
    actually losing a parent.
    """
    if not enabled():
        return None
    getppid = getppid or os.getppid
    on_orphan = on_orphan or (lambda: os._exit(0))
    try:
        original = getppid()
    except OSError:
        original = None          # cannot tell who started us: any later read counts

    def loop():
        while True:
            time.sleep(max(0.2, float(interval)))
            try:
                current = getppid()
            except OSError:
                current = 1
            if current != original:
                log("[parent] launcher is gone (ppid %s -> %s) — shutting down"
                    % (original, current))
                try:
                    on_orphan()
                except SystemExit:
                    raise
                return

    thread = threading.Thread(target=loop, name="parent-guard", daemon=True)
    thread.start()
    return thread
