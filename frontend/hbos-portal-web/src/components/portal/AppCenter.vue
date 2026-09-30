<template>
  <section class="section-panel glass-surface app-center">
    <div class="section-head">
      <div>
        <span class="section-kicker">APPLICATIONS</span>
        <h2>应用中心</h2>
        <p>从这里进入当前账号可使用的业务应用。</p>
      </div>
      <a-button type="link" @click="$router.push('/hbos/apps')">全部应用 <RightOutlined /></a-button>
    </div>

    <div class="app-grid refined-app-grid">
      <button
        v-for="app in primaryApps"
        :key="app.id"
        class="app-tile"
        :class="{ 'digital-twin-app': app.id === 'twin' }"
        type="button"
        @click="open(app)"
      >
        <div class="app-icon" :class="app.accent">
          <component :is="iconMap[app.icon]" />
        </div>
        <div class="app-text">
          <strong>{{ displayTitle(app) }}</strong>
          <small>{{ app.meta || app.description }}</small>
        </div>
        <a-badge v-if="app.pendingCount" :count="app.pendingCount" class="pending-badge" />
      </button>

      <button class="app-tile future" type="button" @click="$router.push('/hbos/apps')">
        <div class="app-icon more"><AppstoreAddOutlined /></div>
        <div class="app-text">
          <strong>更多应用</strong>
          <small>查看全部可用应用</small>
        </div>
      </button>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, type Component } from 'vue'
import { useRouter } from 'vue-router'
import {
  AppstoreAddOutlined,
  BulbOutlined,
  ClockCircleOutlined,
  DeploymentUnitOutlined,
  ExperimentOutlined,
  InboxOutlined,
  ReadOutlined,
  RightOutlined,
  ToolOutlined,
} from '@ant-design/icons-vue'
import type { AppManifestDTO } from '@/contracts/portal'
import { openBusinessRoute } from '@/services/businessNavigation'

const props = defineProps<{ apps: AppManifestDTO[] }>()
const router = useRouter()

const iconMap: Record<string, Component> = {
  ExperimentOutlined,
  InboxOutlined,
  ClockCircleOutlined,
  ToolOutlined,
  ReadOutlined,
  BulbOutlined,
  DeploymentUnitOutlined,
}
const appOrder = ['lims', 'inventory', 'attendance', 'knowledge', 'equipment', 'twin']
const primaryApps = computed(() => props.apps
  .filter((app) => appOrder.includes(app.id))
  .sort((left, right) => appOrder.indexOf(left.id) - appOrder.indexOf(right.id)))

function displayTitle(app: AppManifestDTO) {
  return ({
    attendance: '考勤',
    inventory: '仓储',
    knowledge: '知识助理',
    equipment: '设备',
    twin: '数字孪生',
  } as Record<string, string>)[app.id] || app.shortTitle
}
function open(app: AppManifestDTO) {
  void openBusinessRoute(router, app.id, app.route)
}
</script>
