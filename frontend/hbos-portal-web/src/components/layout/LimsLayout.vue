<template>
  <div class="portal-page">
    <PointerAtmosphere />
    <div class="aurora aurora-a lims-aurora"></div>
    <div class="aurora aurora-b"></div>

    <div class="portal-shell">
      <GlobalHeader
        :avatar-text="portal.user?.avatarText || 'HB'"
        :apps="portal.apps"
        context-label="LIMS"
        @open-command="commandOpen = true"
      />

      <div class="app-layout-grid">
        <AppLocalSidebar />
        <main class="app-route-content">
          <RouterView />
        </main>
      </div>
    </div>

    <CommandPalette :open="commandOpen" @close="commandOpen = false" />
  </div>
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { usePortalStore } from '@/stores/portal'
import GlobalHeader from '@/components/layout/GlobalHeader.vue'
import PointerAtmosphere from '@/components/layout/PointerAtmosphere.vue'
import AppLocalSidebar from '@/components/layout/AppLocalSidebar.vue'
import CommandPalette from '@/components/portal/CommandPalette.vue'

const portal = usePortalStore()
const commandOpen = ref(false)

function shortcut(event: KeyboardEvent) {
  if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k') {
    event.preventDefault()
    commandOpen.value = true
  }
  if (event.key === 'Escape') commandOpen.value = false
}
onMounted(async () => {
  if (!portal.user) await portal.bootstrap()
  window.addEventListener('keydown', shortcut)
})
onBeforeUnmount(() => window.removeEventListener('keydown', shortcut))
</script>
