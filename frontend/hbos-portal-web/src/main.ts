import { createApp } from 'vue'
import { createPinia } from 'pinia'
import { antdComponents } from './components/antdComponents'
import 'ant-design-vue/dist/reset.css'
import './theme/tokens.css'
import './styles/global.css'
import './theme/typography.css'
import App from './App.vue'
import router from './router'
import { clearCachedCsrfToken, setUnauthorizedHandler } from './services/frappeClient'
import { usePortalStore } from './stores/portal'

const canonicalHost = String(import.meta.env.VITE_HBOS_CANONICAL_HOST || '').trim()
const localAliases = new Set(['127.0.0.1', 'localhost'])

if (
  canonicalHost
  && /^[a-z0-9.-]+$/i.test(canonicalHost)
  && window.location.hostname !== canonicalHost
  && localAliases.has(window.location.hostname)
) {
  const port = window.location.port ? `:${window.location.port}` : ''
  window.location.replace(
    `${window.location.protocol}//${canonicalHost}${port}${window.location.pathname}${window.location.search}${window.location.hash}`,
  )
} else {
  const app = createApp(App)
  const pinia = createPinia()

  app.use(pinia)
  app.use(router)
  for (const component of antdComponents) app.use(component)

  // 会话中途失效（cookie 过期等）：同步 store 状态并回到登录页，带上原目标地址。
  setUnauthorizedHandler(() => {
    const portal = usePortalStore(pinia)
    clearCachedCsrfToken()
    portal.markSignedOut()

    const current = router.currentRoute.value
    if (current.name === 'feishu-login') return
    void router.replace({ path: '/hbos/login', query: { redirect_to: current.fullPath } })
  })

  app.mount('#app')
}
