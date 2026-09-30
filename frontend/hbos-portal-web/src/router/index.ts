import { createRouter, createWebHistory } from 'vue-router'
import PortalLayout from '@/components/layout/PortalLayout.vue'
import LimsLayout from '@/components/layout/LimsLayout.vue'
import { portalDataSource } from '@/services/portalProvider'
import { usePortalStore } from '@/stores/portal'
import { resolveLimsShellCapabilities } from '@/services/limsCapabilities'
import type { LimsShellCapability } from '@/services/limsCapabilities'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    { path: '/', redirect: '/hbos' },
    { path: '/login', name: 'login', component: () => import('@/views/PortalLoginView.vue'), meta: { title: '登录' } },
    {
      path: '/hbos',
      component: PortalLayout,
      meta: { requiresAuth: true },
      children: [
        { path: '', name: 'portal-home', component: () => import('@/views/PortalHome.vue'), meta: { title: 'HBOS 首页' } },
        { path: 'work', name: 'my-work', component: () => import('@/views/MyWorkView.vue'), meta: { title: '我的工作' } },
        { path: 'apps', name: 'apps', component: () => import('@/views/AppCenterView.vue'), meta: { title: '应用中心' } },
        { path: 'profile', name: 'profile', component: () => import('@/views/ProfileSettingsView.vue'), meta: { title: '我的与设置' } },
        { path: '403', name: 'forbidden', component: () => import('@/views/ForbiddenView.vue'), meta: { title: '无权限' } },
      ],
    },
    {
      path: '/hbos/lims',
      // LIMS owns its local navigation in both Mock and real Frappe modes.
      // Real mode pages remain pending until the LIMS frontend is implemented,
      // but they must not fall back to the Portal fixed Sidebar.
      component: LimsLayout,
      meta: { requiresAuth: true, appId: 'lims' },
      children: [
        { path: '', name: 'lims-home', component: () => import('@/views/LimsDashboardView.vue'), meta: { title: 'LIMS · 实验室工作台', limsCapability: 'dashboard' } },
        { path: 'tasks', name: 'lims-tasks', component: () => import('@/views/LimsTaskBoardView.vue'), meta: { title: 'LIMS · 任务中心', limsCapability: 'tasks' } },
        { path: 'results', name: 'lims-results', component: () => import('@/views/LimsResultListView.vue'), meta: { title: 'LIMS · 检验结果', limsCapability: 'results' } },
        // Keep static ledger paths ahead of future dynamic result routes.
        { path: 'ledger', name: 'lims-ledger', component: () => import('@/views/LimsLedgerView.vue'), meta: { title: 'LIMS · 结果台账', limsCapability: 'ledger' } },
        { path: 'coa', name: 'lims-coa', component: () => import('@/views/LimsCoaView.vue'), meta: { title: 'LIMS · 检验报告', limsCapability: 'coa' } },
        { path: 'specifications', name: 'lims-specifications', component: () => import('@/views/LimsQualityStandardsView.vue'), meta: { title: 'LIMS · 质量标准', limsCapability: 'specifications' } },
        { path: 'retains', name: 'lims-retains', component: () => import('@/views/LimsRetentionWorkbenchView.vue'), meta: { title: 'LIMS · 留样工作台', limsCapability: 'retains' } },
        { path: 'retains/samples', name: 'lims-retains-samples', component: () => import('@/views/LimsRetentionWorkbenchView.vue'), meta: { title: 'LIMS · 留样登记与台账', limsCapability: 'retains' } },
        { path: 'retains/products', name: 'lims-retains-products', component: () => import('@/views/LimsRetentionWorkbenchView.vue'), meta: { title: 'LIMS · 留样产品规则', limsCapability: 'retains' } },
        { path: 'retains/observations', name: 'lims-retains-observations', component: () => import('@/views/LimsRetentionWorkbenchView.vue'), meta: { title: 'LIMS · 观察任务', limsCapability: 'retains' } },
        { path: 'retains/usage', name: 'lims-retains-usage', component: () => import('@/views/LimsRetentionWorkbenchView.vue'), meta: { title: 'LIMS · 使用申请', limsCapability: 'retains' } },
        { path: 'retains/disposal', name: 'lims-retains-disposal', component: () => import('@/views/LimsRetentionWorkbenchView.vue'), meta: { title: 'LIMS · 处理申请', limsCapability: 'retains' } },
        { path: 'stability', name: 'lims-stability', component: () => import('@/views/LimsStabilityWorkbenchView.vue'), meta: { title: 'LIMS · 稳定性工作台', limsCapability: 'stability' } },
        { path: 'stability/schedule', name: 'lims-stability-schedule', component: () => import('@/views/LimsStabilityWorkbenchView.vue'), meta: { title: 'LIMS · 取样与检测计划', limsCapability: 'stability' } },
        { path: 'stability/samples', name: 'lims-stability-samples', component: () => import('@/views/LimsStabilityWorkbenchView.vue'), meta: { title: 'LIMS · 样品入箱台账', limsCapability: 'stability' } },
        { path: 'stability/results', name: 'lims-stability-results', component: () => import('@/views/LimsStabilityWorkbenchView.vue'), meta: { title: 'LIMS · 稳定性结果', limsCapability: 'stability' } },
        { path: 'stability/trend', name: 'lims-stability-trend', component: () => import('@/views/LimsStabilityWorkbenchView.vue'), meta: { title: 'LIMS · 趋势分析', limsCapability: 'stability' } },
        { path: 'audit', name: 'lims-audit', component: () => import('@/views/LimsAuditView.vue'), meta: { title: 'LIMS · 合规审计', limsCapability: 'audit' } },
        { path: 'samples/new', name: 'lims-sample-new', component: () => import('@/views/LimsPendingView.vue'), meta: { title: 'LIMS · 登记样品', limsCapability: 'samples' } },
        { path: 'samples', name: 'lims-samples', component: () => import('@/views/LimsPendingView.vue'), meta: { title: 'LIMS · 样品与检验', limsCapability: 'samples' } },
        { path: 'results/:resultId/review', name: 'lims-result-review', component: () => import('@/views/LimsResultEntryView.vue'), meta: { title: 'LIMS · 结果复核', limsCapability: 'results' } },
        { path: 'results/:resultId', name: 'lims-result-entry', component: () => import('@/views/LimsResultEntryView.vue'), meta: { title: 'LIMS · 结果录入', limsCapability: 'results' } },
        { path: ':pathMatch(.*)*', name: 'lims-pending', component: () => import('@/views/LimsPendingView.vue'), meta: { title: 'LIMS · 页面待设计' } },
      ],
    },
    { path: '/:pathMatch(.*)*', name: 'not-found', component: () => import('@/views/NotFoundView.vue'), meta: { title: '页面不存在' } },
  ],
  scrollBehavior: () => ({ top: 0 }),
})

