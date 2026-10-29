<template>
  <div class="portal-page" :class="{ 'r6-experience': r6Experience, 'r6-personal': personal, 'r6-fit': fitPage, 'r6-natural': naturalPanels, 'motion-paused': motionPaused }" :data-document-instance="development ? frappeDiagnostics.document : undefined" :data-session-phase="development ? portalSession.phase : undefined" :data-security-reads="development ? frappeDiagnostics.security : undefined" :data-capability-reads="development ? frappeDiagnostics.capabilities : undefined" :data-bootstrap-reads="development ? frappeDiagnostics.bootstrap : undefined" :data-session-resumes="development ? portalSession.resumeEvents : undefined" :data-session-generation="development ? portalSession.generation : undefined">
    <a class="skip-link" href="#main-content">跳到主要内容</a>
    <PointerAtmosphere :paused="motionPaused" />
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
        :management-experience="r6Experience"
        :motion-paused="motionPaused"
        @toggle-motion="motionPaused = !motionPaused"
        @open-command="!masked && (ui.commandOpen = true)"
      />

      <div class="portal-layout-grid">
        <PortalSidebar v-if="!personal" :management="r6Experience" :work-count="actionableCount" :class="{ 'session-content-hidden': masked }" :inert="masked || undefined" />
        <main id="main-content" ref="mainContent" class="portal-route-content" tabindex="-1">
          <template v-if="portalDataSource === 'mock'">
            <a-skeleton v-if="sessionPending" active /><a-alert v-else-if="sessionError" type="error" :message="sessionError" /><RouterView v-else :key="portal.user?.id" />
          </template>
          <template v-else>
            <div v-if="portalSession.phase === 'checking' && portalSession.slow && !masked" class="session-checking" role="status">
              <a-spin size="small" /> 正在核对登录状态：可继续浏览，草稿、筛选与滚动位置不会丢失；提交将在核验完成后恢复。
            </div>
            <div v-if="masked" class="session-recovery" role="status">
              <a-alert type="warning" show-icon :message="routeDenied ? '当前账号已无此页面的管理权限，不能继续办理。可返回工作台或退出登录。' : portalSession.error || '正在重新核对登录状态，页面内容暂时隐藏，草稿仍保留。'" />
              <RouterLink v-if="routeDenied" to="/hbos">返回工作台</RouterLink>
              <a-button :loading="portalSession.phase === 'checking'" @click="retrySession">重试核验</a-button>
              <a-button @click="recoverLogout">退出当前账号</a-button>
              <a-button v-if="portalSession.phase === 'unconfirmed'" @click="returnToLogin">前往登录页</a-button>
            </div>
            <div v-if="portalSession.security?.first_password_required" :class="{ 'session-content-hidden': masked }" :inert="masked || undefined"><FirstPasswordGate :key="portalSession.generation" :subject-user="portalSession.security.user" :security="portalSession.security" @ready="retrySession" /></div>
            <div v-if="portalSession.mounted" :key="portalSession.generation" class="session-content" :class="{ 'session-content-hidden': masked }" :inert="masked || undefined" :aria-hidden="masked || undefined">
              <RouterView v-slot="{ Component }"><KeepAlive include="HbosManagementWorkspace" :max="1"><component :is="Component" /></KeepAlive></RouterView>
            </div>
            <a-skeleton v-else-if="(!portalSession.security && portalSession.phase === 'initial') || portalSession.phase === 'logging_out'" active :paragraph="{ rows: 6 }" />
          </template>
        </main>
      </div>
    </div>

    <MobilePortalNav v-if="!r6Experience" :work-count="actionableCount" :class="{ 'session-content-hidden': masked }" :inert="masked || undefined" />

    <CommandPalette :open="ui.commandOpen" @close="ui.commandOpen = false" />
    <aside v-if="developmentObservation" class="development-observation" aria-label="本机验收观测">
      <details><summary>本机验收观测（开发模式）</summary><output>文档 {{ frappeDiagnostics.document }}；安全读取 {{ frappeDiagnostics.security }}；能力读取 {{ frappeDiagnostics.capabilities }}；业务初始化 {{ frappeDiagnostics.bootstrap }}；恢复事件 {{ portalSession.resumeEvents }}；主体代次 {{ portalSession.generation }}；阶段 {{ portalSession.phase }}</output>
      <output>路由 {{ route.path }}；考勤实例 {{ attendanceObservation.instance }}；挂载/卸载 {{ attendanceObservation.mounts }}/{{ attendanceObservation.unmounts }}；查询/完成/丢弃 {{ attendanceObservation.requests }}/{{ attendanceObservation.completed }}/{{ attendanceObservation.stale }}；权限触发 {{ attendanceObservation.permissions }}；关联 {{ attendanceObservation.request }}；草稿 {{ attendanceObservation.draft }}；已应用 {{ attendanceObservation.applied }}；结果范围 {{ attendanceObservation.range }}；时序 {{ attendanceObservation.events.join('，') }}</output></details>
    </aside>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch, nextTick } from 'vue'
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
import { developmentObservation, frappeDiagnostics } from '@/services/frappeClient'
import FirstPasswordGate from '@/components/account/FirstPasswordGate.vue'
import { useReadablePanels } from '@/composables/useReadablePanels'
import { attendanceObservation } from '@/services/attendanceObservation'

