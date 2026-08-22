#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Start the portfolio tracker web dashboard.

Usage:
    python3 run.py                 # http://127.0.0.1:8080
    python3 run.py --port 9000     # custom port
    python3 run.py --host 0.0.0.0  # expose on LAN
    python3 run.py --init-template # seed missing config files from templates/
                                   # (public example wallets, no private keys)
"""
import argparse
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from tracker.server import run  # noqa: E402
from tracker import profiles, sources  # noqa: E402


def init_template():
    """Ensure the default profile exists, seeded from templates/ (public
    example wallets, empty API keys). No private data involved."""
    profiles.ensure_profiles()
    print(f"[template] default profile ready (active: {profiles.active()})")


def main():
    ap = argparse.ArgumentParser(description="Crypto Portfolio Tracker")
    ap.add_argument("--port", type=int, default=8080)
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--profile", default=None,
                    help="start with a specific profile (see profiles/ dir)")
    ap.add_argument("--init-template", action="store_true",
                    help="seed the default profile from templates/ (public addresses, no keys)")
    args = ap.parse_args()
    if args.init_template:
        init_template()
    run(port=args.port, host=args.host, profile=args.profile)


if __name__ == "__main__":
    main()
