import { createRouter, createWebHistory } from 'vue-router'
import PortalLayout from '@/components/layout/PortalLayout.vue'
import LimsLayout from '@/components/layout/LimsLayout.vue'
import PortalHome from '@/views/PortalHome.vue'
import MyWorkView from '@/views/MyWorkView.vue'
import AppCenterView from '@/views/AppCenterView.vue'
import ProfileSettingsView from '@/views/ProfileSettingsView.vue'
import ForbiddenView from '@/views/ForbiddenView.vue'
import NotFoundView from '@/views/NotFoundView.vue'
import LimsHomeView from '@/views/LimsHomeView.vue'
import LimsResultReviewView from '@/views/LimsResultReviewView.vue'

const KnowledgeTwinLayout = () => import('@/components/layout/KnowledgeTwinLayout.vue')
const KnowledgeView = () => import('@/views/KnowledgeView.vue')
const TwinView = () => import('@/views/TwinView.vue')
const FeishuLoginView = () => import('@/views/FeishuLoginView.vue')

const router = createRouter({
  history: createWebHistory('/'),
  routes: [
    { path: '/', redirect: '/hbos' },
    { path: '/hbos/login', name: 'feishu-login', component: FeishuLoginView, meta: { title: '企业身份登录' } },
    { path: '/hbos/account-connect', component: () => import('@/views/AccountConnectView.vue'), meta: { title: '账号归属与绑定' } },
    { path: '/hbos/reset-password', component: () => import('@/views/ResetPasswordView.vue'), meta: { title: '账号恢复' } },
    {
      path: '/hbos',
      component: PortalLayout,
      children: [
        { path: '', name: 'portal-home', component: PortalHome, meta: { title: 'HBOS 首页' } },
        { path: 'work', name: 'my-work', component: MyWorkView, meta: { title: '我的工作' } },
        { path: 'apps', name: 'apps', component: AppCenterView, meta: { title: '应用中心' } },
        { path: 'profile', name: 'profile', component: ProfileSettingsView, meta: { title: '我的与设置' } },
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
    {
      path: '/hbos/knowledge',
      component: KnowledgeTwinLayout,
      children: [
        { path: '', name: 'knowledge', component: KnowledgeView, meta: { title: '知识助理' } },
      ],
    },
    {
      path: '/hbos/twin',
      component: KnowledgeTwinLayout,
      children: [
        { path: '', name: 'twin', component: TwinView, meta: { title: '设备与工艺' } },
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
