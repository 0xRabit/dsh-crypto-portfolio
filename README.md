# dsh-crypto-portfolio

Crypto portfolio tracker as a [DeepSeek Harness](https://github.com/deepseek-ai/deepseek-harness) (DSH) plugin.

Tracks wallets across **BTC / EVM / Solana / Hyperliquid L1 / CEX (Binance · Bybit · Backpack)** with
multi-provider API failover, per-day snapshots and trend charts — a self-contained web dashboard
launched from a Cordis plugin.

## Features

- **Wallets**: BTC (P2SH/P2TR), EVM (DeBank, all chains), Solana (public RPC: SOL + SPL + native staked SOL),
  Hyperliquid L1 (official API: staked HYPE + spot), CEX accounts (read-only keys, named `<exchange>_read`).
- **Configurable sources**: all API URLs/keys live in per-profile JSON configs (`profiles/<name>/`).
  Each source supports multiple providers with **automatic failover** (last working provider is remembered).
- **Multi-profile**: each named profile has its own sources, wallets, blacklist and snapshot history.
  The `default` profile ships with public example wallets (vitalik.eth, genesis BTC, public SOL) and empty keys.
- **Dashboard**: global filters (category BTC/EVM/Solana/CEX, wallet, chain), wallet-share pie chart,
  per-day trend chart, chain distribution, token table with one-click blacklist, i18n (EN/中文, default EN).
- **Snapshots**: every refresh saves the last result of the day (SQLite); history builds trend charts.

## Privacy

This package contains **no private wallets, API keys or balances**. Private configs are user-local
(`profiles/<name>/`, git-ignored) and never part of this repository. The plugin seeds `profiles/default`
from `templates/` (public addresses, empty keys) on first run.

## Install

Requirements: Python 3.9+ (`requests`; `pynacl` is bundled in `vendor/`).

```sh
# from a DSH source checkout
dsh plugin --profile demo add /path/to/dsh-crypto-portfolio
dsh --profile demo
# dashboard at http://127.0.0.1:8080 (PORTFOLIO_PORT to override)
```

Or run standalone (no DSH):

```sh
python3 run.py --init-template --port 8080   # seeds profiles/default from public templates
```

## Layout

```
profiles/default/   sources.json + wallets.json (public template, auto-seeded)
templates/          public example configs (no secrets)
tracker/            backend fetchers (debank/btc/solana/hyperliquid/cex/prices)
static/             web dashboard (vanilla JS, no external deps)
run.py / fetch.py   web server / CLI snapshot
```

## License

MIT — see [LICENSE](LICENSE).
