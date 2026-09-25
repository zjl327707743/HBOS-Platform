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
        <button
          v-for="item in group.items"
          :key="item.id"
          type="button"
          class="local-nav"
          :class="{ active: item.id === activeId }"
          :title="item.label"
          @click="open(item)"
        >
          <component :is="iconMap[item.icon]" /><span>{{ item.label }}</span>
        </button>
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
  ExportOutlined,
  FileTextOutlined,
  ImportOutlined,
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

const iconMap: Record<string, unknown> = {
  gauge: DashboardOutlined,
  camera: CameraOutlined,
  document: FileTextOutlined,
  import: ImportOutlined,
  export: ExportOutlined,
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
}

const activeId = computed(() => {
  const itemId = route.params.itemId
  if (route.name === 'inventory-unavailable' && typeof itemId === 'string') return itemId
  if (route.name === 'inventory-overview') return 'overview'
  if (route.name === 'inventory-intake') return 'photo-intake'
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
