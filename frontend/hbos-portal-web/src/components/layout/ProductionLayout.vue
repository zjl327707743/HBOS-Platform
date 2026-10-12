<template>
  <div class="portal-page production-shell-page">
    <a class="skip-link" href="#production-main-content">跳到生产看板主要内容</a>
    <PointerAtmosphere />
    <div class="aurora aurora-a production-aurora"></div>
    <div class="aurora aurora-b"></div>

    <div class="portal-shell">
      <GlobalHeader
        :avatar-text="portal.user?.avatarText || 'HB'"
        :avatar-url="portal.user?.avatarUrl"
        :company-logo-url="portal.branding?.logoUrl"
        :apps="portal.apps"
        context-label="生产看板"
        @open-command="commandOpen = true"
      />

      <div class="app-layout-grid">
        <ProductionLocalSidebar />
        <main id="production-main-content" class="app-route-content" tabindex="-1">
          <!-- 与 PortalLayout / InventoryLayout 同款错误处理。 -->
          <ForbiddenView v-if="portal.bootstrapErrorStatus === 403" />
          <a-alert
            v-else-if="portal.bootstrapError"
            type="error"
            show-icon
            class="portal-bootstrap-error"
            :message="portal.bootstrapError"
          />
          <RouterView v-else />
        </main>
      </div>
    </div>

    <MobileAppNav
      aria-label="生产看板移动端导航"
      drawer-title="生产看板导航"
      app-path="/hbos/production"
      quick-label="管理中心"
      :quick-icon="LineChartOutlined"
      :quick-target="PRODUCTION_CENTER_PATH"
      :groups="mobileGroups"
    />
    <CommandPalette :open="commandOpen" @close="commandOpen = false" />
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { LineChartOutlined } from '@ant-design/icons-vue'
import { usePortalStore } from '@/stores/portal'
import GlobalHeader from '@/components/layout/GlobalHeader.vue'
import PointerAtmosphere from '@/components/layout/PointerAtmosphere.vue'
import ProductionLocalSidebar from '@/components/layout/ProductionLocalSidebar.vue'
import MobileAppNav, { type MobileNavGroup } from '@/components/layout/MobileAppNav.vue'
import CommandPalette from '@/components/portal/CommandPalette.vue'
import ForbiddenView from '@/views/ForbiddenView.vue'
import { PRODUCTION_NAV_GROUPS, PRODUCTION_CENTER_PATH } from '@/data/productionNav'

const portal = usePortalStore()
const commandOpen = ref(false)

// 移动端菜单与桌面侧边栏同源，避免两处清单漂移（同 InventoryLayout 的做法）
const mobileGroups = computed<MobileNavGroup[]>(() =>
  PRODUCTION_NAV_GROUPS.map((group) => ({
    label: group.label,
    items: group.items.map((item) => ({ label: item.label, to: item.stablePath })),
  })),
)

function shortcut(event: KeyboardEvent) {
  if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k') {
    event.preventDefault()
    commandOpen.value = true
  }
  if (event.key === 'Escape') commandOpen.value = false
}

onMounted(async () => {
  if (!portal.user) {
    try {
      await portal.bootstrap()
    } catch {
      // Portal shell 负责渲染已归一化的错误态，原始异常不进界面。
    }
  }
  window.addEventListener('keydown', shortcut)
})
onBeforeUnmount(() => window.removeEventListener('keydown', shortcut))
</script>
