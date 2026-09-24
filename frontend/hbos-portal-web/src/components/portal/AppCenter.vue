<template>
  <section class="section-panel glass-surface app-center">
    <div class="section-head">
      <div>
        <span class="section-kicker">APPLICATIONS</span>
        <h2>应用中心</h2>
        <p>业务应用保持平级、独立。Portal 负责发现和入口，不把业务菜单暴露到企业主导航。</p>
      </div>
      <a-button type="link" @click="$router.push('/hbos/apps')">全部应用 <RightOutlined /></a-button>
    </div>

    <div class="app-grid refined-app-grid">
      <button v-for="app in primaryApps" :key="app.id" class="app-tile" type="button" @click="open(app.route)">
        <div class="app-icon" :class="app.accent">
          <component :is="iconMap[app.icon]" />
        </div>
        <div class="app-text">
          <strong>{{ app.shortTitle }}</strong>
          <small>{{ app.meta || app.description }}</small>
        </div>
        <a-badge v-if="app.pendingCount" :count="app.pendingCount" class="pending-badge" />
        <span class="migration">{{ migrationLabel(app.migrationMode) }}</span>
      </button>

      <button class="app-tile digital-twin-app" type="button">
        <div class="app-icon digital-twin"><NodeIndexOutlined /></div>
        <div class="app-text">
          <strong>数字孪生</strong>
          <small>M607B · 空间化入口</small>
        </div>
        <span class="migration">Future Native</span>
      </button>

      <button class="app-tile future" type="button" @click="$router.push('/hbos/apps')">
        <div class="app-icon more"><AppstoreAddOutlined /></div>
        <div class="app-text">
          <strong>更多应用</strong>
          <small>App Registry 自动扩展</small>
        </div>
        <span class="migration">Registry</span>
      </button>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, type Component } from 'vue'
import { useRouter } from 'vue-router'
import {
  AppstoreAddOutlined,
  ClockCircleOutlined,
  ExperimentOutlined,
  InboxOutlined,
  NodeIndexOutlined,
  RightOutlined,
  ToolOutlined,
} from '@ant-design/icons-vue'
import type { AppManifestDTO, AppMigrationMode } from '@/contracts/portal'

const props = defineProps<{ apps: AppManifestDTO[] }>()
const router = useRouter()

const iconMap: Record<string, Component> = {
  ExperimentOutlined,
  InboxOutlined,
  ClockCircleOutlined,
  ToolOutlined,
}
const primaryApps = computed(() =>
  props.apps.filter((app) => ['lims', 'inventory', 'attendance', 'equipment'].includes(app.id)),
)

function migrationLabel(mode: AppMigrationMode) {
  return { legacy: 'Legacy', hybrid: 'Hybrid', native: 'Native' }[mode]
}
function open(route: string) {
  if (route === '/hbos/lims') void router.push(route)
  else void router.push('/hbos/apps')
}
</script>
