import { createRouter, createWebHistory } from 'vue-router'
import PortalLayout from '@/components/layout/PortalLayout.vue'
import LimsLayout from '@/components/layout/LimsLayout.vue'
import PortalHome from '@/views/PortalHome.vue'
import MyWorkView from '@/views/MyWorkView.vue'
import AppCenterView from '@/views/AppCenterView.vue'
import ProfileSettingsView from '@/views/ProfileSettingsView.vue'
import BusinessEmbedView from '@/views/BusinessEmbedView.vue'
import ForbiddenView from '@/views/ForbiddenView.vue'
import NotFoundView from '@/views/NotFoundView.vue'
import LimsHomeView from '@/views/LimsHomeView.vue'
import LimsResultReviewView from '@/views/LimsResultReviewView.vue'

const router = createRouter({
  // 路由表本身已写死 `/hbos` 前缀，故 history base 固定为 `/`。
  // 不能用 import.meta.env.BASE_URL：生产构建的 VITE_BASE=/hbos/ 只用于让资源
  // 落在 /hbos/assets/（避开 Frappe 的 /assets），若把它同时当作 base，
  // 路径会被拼两次，首页变成 /hbos/hbos。
  history: createWebHistory('/'),
  routes: [
    { path: '/', redirect: '/hbos' },
    {
      path: '/hbos',
      component: PortalLayout,
      children: [
        { path: '', name: 'portal-home', component: PortalHome, meta: { title: 'HBOS 首页' } },
        { path: 'work', name: 'my-work', component: MyWorkView, meta: { title: '我的工作' } },
        { path: 'apps', name: 'apps', component: AppCenterView, meta: { title: '应用中心' } },
        { path: 'profile', name: 'profile', component: ProfileSettingsView, meta: { title: '我的与设置' } },
        { path: 'embed', name: 'business-embed', component: BusinessEmbedView, meta: { title: '业务应用' } },
        { path: '403', name: 'forbidden', component: ForbiddenView, meta: { title: '无权限' } },
      ],
    },
    {
      path: '/hbos/lims',
      component: LimsLayout,
      children: [
        { path: '', name: 'lims-home', component: LimsHomeView, meta: { title: 'LIMS · 我的实验室' } },
        { path: 'results/:resultId/review', name: 'lims-result-review', component: LimsResultReviewView, meta: { title: 'LIMS · 结果复核' } },
      ],
    },
    { path: '/:pathMatch(.*)*', name: 'not-found', component: NotFoundView, meta: { title: '页面不存在' } },
  ],
  scrollBehavior: () => ({ top: 0 }),
})

router.afterEach((to) => {
  const title = typeof to.meta.title === 'string' ? to.meta.title : 'HBOS'
  document.title = title === 'HBOS 首页' ? 'HBOS · 海滨智能运营工作台' : `${title} · HBOS`
})

export default router
