<template>
  <div class="portal-page">
    <a class="skip-link" href="#inventory-main-content">跳到仓储库存主要内容</a>
    <PointerAtmosphere />
    <div class="aurora aurora-a inventory-aurora"></div>
    <div class="aurora aurora-b"></div>

    <div class="portal-shell">
      <GlobalHeader
        :avatar-text="portal.user?.avatarText || 'HB'"
        :avatar-url="portal.user?.avatarUrl"
        :company-logo-url="portal.branding?.logoUrl"
        :apps="portal.apps"
        context-label="仓储库存"
        @open-command="commandOpen = true"
      />

      <div class="app-layout-grid">
        <InventoryLocalSidebar />
        <main id="inventory-main-content" class="app-route-content" tabindex="-1">
          <!--
            与 PortalLayout 同款错误处理。缺少这一段的话，bootstrap 失败时
            （会话失效、403、服务不可达）页面会**静默渲染成没有用户、没有提示**的空壳，
            用户只看到一句 axios 原始英文报错或干脆什么都没有。
            ForbiddenView 已经是现成组件，403 时直接用它。
          -->
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
import GlobalHeader from '@/components/layout/GlobalHeader.vue'
import PointerAtmosphere from '@/components/layout/PointerAtmosphere.vue'
import InventoryLocalSidebar from '@/components/layout/InventoryLocalSidebar.vue'
import MobileAppNav, { type MobileNavGroup } from '@/components/layout/MobileAppNav.vue'
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

onMounted(async () => {
  if (!portal.user) {
    try {
      await portal.bootstrap()
    } catch {
      // Portal shell 负责渲染已经归一化的错误态，原始异常不进界面。
    }
  }
  window.addEventListener('keydown', shortcut)
})
onBeforeUnmount(() => window.removeEventListener('keydown', shortcut))
</script>
