import { createRouter, createWebHistory } from 'vue-router'
import PortalLayout from '@/components/layout/PortalLayout.vue'
import LimsLayout from '@/components/layout/LimsLayout.vue'
import AttendanceLayout from '@/components/layout/AttendanceLayout.vue'
import AttendanceDashboardView from '@/views/AttendanceDashboardView.vue'
import AttendanceEmployeesView from '@/views/AttendanceEmployeesView.vue'
import AttendanceBoardView from '@/views/AttendanceBoardView.vue'
import AttendanceEmbedView from '@/views/AttendanceEmbedView.vue'
import AttendanceReportView from '@/views/AttendanceReportView.vue'
import AttendanceListView from '@/views/AttendanceListView.vue'
import AttendanceImportView from '@/views/AttendanceImportView.vue'
import AttendanceMonthlyUploadView from '@/views/AttendanceMonthlyUploadView.vue'
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
      // 考勤已原生进 Portal SPA（migration_mode: native）。
      // 后端 resolve_stable_route 把 /hbos/attendance* 解析回自身，
      // 故前端走「以 /hbos/ 开头即 SPA 路由」分支，不再进 iframe。
      //
      // 三条原生路由挂在 AttendanceLayout 下（2026-10-02 补齐——此前是并列的
      // 顶层路由，**不带门户外壳**，玻璃卡浮在白底上）；embed/:slug 是后台面
      // 的同域 iframe 载体，必须挂在**同一个** layout 下：若复用顶层
      // `/hbos/embed`，点开报表会离开 /hbos/attendance，侧栏整个消失。
      path: '/hbos/attendance',
      component: AttendanceLayout,
      children: [
        { path: '', name: 'attendance-dashboard', component: AttendanceDashboardView, meta: { title: '考勤管理' } },
        { path: 'employees', name: 'attendance-employees', component: AttendanceEmployeesView, meta: { title: '人员管理' } },
        { path: 'board', name: 'attendance-board', component: AttendanceBoardView, meta: { title: '部门看板' } },
        // 报表：门户原生渲染（AntD 表格），不再 iframe 内嵌 Desk 报表。
        { path: 'report/:slug', name: 'attendance-report', component: AttendanceReportView, meta: { title: '考勤报表' } },
        // DocType 列表：同样原生渲染。
        { path: 'list/:slug', name: 'attendance-list', component: AttendanceListView, meta: { title: '考勤记录' } },
        // 导入考勤机导出表：原生页（文件上传 + 三步流程）。
        { path: 'import', name: 'attendance-import', component: AttendanceImportView, meta: { title: '导入考勤机导出表' } },
        // 上传月度考勤表：原生页（原始文件字节 POST，与导入页的 upload_file 通路不同）。
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
    { path: '/:pathMatch(.*)*', name: 'not-found', component: NotFoundView, meta: { title: '页面不存在' } },
  ],
  scrollBehavior: () => ({ top: 0 }),
})

router.afterEach((to) => {
  const title = typeof to.meta.title === 'string' ? to.meta.title : 'HBOS'
  document.title = title === 'HBOS 首页' ? 'HBOS · 海滨智能运营工作台' : `${title} · HBOS`
})

export default router
