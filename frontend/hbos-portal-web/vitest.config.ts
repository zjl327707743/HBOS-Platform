import { defineConfig } from 'vitest/config'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath, URL } from 'node:url'

export default defineConfig({
  plugins: [vue()],
  resolve: { alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) } },
  test: {
    environment: 'jsdom',
    setupFiles: ['./tests/setup.ts'],
    clearMocks: true,
    // 本地 node --test 用例（*.test.mjs）由 npm run test:unit 运行，不进入 vitest。
    include: ['tests/**/*.test.ts'],
    env: { VITE_PORTAL_DATA_MODE: 'frappe' },
  },
})
