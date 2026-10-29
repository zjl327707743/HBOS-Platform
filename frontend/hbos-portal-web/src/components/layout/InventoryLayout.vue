<template>
  <div class="portal-page">
    <a class="skip-link" href="#inventory-main-content">跳到仓储库存主要内容</a>
    <PointerAtmosphere />
    <div class="aurora aurora-a inventory-aurora"></div>
    <div class="aurora aurora-b"></div>

    <div class="portal-shell">
      <GlobalHeader
        :avatar-text="sessionBlocked ? '?' : portal.user?.avatarText || 'HB'"
        :avatar-url="sessionBlocked ? undefined : portal.user?.avatarUrl"
        :company-logo-url="portal.branding?.logoUrl"
        :apps="portal.apps"
        :session-blocked="sessionBlocked"
        context-label="仓储库存"
        @open-command="!sessionBlocked && (commandOpen = true)"
      />

      <div class="app-layout-grid">
        <InventoryLocalSidebar :style="sessionBlocked ? { visibility: 'hidden' } : undefined" :inert="sessionBlocked || undefined" />
        <main id="inventory-main-content" class="app-route-content" tabindex="-1">
          <SessionContent :pending="sessionPending" :ready="sessionReady" :blocked="sessionBlocked" :generation="sessionGeneration" :error="sessionError" @retry="synchronize"><RouterView /></SessionContent>
        </main>
      </div>
    </div>

    <MobileAppNav
      aria-label="仓储库存移动端导航"
      drawer-title="仓储库存导航"
      app-path="/hbos/inventory"
      quick-label="入库"
      :quick-icon="CameraOutlined"
      :quick-target="intakePath"
      :groups="mobileGroups"
    />
    <CommandPalette :open="commandOpen" @close="commandOpen = false" />
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { CameraOutlined } from '@ant-design/icons-vue'
import { usePortalStore } from '@/stores/portal'
import { usePortalSession } from '@/composables/usePortalSession'
import GlobalHeader from '@/components/layout/GlobalHeader.vue'
import SessionContent from '@/components/layout/SessionContent.vue'
import PointerAtmosphere from '@/components/layout/PointerAtmosphere.vue'
import InventoryLocalSidebar from '@/components/layout/InventoryLocalSidebar.vue'
import MobileAppNav, { type MobileNavGroup } from '@/components/layout/MobileDomainNav.vue'
import CommandPalette from '@/components/portal/CommandPalette.vue'
import ForbiddenView from '@/views/ForbiddenView.vue'
import {
  INVENTORY_NAV_GROUPS,
  INVENTORY_OVERVIEW_PATH,
  inventoryUnavailablePath,
} from '@/data/inventoryNav'
import { businessNavigationTarget } from '@/services/businessNavigation'

const portal = usePortalStore()
const commandOpen = ref(false)
const { sessionPending, sessionError, sessionReady, sessionBlocked, sessionGeneration, synchronize } = usePortalSession()

/**
 * 移动端「入库」快捷动作的目标。
 *
 * 从导航数据里取，不写死路径——写死的话导航改了这个快捷方式会**静默指向旧地址**
 * （此前它硬编码 `/hbos/inventory/unavailable/stock-entry`，于是入库快捷动作
 * 落到「这个功能的前端页还没有做出来」，而那张页早就做好了）。
 */
const intakePath = computed(
  () =>
    INVENTORY_NAV_GROUPS.flatMap((g) => g.items).find((i) => i.id === 'photo-intake')
      ?.stablePath || INVENTORY_OVERVIEW_PATH,
)

// 移动端菜单与桌面侧边栏同源，避免两处清单漂移
const mobileGroups = computed<MobileNavGroup[]>(() =>
  INVENTORY_NAV_GROUPS.map((group) => ({
    label: group.label,
    items: group.items.map((item) => {
      if (!item.implemented) {
        return { label: item.label, to: inventoryUnavailablePath(item.id) }
      }
      if (item.stablePath === INVENTORY_OVERVIEW_PATH) {
        return { label: item.label, to: INVENTORY_OVERVIEW_PATH }
      }
      // 尚未前端化的入口会离开 SPA，可能拿到跨源绝对地址
      return {
        label: item.label,
        to: businessNavigationTarget(item.stablePath || ''),
      }
    }),
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
