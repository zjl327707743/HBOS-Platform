import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const routes = [
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
        path: 'results',
        name: 'results-list',
        component: () => import('@/views/ResultListView.vue'),
        meta: { title: '检验结果清单' },
      },
      {
        path: 'results/ledger',
        name: 'results-ledger',
        component: () => import('@/views/ResultLedgerView.vue'),
        meta: { title: '检验结果台账' },
      },
      {
        path: 'results/:id',
        name: 'results',
        component: () => import('@/views/ResultEntryView.vue'),
        meta: { title: '检验结果录入' },
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
  history: createWebHistory(import.meta.env.BASE_URL),
  routes,
})

// 认证守卫：HBOS LIMS 无独立登录页，必须通过 Frappe Desk 登录后进入
// （Desk 桌面图标 target=_blank 打开，新标签页继承 Frappe 会话 cookie）。
// 不再做"未登录跳 /login"（Frappe 已登录访问 /login 会重定向回 /desk 造成死循环），
// 若会话未建立，Frappe 后端 API 会拒绝未授权请求并返回错误。
router.beforeEach(async () => {
  const auth = useAuthStore()
  if (!auth.initialized) {
    await auth.checkSession()
  }
  return true
})

router.afterEach((to) => {
  document.title = to.meta.title ? `${String(to.meta.title)} · HBOS LIMS` : 'HBOS LIMS'
})

export default router
