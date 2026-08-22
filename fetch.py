#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""One-shot CLI: fetch all wallets and save today's snapshot (no web server).

Useful for cron / launchd daily snapshots:
    0 9 * * * cd /path/to/crypto-portfolio-tracker && /usr/bin/python3 fetch.py >> fetch.log 2>&1

Usage:
    python3 fetch.py            # fetch + save + print summary
    python3 fetch.py --quiet    # only print total
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from tracker import portfolio, profiles, sources, storage  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description="Fetch portfolio and save daily snapshot")
    ap.add_argument("--quiet", action="store_true")
    ap.add_argument("--profile", default=None, help="profile name to fetch")
    args = ap.parse_args()

    profiles.ensure_profiles()
    if args.profile:
        profiles.set_active(args.profile)
    sources.ensure_file()
    storage.init_db()
    data, prev = portfolio.refresh_snapshot()

    if args.quiet:
        print(json.dumps({"date": data["date"], "total_usd": data["total_usd"]}))
        return

    print(f"Snapshot date: {data['date']}")
    print(f"Total assets: ${data['total_usd']:,.2f}")
    if prev:
        delta = data["total_usd"] - prev["total_usd"]
        pct = delta / prev["total_usd"] * 100 if prev["total_usd"] else 0
        print(f"vs previous ({prev['date']}): {delta:+,.2f} ({pct:+.2f}%)")
    print("--- wallets ---")
    for w in data["wallets"]:
        print(f"  {w['wallet']:<18} ${w['total_usd']:>14,.2f}  ({len(w['tokens'])} 项)")
    by_chain = sorted(data["by_chain"].items(), key=lambda kv: -kv[1])
    if by_chain:
        print("--- chains ---")
        for c, v in by_chain:
            print(f"  {c:<10} ${v:>14,.2f}")


if __name__ == "__main__":
    main()
