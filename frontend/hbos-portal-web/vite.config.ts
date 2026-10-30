import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath, URL } from 'node:url'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const dataMode = (env.VITE_PORTAL_DATA_MODE || 'mock').toLowerCase()
  const proxyTarget =
    env.VITE_FRAPPE_PROXY_TARGET ||
    (dataMode === 'frappe' ? 'http://127.0.0.1:8081' : '')

  return {
    base: env.VITE_BASE || '/',
    plugins: [vue()],
    resolve: {
      alias: {
        '@': fileURLToPath(new URL('./src', import.meta.url)),
      },
    },
    build: {
      // 主包曾到 1.97 MB（gzip 609 kB），Vite 一直在警告。
      // 拆成三类独立 vendor：它们的更新频率完全不同，
      // 拆开之后业务代码改动不会再让用户重下 antd/three。
      rollupOptions: {
        output: {
          manualChunks(id: string) {
            if (!id.includes('node_modules')) return undefined
            // three 只在 Twin 页用，且它自己就 679 kB —— 单独一块，别拖累首屏
            if (id.includes('/three/')) return 'vendor-three'
            // antd + 图标 + 它的底层依赖放进**同一块**。
            //
            // 早先把 `@ant-design/icons` 单独拆出来，结果 rollup 报
            //   Circular chunk: vendor-icons -> vendor-antd -> vendor-icons
            // —— 图标与组件库互相引用，拆开反而制造循环依赖。
            if (
              id.includes('ant-design-vue')
              || id.includes('@ant-design/')
              || id.includes('/rc-')
            ) {
              return 'vendor-antd'
            }
            if (id.includes('/vue/') || id.includes('vue-router') || id.includes('/pinia/')) {
              return 'vendor-vue'
            }
            return 'vendor'
          },
        },
      },
      // 门槛设到 700 kB：拆完还剩两块超标的（three 只在 Twin 页按需加载，
      // vendor-antd 是组件库本体，再拆只会增加请求数）。留一点余量让真正的
      // 意外增长（比如有人把整个库重新全量引入）还能报警。
      chunkSizeWarningLimit: 700,
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
