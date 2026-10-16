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
          <KnowledgeSidebar :can-maintain="canMaintain" :maintenance="isMaintenance" />
          <main id="kt-main-content" class="kb-main" tabindex="-1" :aria-busy="sessionPending || permissionPending">
            <a-skeleton v-if="sessionPending || permissionPending" active :paragraph="{rows:6}" />
            <a-alert v-if="sessionError" type="error" show-icon :message="sessionError" />
            <a-result v-if="!sessionPending && !permissionPending && isMaintenance && !canMaintain" status="403" title="当前账号没有知识维护权限" />
            <div v-if="portal.user && !sessionError" v-show="!sessionPending && !permissionPending && (!isMaintenance || canMaintain)">
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
import { useRoute } from 'vue-router'
import { usePortalStore } from '@/stores/portal'
import '@/styles/knowledge.css'
import zhCN from 'ant-design-vue/es/locale/zh_CN'
import { hbosAntdTheme } from '@/theme/antdTheme'
import { getKnowledgeStatus } from '@/services/p1Api'
import KnowledgeHeader from '@/components/layout/KnowledgeHeader.vue'
import KnowledgeSidebar from '@/components/layout/KnowledgeSidebar.vue'
import GlobalHeader from '@/components/layout/GlobalHeader.vue'
import PointerAtmosphere from '@/components/layout/PointerAtmosphere.vue'
import KnowledgeTwinSidebar from '@/components/layout/KnowledgeTwinSidebar.vue'
import CommandPalette from '@/components/portal/CommandPalette.vue'
import { usePortalSession } from '@/composables/usePortalSession'

const portal = usePortalStore()
const route = useRoute()
const commandOpen = ref(false)
const isTwin = computed(() => route.path.startsWith('/hbos/twin'))
const isMaintenance = computed(() => route.path.startsWith('/hbos/knowledge/maintenance'))
const canMaintain = ref(false)
const knowledgeTheme = { ...hbosAntdTheme, token: { ...hbosAntdTheme.token, colorPrimary:'#159b89', colorLink:'#159b89' } }
const { sessionPending, sessionError } = usePortalSession()
const permissionPending = ref(false), sessionRevision = ref(0)
watch(sessionPending, (pending, previous) => { if (!pending && previous) sessionRevision.value++ })
let permissionEpoch = 0
watch(() => [portal.user?.id, route.path, sessionPending.value], async () => {
  const epoch = ++permissionEpoch
  canMaintain.value = false
  permissionPending.value = false
  if (!portal.user?.id || isTwin.value || sessionPending.value) return
  permissionPending.value = true
  try { const status = await getKnowledgeStatus(); if (epoch === permissionEpoch) canMaintain.value = Boolean(status.can_maintain) } catch { /* permissions remain closed */ }
  finally { if (epoch === permissionEpoch) permissionPending.value = false }
}, { immediate: true })
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
@media (max-width: 900px) {
  .kt-layout-grid { grid-template-columns: 1fr; }
}
</style>
