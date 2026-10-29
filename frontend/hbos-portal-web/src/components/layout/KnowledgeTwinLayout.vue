<template>
  <div v-if="isTwin" class="portal-page">
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
          <RouterView v-else :key="portal.user?.id" />
        </main>
      </div>
    </div>
    <CommandPalette :open="commandOpen" @close="commandOpen = false" />
  </div>
  <a-config-provider v-else :theme="knowledgeTheme" :locale="zhCN">
    <div class="kb-scope kb-canvas">
      <div class="kb-candidate-note">本机验收候选 · 已共享资料可查阅</div>
      <a class="skip-link" href="#kt-main-content">跳到主要内容</a>
      <div class="kb-shell">
        <KnowledgeHeader :maintenance="isMaintenance" />
        <div class="kb-layout">
          <KnowledgeSidebar :can-maintain="permissionState === 'granted'" :maintenance="isMaintenance" />
          <main id="kt-main-content" class="kb-main" tabindex="-1" :aria-busy="sessionPending || sessionBlocked || permissionPending">
            <a-skeleton v-if="sessionPending || permissionPending" active :paragraph="{rows:6}" />
            <a-alert v-if="sessionError" type="error" show-icon :message="sessionError" />
            <a-result v-if="!sessionPending && !permissionPending && isMaintenance && permissionState === 'denied'" status="403" title="当前账号没有知识维护权限" />
            <div v-if="isMaintenance && !sessionPending && !permissionPending && permissionState === 'unknown'" class="kt-permission-unknown" role="alert">
              <p>维护权限状态暂时无法确认，这不是“没有权限”。当前网络或知识状态接口暂时不可用。</p>
              <a-button size="small" @click="checkPermission()">重试</a-button>
            </div>
            <div v-if="portal.user && !sessionError" v-show="!sessionPending && !permissionPending && (!isMaintenance || permissionState === 'granted')" :class="{ 'kb-session-masked': sessionBlocked }" :inert="sessionBlocked || undefined" :aria-hidden="sessionBlocked || undefined">
              <RouterView v-slot="{ Component }"><component :is="Component" :key="portal.user.id" :session-revision="sessionRevision" /></RouterView>
            </div>
          </main>
        </div>
      </div>
    </div>
  </a-config-provider>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { usePortalStore } from '@/stores/portal'
import '@/styles/knowledge.css'
import zhCN from 'ant-design-vue/es/locale/zh_CN'
import { hbosAntdTheme } from '@/theme/antdTheme'
import { getKnowledgeStatus, DomainApiError } from '@/services/p1Api'
import KnowledgeHeader from '@/components/layout/KnowledgeHeader.vue'
import KnowledgeSidebar from '@/components/layout/KnowledgeSidebar.vue'
import GlobalHeader from '@/components/layout/GlobalHeader.vue'
import PointerAtmosphere from '@/components/layout/PointerAtmosphere.vue'
import KnowledgeTwinSidebar from '@/components/layout/KnowledgeTwinSidebar.vue'
import CommandPalette from '@/components/portal/CommandPalette.vue'
import { usePortalSession } from '@/composables/usePortalSession'
import { portalSession } from '@/services/portalSessionCoordinator'
import { portalDataSource } from '@/services/portalProvider'
import { accountRedirect } from '@/services/accountNavigation'

const portal = usePortalStore()
const route = useRoute()
const router = useRouter()
const commandOpen = ref(false)
const isTwin = computed(() => route.path.startsWith('/hbos/twin'))
const isMaintenance = computed(() => route.path.startsWith('/hbos/knowledge/maintenance'))
const knowledgeTheme = { ...hbosAntdTheme, token: { ...hbosAntdTheme.token, colorPrimary:'#159b89', colorLink:'#159b89' } }
// ``sessionRevision`` comes from the composable and advances only after a
// *successful* re-verification, so a failed or transient resume does not look
// like an authorization change to the child views.
const { sessionPending, sessionError, sessionBlocked, sessionRevision } = usePortalSession()
const permissionPending = ref(false)
// 'unknown' is a status endpoint that failed for a reason other than an explicit
// denial. Rendering it as a 403 told real maintainers they had lost access.
const permissionState = ref<'unknown' | 'granted' | 'denied'>('unknown')
let permissionEpoch = 0
// Whether the current identity's permission has been answered at least once.
// A route change inside the knowledge workspace must not re-ask it.
let checkedPermission = false

function denial(error: unknown) {
  return error instanceof DomainApiError && ['FORBIDDEN', 'SCOPE_REJECTED', 'AUTHENTICATION_REQUIRED', 'CLIENT_AUTH_FAILED'].includes(error.code)
}

async function checkPermission() {
  const epoch = ++permissionEpoch
  if (!portal.user?.id || isTwin.value || sessionPending.value) return
  permissionPending.value = permissionState.value === 'unknown' && !checkedPermission
  try {
    const status = await getKnowledgeStatus()
    if (epoch !== permissionEpoch) return
    permissionState.value = status.can_maintain ? 'granted' : 'denied'
    checkedPermission = true
  } catch (error) {
    if (epoch !== permissionEpoch) return
    // Only an explicit denial is a 403; a service or network failure leaves the
    // state unknown and offers a retry instead of claiming the account lost it.
    permissionState.value = denial(error) ? 'denied' : 'unknown'
  } finally {
    if (epoch === permissionEpoch) permissionPending.value = false
  }
}

// An identity change invalidates the earlier answer; a mere route change within
// the knowledge workspace does not, so switching pages no longer re-asks the
// status endpoint or flashes a skeleton over the page.
watch(() => portal.user?.id, () => {
  checkedPermission = false
  permissionState.value = 'unknown'
  permissionPending.value = false
  void checkPermission()
}, { immediate: true })
watch([() => route.path, () => sessionPending.value], () => {
  if (checkedPermission || !portal.user?.id) return
  void checkPermission()
})
// A confirmed sign-out finishes at the login page, exactly as in PortalLayout.
// A transient failure leaves the phase 'unconfirmed' and keeps this page with
// its recovery control, so it is never mistaken for a revocation.
watch(() => portalSession.phase, phase => {
  if (phase === 'guest' && portalDataSource === 'frappe' && route.path.startsWith('/hbos/knowledge')) {
    void router.replace({ path: '/hbos/login', query: { status: 'session_required', redirect_to: accountRedirect(route.fullPath) } })
  }
})

const contextLabel = computed(() => route.path.startsWith('/hbos/twin') ? '设备与工艺' : '知识库')

function shortcut(event: KeyboardEvent) {
  if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k') {
    event.preventDefault()
    commandOpen.value = true
  }
  if (event.key === 'Escape') commandOpen.value = false
}

onMounted(() => window.addEventListener('keydown', shortcut))
onBeforeUnmount(() => { permissionEpoch++; window.removeEventListener('keydown', shortcut) })
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
/* A resume re-check hides what is on screen without destroying it: the answer,
   draft, filters and scroll position are all still there when it clears. */
.kb-session-masked { visibility: hidden; pointer-events: none; }
@media (max-width: 900px) {
  .kt-layout-grid { grid-template-columns: 1fr; }
}
</style>
