# dsh-crypto-portfolio

English | [中文](README.zh.md)

A free, 100% self-hosted [DeepSeek Harness](https://github.com/deepseek-ai/deepseek-harness) (DSH) plugin that unifies your **on-chain and CEX assets** into one self-contained web dashboard.

**Requires** `dsh` `0.1.1-rc.2` (Node `^22.19 || >=24`) · Python 3.9+ · `pip3 install requests pynacl`

```sh
dsh plugin --profile demo add dsh-crypto-portfolio   # npm
dsh --profile demo                                    # dashboard at http://127.0.0.1:8080
```

![Crypto Portfolio Tracker — every chain, every wallet, one self-hosted dashboard](assets/screenshot.png)

> Unofficial project, independently developed and maintained by community members.

---

## Why it exists / The pain points

I built it because the pain points are real.

### 1 · My money lives in seven places, and checking the total means opening six pages

EVM assets in DeBank, SOL and staking on-chain, BTC in a block explorer, plus Binance / Bybit / Backpack — each with its own app. Checking "how much do I actually have" meant hopping between six pages, and it was easy to miss a wallet along the way.

**This plugin puts all of it on a single screen.**

### 2 · Assets that block explorers can't see

Some money is genuinely invisible: native Solana stake accounts (`getParsedStakeAccounts` misses them), Hyperliquid L1 staked HYPE and spot balances, exchange earn/funding accounts. None of these are plain SPL/ERC-20 tokens, so ordinary tools never read them.

**This plugin digs them out and prices them into your total** — including the 12.1 SOL staked in the account above and the ~318 HYPE staked on Hyperliquid.

### 3 · Dust coins and phishing tokens inflate the numbers

DeBank lists plenty of fake tokens — ETHG, for example, is a **phishing token with a manipulated price** that once inflated one account by $570K.

**One-click blacklisting**: every token you blacklist is removed from totals, trends and historical snapshots instantly.

### 4 · "How much did I have last week?"

Without history there's no peace of mind.

**Every refresh saves the last snapshot of the day** (SQLite, deduplicated by day); over time it draws a trend line that is uniquely yours:

![Daily snapshots become trend charts](assets/flow.svg)

---

## What it does

- **A zero-dependency web dashboard, launched from a real DSH plugin.** No framework, no CDN — Python stdlib + vanilla JS.
- **Covers BTC / EVM / Solana / Dogecoin / Cardano / Hyperliquid L1 / CEX.** DeBank's 73 chains, BTC P2SH+P2TR, native Solana staking, Dogecoin (BlockCypher), Cardano (Koios, incl. stake addresses), Hyperliquid's official API (staked HYPE + spot + perp equity + vault equity), and read-only CEX keys (named `<exchange>_read`). Read-only CEX keys cover spot **and the futures collateral account**, including tokenised equities.
- **Global filters.** Category (BTC / EVM / Solana / Dogecoin / Cardano / CEX), wallet and chain dropdowns drive every panel — total, wallet-share pie, trend, chain distribution, token table.
- **Up to five block explorers per wallet.** Each wallet card ends in a row of explorer icons — the provider this app actually reads from comes first (DeBank · bitaps · Jupiter · Dogechain · Cardanoscan), then the other mainstream explorers in popularity order (Etherscan, mempool.space, Solscan, Blockchair, CExplorer, …). Dogecoin shows three and Cardano four, because that is how many credible explorers those chains have. CEX rows show the exchange mark instead, since an exchange account has no explorer page.
- **Free + paid data sources, clearly labeled.** EVM uses DeBank with two providers: paid `debank-pro` (badged "PAID", with a registration link) and free keyless `debank-public` fallback; CEX rows always show Binance/Bybit/Backpack with "get API key" links to each exchange. Each source displays when it last succeeded.
- **Automatic API failover.** Each source has several providers (prices: CoinGecko → Binance → Coinbase → OKX; BTC: blockchain.info → mempool.space; multiple Solana RPCs; Hyperliquid dual endpoints). A dead provider is skipped and the last working one is remembered.
- **Scheduled daily refresh.** Every profile can auto-refresh at a local time (server-side daemon; closing the browser page does not stop it); per-source last-success timestamps are shown in Settings.
- **Multi-profile configs.** The `default` profile ships with public template wallets (vitalik.eth, genesis BTC, public SOL, public DOGE, public ADA) and empty keys; each profile can be renamed — its snapshots move with it — and keeps its own daily refresh time; your private wallets and keys live in a separately named profile with its own snapshot history.
- **Local-first by default.** The API binds to `127.0.0.1` and masks API keys in its responses; writes are refused for cross-site requests (`Sec-Fetch-Site: cross-site`, foreign or opaque `Origin`, non-JSON bodies) and refresh is rate-limited to one run per minute. Snapshot history is kept as a 90-day window plus one per month, so the database does not grow without bound.
- **Asset labels.** A second donut breaks the portfolio down by asset label, and the system detects stablecoins / bitcoin / ether / SOL / HYPE on its own (bridged, wrapped and staked forms included). Every token table row carries a one-label control, and you can define your own labels in Settings — a custom label gets its own slice and colour, and your rules always beat the built-in wildcards.
- **Themes & i18n**: light/dark theme toggle, EN / 中文 (English by default), chain/exchange logos throughout.


Every box in the diagram is a real data pipeline:

![Architecture](assets/arch.svg)

## How it integrates with DSH

Not a wrapper — a real plugin:

- Declares a `dsh.bundle` manifest (`cordis.patch.yml`), so it installs with `dsh plugin add`.
- `apply(ctx)` hooks into the Cordis lifecycle: seeds user-local `profiles/default` from public templates on first run, spawns the dashboard as a child process, and stops it cleanly on `ctx.on('dispose')`.
- Exposes JSON APIs (`GET /api/refresh`, `/api/history`, `/api/tokens`, ...) that an agent can call directly, in addition to the web UI.

## Privacy (important)

This repository contains **no private keys, no private wallets, no balances** — `tracker/config.py` ships with `WALLETS = []` and empty keys. All private configs live in git-ignored local `profiles/`. Clone it, review it, run it with confidence.

## Install

### Requirements

- **`dsh` `0.1.1-rc.2`** (or a compatible release within the same pre-release line)
  and **Node `^22.19.0 || >=24.0.0`** — the range DSH itself declares.
- **Python 3.9+** with two pip packages:

  ```sh
  pip3 install requests pynacl
  ```

  These are ordinary runtime dependencies, not vendored, so `pip` can pick the
  build that matches your platform.

### From npm (recommended)

Installs prebuilt code and needs **no build permission**:

```sh
dsh plugin --profile demo add dsh-crypto-portfolio
dsh --profile demo
```

### From a tarball (offline / air-gapped)

```sh
pnpm pack                                    # produces dsh-crypto-portfolio-0.1.0.tgz
dsh plugin --profile demo add ./dsh-crypto-portfolio-0.1.0.tgz
```

### From GitHub

```sh
dsh plugin --profile demo add github:0xRabit/dsh-crypto-portfolio#<commit-sha>
```

This package is plain JavaScript + Python with **no build step**, so its
`prepare` is a no-op and pnpm does not need you to allowlist a build script —
unlike plugins that ship TypeScript sources. Pin a commit SHA anyway, so a
later push cannot change what runs on your machine.

### Verify the layer before booting

```sh
dsh --profile demo --dump-config      # look for: # == dsh-crypto-portfolio
```

If that line is missing, the bundle did not activate — the package installed as a
plain dependency instead. Re-run the `add` and check the warning it printed.

### Override the port

A patch replaces the whole `config` of a row, so restate every key you need.
Put this in `$DSH_HOME/profiles/demo/cordis.patch.yml`:

```yaml
- id: portfolio-tracker
  name: dsh-crypto-portfolio
  config:
    port: 8199
    host: 127.0.0.1
```

Or set `PORTFOLIO_PORT` in the environment.

### Standalone (no DSH)

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
