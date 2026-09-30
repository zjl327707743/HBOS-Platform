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
        :company-logo-url="portal.branding?.logoUrl"
        :apps="portal.apps"
        context-label="LIMS"
        @open-command="commandOpen = true"
      />

      <div class="app-layout-grid">
        <AppLocalSidebar />
        <main id="lims-main-content" class="app-route-content" tabindex="-1">
          <a-skeleton v-if="sessionPending" active :paragraph="{ rows: 6 }" />
          <a-alert
            v-else-if="sessionError"
            type="error"
            show-icon
            :message="sessionError"
          />
          <RouterView v-else />
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
import { usePortalSession } from '@/composables/usePortalSession'

const portal = usePortalStore()
const commandOpen = ref(false)
const { sessionPending, sessionError } = usePortalSession()

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
