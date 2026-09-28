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
      {
        target: proxyTarget,
        changeOrigin: true,
        // 仅 socket.io 需要转发 WebSocket 升级。Vite 只在 opts.ws 为真
        // （或 target 以 ws:// / wss:// 开头）时才安装 upgrade 处理器
        // （vite/dist/node/chunks/config.js 实测），否则该条目只管
        // HTTP 长轮询、不发升级请求——即「看着支持实时、实际不发」。
        ...(path === '/socket.io' ? { ws: true } : {}),
      },
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
