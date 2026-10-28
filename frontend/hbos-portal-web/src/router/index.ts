import { createRouter, createWebHistory } from 'vue-router'
import PortalLayout from '@/components/layout/PortalLayout.vue'
import LimsLayout from '@/components/layout/LimsLayout.vue'
import { canIam } from '@/services/iamAccess'
import { ensurePortalSession } from '@/services/portalSessionCoordinator'
import { accountRedirect } from '@/services/accountNavigation'
import { isUnauthenticatedError, probeFrappeSession } from '@/services/frappeClient'
import { portalDataSource } from '@/services/portalProvider'
import { usePortalStore } from '@/stores/portal'
import { checkPortalAccess } from '@/router/portalGuard'
import InventoryLayout from '@/components/layout/InventoryLayout.vue'
import InventoryOverviewView from '@/views/InventoryOverviewView.vue'
import InventoryIntakeView from '@/views/InventoryIntakeView.vue'
import InventoryDraftReviewView from '@/views/InventoryDraftReviewView.vue'
import InventoryBatchView from '@/views/InventoryBatchView.vue'
import InventoryReportView from '@/views/InventoryReportView.vue'
import InventoryBatchPickerView from '@/views/InventoryBatchPickerView.vue'
import InventoryWarehouseView from '@/views/InventoryWarehouseView.vue'
import InventoryPendingView from '@/views/InventoryPendingView.vue'
import InventoryEntryView from '@/views/InventoryEntryView.vue'
import InventoryPickView from '@/views/InventoryPickView.vue'
import InventoryReconcileView from '@/views/InventoryReconcileView.vue'
import InventoryUnavailableView from '@/views/InventoryUnavailableView.vue'
import ProductionLayout from '@/components/layout/ProductionLayout.vue'
import ProductionDashboardView from '@/views/ProductionDashboardView.vue'

const KnowledgeTwinLayout = () => import('@/components/layout/KnowledgeTwinLayout.vue')
const KnowledgeView = () => import('@/views/KnowledgeView.vue')
const TwinView = () => import('@/views/TwinView.vue')
const FeishuLoginView = () => import('@/views/FeishuLoginView.vue')

// 考勤工作台（ported from feature/hbos-attendance-console）。
// 全部走懒加载，避免把考勤页塞进首屏 chunk；路由表其余部分不动。
const AttendanceLayout = () => import('@/components/layout/AttendanceLayout.vue')
const AttendanceDashboardView = () => import('@/views/AttendanceDashboardView.vue')
const AttendanceEmployeesView = () => import('@/views/AttendanceEmployeesView.vue')
const AttendanceBoardView = () => import('@/views/AttendanceBoardView.vue')
const AttendanceReportView = () => import('@/views/AttendanceReportView.vue')
const AttendanceListView = () => import('@/views/AttendanceListView.vue')
const AttendanceImportView = () => import('@/views/AttendanceImportView.vue')
const AttendanceMonthlyUploadView = () => import('@/views/AttendanceMonthlyUploadView.vue')
const AttendanceEmbedView = () => import('@/views/AttendanceEmbedView.vue')

