import { createRequire } from 'node:module'
import { fileURLToPath, pathToFileURL } from 'node:url'
import path from 'node:path'

const root = fileURLToPath(new URL('.', import.meta.url))
const repository = fileURLToPath(new URL('../../../../', import.meta.url))
const frontend = path.join(repository, 'frontend/hbos-portal-web')
const require = createRequire(path.join(frontend, 'package.json'))
const { default: vue } = await import(pathToFileURL(require.resolve('@vitejs/plugin-vue')).href)
const dependency = name => path.join(frontend, 'node_modules', name)

export default {
  root,
  envDir: root,
  cacheDir: '/private/tmp/hbos-portal-iam-preview-vite',
  plugins: [vue(), {
    name: 'permission-preview-no-backend',
    configureServer(server) {
      server.middlewares.use((req, res, next) => {
        if (/^\/(api|socket\.io|desk|login|logout)(\/|\?|$)/.test(req.url || '')) {
          res.statusCode = 403
          res.setHeader('Content-Type', 'application/json')
          res.end('{"error":"Design preview has no backend"}')
          return
        }
        next()
      })
    },
  }],
  resolve: {
    alias: {
      '@': path.join(frontend, 'src'),
      'vue': dependency('vue'),
      'vue-router': dependency('vue-router'),
      'pinia': dependency('pinia'),
      'ant-design-vue': dependency('ant-design-vue'),
      '@ant-design/icons-vue': dependency('@ant-design/icons-vue'),
    },
    dedupe: ['vue', 'vue-router', 'pinia'],
  },
  define: { 'import.meta.env.VITE_PORTAL_DATA_MODE': JSON.stringify('mock') },
  optimizeDeps: { include: ['vue', 'vue-router', 'pinia', 'ant-design-vue', '@ant-design/icons-vue'] },
  server: { host: '127.0.0.1', port: 5197, strictPort: true, fs: { allow: [repository] } },
  build: { outDir: '/private/tmp/hbos-portal-iam-preview-build', emptyOutDir: true },
}
