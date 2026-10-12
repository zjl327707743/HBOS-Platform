<template>
  <div class="portal-page production-shell-page">
    <a class="skip-link" href="#production-main-content">跳到生产看板主要内容</a>
    <PointerAtmosphere />
    <div class="aurora aurora-a"></div>
    <div class="aurora aurora-b"></div>
    <div class="aurora aurora-c"></div>

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
          <!-- 会话态与 KnowledgeTwinLayout / LimsLayout 同款：交给 usePortalSession ——
               它负责未登录跳登录页、无权限跳 403、其余渲染错误条。
               不在这里自己读 store 内部字段拼错误态（旧写法，会和会话逻辑打架）。 -->
          <a-skeleton v-if="sessionPending" active :paragraph="{ rows: 6 }" />
          <a-alert
            v-else-if="sessionError"
            type="error"
            show-icon
            class="portal-bootstrap-error"
            :message="sessionError"
          />
          <RouterView v-else :key="portal.user?.id" />
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
import { usePortalSession } from '@/composables/usePortalSession'
import { PRODUCTION_NAV_GROUPS, PRODUCTION_CENTER_PATH } from '@/data/productionNav'

const portal = usePortalStore()
const commandOpen = ref(false)
const { sessionPending, sessionError } = usePortalSession()

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

onMounted(() => window.addEventListener('keydown', shortcut))
onBeforeUnmount(() => window.removeEventListener('keydown', shortcut))
</script>

<style scoped>
/* 版面类（portal-page / portal-shell / app-layout-grid / app-route-content /
   app-local-sidebar）取自 global.css，与 PortalLayout / LimsLayout 同源，
   这里不重复定义 —— 生产看板不新增全局样式，避免碰共享 CSS。 */
.production-shell-page :deep(.app-local-sidebar) {
  border-left: 3px solid transparent;
  border-image: var(--hbos-domain-production, linear-gradient(180deg, #458eff, #5d64ff)) 1;
}
</style>
