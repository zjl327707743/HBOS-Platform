import { createApp } from 'vue'
import { createPinia } from 'pinia'
import Antd from 'ant-design-vue'
import 'ant-design-vue/dist/reset.css'
import './theme/tokens.css'
import './styles/global.css'
import './theme/typography.css'
import App from './App.vue'
import router from './router'

const canonicalHost = String(import.meta.env.VITE_HBOS_CANONICAL_HOST || '').trim()
const localAliases = new Set(['127.0.0.1', 'localhost'])

if (
  canonicalHost &&
  /^[a-z0-9.-]+$/i.test(canonicalHost) &&
  window.location.hostname !== canonicalHost &&
  localAliases.has(window.location.hostname)
) {
  const port = window.location.port ? `:${window.location.port}` : ''
  window.location.replace(
    `${window.location.protocol}//${canonicalHost}${port}${window.location.pathname}${window.location.search}${window.location.hash}`,
  )
} else {
  createApp(App)
    .use(createPinia())
    .use(router)
    .use(Antd)
    .mount('#app')
}
