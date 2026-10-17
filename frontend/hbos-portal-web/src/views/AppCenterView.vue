<template>
  <section class="product-page">
    <div class="apps-hero glass-hero">
      <div>
        <span class="page-kicker">APPLICATIONS</span>
        <h1>应用中心</h1>
        <p>搜索并进入当前账号可使用的业务应用。</p>
      </div>
      <div class="apps-search">
        <SearchOutlined />
        <input v-model="query" placeholder="搜索应用…" />
      </div>
    </div>

    <section class="app-section">
      <div class="section-head simple">
        <div><h2>常用应用</h2><p>优先展示与你当前角色最相关的应用</p></div>
      </div>
      <div class="featured-apps">
        <button v-for="app in featured" :key="app.id" class="featured-app glass-surface" type="button" @click="go(app)">
          <div class="featured-icon app-icon" :class="app.accent"><component :is="iconMap[app.icon]" /></div>
          <div class="featured-copy">
            <div class="featured-title"><strong>{{ app.shortTitle }}</strong><span>{{ app.title }}</span></div>
            <p>{{ app.description }}</p>
            <div class="featured-meta">
              <a-tag>{{ migrationLabel(app.migrationMode) }}</a-tag>
              <span v-if="app.pendingCount">{{ app.pendingCount }} 个待处理</span>
              <span v-else>{{ app.meta }}</span>
            </div>
          </div>
          <ArrowRightOutlined />
        </button>
      </div>
    </section>

    <section class="app-section">
      <div class="section-head simple">
        <div><h2>全部应用</h2><p>{{ visibleApps.length }} 个当前可用应用</p></div>
      </div>
      <div class="app-directory">
        <button v-for="app in visibleApps" :key="app.id" class="directory-app glass-surface" type="button" @click="go(app)">
          <div class="app-icon" :class="app.accent"><component :is="iconMap[app.icon]" /></div>
          <strong>{{ app.shortTitle }}</strong>
          <span>{{ app.description }}</span>
          <small>{{ app.meta }}</small>
        </button>
      </div>
    </section>
  </section>
</template>

<script setup lang="ts">
import { computed, type Component, ref } from 'vue'
import { useRouter } from 'vue-router'
import {
  ArrowRightOutlined,
  BulbOutlined,
  ClockCircleOutlined,
  DeploymentUnitOutlined,
  ExperimentOutlined,
  InboxOutlined,
  ReadOutlined,
  SafetyOutlined,
  SearchOutlined,
  ThunderboltOutlined,
  ToolOutlined,
} from '@ant-design/icons-vue'
import { usePortalStore } from '@/stores/portal'
import type { AppManifestDTO, AppMigrationMode } from '@/contracts/portal'
import { openBusinessRoute } from '@/services/businessNavigation'

const portal = usePortalStore()
const router = useRouter()
const query = ref('')

const iconMap: Record<string, Component> = {
  ExperimentOutlined, InboxOutlined, ClockCircleOutlined, ReadOutlined,
  SafetyOutlined, ThunderboltOutlined, ToolOutlined,
  DeploymentUnitOutlined, BulbOutlined,
}
const featured = computed(() => portal.apps.filter((app) => app.featured))
const visibleApps = computed(() => portal.apps.filter((app) =>
  !query.value || `${app.shortTitle} ${app.title} ${app.description}`.toLowerCase().includes(query.value.toLowerCase()),
))
function migrationLabel(mode: AppMigrationMode) {
  return { legacy: 'Legacy · Desk', hybrid: 'Hybrid', native: 'Native' }[mode]
}
function go(app: AppManifestDTO) {
  void openBusinessRoute(router, app.id, app.route)
}
</script>
