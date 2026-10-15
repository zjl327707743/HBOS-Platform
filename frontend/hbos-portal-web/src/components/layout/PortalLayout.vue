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
          <a-skeleton v-if="sessionPending" active :paragraph="{ rows: 6 }" />
          <a-alert
            v-else-if="sessionError"
            type="error"
            show-icon
            class="portal-bootstrap-error"
            :message="sessionError"
          />
          <FirstPasswordGate v-else-if="securityUser" :key="securityUser" :subject-user="securityUser" @blocked="sessionReady = false; clearIamAccess()" @ready="finishSession"><RouterView v-if="sessionReady" :key="portal.user?.id" /><a-skeleton v-else active /></FirstPasswordGate>
          <RouterView v-else-if="portalDataSource === 'mock'" :key="portal.user?.id" />
        </main>
      </div>
    </div>

    <MobilePortalNav :work-count="actionableCount" />

    <CommandPalette :open="ui.commandOpen" @close="ui.commandOpen = false" />
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import { usePortalStore } from '@/stores/portal'
import GlobalHeader from '@/components/layout/GlobalHeader.vue'
import PointerAtmosphere from '@/components/layout/PointerAtmosphere.vue'
import PortalSidebar from '@/components/layout/PortalSidebar.vue'
import MobilePortalNav from '@/components/layout/MobilePortalNav.vue'
import CommandPalette from '@/components/portal/CommandPalette.vue'
import { usePortalSession } from '@/composables/usePortalSession'
import { useRoute, useRouter } from 'vue-router'
import { portalDataSource } from '@/services/portalProvider'
import { getIamSecurity } from '@/services/iamAccount'
import { clearIamAccess, loadIamAccess } from '@/services/iamAccess'
import { isUnauthenticatedError } from '@/services/frappeClient'
import { accountRedirect } from '@/services/accountNavigation'
import FirstPasswordGate from '@/components/account/FirstPasswordGate.vue'

const portal = usePortalStore()
const ui = reactive({ commandOpen: false })
const actionableCount = computed(() => portal.tasks.filter((task) => task.status === 'open').length)
const { sessionPending, sessionError } = portalDataSource === 'mock' ? usePortalSession() : { sessionPending: ref(true), sessionError: ref<string | null>(null) }
const route = useRoute(), router = useRouter(), securityUser = ref(''), sessionReady = ref(false)
let disposed = false, checking = false, bootstrapping = false
async function finishSession() {
  if (disposed || bootstrapping) return
  bootstrapping = true
  try { await portal.bootstrap(); if (disposed) return; if (portal.user?.id !== securityUser.value) throw new Error('当前会话已改变，请重新核对。'); try { await loadIamAccess(securityUser.value) } catch { /* Keep the failed capability state; ordinary workspace uses its own server gates. */ }; sessionReady.value = true }
  catch (e) { await sessionFailure(e) } finally { bootstrapping = false }
}
async function sessionFailure(error: unknown) {
  sessionReady.value = false; portal.clearSession(); clearIamAccess()
  if (isUnauthenticatedError(error)) { portal.clearSession(); securityUser.value = ''; await router.replace({path:'/hbos/login',query:{status:'session_required',redirect_to:accountRedirect(route.fullPath)}}) }
  else sessionError.value = error instanceof Error ? error.message : '当前会话暂时无法确认，请重试。'
}
async function synchronize() {
  if (disposed || checking || portalDataSource !== 'frappe') return
  checking = true; sessionPending.value = true; sessionError.value = null
  try { const security = await getIamSecurity(); if (disposed) return; if (portal.user?.id && portal.user.id !== security.user) { portal.clearSession(); clearIamAccess() }; securityUser.value = security.user; if (security.first_password_required) { portal.clearSession(); sessionReady.value = false; clearIamAccess() } else await finishSession() }
  catch (e) { if (!disposed) await sessionFailure(e) } finally { if (!disposed) sessionPending.value = false; checking = false }
}
const resume = () => { if (document.visibilityState !== 'hidden') void synchronize() }

function onShortcut(event: KeyboardEvent) {
  if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k') {
    event.preventDefault()
    ui.commandOpen = true
  }
  if (event.key === 'Escape') ui.commandOpen = false
}

onMounted(() => { window.addEventListener('keydown', onShortcut); if (portalDataSource === 'frappe') { void synchronize(); window.addEventListener('focus',resume); window.addEventListener('pageshow',resume); document.addEventListener('visibilitychange',resume) } })
onBeforeUnmount(() => { disposed = true; clearIamAccess(); window.removeEventListener('keydown', onShortcut); window.removeEventListener('focus',resume); window.removeEventListener('pageshow',resume); document.removeEventListener('visibilitychange',resume) })
</script>
