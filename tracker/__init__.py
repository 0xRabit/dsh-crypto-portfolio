# -*- coding: utf-8 -*-
"""Crypto portfolio tracker: multi-wallet (EVM/BTC/Solana/CEX) USD portfolio
with daily snapshots."""
import os
import sys

# vendored dependencies (pynacl for Backpack Ed25519 signing)
_vendor = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "vendor")
if os.path.isdir(_vendor) and _vendor not in sys.path:
    sys.path.insert(0, _vendor)
