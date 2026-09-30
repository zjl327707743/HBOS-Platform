<template>
  <div class="portal-page">
    <a class="skip-link" href="#kt-main-content">跳到主要内容</a>
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
        :context-label="contextLabel"
        @open-command="commandOpen = true"
      />
      <div class="kt-layout-grid">
        <KnowledgeTwinSidebar />
        <main id="kt-main-content" class="kt-route-content" tabindex="-1">
          <a-skeleton v-if="sessionPending" active :paragraph="{ rows: 6 }" />
          <a-alert
            v-else-if="sessionError"
            type="error"
            show-icon
            :message="sessionError"
            class="kt-bootstrap-error"
          />
          <RouterView v-else />
        </main>
      </div>
    </div>
    <CommandPalette :open="commandOpen" @close="commandOpen = false" />
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { usePortalStore } from '@/stores/portal'
import GlobalHeader from '@/components/layout/GlobalHeader.vue'
import PointerAtmosphere from '@/components/layout/PointerAtmosphere.vue'
import KnowledgeTwinSidebar from '@/components/layout/KnowledgeTwinSidebar.vue'
import CommandPalette from '@/components/portal/CommandPalette.vue'
import { usePortalSession } from '@/composables/usePortalSession'

const portal = usePortalStore()
const route = useRoute()
const commandOpen = ref(false)
const contextLabel = computed(() => route.path.startsWith('/hbos/twin') ? '设备与工艺' : '知识助理')
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

<style scoped>
.kt-layout-grid {
  display: grid;
  grid-template-columns: 224px minmax(0, 1fr);
  gap: 18px;
  margin-top: 18px;
}
.kt-route-content { min-width: 0; }
.kt-bootstrap-error { border-radius: 16px; }
@media (max-width: 900px) {
  .kt-layout-grid { grid-template-columns: 1fr; }
}
</style>
