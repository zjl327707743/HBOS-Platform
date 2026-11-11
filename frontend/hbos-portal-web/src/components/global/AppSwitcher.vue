<template>
  <a-popover
    v-model:open="opened"
    trigger="click"
    placement="bottomRight"
    :overlay-class-name="portalDesign ? 'hbos-app-switcher-overlay v10-switcher-overlay' : 'hbos-app-switcher-overlay'"
  >
    <template #content>
      <div ref="panel" class="app-switcher-panel" @keydown.esc="onEscape">
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

          <button v-if="!portalDesign" type="button" class="app-switcher-item" @click="go('/hbos/apps')">
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
        ref="trigger"
        class="top-icon-button"
        @keydown.esc="onEscape"
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
import { iconMap } from '@/components/appIcons'
import { computed, nextTick, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  AppstoreOutlined,
  NodeIndexOutlined,
} from '@ant-design/icons-vue'
import type { AppManifestDTO } from '@/contracts/portal'
import { openBusinessRoute } from '@/services/businessNavigation'

const props = defineProps<{ apps: AppManifestDTO[]; portalDesign?: boolean }>()
const router = useRouter(), route = useRoute()
const opened = ref(false)
const panel = ref<HTMLElement | null>(null)
const trigger = ref<{ $el: HTMLElement } | null>(null)
function close(focus = false) {
  if (!opened.value) return
  opened.value = false
  if (focus) trigger.value?.$el?.focus()
}
function onEscape(event: KeyboardEvent) {
  if (!opened.value || event.isComposing) return
  event.preventDefault()
  event.stopPropagation()
  close(true)
}
watch(opened, async value => {
  if (!value || !props.portalDesign) return
  await nextTick()
  panel.value?.querySelector<HTMLElement>('button')?.focus()
})
watch(() => route.fullPath, () => close())

const visibleApps = computed(() =>
  props.apps.filter((app) => ['knowledge', 'twin', 'lims', 'inventory', 'attendance', 'equipment', 'production'].includes(app.id)),
)

function go(path: string) {
  close()
  void router.push(path)
}

function openApp(app: AppManifestDTO) {
  close()
  void openBusinessRoute(router, app.id, app.route)
}
</script>