router.beforeEach(async (to) => {
  if (!to.meta.requiresAuth) return true
  const portal = usePortalStore()
  if (!(await portal.ensureSession())) {
    return { name: 'login', query: { redirect: to.fullPath } }
  }

  // Bootstrap only includes apps whose provider grants access. Apply that
  // check to copied URLs as well as clicks from the App Center.
  if (
    portalDataSource === 'frappe' &&
    to.meta.appId === 'lims' &&
    !portal.apps.some((app) => app.id === 'lims')
  ) {
    return { name: 'forbidden' }
  }

  if (
    portalDataSource === 'frappe' &&
    to.meta.appId === 'lims' &&
    typeof to.meta.limsCapability === 'string'
  ) {
    const limsApp = portal.apps.find((app) => app.id === 'lims')
    const capabilities = resolveLimsShellCapabilities(limsApp, portalDataSource)
    if (!capabilities.has(to.meta.limsCapability as LimsShellCapability)) {
      // A declared Provider capability without the user's semantic access is
      // a permission result; an undeclared capability is still pending design.
      return limsApp?.capabilities?.includes(to.meta.limsCapability) ? { name: 'forbidden' } : { name: 'lims-pending' }
    }
  }

  return true
})

router.afterEach((to) => {
  const title = typeof to.meta.title === 'string' ? to.meta.title : 'HBOS'
  document.title = title === 'HBOS 首页' ? 'HBOS · 海滨智能运营工作台' : `${title} · HBOS`
})

export default router
