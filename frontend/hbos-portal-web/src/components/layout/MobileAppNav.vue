<template>
  <nav class="mobile-app-nav glass-surface" :aria-label="ariaLabel">
    <button type="button" class="mobile-app-nav-item" @click="$router.push(homePath)">
      <ArrowLeftOutlined /><span>HBOS</span>
    </button>
    <button type="button" class="mobile-app-nav-item active" @click="$router.push(appPath)">
      <DashboardOutlined /><span>工作台</span>
    </button>
    <button type="button" class="mobile-app-nav-item" @click="quickTarget && $router.push(quickTarget)">
      <component :is="quickIcon" /><span>{{ quickLabel }}</span>
    </button>
    <button type="button" class="mobile-app-nav-item" @click="drawerOpen = true">
      <MenuOutlined /><span>菜单</span>
    </button>
  </nav>

  <a-drawer
    v-model:open="drawerOpen"
    :title="drawerTitle"
    placement="bottom"
    height="70vh"
    root-class-name="mobile-lims-drawer"
  >
    <div class="mobile-local-menu">
      <template v-for="(group, index) in groups" :key="group.label">
        <div class="nav-section-label" :class="{ spaced: index > 0 }">{{ group.label }}</div>
        <button
          v-for="item in group.items"
          :key="item.label"
          type="button"
          @click="go(item)"
        >
          <component :is="item.icon" v-if="item.icon" />{{ item.label }}
        </button>
      </template>
    </div>
  </a-drawer>
</template>

<script setup lang="ts">
import { ref, type Component } from 'vue'
import { useRouter } from 'vue-router'
import {
  ArrowLeftOutlined,
  CheckCircleOutlined,
  DashboardOutlined,
  ExperimentOutlined,
  MenuOutlined,
  SafetyCertificateOutlined,
} from '@ant-design/icons-vue'

export interface MobileNavEntry {
  label: string
  icon?: Component
  to?: string
}

export interface MobileNavGroup {
  label: string
  items: MobileNavEntry[]
}

/**
 * 业务应用移动端底栏。
 *
 * 默认值保留 LIMS 的既有文案与结构，所以 `LimsLayout` 无需改动即可保持原样；
 * 其他应用（如仓储库存）通过 props 传入自己的导航。
 */
const props = withDefaults(
  defineProps<{
    ariaLabel?: string
    drawerTitle?: string
    homePath?: string
    appPath?: string
    quickLabel?: string
    quickIcon?: Component
    quickTarget?: string
    groups?: MobileNavGroup[]
  }>(),
  {
    ariaLabel: 'LIMS 移动端导航',
    drawerTitle: 'LIMS 导航',
    homePath: '/hbos',
    appPath: '/hbos/lims',
    quickLabel: '待检',
    quickIcon: () => ExperimentOutlined,
    quickTarget: '',
    groups: () => [
      {
        label: '我的工作',
        items: [
          { label: '工作台', icon: DashboardOutlined },
          { label: '我的待检', icon: ExperimentOutlined },
          { label: '我的复核', icon: CheckCircleOutlined },
          { label: '我的审批', icon: SafetyCertificateOutlined },
        ],
      },
      {
        label: '专业业务',
        items: [
          { label: '样品与检验' },
          { label: '质量与报告' },
          { label: '留样管理' },
          { label: '稳定性管理' },
          { label: '合规审计' },
        ],
      },
    ],
  },
)

const router = useRouter()
const drawerOpen = ref(false)

function go(item: MobileNavEntry) {
  drawerOpen.value = false
  if (!item.to) return
  // 尚未前端化的入口由后端解析到 Desk 页，可能是跨源绝对地址
  if (item.to.startsWith('http')) window.location.assign(item.to)
  else void router.push(item.to)
}
</script>
