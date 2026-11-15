import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath } from 'node:url'
import { createReadStream } from 'node:fs'
import { stat } from 'node:fs/promises'
import { resolve } from 'node:path'
import { installFixture } from './fixture.mjs'

const root = fileURLToPath(new URL('../../', import.meta.url))

function servePdfAssets(server) {
  server.middlewares.use(async (req, res, next) => {
    const asset = /^\/pdfjs\/((?:cmaps|standard_fonts|wasm)\/[A-Za-z0-9_.-]+)$/.exec(req.url || '')?.[1]
    if (!asset) return next()
    const filename = resolve(root, 'node_modules/pdfjs-dist', asset)
    try {
      const file = await stat(filename)
      if (!file.isFile()) return next()
      res.setHeader('Content-Length', file.size)
      res.setHeader('Content-Type', filename.endsWith('.wasm') ? 'application/wasm' : 'application/octet-stream')
      createReadStream(filename).pipe(res)
    } catch {
      next()
    }
  })
}

export default defineConfig({
  root,
  envDir: false,
  mode: 'knowledge-preview',
  base: '/',
  define: {
    'import.meta.env.VITE_PORTAL_DATA_MODE': JSON.stringify('mock'),
    'import.meta.env.VITE_HBOS_CANONICAL_HOST': JSON.stringify(''),
  },
  plugins: [vue(), { name: 'knowledge-v17-fixture', apply: 'serve', configureServer(server) { installFixture(server); servePdfAssets(server) } }],
  resolve: {
    alias: [
      { find: '@/data/mockPortal', replacement: fileURLToPath(new URL('./portal.ts', import.meta.url)) },
      { find: '@', replacement: fileURLToPath(new URL('../../src', import.meta.url)) },
    ],
  },
  server: { host: '127.0.0.1', port: 18650, strictPort: true, hmr: false },
})
