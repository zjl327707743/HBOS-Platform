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
        :company-logo-url="portal.branding?.logoUrl"
        :context-label="portal.branding?.workspaceName"
        :apps="portal.apps"
        @open-command="ui.commandOpen = true"
      />

      <div class="portal-layout-grid">
        <PortalSidebar :work-count="actionableCount" />
        <main id="main-content" class="portal-route-content" tabindex="-1">
          <a-alert
            v-if="portal.bootstrapError"
            type="error"
            show-icon
            class="portal-bootstrap-error"
            :message="portal.bootstrapError"
          />
          <RouterView v-else />
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
  if (!portal.user) {
    try {
      await portal.bootstrap()
    } catch {
      // Error state is rendered in the shell. No raw exception reaches the UI.
    }
  }
  window.addEventListener('keydown', onShortcut)
})
onBeforeUnmount(() => window.removeEventListener('keydown', onShortcut))
</script>
