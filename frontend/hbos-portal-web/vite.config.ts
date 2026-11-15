import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'
import { cp, mkdir } from 'node:fs/promises'
import { resolve } from 'node:path'
import { fileURLToPath, URL } from 'node:url'

function localKnowledgePdfAssets() {
  let output: string
  return {
    name: 'hbos-knowledge-pdf-assets',
    apply: 'build' as const,
    configResolved(config: { root: string; build: { outDir: string } }) {
      output = resolve(config.root, config.build.outDir, 'pdfjs')
    },
    async closeBundle() {
      const source = fileURLToPath(new URL('./node_modules/pdfjs-dist/', import.meta.url))
      await mkdir(output, { recursive: true })
      await Promise.all(['cmaps', 'standard_fonts', 'wasm', 'LICENSE'].map(name =>
        cp(resolve(source, name), resolve(output, name), { recursive: true })))
    },
  }
}

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const dataMode = (env.VITE_PORTAL_DATA_MODE || 'mock').toLowerCase()
  const proxyTarget =
    env.VITE_FRAPPE_PROXY_TARGET ||
    (dataMode === 'frappe' ? 'http://127.0.0.1:8081' : '')

  return {
    base: env.VITE_BASE || '/',
    plugins: [vue(), localKnowledgePdfAssets()],
    resolve: {
      alias: {
        '@': fileURLToPath(new URL('./src', import.meta.url)),
      },
    },
    server: {
      host: '0.0.0.0',
      port: 5178,
      ...(proxyTarget
        ? {
            proxy: {
              '/api': {
                target: proxyTarget,
                changeOrigin: false,
              },
            },
          }
        : {}),
    },
  }
})
