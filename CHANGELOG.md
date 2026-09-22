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
- **Security hardening.** `GET /api/sources` masks API keys by default (a stub like
  `cdd7…88e1`) and reveals them only on an explicit request, so a local process, a
  log dump or a screenshot no longer exposes them; a save from the settings form is
  merged against the stored config so a mask can never overwrite a live key. Writes
  (including refresh) are fenced against cross-site requests — non-JSON bodies are
  refused with 415 and cross-site / foreign / opaque origins with 403 — and refresh
  is rate-limited to one run per minute.
- **Snapshot retention.** A profile keeps a dense 90-day window plus one snapshot per
  month for the tail (`PORTFOLIO_KEEP_DAILY_DAYS` / `PORTFOLIO_KEEP_MONTHLY`), instead
  of growing by ~0.75 MB/day forever.
- **Performance.** The token table renders in pages of 200 with a "show more" row, so
  turning off "Hide USD≈0" no longer pushes ~1.4k rows into the DOM at once.
- **Accessibility.** Wallet cards are real controls (`role="button"`, tabindex,
  Enter/Space, visible focus ring), both charts carry live `aria-label` text
  alternatives, and `prefers-reduced-motion` is honoured.
- **Interaction.** Refresh can be cancelled mid-run (nothing is written), the filter
  choice persists across reloads, the newest snapshot is marked in the date picker
  and viewing history is called out.
- **Asset labels + "asset type" donut.** A second donut in the asset rail breaks the
  portfolio down by label, stacked under the wallet-share donut. The system detects
  **stable / btc / eth / sol / hype** on its own (including bridged, wrapped and
  staked forms), and anything it cannot place is `other`.
- **Labels are yours to define.** Every row of the token table carries a single-select
  label control — one label per row, by construction — and the Settings panel lets you
  add rules with your *own* label names (they get their own slice, colour and legend
  entry, exactly like a built-in one). Matching uses symbol globs plus a name/token/chain
  filter; stablecoins additionally use a price band so a pegged asset under an unfamiliar
  ticker is caught while depegged assets and $0 tokens named after a stablecoin are not.
  Your own rules always take precedence over the built-in wildcards.
- **Create and rename labels where you use them.** The row control is a tag
  picker: type to filter, Enter or click to apply, and a *Create "…"* entry
  appears for any name that does not exist yet. Each entry can be renamed
  inline — a user label has its rules rewritten, a built-in keeps its id and
  takes a display name, so detection never breaks. Settings lists every label
  with its rule count, and lets user labels be deleted (built-ins cannot).

- **Renamed for accuracy**: the Settings section is now *Asset Label Rules*
  (was *Stablecoin Rules*), because it governs every label, not just
  stablecoins. The rule file moved to `asset_labels.json` and the module to
  `tracker/assetlabels.py`; the old `stablecoins.json` is migrated on first
  read, so existing rules carry over untouched.

- **Crash-safe config writes.** Every JSON config file is now written to a sibling
  temp file, fsynced, then `os.replace`d into position (`tracker/atomicio.py`), so an
  interrupted write can no longer leave a truncated `sources.json` or an empty
  `.active` pointing at the wrong profile. New files are created mode 0600.
- **Locks on the shared config.** `profiles`, `schedule` and `status` were the three
  modules doing unguarded read-modify-write while both the HTTP threads and the
  scheduler thread touched the same files; a lost update could drop source
  timestamps or a schedule edit. They now take a lock like the rest.
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
