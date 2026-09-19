# -*- coding: utf-8 -*-
"""Crypto portfolio tracker: multi-wallet (EVM/BTC/Solana/CEX) USD portfolio
with daily snapshots."""
import os
import sys

# Optional local fallback libraries (pynacl for Backpack Ed25519 signing).
#
# APPENDED, never prepended: a vendor directory must never shadow the packages
# the user actually installed. The published bundle ships no vendor/ at all and
# declares pynacl in requirements.txt, so a normal `pip install -r
# requirements.txt` provides the platform-correct wheel. A vendor directory is
# only consulted when nothing else can satisfy the import — and because it is
# last, it cannot break a correct install on another platform.
_vendor = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "vendor")
if os.path.isdir(_vendor) and _vendor not in sys.path:
    sys.path.append(_vendor)
