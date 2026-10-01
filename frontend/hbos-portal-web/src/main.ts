import { createApp } from 'vue'
import { createPinia } from 'pinia'
import Antd from 'ant-design-vue'
import 'ant-design-vue/dist/reset.css'
import './theme/tokens.css'
import './styles/global.css'
import './theme/typography.css'
import App from './App.vue'
import router from './router'
import { clearCachedCsrfToken, setUnauthorizedHandler } from './services/frappeClient'
import { usePortalStore } from './stores/portal'

const app = createApp(App)
const pinia = createPinia()

app.use(pinia)
app.use(router)
app.use(Antd)

// 会话中途失效（cookie 过期等）：同步 store 状态并回到登录页，带上原目标地址。
setUnauthorizedHandler(() => {
  const portal = usePortalStore(pinia)
  clearCachedCsrfToken()
  portal.markSignedOut()

  const current = router.currentRoute.value
  if (current.name === 'login') return
  void router.replace({ name: 'login', query: { redirect: current.fullPath } })
})

app.mount('#app')
