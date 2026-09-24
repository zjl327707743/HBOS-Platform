<template>
  <div class="portal-page">
    <a class="skip-link" href="#main-content">跳到主要内容</a>
    <PointerAtmosphere />
    <div class="aurora aurora-a"></div>
    <div class="aurora aurora-b"></div>
    <div class="aurora aurora-c"></div>

    <div class="portal-shell">
      <GlobalHeader
        :avatar-text="portal.user?.avatarText || 'HB'"
        :avatar-url="portal.user?.avatarUrl"
        :apps="portal.apps"
        @open-command="ui.commandOpen = true"
      />

      <div class="portal-layout-grid">
        <PortalSidebar :work-count="actionableCount" />
        <main id="main-content" class="portal-route-content" tabindex="-1">
          <RouterView />
        </main>
      </div>
    </div>

    <MobilePortalNav :work-count="actionableCount" />

    <CommandPalette :open="ui.commandOpen" @close="ui.commandOpen = false" />
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, reactive } from 'vue'
import { usePortalStore } from '@/stores/portal'
import GlobalHeader from '@/components/layout/GlobalHeader.vue'
import PointerAtmosphere from '@/components/layout/PointerAtmosphere.vue'
import PortalSidebar from '@/components/layout/PortalSidebar.vue'
import MobilePortalNav from '@/components/layout/MobilePortalNav.vue'
import CommandPalette from '@/components/portal/CommandPalette.vue'

const portal = usePortalStore()
const ui = reactive({ commandOpen: false })
const actionableCount = computed(() => portal.tasks.filter((task) => task.status === 'open').length)

function onShortcut(event: KeyboardEvent) {
  if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k') {
    event.preventDefault()
    ui.commandOpen = true
  }
  if (event.key === 'Escape') ui.commandOpen = false
}

onMounted(async () => {
  if (!portal.user) await portal.bootstrap()
  window.addEventListener('keydown', onShortcut)
})
onBeforeUnmount(() => window.removeEventListener('keydown', onShortcut))
</script>
