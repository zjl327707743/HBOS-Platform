<template>
  <aside class="app-local-sidebar inventory-sidebar glass-surface" aria-label="仓储库存应用导航">
    <div class="app-local-brand">
      <div class="app-icon inventory"><InboxOutlined /></div>
      <div>
        <strong>仓储库存</strong>
        <span>入库与库存作业</span>
      </div>
    </div>

    <button class="back-workspace" type="button" title="返回 HBOS 工作台" @click="$router.push('/hbos')">
      <ArrowLeftOutlined /><span>返回 HBOS 工作台</span>
    </button>

    <nav>
      <template v-for="(group, index) in groups" :key="group.label">
        <div class="nav-section-label" :class="{ spaced: index > 0 }">{{ group.label }}</div>
        <template v-for="item in group.items" :key="item.id">
          <button
            type="button"
            class="local-nav"
            :class="{ active: item.id === activeId }"
            :title="item.label"
            @click="open(item)"
          >
            <component :is="iconMap[item.icon]" /><span>{{ item.label }}</span>
          </button>
          <!--
            下一级：同一个页面的几种形态。
            库存单据那一项下面同时管入库 / 领用出库 / 移库——不展开的话，
            「出库」在侧边栏里没有名字，只能先进去再选类型。
          -->
          <button
            v-for="child in item.children || []"
            :key="child.id"
            type="button"
            class="local-nav local-nav-child"
            :class="{ active: child.id === activeId }"
            :title="child.label"
            @click="open(child)"
          >
            <component :is="iconMap[child.icon]" /><span>{{ child.label }}</span>
          </button>
        </template>
      </template>
    </nav>
  </aside>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  ArrowLeftOutlined,
  AuditOutlined,
  CameraOutlined,
  ClockCircleOutlined,
  DashboardOutlined,
  DatabaseOutlined,
  PlusOutlined,
  SendOutlined,
  SwapOutlined,
  FileTextOutlined,
  InboxOutlined,
  LineChartOutlined,
  ReconciliationOutlined,
  SafetyCertificateOutlined,
  SearchOutlined,
  TableOutlined,
  UnorderedListOutlined,
} from '@ant-design/icons-vue'
import {
  INVENTORY_NAV_GROUPS,
  inventoryUnavailablePath,
  type InventoryNavItem,
} from '@/data/inventoryNav'
import { openBusinessRoute } from '@/services/businessNavigation'

const router = useRouter()
const route = useRoute()

const groups = INVENTORY_NAV_GROUPS

/** 摊平一次（含下一级），供 activeId 反查用 */
const ALL_NAV_ITEMS: InventoryNavItem[] = INVENTORY_NAV_GROUPS.flatMap((g) =>
  g.items.flatMap((item) => [item, ...(item.children || [])]),
)

const iconMap: Record<string, unknown> = {
  gauge: DashboardOutlined,
  camera: CameraOutlined,
  document: FileTextOutlined,
  list: UnorderedListOutlined,
  release: SafetyCertificateOutlined,
  reconcile: ReconciliationOutlined,
  audit: AuditOutlined,
  batch: DatabaseOutlined,
  shelf: LineChartOutlined,
  item: InboxOutlined,
  table: TableOutlined,
  clock: ClockCircleOutlined,
  search: SearchOutlined,
  // 库存单据的下一级：三种单据形态（与 InventoryEntryView 的 iconMap 同款）
  in: PlusOutlined,
  out: SendOutlined,
  swap: SwapOutlined,
}

/**
 * 当前高亮哪一项。
 *
 * **按路径反查，不按路由名分支**——路由名一多就必然漏（报表四条路由共用一个组件，
 * batch / draft 又各带单据号）。反查是数据驱动的：侧边栏项自己带 `stablePath`，
 * 它就是 Authority。
 */
const activeId = computed(() => {
  const path = route.path

  // ① 精确匹配侧边栏项自己的 stablePath（概览 / 拍照识别 / 批次 / 四张报表）
  //    先比 fullPath —— 库存单据的下一级靠 `?type=` 区分，只比 path 会三条都亮。
  //    再退回 path —— 报表页会带上自己的筛选查询串，不该因此丢失高亮。
  const direct =
    ALL_NAV_ITEMS.find((item) => item.stablePath === route.fullPath) ??
    ALL_NAV_ITEMS.find((item) => item.stablePath === path)
  if (direct) return direct.id

  // ② 带单据号的子路由，按前缀归到它的父入口
  if (path.startsWith('/hbos/inventory/draft/')) return 'photo-intake'
  if (path.startsWith('/hbos/inventory/batch/')) return 'batch'

  // ③ 「尚未实现」提示页：高亮被点的那一项
  if (route.name === 'inventory-unavailable') {
    const itemId = route.params.itemId
    return typeof itemId === 'string' ? itemId : ''
  }

  return ''
})

function open(item: InventoryNavItem) {
  // 前端页还没做出来的入口，落到统一的「尚未实现」提示页，不留死链接
  if (!item.implemented) {
    void router.push(inventoryUnavailablePath(item.id))
    return
  }
  // 已原生进 Portal 的页面直接走前端路由；其余交给后端路由解析（可能离开 SPA）
  if (item.stablePath?.startsWith('/hbos/')) {
    void router.push(item.stablePath)
    return
  }
  void openBusinessRoute(router, 'inventory', item.stablePath || '')
}
</script>
