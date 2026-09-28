import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath, URL } from 'node:url'

// Frappe 拥有的路径前缀。其余路径留在 Portal SPA 内。
// 必须收敛到同一来源：Frappe 发 X-Frame-Options: SAMEORIGIN，
// 只有浏览器可见来源完全一致时 iframe 才被允许加载。
const FRAPPE_PATHS = [
  '/api',
  '/app',
  '/desk',
  '/assets',
  '/files',
  '/private',
  '/login',
  '/logout',
  '/method',
  '/printview',
  '/socket.io',
  '/favicon.ico',
]

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const proxyTarget = env.VITE_FRAPPE_PROXY_TARGET || 'http://127.0.0.1:8080'
  const proxy = Object.fromEntries(
    FRAPPE_PATHS.map((path) => [
      path,
      { target: proxyTarget, changeOrigin: true },
    ]),
  )

  return {
    // R4 生产形态必须设 VITE_BASE=/hbos/，否则 Vite 产物 dist/assets/
    // 会与 Frappe 的 /assets/ 撞路径。
    base: env.VITE_BASE || '/',
    plugins: [vue()],
    resolve: {
      alias: {
        '@': fileURLToPath(new URL('./src', import.meta.url)),
      },
    },
    server: {
      host: '0.0.0.0',
      port: 5178,
      proxy,
    },
  }
})
