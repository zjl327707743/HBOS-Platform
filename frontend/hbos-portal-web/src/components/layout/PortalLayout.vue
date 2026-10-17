<template>
  <div class="portal-page" :data-session-resumes="development ? portalSession.resumeEvents : undefined" :data-session-generation="development ? portalSession.generation : undefined">
    <a class="skip-link" href="#main-content">跳到主要内容</a>
    <PointerAtmosphere />
    <div class="aurora aurora-a"></div>
    <div class="aurora aurora-b"></div>
    <div class="aurora aurora-c"></div>

    <div class="portal-shell">
      <GlobalHeader
        :avatar-text="masked ? '?' : portal.user?.avatarText || 'HB'"
        :avatar-url="masked ? undefined : portal.user?.avatarUrl"
        :company-logo-url="portal.branding?.logoUrl"
        :context-label="portal.branding?.workspaceName"
        :apps="portal.apps"
        :session-blocked="masked"
        @open-command="!masked && (ui.commandOpen = true)"
      />

      <div class="portal-layout-grid">
        <PortalSidebar :work-count="actionableCount" :class="{ 'session-content-hidden': masked }" :inert="masked || undefined" />
        <main id="main-content" class="portal-route-content" tabindex="-1">
          <template v-if="portalDataSource === 'mock'">
            <a-skeleton v-if="sessionPending" active /><a-alert v-else-if="sessionError" type="error" :message="sessionError" /><RouterView v-else :key="portal.user?.id" />
          </template>
          <template v-else>
            <div v-if="masked" class="session-recovery" role="status">
              <a-alert type="warning" show-icon :message="routeDenied ? '当前账号已无此页面的管理权限，不能继续办理。可返回工作台或退出登录。' : portalSession.error || '正在重新核对登录状态，页面内容暂时隐藏，草稿仍保留。'" />
              <RouterLink v-if="routeDenied" to="/hbos">返回工作台</RouterLink>
              <a-button :loading="portalSession.phase === 'checking'" @click="retrySession">重试核验</a-button>
              <a-button @click="recoverLogout">退出当前账号</a-button>
              <a-button v-if="portalSession.phase === 'unconfirmed'" @click="returnToLogin">前往登录页</a-button>
            </div>
            <div v-if="portalSession.security?.first_password_required" :class="{ 'session-content-hidden': masked }" :inert="masked || undefined"><FirstPasswordGate :key="portalSession.generation" :subject-user="portalSession.security.user" :security="portalSession.security" @ready="retrySession" /></div>
            <div v-if="portalSession.mounted" :key="portalSession.generation" class="session-content" :class="{ 'session-content-hidden': masked }" :inert="masked || undefined" :aria-hidden="masked || undefined">
              <RouterView />
            </div>
            <a-skeleton v-else-if="(!portalSession.security && portalSession.phase === 'initial') || portalSession.phase === 'logging_out'" active :paragraph="{ rows: 6 }" />
          </template>
        </main>
      </div>
    </div>

    <MobilePortalNav :work-count="actionableCount" :class="{ 'session-content-hidden': masked }" :inert="masked || undefined" />

    <CommandPalette :open="ui.commandOpen" @close="ui.commandOpen = false" />
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { usePortalStore } from '@/stores/portal'
import GlobalHeader from '@/components/layout/GlobalHeader.vue'
import PointerAtmosphere from '@/components/layout/PointerAtmosphere.vue'
import PortalSidebar from '@/components/layout/PortalSidebar.vue'
import MobilePortalNav from '@/components/layout/MobilePortalNav.vue'
import CommandPalette from '@/components/portal/CommandPalette.vue'
import { usePortalSession } from '@/composables/usePortalSession'
import { useRoute, useRouter } from 'vue-router'
import { portalDataSource } from '@/services/portalProvider'
import { attachPortalSession, ensurePortalSession, portalSession, resetPortalSession, signOutPortalSession } from '@/services/portalSessionCoordinator'
import { accountRedirect } from '@/services/accountNavigation'
import { canIam } from '@/services/iamAccess'
import { Modal } from 'ant-design-vue'
import FirstPasswordGate from '@/components/account/FirstPasswordGate.vue'

const portal = usePortalStore()
const development = import.meta.env.DEV
const ui = reactive({ commandOpen: false })
const actionableCount = computed(() => portal.tasks.filter((task) => task.status === 'open').length)
const { sessionPending, sessionError } = portalDataSource === 'mock' ? usePortalSession() : { sessionPending: ref(true), sessionError: ref<string | null>(null) }
const route = useRoute(), router = useRouter()
const routeDenied = computed(() => portalSession.mounted && typeof route.meta.iamCapability === 'string' && !canIam(route.meta.iamCapability))
const masked = computed(() => ['unconfirmed', 'guest', 'logging_out'].includes(portalSession.phase) || routeDenied.value)
watch(masked, value => { document.body.classList.toggle('hbos-session-shield', value); if(value) ui.commandOpen=false }, { immediate:true })
const closeSecurityDialogs = () => Modal.destroyAll()
let detach: (() => void) | undefined
async function retrySession() { try { await ensurePortalSession({ force: true }) } catch { /* Local recovery stays available. */ } }
async function recoverLogout() { try { await signOutPortalSession(); await router.replace({ path: '/hbos/login', query: { status: 'signed_out' } }) } catch { /* Do not claim a server logout without confirmation. */ } }
async function returnToLogin() { resetPortalSession(false); await router.replace({path:'/hbos/login',query:{status:'logout_unconfirmed',redirect_to:accountRedirect(route.fullPath)}}) }
watch(() => portalSession.phase, phase => {
  if (phase === 'guest' && portalDataSource === 'frappe') void router.replace({ path: '/hbos/login', query: { status: 'session_required', redirect_to: accountRedirect(route.fullPath) } })
})

function onShortcut(event: KeyboardEvent) {
  if (masked.value) return
  if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k') {
    event.preventDefault()
    ui.commandOpen = true
  }
  if (event.key === 'Escape') ui.commandOpen = false
}

onMounted(() => { window.addEventListener('keydown', onShortcut); window.addEventListener('hbos:session-boundary', closeSecurityDialogs); if (portalDataSource === 'frappe') { detach = attachPortalSession(); void ensurePortalSession().catch(() => undefined) } })
onBeforeUnmount(() => { window.removeEventListener('keydown', onShortcut); window.removeEventListener('hbos:session-boundary', closeSecurityDialogs); document.body.classList.remove('hbos-session-shield'); detach?.() })
</script>
<style scoped>
.session-content{min-width:0;width:100%}.session-content-hidden{visibility:hidden;pointer-events:none}.session-recovery{display:flex;flex-wrap:wrap;gap:12px;padding:16px}.session-recovery .ant-alert{width:100%}
:global(body.hbos-session-shield .ant-drawer),:global(body.hbos-session-shield .ant-modal-root),:global(body.hbos-session-shield .ant-popover){visibility:hidden!important;pointer-events:none!important}
</style>
