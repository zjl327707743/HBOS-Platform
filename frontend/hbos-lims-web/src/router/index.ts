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
        path: 'my-todos',
        name: 'my-todos',
        component: () => import('@/views/MyTodosView.vue'),
        meta: { title: '我的待办' },
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
        path: 'retention',
        name: 'retention-dashboard',
        component: () => import('@/views/RetentionDashboardView.vue'),
        meta: { title: '留样工作台' },
      },
      {
        path: 'retention/samples',
        name: 'retention-samples',
        component: () => import('@/views/RetentionView.vue'),
        meta: { title: '留样登记与台账' },
      },
      {
        path: 'retention/products',
        name: 'retention-products',
        component: () => import('@/views/RetentionProductView.vue'),
        meta: { title: '留样产品' },
      },
      {
        path: 'retention/observations',
        name: 'retention-observations',
        component: () => import('@/views/RetentionObservationsView.vue'),
        meta: { title: '观察任务' },
      },
      {
        path: 'retention/usage',
        name: 'retention-usage',
        component: () => import('@/views/RetentionUsageView.vue'),
        meta: { title: '使用申请' },
      },
      {
        path: 'retention/disposal',
        name: 'retention-disposal',
        component: () => import('@/views/RetentionDisposalView.vue'),
        meta: { title: '处理申请' },
      },
      {
        path: 'audit',
        name: 'audit',
        component: () => import('@/views/AuditTrailView.vue'),
        meta: { title: '审计追踪查询' },
      },
      {
        path: 'audit-log',
        name: 'audit-log',
        component: () => import('@/views/AuditLogView.vue'),
        meta: { title: '合规审计日志' },
      },
      {
        path: 'stability',
        name: 'stability-dashboard',
        component: () => import('@/views/StabilityDashboardView.vue'),
        meta: { title: '稳定性工作台' },
      },
      {
        path: 'stability/study',
        name: 'stability-study',
        component: () => import('@/views/StabilityStudyView.vue'),
        meta: { title: '考察申请与方案' },
      },
      {
        path: 'stability/samples',
        name: 'stability-samples',
        component: () => import('@/views/StabilitySampleView.vue'),
        meta: { title: '样品入箱与台账' },
      },
      {
        path: 'stability/schedule',
        name: 'stability-schedule',
        component: () => import('@/views/StabilityScheduleView.vue'),
        meta: { title: '取样与检测计划' },
      },
      {
        path: 'stability/results',
        name: 'stability-results',
        component: () => import('@/views/StabilityResultView.vue'),
        meta: { title: '结果录入与趋势' },
      },
      {
        path: 'stability/reports',
        name: 'stability-reports',
        component: () => import('@/views/StabilityReportView.vue'),
        meta: { title: '报告与有效期' },
      },
      {
        path: 'stability/ops',
        name: 'stability-ops',
        component: () => import('@/views/StabilityOpsView.vue'),
        meta: { title: '变更 / 稳定性室 / 设备' },
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
