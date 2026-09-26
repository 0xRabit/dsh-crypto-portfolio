// dsh-crypto-portfolio — DSH (Cordis) plugin wrapper.
//
// Starts the bundled Python portfolio tracker as a child process.
// On first run it seeds user-local config files from templates/ (public
// example addresses, empty API keys) — the package itself never contains
// private wallets or exchange secrets.
import { spawn } from 'node:child_process'
import { existsSync, mkdirSync, copyFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

export const name = 'dsh-crypto-portfolio'

const ROOT = dirname(fileURLToPath(import.meta.url))
const PYTHON = process.env.PORTFOLIO_PYTHON || 'python3'

/** Where the profiles (wallets, keys, snapshot DB) live.
 *
 * Inside the package by default, but an installed plugin MUST keep them outside:
 * `dsh plugin add`/update runs pnpm, which replaces the package directory — data
 * kept there is gone after an update. So when this file sits under node_modules and
 * no directory was configured, fall back to the DSH home instead of silently
 * storing a user's portfolio in a cache directory.
 */
function resolveDataDir(config) {
  const configured = (config && config.dataDir) || process.env.PORTFOLIO_PROFILES_DIR
  if (configured) return configured.replace(/^~(?=\/)/, process.env.HOME || '~')
  if (ROOT.includes(`${'node_modules'}`)) {
    const home = process.env.DSH_HOME || join(process.env.HOME || '.', '.dsh')
    return join(home, 'storages', 'crypto-portfolio')
  }
  return join(ROOT, 'profiles')
}

function seedConfigs(dataDir) {
  // seed the default profile (<dataDir>/default) from the public templates
  const dir = join(dataDir, 'default')
  mkdirSync(dir, { recursive: true })
  for (const [tpl, dst] of [['portfolio_sources.json', 'sources.json'], ['portfolio_wallets.json', 'wallets.json']]) {
    const target = join(dir, dst)
    const src = join(ROOT, 'templates', tpl)
    if (!existsSync(target) && existsSync(src)) {
      try { copyFileSync(src, target); console.log(`[dsh-crypto-portfolio] seeded profiles/default/${dst} from templates`) } catch (e) { /* ignore */ }
    }
  }
}

// Cordis hands the row's config to apply() as the SECOND argument. Reading it
// from `ctx.config` throws "cannot get property config without inject".
export function apply(ctx, config) {
  const cfg = config || {}
  const port = cfg.port || Number(process.env.PORTFOLIO_PORT) || 8080
  const host = cfg.host || '127.0.0.1'

  const dataDir = resolveDataDir(cfg)
  seedConfigs(dataDir)

  const child = spawn(PYTHON, [join(ROOT, 'run.py'), '--port', String(port), '--host', host], {
    cwd: ROOT,
    env: {
      ...process.env,
      PORTFOLIO_NO_BUILTIN_WALLETS: '1',
      PORTFOLIO_PROFILES_DIR: dataDir,
    },
    stdio: 'inherit',
  })

  console.log(`[dsh-crypto-portfolio] dashboard: http://${host}:${port}`)
  console.log(`[dsh-crypto-portfolio] profiles: ${dataDir} (first run: click Refresh)`)
  // The child is tied to this plugin's lifecycle: unloading the row stops it.
  ctx.on('dispose', () => { child.kill('SIGTERM') })
}
