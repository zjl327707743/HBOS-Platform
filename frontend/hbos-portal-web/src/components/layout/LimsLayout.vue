<template>
  <div class="portal-page">
    <a class="skip-link" href="#lims-main-content">跳到 LIMS 主要内容</a>
    <PointerAtmosphere />
    <div class="aurora aurora-a lims-aurora"></div>
    <div class="aurora aurora-b"></div>

    <div class="portal-shell">
      <GlobalHeader
        :avatar-text="portal.user?.avatarText || 'HB'"
        :avatar-url="portal.user?.avatarUrl"
        :company-logo-url="portal.branding?.logoUrl || LIMS_BRANDING.companyLogoUrl"
        :group-logo-url="LIMS_BRANDING.groupLogoUrl"
        :apps="portal.apps"
        context-label="LIMS"
        @open-command="commandOpen = true"
      />

      <div class="app-layout-grid">
        <AppLocalSidebar />
        <main id="lims-main-content" class="app-route-content" tabindex="-1">
          <a-alert
            v-if="portal.bootstrapError"
            type="error"
            show-icon
            class="portal-bootstrap-error"
            :message="portal.bootstrapError"
          />
          <RouterView />
        </main>
      </div>
    </div>

    <MobileAppNav />

    <CommandPalette :open="commandOpen" @close="commandOpen = false" />
  </div>
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { usePortalStore } from '@/stores/portal'
import GlobalHeader from '@/components/layout/GlobalHeader.vue'
import PointerAtmosphere from '@/components/layout/PointerAtmosphere.vue'
import AppLocalSidebar from '@/components/layout/AppLocalSidebar.vue'
import MobileAppNav from '@/components/layout/MobileAppNav.vue'
import CommandPalette from '@/components/portal/CommandPalette.vue'
import { LIMS_BRANDING } from '@/data/limsBranding'

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
  if (!portal.user) {
    try {
      await portal.bootstrap()
    } catch {
      // Portal shell owns the sanitized bootstrap error state.
    }
  }
  window.addEventListener('keydown', shortcut)
})
onBeforeUnmount(() => window.removeEventListener('keydown', shortcut))
</script>
