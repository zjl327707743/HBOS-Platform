import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const routes = [
  {
    path: '/login',
    name: 'login',
    component: () => import('@/views/LoginView.vue'),
    meta: { title: '登录', public: true },
  },
  {
    path: '/',
    component: () => import('@/components/layout/AppShell.vue'),
    children: [
      { path: '', redirect: '/dashboard' },
      {
        path: 'dashboard',
        name: 'dashboard',
        component: () => import('@/views/DashboardView.vue'),
        meta: { title: '工作台总览' },
      },
      {
        path: 'samples',
        name: 'samples',
        component: () => import('@/views/SampleView.vue'),
        meta: { title: '样品登记与台账' },
      },
      {
        path: 'tasks',
        name: 'tasks',
        component: () => import('@/views/TaskBoardView.vue'),
        meta: { title: '待检任务看板' },
      },
      {
        path: 'results/:id',
        name: 'results',
        component: () => import('@/views/ResultEntryView.vue'),
        meta: { title: '检验结果录入' },
      },
      {
        path: 'results',
        redirect: '/tasks',
      },
      {
        path: 'coas',
        name: 'coas',
        component: () => import('@/views/CoaListView.vue'),
        meta: { title: 'COA 报告管理' },
      },
      {
        path: 'specs',
        name: 'specs',
        component: () => import('@/views/SpecListView.vue'),
        meta: { title: '质量标准库' },
      },
      {
        path: 'audit',
        name: 'audit',
        component: () => import('@/views/AuditTrailView.vue'),
        meta: { title: '审计追踪查询' },
      },
    ],
  },
  { path: '/:pathMatch(.*)*', redirect: '/dashboard' },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

// 认证守卫：非 public 路由需要登录
router.beforeEach(async (to) => {
  const auth = useAuthStore()
  if (to.meta.public) {
    // 已登录访问登录页则跳转到工作台
    if (auth.initialized && auth.isLoggedIn) return '/dashboard'
    return true
  }
  if (!auth.initialized) {
    await auth.checkSession()
  }
  if (!auth.isLoggedIn) {
    return { name: 'login', query: { redirect: to.fullPath } }
  }
  return true
})

router.afterEach((to) => {
  document.title = to.meta.title ? `${String(to.meta.title)} · HBOS LIMS` : 'HBOS LIMS'
})

export default router
