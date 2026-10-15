import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath, URL } from 'node:url'
import { validatePortalBuildMode } from './src/contracts/dataMode'

export default defineConfig(({ mode, command }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const dataMode = validatePortalBuildMode(env.VITE_PORTAL_DATA_MODE, command, mode)
  const proxyTarget =
    env.VITE_FRAPPE_PROXY_TARGET ||
    (dataMode === 'frappe' ? 'http://127.0.0.1:8080' : '')
  const frappeAppOrigin = env.VITE_FRAPPE_APP_ORIGIN
    || (command === 'serve' && dataMode === 'frappe' ? proxyTarget : '')

  return {
    base: env.VITE_BASE || '/',
    define: {
      'import.meta.env.VITE_FRAPPE_APP_ORIGIN': JSON.stringify(frappeAppOrigin),
    },
    plugins: [vue()],
    resolve: {
      alias: {
        '@': fileURLToPath(new URL('./src', import.meta.url)),
      },
    },
    server: {
      host: '0.0.0.0',
      port: dataMode === 'frappe' ? 5178 : 5193,
      strictPort: true,
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
    build: {
      rollupOptions: {
        output: {
          manualChunks: {
            vue: ['vue', 'vue-router', 'pinia'],
            ant: ['ant-design-vue', '@ant-design/icons-vue'],
            http: ['axios'],
          },
        },
      },
    },
  }
})
