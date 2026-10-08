<template>
  <aside class="app-local-sidebar glass-surface" aria-label="考勤应用导航">
    <div class="app-local-brand">
      <div class="app-icon attendance"><ClockCircleOutlined /></div>
      <div>
        <strong>考勤</strong>
        <span>ATTENDANCE</span>
      </div>
    </div>

    <button
      class="back-workspace"
      type="button"
      title="返回 HBOS 工作台"
      @click="$router.push('/hbos')"
    >
      <ArrowLeftOutlined /><span>返回 HBOS 工作台</span>
    </button>

    <nav>
      <template v-for="group in attendanceNavGroups" :key="group.label">
        <div class="nav-section-label">{{ group.label }}</div>
        <RouterLink
          v-for="item in group.items"
          :key="item.slug"
          class="local-nav"
          :class="{ active: activeSlug === item.slug }"
          :to="navTarget(item)"
          :title="item.label"
        >
          <component :is="iconOf(item.icon)" />
          <span>{{ item.label }}</span>
        </RouterLink>
      </template>
    </nav>

    <div class="sidebar-spacer"></div>

    <!-- 管理后台 = Frappe Desk 的管理控制台。按分层约定它保留自身身份、
         不与门户逐像素一致，故这里不内嵌，直接新开页签。 -->
    <button
      type="button"
      class="local-nav management"
      title="打开管理后台"
      @click="openManagementConsole"
    >
      <SettingOutlined /><span>管理后台</span><RightOutlined />
    </button>
  </aside>
</template>

<script setup lang="ts">
import { computed, type Component } from 'vue'
import { useRoute } from 'vue-router'
import {
  ApartmentOutlined,
  ArrowLeftOutlined,
  BarChartOutlined,
  CalendarOutlined,
  ClockCircleOutlined,
  CloudUploadOutlined,
  DashboardOutlined,
  FieldTimeOutlined,
  FileSearchOutlined,
  ProfileOutlined,
  ReconciliationOutlined,
  RightOutlined,
  SettingOutlined,
  SwapOutlined,
  TableOutlined,
  TeamOutlined,
  UploadOutlined,
} from '@ant-design/icons-vue'
import { activeNavForPath, attendanceNavGroups, navTarget } from '@/services/attendanceNav'

const route = useRoute()

// 图标按名字查表：导航数据里只存字符串，避免把组件实例塞进纯数据模块
// （那样 attendanceNav.ts 就依赖了 Vue，无法单独在别处复用/测试）。
const ICONS: Record<string, Component> = {
  dashboard: DashboardOutlined,
  team: TeamOutlined,
  apartment: ApartmentOutlined,
  chart: BarChartOutlined,
  profile: ProfileOutlined,
  table: TableOutlined,
  reconciliation: ReconciliationOutlined,
  upload: UploadOutlined,
  cloudUpload: CloudUploadOutlined,
  fileSearch: FileSearchOutlined,
  calendar: CalendarOutlined,
  fieldTime: FieldTimeOutlined,
  swap: SwapOutlined,
  setting: SettingOutlined,
}

function iconOf(name: string): Component {
  return ICONS[name] ?? DashboardOutlined
}

const activeSlug = computed(() => activeNavForPath(route.path)?.slug)

function openManagementConsole() {
  window.open('/app/海滨考勤工作台', '_blank', 'noopener,noreferrer')
}
</script>

<style scoped>
/* 考勤有 15 个入口，远超 LIMS（不到 10 个），而共享样式给侧栏定的是
   `height: calc(100vh - 116px)` 且**没有 overflow**——多出来的项直接被裁掉，
   底部的「班次管理 / 管理后台」点不到。

   改法：让**中间的 nav 滚动**，首尾（品牌 / 返回 / 管理后台）钉住不动。
   不整体滚动，是因为滚到底才看得到「管理后台」会让人以为它不存在。
   min-height: 0 是必需的：flex 子项默认 min-height:auto，不加就不会收缩。 */
.app-local-sidebar > nav {
  flex: 1 1 auto;
  min-height: 0;
  overflow-y: auto;
  overscroll-behavior: contain;
  /* 滚动条常隐、悬停才显，避免在浅色玻璃上出现一条突兀的深色竖线 */
  scrollbar-width: thin;
  scrollbar-color: rgba(65, 91, 138, .28) transparent;
}
.app-local-sidebar > nav::-webkit-scrollbar { width: 6px; }
.app-local-sidebar > nav::-webkit-scrollbar-thumb {
  background: rgba(65, 91, 138, .22);
  border-radius: 999px;
}
.app-local-sidebar > nav::-webkit-scrollbar-track { background: transparent; }

/* spacer 原本 flex:1，会与 nav 抢空间，改成一个固定的呼吸位 */
.app-local-sidebar .sidebar-spacer { flex: 0 0 10px; }

/* 窄屏是图标栏（76px），项高更小但仍可能超高；同样交给 nav 滚动 */
@media (max-width: 1100px) {
  .app-local-sidebar > nav { overflow-y: auto; }
}
</style>
