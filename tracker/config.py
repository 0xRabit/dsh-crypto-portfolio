# -*- coding: utf-8 -*-
"""Portfolio tracker configuration: wallets, API keys, settings."""

# DeBank Pro Open API key (EVM wallets)
DEBANK_API_KEY = ""

# Wallets to track. type: evm (DeBank), btc (public BTC APIs), sol (Solana public RPC)
WALLETS = []  # public deployments keep wallets in portfolio_wallets.json

# Token blacklist: phishing / fake tokens excluded from ALL stats and displays.
# Entry fields: token_id (合约/铸币地址), symbol, name (子串匹配), chain (可选限制链).
TOKEN_BLACKLIST = [
    {
        "token_id": "0x3fc29836e84e471a053d2d9e80494a867d670ead",
        "symbol": "ETHG",
        "name": "Ethereum Games",
        "note": "Phishing fake token (manipulated price) - blacklisted by user request",
    },
]

# Concurrency / timeouts
MAX_EVM_WORKERS = 6
REQUEST_TIMEOUT = 25
RETRIES = 2

# Snapshot storage
DB_PATH = None  # resolved relative to project root in storage.py

# Server
DEFAULT_PORT = 8080
