# -*- coding: utf-8 -*-
"""Portfolio tracker configuration: wallets, API keys, settings."""

# DeBank Pro Open API key (EVM wallets)
DEBANK_API_KEY = ""

# Wallets to track. type: evm (DeBank), btc (public BTC APIs), sol (Solana public RPC)
WALLETS = []  # public deployments keep wallets in portfolio_wallets.json

# Token blacklist: phishing / fake tokens excluded from ALL stats and displays.
# Entry fields: token_id (合约/铸币地址), symbol, name (子串匹配), chain (可选限制链).
# Asset-type classification (the "asset type" donut). Glob patterns matched
# case-insensitively against the token symbol, plus a price band so pegged assets
# with unfamiliar tickers are still caught. Edit these, or add/remove rules from
# the dashboard (profiles/<name>/stablecoins.json).
STABLECOIN_SYMBOLS = [
    # dollar-pegged majors and their bridged/wrapped forms
    "USDT*", "USDC*", "*USDT", "*USDC", "USDT.E", "USDC.E", "USDBC", "USDTB",
    "BUSD*", "TUSD*", "FDUSD*", "PYUSD*", "USDD*", "USDE", "SUSDE", "USDS*",
    "GUSD*", "LUSD*", "SUSD*", "CRVUSD*", "ALUSD*", "CUSD*", "VAI*", "DOLA*",
    "DAI", "DAI.E", "MIM*", "FRAX*", "USDP*", "USDL*", "USDX*", "USD1*", "ZUSD*",
    # price-band auto-detection looks for these markers in symbol or name
    "*USD*",
]
STABLECOIN_PRICE_BAND = (0.95, 1.05)   # a $1 peg must actually trade near $1
BITCOIN_SYMBOLS = [
    "BTC", "WBTC*", "*BTC", "TBTC*", "CBBTC*", "LBTC*", "SBTC*", "RENBTC*",
    "BTCB*", "RBTC*", "CLBTC*", "SOLVBTC*", "BTC.B", "BTC.E",
]
ETHEREUM_SYMBOLS = [
    "ETH", "WETH*", "*ETH", "ETHX*", "CBETH*", "RETH*", "SETH*", "ETH.E",
]
SOLANA_SYMBOLS = [
    "SOL", "WSOL*", "*SOL", "SOL.E", "JUPSOL*", "JITOSOL*", "MSOL*", "BSOL*",
    "HSOL*", "STSOL*", "INF",
]
HYPE_SYMBOLS = [
    "HYPE", "WHYPE*", "*HYPE", "KHYPE*", "STHYPE*",
]

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