const router = createRouter({
  history: createWebHistory('/'),
  routes: [
    { path: '/', redirect: '/hbos' },
    { path: '/login', redirect: (to) => ({ path: '/hbos/login', query: to.query.redirect ? { redirect_to: to.query.redirect } : {} }) },
    { path: '/hbos/login', name: 'feishu-login', component: FeishuLoginView, meta: { title: '企业身份登录' } },
    { path: '/hbos/account-connect', component: () => import('@/views/AccountConnectView.vue'), meta: { title: '账号归属与绑定' } },
    { path: '/hbos/account-change', component: () => import('@/views/AccountChangeView.vue'), meta: { title: '绑定与职责交接' } },
    { path: '/hbos/reset-password', component: () => import('@/views/ResetPasswordView.vue'), meta: { title: '账号恢复' } },
    {
      path: '/hbos',
      component: PortalLayout,
      meta: { requiresAuth: true },
      children: [
        { path: '', name: 'portal-home', component: () => import('@/views/PortalHome.vue'), meta: { title: 'HBOS 首页' } },
        { path: 'work', name: 'my-work', component: () => import('@/views/MyWorkView.vue'), meta: { title: '我的工作' } },
        { path: 'apps', name: 'apps', component: () => import('@/views/AppCenterView.vue'), meta: { title: '应用中心' } },
        { path: 'profile', name: 'profile', component: () => import('@/views/ProfileSettingsView.vue'), meta: { title: '个人中心' } },
        { path: 'inventory/item/:itemCode?', name: 'inventory-item-readonly', component: () => import('@/views/InventoryItemReadOnlyView.vue'), meta: { title: '仓储 · 物料只读浏览' } },
        { path: 'attendance/me', component: () => import('@/views/attendance/MyAttendanceView.vue'), meta: { title: '我的考勤', attendanceSelf: true } },
        { path: 'admin', component: () => import('@/views/admin/AdminWorkspaceView.vue'), meta: { title: '管理中心', iam: true }, children: [
          { path: '', component: () => import('@/views/admin/AdminAccessUnavailableView.vue') },
          { path: 'people', component: () => import('@/views/admin/PeopleAdminView.vue'), meta: { title: '员工管理', iamCapability: 'iam.people.read' } },
          { path: 'departments', component: () => import('@/views/admin/DepartmentsAdminView.vue'), meta: { title: '部门应用权限', iamCapability: 'iam.departments.read' } },
          { path: 'access', component: () => import('@/views/admin/AccessAdminView.vue'), meta: { title: '应用权限', iamCapability: 'iam.access.read' } },
          { path: 'roles', component: () => import('@/views/admin/RolesAdminView.vue'), meta: { title: '角色与权限', iamCapability: 'iam.roles.read' } },
          { path: 'audit', component: () => import('@/views/admin/AuditAdminView.vue'), meta: { title: '变更记录', iamCapability: 'iam.audit.read' } },
          { path: 'unavailable', component: () => import('@/views/admin/AdminAccessUnavailableView.vue'), meta: { title: '管理功能暂不可用' } },
        ] },
        { path: '403', name: 'forbidden', component: () => import('@/views/ForbiddenView.vue'), meta: { title: '无权限' } },
      ],
    },
    {
      // 考勤原生进 Portal SPA：/hbos/attendance* 由前端 SPA 渲染，不再进 iframe。
      // 原生路由挂在 AttendanceLayout 下统一带门户外壳；embed/:slug 是报表/列表等
      // 后台页面的同域 iframe 载体，必须挂同一 layout，否则点开报表会离开
      // /hbos/attendance，侧栏整个消失。
      // 稳定路径须与后端 Attendance portal 路由的 NATIVE_PATHS/EMBEDDED_ROUTES 对应
      // （见 src/services/attendanceNav.ts）。
      path: '/hbos/attendance',
      component: AttendanceLayout,
      children: [
        { path: '', name: 'attendance-dashboard', component: AttendanceDashboardView, meta: { title: '考勤管理' } },
        { path: 'employees', name: 'attendance-employees', component: AttendanceEmployeesView, meta: { title: '人员管理' } },
        { path: 'exports', component: () => import('@/views/AttendanceExportsView.vue'), meta: { title: '考勤导出' } },
        { path: 'rules', component: () => import('@/views/AttendanceRulesView.vue'), meta: { title: '规则与重算' } },
        { path: 'shifts', component: () => import('@/views/AttendanceShiftsView.vue'), meta: { title: '班次与排班' } },
        { path: 'corrections', name: 'attendance-corrections', component: () => import('@/views/AttendanceCorrectionsView.vue'), meta: { title: '考勤更正' } },
        { path: 'board', name: 'attendance-board', component: AttendanceBoardView, meta: { title: '部门看板' } },
        { path: 'report/:slug', name: 'attendance-report', component: AttendanceReportView, meta: { title: '考勤报表' } },
        { path: 'list/:slug', name: 'attendance-list', component: AttendanceListView, meta: { title: '考勤记录' } },
        { path: 'import', name: 'attendance-import', component: AttendanceImportView, meta: { title: '导入考勤机导出表' } },
        { path: 'monthly-upload', name: 'attendance-monthly-upload', component: AttendanceMonthlyUploadView, meta: { title: '上传月度考勤表' } },
        { path: 'embed/:slug', name: 'attendance-embed', component: AttendanceEmbedView, meta: { title: '考勤业务页面' } },
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
        { path: 'roles', component: () => import('@/views/admin/RolesAdminView.vue'), meta: { title: '角色与权限', iam: true, iamCapability: 'iam.roles.read' } },
          { path: 'audit', name: 'lims-audit', component: () => import('@/views/LimsAuditView.vue'), meta: { title: 'LIMS · 合规审计', limsCapability: 'audit' } },
        { path: 'samples/new', name: 'lims-sample-new', component: () => import('@/views/LimsPendingView.vue'), meta: { title: 'LIMS · 登记样品', limsCapability: 'samples' } },
        { path: 'samples', name: 'lims-samples', component: () => import('@/views/LimsPendingView.vue'), meta: { title: 'LIMS · 样品与检验', limsCapability: 'samples' } },
        { path: 'results/:resultId/review', name: 'lims-result-review', component: () => import('@/views/LimsResultEntryView.vue'), meta: { title: 'LIMS · 结果复核', limsCapability: 'results' } },
        { path: 'results/:resultId', name: 'lims-result-entry', component: () => import('@/views/LimsResultEntryView.vue'), meta: { title: 'LIMS · 结果录入', limsCapability: 'results' } },
        { path: ':pathMatch(.*)*', name: 'lims-pending', component: () => import('@/views/LimsPendingView.vue'), meta: { title: 'LIMS · 页面待设计' } },
      ],
    },
    {
      // 仓储库存已原生进 Portal SPA（后端 /hbos/inventory 解析回自身）。
      // 入库拍照识别等尚未前端化的入口会离开 SPA 去 Desk，由后端路由决定。
      path: '/hbos/inventory',
      component: InventoryLayout,
      children: [
        { path: '', name: 'inventory-overview', component: InventoryOverviewView, meta: { title: '仓储库存' } },
        { path: 'intake', name: 'inventory-intake', component: InventoryIntakeView, meta: { title: '入库拍照识别' } },
        {
          path: 'draft/:draftName',
          name: 'inventory-draft',
          component: InventoryDraftReviewView,
          meta: { title: '草稿复核' },
        },
        {
          // 批次有两个入口：
          //   1. 带单号进来（入库提交后、按批号查货位点批号）→ 详情；
          //   2. 不带单号（侧边栏「批次」）→ 选择器，与物料/货位同构。
          // 两条路由分开而不是一条带可选参数——详情页依赖 :batchName，
          // 可选参数会让它在缺失时渲染出空壳。
          path: 'batch',
          name: 'inventory-batch-picker',
          component: InventoryBatchPickerView,
          meta: { title: '批次' },
        },
        {
          path: 'batch/:batchName',
          name: 'inventory-batch',
          component: InventoryBatchView,
          meta: { title: '批次' },
        },
        {
          // 四张报表共用一个视图组件，仅路由参数不同。
          // 给四条路由而不是一个下拉：报表需要可分享、可后退的 Deep Link（EA-5.4 §37）。
          path: 'report/:reportId',
          name: 'inventory-report',
          component: InventoryReportView,
          meta: { title: '库存报表' },
        },
        {
          path: 'warehouse/:warehouseName?',
          name: 'inventory-warehouse',
          component: InventoryWarehouseView,
          meta: { title: '货位' },
        },
        {
          // 库存单据：新建（无参）与编辑（带单号）共用一条路由。
          // 可写页 —— 建/改/提交/删除，放行门禁由 release_gate.py 兜底。
          path: 'entry/:entryName?',
          name: 'inventory-entry',
          component: InventoryEntryView,
          meta: { title: '库存单据' },
        },
        {
          // 拣货单：列表（新建）与详情共用一条路由。
          // 前一步是「先保存」——定位货位要求单据已存在（见 inventoryPick 的注释）。
          path: 'pick/:pickName?',
          name: 'inventory-pick',
          component: InventoryPickView,
          meta: { title: '拣货单' },
        },
        {
          // 库存对账：列表（新建）与详情共用一条路由。**会调账**。
          path: 'reconcile/:reconcileName?',
          name: 'inventory-reconcile',
          component: InventoryReconcileView,
          meta: { title: '库存对账' },
        },
        {
          // 只读工作台：放行由 LIMS 投影写入，仓库侧无权改（见 quality_projection.py）
          path: 'pending',
          name: 'inventory-pending',
          component: InventoryPendingView,
          meta: { title: '待检批次' },
        },
        {
          path: 'unavailable/:itemId',
          name: 'inventory-unavailable',
          component: InventoryUnavailableView,
          meta: { title: '暂未实现' },
        },
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
    {
      // 生产看板：Portal SPA 原生页。数据**不直连**外部服务 ——
      // 走受控后端 hbos_portal.api.production.*（会话 + 应用权限 + 服务间令牌）。
      // 无权限时后端拒绝，页面渲染「未接入」态，不显示任何数字。
      path: '/hbos/production',
      component: ProductionLayout,
      children: [
        { path: '', name: 'production-baseline', component: ProductionDashboardView, meta: { title: '生产看板' } },
        { path: 'center', name: 'production-center', component: ProductionDashboardView, meta: { title: '生产管理中心看板' } },
      ],
    },
    { path: '/:pathMatch(.*)*', name: 'not-found', component: () => import('@/views/NotFoundView.vue'), meta: { title: '页面不存在' } },
  ],
  scrollBehavior: () => ({ top: 0 }),
})

router.beforeEach(async (to) => {
  const portal = usePortalStore()
  if (portalDataSource === 'mock') return checkPortalAccess(to, portal, portalDataSource)
  const protectedRoute = to.meta.requiresAuth || to.meta.iam || to.meta.attendanceSelf || /^\/hbos\/(attendance|inventory|production|lims)(?:\/|$)/.test(to.path)
  if (!protectedRoute) return true
  try {
    const security = await ensurePortalSession()
    if (security.first_password_required) return to.meta.iam || to.meta.attendanceSelf || to.path === '/hbos/profile' ? true : '/hbos/profile'
    if (to.meta.iam) {
      if (to.path === '/hbos/admin/unavailable') return true
      if (to.path === '/hbos/admin' || to.path === '/hbos/admin/') {
        const entry = [['iam.people.read','people'],['iam.departments.read','departments'],['iam.access.read','access'],['iam.roles.read','roles'],['iam.audit.read','audit']].find(([cap]) => canIam(cap!))
        return entry ? '/hbos/admin/' + entry[1] : '/hbos/admin/unavailable'
      }
      if (typeof to.meta.iamCapability !== 'string' || !canIam(to.meta.iamCapability)) return '/hbos/admin/unavailable'
    }
    return checkPortalAccess(to, portal, portalDataSource, true)
  } catch (error) {
    if (isUnauthenticatedError(error)) return { path: '/hbos/login', query: { status: 'session_required', redirect_to: accountRedirect(to.fullPath) } }
    // A guest hitting a protected route may receive a generic 403 (not the
    // UNAUTHENTICATED code). Ask the guest-safe endpoint before deciding, so an
    // unauthenticated visitor always reaches the HBOS enterprise login page.
    // Only an authorization ambiguity is worth a guest probe. A 429, a 5xx or a
    // network failure cannot prove anything about the visitor and would burn
    // another timeout (and another rate-limit token).
    if ((error as { status?: number } | null)?.status === 403) {
      try {
        // Reuse the validating probe: it rejects a malformed payload instead of
        // treating a missing `authenticated` flag as "Guest".
        const request = await probeFrappeSession()
        if (!request.authenticated) return { path: '/hbos/login', query: { status: 'session_required', redirect_to: accountRedirect(to.fullPath) } }
      } catch {
        // Keep the existing bounded fallback when the session probe itself fails.
      }
    }
    return to.meta.iam && to.path !== '/hbos/admin/unavailable' ? '/hbos/admin/unavailable' : true
  }
})

router.afterEach((to) => {
  const title = typeof to.meta.title === 'string' ? to.meta.title : 'HBOS'
  document.title = title === 'HBOS 首页' ? 'HBOS · 海滨智能运营工作台' : `${title} · HBOS`
})

export default router
