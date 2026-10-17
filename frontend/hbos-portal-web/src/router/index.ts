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
import { canIam } from '@/services/iamAccess'
import { ensurePortalSession } from '@/services/portalSessionCoordinator'
import { accountRedirect } from '@/services/accountNavigation'
import { isUnauthenticatedError } from '@/services/frappeClient'

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
    { path: '/hbos/account-change', component: () => import('@/views/AccountChangeView.vue'), meta: { title: '绑定与职责交接' } },
    { path: '/hbos/reset-password', component: () => import('@/views/ResetPasswordView.vue'), meta: { title: '账号恢复' } },
    {
      path: '/hbos',
      component: PortalLayout,
      children: [
        { path: '', name: 'portal-home', component: PortalHome, meta: { title: 'HBOS 首页' } },
        { path: 'work', name: 'my-work', component: MyWorkView, meta: { title: '我的工作' } },
        { path: 'apps', name: 'apps', component: AppCenterView, meta: { title: '应用中心' } },
        { path: 'profile', name: 'profile', component: ProfileSettingsView, meta: { title: '我的与设置' } },
        { path: 'inventory/item/:itemCode?', name: 'inventory-item-readonly', component: () => import('@/views/InventoryItemReadOnlyView.vue'), meta: { title: '仓储 · 物料只读浏览' } },
        { path: '403', name: 'forbidden', component: ForbiddenView, meta: { title: '无权限' } },
        { path: 'attendance/me', component: () => import('@/views/attendance/MyAttendanceView.vue'), meta: { title: '我的考勤', attendanceSelf: true } },
        { path: 'admin', component: () => import('@/views/admin/AdminWorkspaceView.vue'), meta: { title: '管理中心', iam: true }, children: [
          { path: '', component: () => import('@/views/admin/AdminAccessUnavailableView.vue') },
          { path: 'people', component: () => import('@/views/admin/PeopleAdminView.vue'), meta: { title: '员工管理', iamCapability: 'iam.people.read' } },
          { path: 'departments', component: () => import('@/views/admin/DepartmentsAdminView.vue'), meta: { title: '部门管理', iamCapability: 'iam.departments.read' } },
          { path: 'access', component: () => import('@/views/admin/AccessAdminView.vue'), meta: { title: '应用权限', iamCapability: 'iam.access.read' } },
          { path: 'audit', component: () => import('@/views/admin/AuditAdminView.vue'), meta: { title: '变更审计', iamCapability: 'iam.audit.read' } },
          { path: 'unavailable', component: () => import('@/views/admin/AdminAccessUnavailableView.vue'), meta: { title: '管理功能暂不可用' } },
        ] },
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

router.beforeEach(async (to) => {
  if (!to.meta.iam && !to.meta.attendanceSelf) return true
  try {
    const security = await ensurePortalSession()
    if (security.first_password_required) return true
    if (to.meta.attendanceSelf || to.path === '/hbos/admin/unavailable') return true
    if (to.path === '/hbos/admin' || to.path === '/hbos/admin/') {
      const entry = [['iam.people.read','people'],['iam.departments.read','departments'],['iam.access.read','access'],['iam.audit.read','audit']].find(([cap]) => canIam(cap!))
      return entry ? `/hbos/admin/${entry[1]}` : '/hbos/admin/unavailable'
    }
    return typeof to.meta.iamCapability === 'string' && canIam(to.meta.iamCapability) ? true : '/hbos/admin/unavailable'
  } catch (e) {
    if (isUnauthenticatedError(e)) return { path: '/hbos/login', query: { status: 'session_required', redirect_to: accountRedirect(to.fullPath) } }
    return to.path === '/hbos/admin/unavailable' || to.meta.attendanceSelf ? true : '/hbos/admin/unavailable'
  }
})

router.afterEach((to) => {
  const title = typeof to.meta.title === 'string' ? to.meta.title : 'HBOS'
  document.title = title === 'HBOS 首页' ? 'HBOS · 海滨智能运营工作台' : `${title} · HBOS`
})

export default router
