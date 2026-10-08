<template>
  <div class="portal-page">
    <a class="skip-link" href="#attendance-main-content">跳到考勤主要内容</a>
    <PointerAtmosphere />
    <!-- 默认 aurora-a 就是紫罗兰 #8177ff，与考勤域色（--hbos-domain-attendance
         的 #6b60ff→#8c61ff）同族，故本应用不加 tints 变体。LIMS 需要是因为
         它的域色是青绿，与默认紫罗兰冲突。 -->
    <div class="aurora aurora-a"></div>
    <div class="aurora aurora-b"></div>

    <div class="portal-shell">
      <GlobalHeader
        :avatar-text="portal.user?.avatarText || 'HB'"
        :avatar-url="portal.user?.avatarUrl"
        :company-logo-url="portal.branding?.logoUrl"
        :apps="portal.apps"
        context-label="ATTENDANCE"
        @open-command="commandOpen = true"
      />

      <!-- 应用内导航：分组左侧栏。
           考勤共有 14 个入口（概览 3 / 报表 4 / 数据与导入 6 / 配置 1），
           横向页签放不下，故改为分组侧栏；形态与 LIMS 的 AppLocalSidebar
           一致，用户在两个应用间往返时不用重新学导航。
           Owner 2026-10-08 决定。 -->
      <div class="app-layout-grid">
        <AttendanceSidebar />
        <main id="attendance-main-content" class="app-route-content" tabindex="-1">
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
import AttendanceSidebar from '@/components/layout/AttendanceSidebar.vue'
import MobileAppNav from '@/components/layout/MobileAppNav.vue'
import CommandPalette from '@/components/portal/CommandPalette.vue'

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
