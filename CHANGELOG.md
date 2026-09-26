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
- **CEX** — read-only keys for Binance, Bybit, Backpack, **OKX** and **Bitget**.
  OKX reads the trading *and* funding sub-accounts (deposits sit in funding, and
  the exchange's own total adds them up); Bitget sums the spot account with the
  real USDT/USDC/coin-margined futures accounts, and deliberately ignores the
  `S*` demo products, which answer with play money on a live key.
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
- **Your data can live outside the package.** Profiles (wallets, API keys, the
  snapshot database) default to `<package>/profiles`, which is the wrong place for an
  installed plugin: `dsh plugin add`/update replaces that directory, so a portfolio
  kept there would be lost on the next update. Set `dataDir` in the plugin config (or
  `PORTFOLIO_PROFILES_DIR`) and the data stays where you put it — the plugin also
  defaults to `$DSH_HOME/storages/crypto-portfolio` when it detects it is running from
  inside `node_modules`, instead of silently storing a portfolio in a cache directory.
- **Binance reads every sub-account, and says why when it cannot.** A refresh once
  reported a funded account as `$0` because Binance answered a signed request with
  HTTP 400 — the body said `-1021 Timestamp for this request is outside of the
  recvWindow` (a proxy held the request past the 5 s window). The query is now signed
  by hand so what is signed is what is sent, the error body is read instead of
  surfacing "400 Bad Request", one retry uses a fresh timestamp, and the window is
  60 s. Reading is also complete: spot (free **and** locked), Funding, Simple Earn
  (the underlying coin, with the `LDxxx` receipt that mirrors it de-duplicated), cross
  margin and USD-M futures are summed, and a key without Futures permission degrades
  to a note rather than an error row.
- **Every source has its own Test button.** Settings → Data sources probes one row at
  a time (each CEX account, DeBank, Etherscan, every BTC/DOGE/ADA/price/Hyperliquid
  provider, each Solana RPC, Birdeye, SPL prices) and prints the result where the key
  is typed — total and asset count for an exchange, chain count for DeBank, the
  provider's own wording when it refuses. Tolerated sub-accounts are shown as notes,
  so a missing permission is visible before a refresh depends on it.
- **A wallet that failed to update is impossible to miss.** The dashboard card gets an
  asterisk with the reason in its tooltip and the wallet panel title counts them
  ("Wallets (14) · 1 failed"); Settings shows the same wallet as a red-bordered row
  with the provider's message. Before this, a failed fetch simply read as "$0".
- **Page loads are ~50× faster.** Every path helper (`blacklist.json`, `labels.json`,
  `wallets.json`, …) resolved the active profile by opening and reading
  `profiles/.active` — ~85 µs per call, against ~1 µs for a bare stat — and a trend
  rebuild called it once per token row. The pointer is now cached against the file's
  (mtime, size) and invalidated by every profile mutation, which alone took
  `/api/current` from 360 ms to 56 ms and the history call from 5.8 s to 0.9 s.
- **The trend reads aggregates, not every snapshot.** `get_history` re-parsed all
  snapshots and re-filtered every token row on each page load, so its cost grew with
  the portfolio rather than with the number of days. A per-date `history_totals`
  table (written incrementally on refresh) is now the source, rebuilt once when
  something that rewrites history changes — a new snapshot, the blacklist, or the
  label rules. `/api/history` went from 5.8 s to **2 ms**, and the blacklist still
  retroactively rewrites past totals, which is what the old approach was protecting.
- **The first paint no longer waits for the trend.** The dashboard, wallet cards,
  donuts and health report render from the snapshot, and the trend arrives on its
  own; the date list comes from the tiny `/api/snapshots`. First wallet card:
  **7.5 s → 140 ms** (measured with `performance.mark` hooks, which now exist for
  exactly this kind of profiling).
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
- **Backpack reads both balance views.** The exchange UI's "US Dollar" row is USDC in
  the futures collateral account (`/api/v1/capital/collateral`, signed with
  `instruction=collateralQuery`), which the spot endpoint never mentions — so the
  largest position in a Backpack account was invisible. The two views are merged
  per asset with `max()` rather than summed, because a pledged spot balance is
  reported identically in both and summing would double count it.
- **Tokenised equities are priced.** Stocks such as `GOOGL.US` have no `*_USDC`
  ticker at all; their price comes from the collateral view's `assetMarkPrice`.
  A native asset whose on-chain price is unavailable now falls back to the
  exchange's own price instead of being reported as worth nothing.
- **Asset health report.** A panel directly above the token table grades the
  portfolio on the three questions a reviewer actually asks, one card each:
  **volatility risk** (💵 stablecoins · ₿ bitcoin · 🪙 everything else, scored on the
  third bucket), **concentration** (the largest single wallet, drawn as a gauge with
  both thresholds marked on it) and **storage security** (❄️ cold · 🔥 hot · 🏦
  exchange custody). Every row carries its balance *and* its share, and each failing
  check adds one plain sentence below the cards. Figures come from the
  blacklist-filtered snapshot, so they can never disagree with the totals above; the
  report is deliberately not filter-aware, because hiding the CEX wallets would
  change the maths. The maths lives in `tracker/health.py`.
- **The thresholds are yours to set.** Settings → *Health Thresholds* edits the
  warning/danger lines for all three checks (storage is inverted: its safe line sits
  above its warning line) and stores them per profile in `health.json`. They are
  validated on the way in — range, ordering, junk values — and a corrupt file falls
  back to the defaults rather than taking the report down. The volatility split is
  computed from the token labels, so your own label rules move it too. The hot/cold
  class follows the **live** wallet list rather than the value frozen into the
  snapshot: marking a wallet cold moves the panel immediately instead of at the next
  refresh (a wallet removed from the live list keeps the class its snapshots
  recorded).
- **Wallets know where their keys live.** Each wallet is *hot* or *cold* (Settings →
  Wallet Management, or on creation); exchange accounts are always exchange custody.
  Cold wallets are marked with a ❄ on their card. The class is stored with the
  snapshot, so a historical snapshot's health report reflects what was cold at the
  time rather than what is cold now.
- **Share card.** A *Share* button in the header opens a dialog with a live
  preview of a 1200×630 PNG — total, change vs the previous day, top five holdings
  (aggregated by symbol), the asset-label donut with its legend and the three health
  verdicts — plus **Download PNG**, **Copy image**, **Copy text** and share intents
  for **X / Facebook / WhatsApp / Telegram**. The image is drawn by hand on a canvas:
  no `html2canvas`, no CDN, and no address ever reaches it. The text is generated
  from the same figures, states nothing it cannot back up, and is editable before
  copying.
- **Author links + a tip jar in Settings.** The footer of the settings page carries
  the author's avatar, handle and social links (X / Discord / GitHub) plus a *Buy me a
  coffee* button that opens a small dialog with the **tip.md** badge and a **Binance
  Pay** QR. The badge is vendored as a local SVG rather than hot-linked, so the page
  still makes no outbound requests of its own.
- **Linkable pages.** `#pageSettings` opens the settings page and
  `#pageSettings/secWallets` opens that section, so a refresh stays where you were.
- **No silent failures on start.** A rejected `init()` used to leave a blank
  dashboard with nothing in the console; it is now logged and recorded on the page.
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
