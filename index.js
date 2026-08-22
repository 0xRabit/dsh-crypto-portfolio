// dsh-portfolio-tracker — DSH (Cordis) plugin wrapper.
//
// Starts the bundled Python portfolio tracker as a child process.
// On first run it seeds user-local config files from templates/ (public
// example addresses, empty API keys) — the package itself never contains
// private wallets or exchange secrets.
import { spawn } from 'node:child_process'
import { existsSync, mkdirSync, copyFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

export const name = 'dsh-portfolio-tracker'

const ROOT = dirname(fileURLToPath(import.meta.url))
const PYTHON = process.env.PORTFOLIO_PYTHON || 'python3'

function seedConfigs() {
  // seed the default profile (profiles/default) from the public templates
  const dir = join(ROOT, 'profiles', 'default')
  mkdirSync(dir, { recursive: true })
  for (const [tpl, dst] of [['portfolio_sources.json', 'sources.json'], ['portfolio_wallets.json', 'wallets.json']]) {
    const target = join(dir, dst)
    const src = join(ROOT, 'templates', tpl)
    if (!existsSync(target) && existsSync(src)) {
      try { copyFileSync(src, target); console.log(`[portfolio-tracker] seeded profiles/default/${dst} from templates`) } catch (e) { /* ignore */ }
    }
  }
}

export function apply(ctx) {
  const cfg = ctx.config || {}
  const port = cfg.port || Number(process.env.PORTFOLIO_PORT) || 8080
  const host = cfg.host || '127.0.0.1'

  seedConfigs()

  const child = spawn(PYTHON, [join(ROOT, 'run.py'), '--port', String(port), '--host', host], {
    cwd: ROOT,
    env: { ...process.env, PORTFOLIO_NO_BUILTIN_WALLETS: '1' },
    stdio: 'inherit',
  })

  console.log(`[portfolio-tracker] dashboard: http://${host}:${port} (first run: click Refresh)`)
  ctx.on('dispose', () => { child.kill('SIGTERM') })

  // Surface the URL as a runtime service value other plugins can read.
  ctx.set('portfolioTracker', { url: `http://${host}:${port}`, child }, true)
}
