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
