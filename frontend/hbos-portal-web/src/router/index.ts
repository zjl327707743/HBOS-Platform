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
import InventoryLayout from '@/components/layout/InventoryLayout.vue'
import InventoryOverviewView from '@/views/InventoryOverviewView.vue'
import InventoryIntakeView from '@/views/InventoryIntakeView.vue'
import InventoryDraftReviewView from '@/views/InventoryDraftReviewView.vue'
import InventoryBatchView from '@/views/InventoryBatchView.vue'
import InventoryReportView from '@/views/InventoryReportView.vue'
import InventoryItemView from '@/views/InventoryItemView.vue'
import InventoryWarehouseView from '@/views/InventoryWarehouseView.vue'
import InventoryUnavailableView from '@/views/InventoryUnavailableView.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
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
          // 主数据浏览（只读）。列表与详情共用一条路由：
          // 详情靠可选的 :itemCode / :warehouseName 落到选中态，刷新/分享都能还原。
          path: 'item/:itemCode?',
          name: 'inventory-item',
          component: InventoryItemView,
          meta: { title: '物料' },
        },
        {
          path: 'warehouse/:warehouseName?',
          name: 'inventory-warehouse',
          component: InventoryWarehouseView,
          meta: { title: '货位' },
        },
        {
          path: 'unavailable/:itemId',
          name: 'inventory-unavailable',
          component: InventoryUnavailableView,
          meta: { title: '暂未实现' },
        },
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
