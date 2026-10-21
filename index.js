// dsh-crypto-portfolio — DSH (Cordis) plugin wrapper.
//
// Starts the bundled Python portfolio tracker as a child process.
// On first run it seeds user-local config files from templates/ (public
// example addresses, empty API keys) — the package itself never contains
// private wallets or exchange secrets.
import { spawn } from 'node:child_process'
import { existsSync, mkdirSync, copyFileSync } from 'node:fs'
import { createConnection } from 'node:net'
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
/** Is nothing listening on host:port? A leaked server from an earlier run would
 *  hold the port, and the new child would exit on EADDRINUSE — the dashboard then
 *  keeps serving *old code* while this plugin looks loaded. Probe first instead. */
function portFree(host, port, timeout = 800) {
  return new Promise((resolve) => {
    const sock = createConnection({ host, port })
    let done = false
    const finish = (free) => {
      if (done) return
      done = true
      sock.destroy()
      resolve(free)
    }
    sock.once('connect', () => finish(false))
    sock.once('error', () => finish(true))
    setTimeout(() => finish(true), timeout)
  })
}

// Cordis hands the row's config to apply() as the SECOND argument. Reading it
// from `ctx.config` throws "cannot get property config without inject".
export function apply(ctx, config) {
  const cfg = config || {}
  const port = cfg.port || Number(process.env.PORTFOLIO_PORT) || 8080
  const host = cfg.host || '127.0.0.1'

  const dataDir = resolveDataDir(cfg)
  seedConfigs(dataDir)

  // A crashing server must not leave the plugin silently dead, and a busy port must
  // not leave it silently stale: both cases retry with a backoff and say so in the
  // log. After RETRIES the plugin stops trying — loudly — instead of spinning.
  const RETRIES = Number(process.env.PORTFOLIO_START_RETRIES || 12)
  const RETRY_MS = Number(process.env.PORTFOLIO_START_RETRY_MS || 5000)
  let child = null
  let stopped = false
  let busy = 0
  let crashes = 0

  const env = {
    ...process.env,
    PORTFOLIO_NO_BUILTIN_WALLETS: '1',
    PORTFOLIO_PROFILES_DIR: dataDir,
  }

  async function start() {
    if (stopped) return
    if (!(await portFree(host, port))) {
      busy += 1
      if (busy > RETRIES) {
        console.error(`[dsh-crypto-portfolio] port ${host}:${port} is still in use after ${RETRIES} tries — ` +
          'the dashboard is NOT running from this plugin. Stop whatever holds the port ' +
          `(lsof -nP -iTCP:${port} -sTCP:LISTEN) and restart DSH.`)
        return
      }
      console.warn(`[dsh-crypto-portfolio] port ${host}:${port} is busy ` +
        `(a server from an earlier run?); retry ${busy}/${RETRIES} in ${RETRY_MS / 1000}s`)
      setTimeout(start, RETRY_MS)
      return
    }
    busy = 0
    child = spawn(PYTHON, [join(ROOT, 'run.py'), '--port', String(port), '--host', host], {
      cwd: ROOT,
      env,
      stdio: 'inherit',
    })
    console.log(`[dsh-crypto-portfolio] dashboard: http://${host}:${port} (pid ${child.pid})`)
    console.log(`[dsh-crypto-portfolio] profiles: ${dataDir} (first run: click Refresh)`)
    // it stayed up long enough to be considered healthy: the crash counter resets
    const healthy = setTimeout(() => { crashes = 0 }, 20000)
    child.on('exit', (code, signal) => {
      clearTimeout(healthy)
      child = null
      if (stopped) return
      crashes += 1
      if (crashes > 5) {
        console.error(`[dsh-crypto-portfolio] the server exited ${crashes} times ` +
          `(last: code ${code}, signal ${signal}) — giving up. Fix the error above, then restart DSH.`)
        return
      }
      console.warn(`[dsh-crypto-portfolio] server exited (code ${code}, signal ${signal}); ` +
        `restarting (${crashes}/5)`)
      setTimeout(start, 3000)
    })
  }

  start()

  // The child is tied to this plugin's lifecycle: unloading the row stops it. Also
  // catch a plain process exit, which is how the child used to be leaked when the
  // app was quit without running dispose().
  const stop = () => {
    stopped = true
    if (child) {
      try { child.kill('SIGTERM') } catch (e) { /* ignore */ }
      child = null
    }
  }
  ctx.on('dispose', stop)
  for (const sig of ['SIGINT', 'SIGTERM', 'SIGHUP']) {
    process.on(sig, () => { stop(); process.exit(0) })
  }
  process.on('exit', stop)
}
