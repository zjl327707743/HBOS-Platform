import { defineConfig } from 'vitest/config'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath, URL } from 'node:url'
import { realpathSync } from 'node:fs'

export default defineConfig({
  plugins: [vue()],
  resolve: { alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) } },
  // Worktrees may resolve installed packages through a shared node_modules
  // symlink. Vite must read the real worker asset, with no access to unrelated
  // host directories. This keeps the actual pdf.js worker URL in reader tests.
  server: { fs: { allow: [fileURLToPath(new URL('.', import.meta.url)),
    realpathSync(fileURLToPath(new URL('./node_modules', import.meta.url)))] } },
  test: { environment: 'jsdom', setupFiles: ['./tests/setup.ts'], clearMocks: true },
})
