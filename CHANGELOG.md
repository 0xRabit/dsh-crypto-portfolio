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
- Up to **five block explorers per wallet**: the provider this app reads from
  comes first, the rest follow in popularity order (BTC: bitaps → mempool.space →
  Blockstream → Blockchain.com → Blockchair; EVM: DeBank → Etherscan → Zerion →
  Blockscout → Blockchair; SOL: Jupiter → Solscan → Solana Explorer → SolanaFM →
  Birdeye; DOGE: 3; ADA: 4). CEX rows show the exchange mark, since an exchange
  account has no explorer page.
- One-click address copy on every wallet card.
- **Each wallet card is a fixed four-row stack** — name · balance (with that
  wallet's share of the total) · address + copy · type badge on the left and
  block-explorer icons on the right.
- **Layout tuned for wide screens**: the asset rail and the wallet grid sit at
  1:3 and are exactly equal in height — the figure and the donut spread down the
  rail's full height, both panels ending on the same line. The token table sits
  directly under the pie + wallet row so that clicking a wallet card visibly
  narrows the table below it.
- **Focusing a wallet never moves the page.** Clicking a card filters every panel
  in place; each panel below names the focused wallet in its own title, and the
  wallet panel says up front that the cards are clickable.
- The pie's clickable legend was dropped: it repeated figures already on the
  wallet cards, which are the click target for focusing a wallet.
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
