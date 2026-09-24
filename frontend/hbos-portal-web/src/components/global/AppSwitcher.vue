<template>
  <a-popover
    trigger="click"
    placement="bottomRight"
    overlay-class-name="hbos-app-switcher-overlay"
  >
    <template #content>
      <div class="app-switcher-panel">
        <div class="app-switcher-head">
          <div>
            <strong>应用</strong>
            <span>切换到你有权限访问的工作空间</span>
          </div>
          <a-button type="link" size="small" @click="go('/hbos/apps')">全部应用</a-button>
        </div>

        <div class="app-switcher-grid">
          <button
            v-for="app in visibleApps"
            :key="app.id"
            type="button"
            class="app-switcher-item"
            @click="openApp(app)"
          >
            <div class="app-switcher-icon" :class="app.accent">
              <component :is="iconMap[app.icon]" />
            </div>
            <div>
              <strong>{{ app.shortTitle }}</strong>
              <span>{{ app.meta || app.description }}</span>
            </div>
            <a-badge v-if="app.pendingCount" :count="app.pendingCount" />
          </button>

          <button type="button" class="app-switcher-item" @click="go('/hbos/apps')">
            <div class="app-switcher-icon digital-twin"><NodeIndexOutlined /></div>
            <div>
              <strong>数字孪生</strong>
              <span>空间化运营入口</span>
            </div>
          </button>
        </div>
      </div>
    </template>

    <a-tooltip title="应用">
      <a-button
        class="top-icon-button"
        type="text"
        shape="circle"
        aria-label="打开应用切换器"
      >
        <AppstoreOutlined />
      </a-button>
    </a-tooltip>
  </a-popover>
</template>

<script setup lang="ts">
import { computed, type Component } from 'vue'
import { useRouter } from 'vue-router'
import {
  AppstoreOutlined,
  ClockCircleOutlined,
  ExperimentOutlined,
  InboxOutlined,
  NodeIndexOutlined,
  ToolOutlined,
} from '@ant-design/icons-vue'
import type { AppManifestDTO } from '@/contracts/portal'

const props = defineProps<{ apps: AppManifestDTO[] }>()
const router = useRouter()

const iconMap: Record<string, Component> = {
  ExperimentOutlined,
  InboxOutlined,
  ClockCircleOutlined,
  ToolOutlined,
}

const visibleApps = computed(() =>
  props.apps.filter((app) => ['lims', 'inventory', 'attendance', 'equipment'].includes(app.id)),
)

function go(path: string) {
  void router.push(path)
}

function openApp(app: AppManifestDTO) {
  if (app.route === '/hbos/lims') {
    go(app.route)
    return
  }
  go('/hbos/apps')
}
</script>
