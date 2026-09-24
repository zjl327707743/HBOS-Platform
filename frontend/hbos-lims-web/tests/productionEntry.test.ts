import assert from 'node:assert/strict'
import test from 'node:test'
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, resolve } from 'node:path'

const here = dirname(fileURLToPath(import.meta.url))
const root = resolve(here, '..')

test('production build separates static asset base from router base', () => {
  const pkg = JSON.parse(readFileSync(resolve(root, 'package.json'), 'utf8'))
  assert.match(pkg.scripts['build:prod'], /VITE_BASE=\/assets\/hb_lims_app\/hbos-lims\//)
  assert.match(pkg.scripts['build:prod'], /VITE_ROUTER_BASE=\/hbos-lims\//)

  const router = readFileSync(resolve(root, 'src/router/index.ts'), 'utf8')
  assert.match(router, /VITE_ROUTER_BASE/)
  assert.match(router, /createWebHistory\(routerBase\)/)

  const vite = readFileSync(resolve(root, 'vite.config.ts'), 'utf8')
  assert.match(vite, /manifest:\s*true/)
})
