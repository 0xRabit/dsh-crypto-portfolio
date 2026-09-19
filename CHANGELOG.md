# Changelog

All notable changes to this project are documented here.
This project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] — 2026-09-19

First public release.

### Supported sources

- **Bitcoin** — P2SH / P2TR addresses via public APIs (blockchain.info, mempool.space).
- **EVM** — every chain DeBank indexes (73 chains, ERC-20 and friends); optional
  Hyperliquid L1 balances (staked HYPE, spot, perp equity, leader-vault equity).
- **Solana** — native SOL, native stake accounts, and SPL tokens.
- **Dogecoin** — via BlockCypher (no API key required).
- **Cardano** — via Koios (no API key required); payment addresses and stake addresses.
- **CEX** — read-only keys for Binance, Bybit and Backpack.
- **Prices** — CoinGecko → Binance → Coinbase → OKX, with automatic failover.

### Dashboard

- Single-page dashboard with no framework and no CDN (Python stdlib + vanilla JS).
- Global filters (category / wallet / chain) driving total, pie, trend, chain
  distribution and the token table together.
- Per-wallet history pages on the matching block explorer, one-click address copy.
- Light and dark themes; English and 中文.
- Token blacklist with one-click blocking of phishing tokens.

### Configuration

- Independent profiles, each with its own sources, wallets, blacklist, snapshot
  history and daily auto-refresh time.
- Profiles can be renamed; snapshots move with the directory.
- Configurable data sources with multi-provider failover and per-source last-ok status.
- Config export / import.

### Notes

- Requires Python 3.9+ and `pip install -r requirements.txt`.
- No private keys, wallets or balances are shipped in this package; the default
  profile is seeded from public example addresses with empty API keys.
