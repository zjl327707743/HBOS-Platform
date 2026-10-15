import { createApp } from 'vue'
import { createPinia } from 'pinia'
import { createRouter, createWebHistory } from 'vue-router'
import Antd from 'ant-design-vue'
import 'ant-design-vue/dist/reset.css'
import '@/theme/tokens.css'
import '@/styles/global.css'
import '@/theme/typography.css'
import App from '@/App.vue'
import { usePortalStore } from '@/stores/portal'
import PreviewLayout from './Portal预览布局.vue'
import PermissionPreview from './人员权限预览.vue'
import PreviewDestination from './预览入口说明.vue'

// 独立预览入口。没有导入或改动正式 router、guard、登录入口、API 代理。
const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', redirect: '/hbos/admin/people' },
    {
      path: '/hbos', component: PreviewLayout,
      children: [
        { path: 'admin/people', name: 'preview-people', component: PermissionPreview },
        { path: 'admin/roles', name: 'preview-roles', component: PermissionPreview },
        { path: ':pathMatch(.*)*', component: PreviewDestination },
      ],
    },
    { path: '/:pathMatch(.*)*', redirect: '/hbos/admin/people' },
  ],
  scrollBehavior: () => ({ top: 0 }),
})
router.afterEach(to => {
  document.title = `${to.path.endsWith('/roles') ? '权限管理' : '人员与权限'} · Portal 展示预览`
})

const app = createApp(App)
const pinia = createPinia()
app.use(pinia).use(router).use(Antd)
const portal = usePortalStore(pinia)
// 配置固定 mock；只载入已有合成目录，不读取 5178 的用户或身份。
await portal.bootstrap()
portal.user = {
  id: 'prototype-admin@example.invalid', displayName: '演示管理员', avatarText: '管',
  avatarUrl: null, identityProvider: 'frappe', roleLabel: '原型预览', department: '海滨药业',
}
portal.tasks = []
await router.isReady()
app.mount('#app')
