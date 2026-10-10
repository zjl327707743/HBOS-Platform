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
            v-if="shellError"
            type="error"
            show-icon
            class="portal-bootstrap-error"
            :message="shellError"
          >
            <template #action><a-button :loading="portal.loading" @click="retryBootstrap">重试</a-button></template>
          </a-alert>
          <a-skeleton v-else-if="sessionPending" active :paragraph="{ rows: 6 }" />
          <RouterView v-else :key="portal.user?.id" />
        </main>
      </div>
    </div>

    <MobileAppNav />

    <CommandPalette :open="commandOpen" @close="commandOpen = false" />
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { usePortalStore } from '@/stores/portal'
import GlobalHeader from '@/components/layout/GlobalHeader.vue'
import PointerAtmosphere from '@/components/layout/PointerAtmosphere.vue'
import AppLocalSidebar from '@/components/layout/AppLocalSidebar.vue'
import MobileAppNav from '@/components/layout/MobileAppNav.vue'
import CommandPalette from '@/components/portal/CommandPalette.vue'
import { LIMS_BRANDING } from '@/data/limsBranding'
import { usePortalSession } from '@/composables/usePortalSession'

const portal = usePortalStore()
const route = useRoute()
const router = useRouter()
const commandOpen = ref(false)
const { sessionPending, sessionError, synchronize } = usePortalSession()

// 会话探测或 bootstrap 失败时统一显示错误壳，并保留重试入口。
const shellError = computed(() => sessionError.value || portal.bootstrapError)

async function retryBootstrap() {
  const ok = await synchronize().catch(() => false)
  // 检查成功后强制重挂载，避免后台已恢复但子视图仍停在错误壳。
  if (ok) await router.replace({ path: route.path, query: route.query, hash: route.hash, force: true })
}

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
