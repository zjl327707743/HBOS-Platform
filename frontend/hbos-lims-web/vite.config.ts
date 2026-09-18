import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath, URL } from 'node:url'

// 生产部署挂载路径（Frappe Nginx 下 /hbos-lims 目录）
// 开发时保持 base=/，生产构建用 `npm run build:prod` 设置 /hbos-lims/
const base = process.env.VITE_BASE || '/'

// https://vite.dev/config/
export default defineConfig({
  base,
  plugins: [vue()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  server: {
    host: '0.0.0.0',
    port: 5173,
    proxy: {
      // 同域部署：开发时代理到 Frappe 后端（frontend 容器 8080）
      '/api': {
        target: 'http://localhost:8080',
        changeOrigin: true,
      },
      '/assets': {
        target: 'http://localhost:8080',
        changeOrigin: true,
      },
      '/app': {
        target: 'http://localhost:8080',
        changeOrigin: true,
      },
      // 标签打印走 Frappe 打印视图（生产同源天然可用，开发需代理）
      '/printview': {
        target: 'http://localhost:8080',
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: 'dist',
    assetsDir: 'assets',
    sourcemap: false,
  },
})