const portal = usePortalStore()
const development = import.meta.env.DEV
const ui = reactive({ commandOpen: false })
const actionableCount = computed(() => portal.tasks.filter((task) => task.status === 'open').length)
const { sessionPending, sessionError } = portalDataSource === 'mock' ? usePortalSession() : { sessionPending: ref(true), sessionError: ref<string | null>(null) }
const route = useRoute(), router = useRouter()
const personal = computed(() => route.path === '/hbos/profile')
const r6Experience = computed(() => personal.value || route.path.startsWith('/hbos/admin'))
const fitPage = computed(() => ['/hbos/admin/departments', '/hbos/admin/roles'].includes(route.path))
const motionPaused = ref(false)
const mainContent = ref<HTMLElement | null>(null)
const naturalPanels = useReadablePanels(fitPage, mainContent)
watch(() => route.path, () => { if (mainContent.value) mainContent.value.scrollTop = 0 }, { flush: 'sync' })
const routeDenied = computed(() => portalSession.mounted && typeof route.meta.iamCapability === 'string' && !canIam(route.meta.iamCapability))
const masked = computed(() => ['unconfirmed', 'guest', 'logging_out'].includes(portalSession.phase) || routeDenied.value)
let maskedFocus: {element:HTMLElement;generation:number}|null = null
watch(masked, async value => {
  if(value && document.activeElement instanceof HTMLElement && document.activeElement !== document.body) maskedFocus={element:document.activeElement,generation:portalSession.generation}
  document.body.classList.toggle('hbos-session-shield', value)
  if(value) ui.commandOpen=false
  else {
    const prior=maskedFocus;maskedFocus=null;await nextTick()
    if(prior?.generation===portalSession.generation && prior.element.isConnected && !masked.value && portalSession.phase==='ready') prior.element.focus({preventScroll:true})
  }
}, { immediate:true })
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
.session-content{min-width:0;width:100%}.session-checking{display:flex;align-items:center;gap:8px;padding:8px 16px;font-size:14px;color:var(--hbos-text-secondary);background:var(--hbos-bg-surface)}.session-content-hidden{visibility:hidden;pointer-events:none}.session-recovery{display:flex;flex-wrap:wrap;gap:12px;padding:16px}.session-recovery .ant-alert{width:100%}
.development-observation{position:fixed;bottom:0;left:8px;z-index:2000;max-width:min(700px,90vw);padding:4px 8px;background:#fff;border:1px solid #ccd5e0;font-size:12px;max-height:35vh;overflow:auto}.development-observation output{display:block;overflow-wrap:anywhere}
:global(body.hbos-session-shield .ant-drawer),:global(body.hbos-session-shield .ant-modal-root),:global(body.hbos-session-shield .ant-popover){visibility:hidden!important;pointer-events:none!important}
</style>
