# dsh-portfolio-tracker

Crypto portfolio tracker (BTC / EVM / Solana / Hyperliquid L1 / CEX Binance-Bybit-Backpack)
packaged as a DSH (Cordis) plugin.

**Privacy**: this package contains NO private wallets, API keys or balances.
`tracker/config.py` ships with an empty wallet list; `portfolio_sources.json` /
`portfolio_wallets.json` are seeded on first run from `templates/` (public
example addresses, empty keys). Your personal configs stay in user-local JSON
files that are excluded from the published bundle.

## Requirements

- Python 3.9+ with `requests` (`pip3 install -r requirements.txt`); `pynacl`
  is bundled in `vendor/`.
- DSH CLI (`dsh`) for plugin installation.

## Local test (without DSH)

```sh
cd dist/dsh-portfolio-tracker
python3 run.py --init-template --port 8090   # seeds public template configs
# open http://127.0.0.1:8090
```

## Install as a DSH plugin

```sh
# from a source checkout: pnpm dsh plugin --profile demo add ./dist/dsh-portfolio-tracker
dsh plugin --profile demo add ./dist/dsh-portfolio-tracker
dsh --profile demo
```

The dashboard runs at http://127.0.0.1:8080 (override with
`PORTFOLIO_PORT` env or the plugin `config.port`).

## Publish

No GitHub account is required — DSH bundles are npm packages:

```sh
cd dist/dsh-portfolio-tracker
npm publish          # needs an npm account; publish to npmjs or a private registry
# or keep it local/private: dsh plugin --profile demo add <path> works without any publish
```

The `dsh.bundle` manifest + `cordis.patch.yml` make `dsh plugin add` register
the plugin automatically. See DSH docs: `docs/user/develop/basic/publish.md`.
