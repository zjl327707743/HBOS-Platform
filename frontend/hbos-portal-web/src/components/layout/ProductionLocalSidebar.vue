<template>
  <aside class="app-local-sidebar production-sidebar glass-surface" aria-label="生产看板应用导航">
    <div class="app-local-brand">
      <div class="app-icon production"><ThunderboltOutlined /></div>
      <div>
        <strong>生产看板</strong>
        <span>产量达成与工艺分析</span>
      </div>
    </div>

    <button class="back-workspace" type="button" title="返回 HBOS 工作台" @click="$router.push('/hbos')">
      <ArrowLeftOutlined /><span>返回 HBOS 工作台</span>
    </button>

    <nav>
      <template v-for="(group, index) in PRODUCTION_NAV_GROUPS" :key="group.label">
        <div class="nav-section-label" :class="{ spaced: index > 0 }">{{ group.label }}</div>
        <button
          v-for="item in group.items"
          :key="item.id"
          type="button"
          class="local-nav"
          :class="{ active: isActive(item) }"
          :title="item.label"
          @click="$router.push(item.stablePath)"
        >
          <component :is="iconMap[item.icon]" /><span>{{ item.label }}</span>
        </button>
      </template>
    </nav>
  </aside>
</template>

<script setup lang="ts">
import { type Component } from 'vue'
import { useRoute } from 'vue-router'
import {
  ArrowLeftOutlined,
  DashboardOutlined,
  LineChartOutlined,
  ThunderboltOutlined,
} from '@ant-design/icons-vue'
import {
  PRODUCTION_NAV_GROUPS,
  PRODUCTION_CENTER_PATH,
  type ProductionNavItem,
} from '@/data/productionNav'

const route = useRoute()

const iconMap: Record<string, Component> = {
  DashboardOutlined,
  LineChartOutlined,
}

/**
 * 当前项判定。
 *
 * 只看精确路径 —— 生产看板只有两条路由、没有子页，
 * 不用像库存那样做「前缀匹配」（那里有 `/entry/:name` 这类详情页）。
 */
function isActive(item: ProductionNavItem): boolean {
  return route.path === item.stablePath
}

// 让两页的默认跳转集中一处，避免模板里写死
void PRODUCTION_CENTER_PATH
</script>
