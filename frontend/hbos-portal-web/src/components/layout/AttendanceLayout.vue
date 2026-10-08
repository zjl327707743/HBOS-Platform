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

      <!-- 应用内导航：横向页签。
           考勤只有三个页面、且是「同一件事的三个视角」（总览 / 人 / 部门），
           横向页签比左侧栏更贴合这个心智，也让表格拿到完整宽度——
           人员管理那张表有 6 列 696 行，横向空间是硬需求。
           Owner 2026-10-02 从三案对比中选定本方案。 -->
      <nav class="att-tabs" aria-label="考勤页面">
        <RouterLink
          v-for="tab in tabs"
          :key="tab.to"
          :to="tab.to"
          class="att-tab"
          :class="{ on: isActive(tab) }"
        >{{ tab.label }}</RouterLink>

        <span class="att-tabs-spacer"></span>

        <!-- 管理后台 = Frappe Desk 的管理控制台。按
             docs/experience 的分层（Frappe Desk = V0 management console），
             它保留自身身份、不与门户逐像素一致，故这里不内嵌，直接新开页签。 -->
        <a class="att-console" :href="consoleUrl" target="_blank" rel="noopener noreferrer">
          管理后台 <span aria-hidden="true">↗</span>
        </a>
      </nav>

      <main id="attendance-main-content" class="app-route-content" tabindex="-1">
        <RouterView />
      </main>
    </div>

    <MobileAppNav />

    <CommandPalette :open="commandOpen" @close="commandOpen = false" />
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { usePortalStore } from '@/stores/portal'
import GlobalHeader from '@/components/layout/GlobalHeader.vue'
import PointerAtmosphere from '@/components/layout/PointerAtmosphere.vue'
import MobileAppNav from '@/components/layout/MobileAppNav.vue'
import CommandPalette from '@/components/portal/CommandPalette.vue'

const portal = usePortalStore()
const route = useRoute()
const commandOpen = ref(false)

const tabs = [
  { to: '/hbos/attendance', label: '考勤仪表盘' },
  { to: '/hbos/attendance/employees', label: '人员管理' },
  { to: '/hbos/attendance/board', label: '部门看板' },
]

// 精确匹配：'/hbos/attendance' 是其它两条的前缀，用 startsWith 会让三个页签同时高亮
function isActive(tab: { to: string }) {
  return route.path === tab.to
}

// 考勤工作台（Desk 侧），入口是 Workspace 而非某个具体页面：
// 那里才是「导入 / 月度汇总 / 班次管理 / 报表」的家。
const consoleUrl = computed(() => '/app/海滨考勤工作台')

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

<style scoped>
.att-tabs {
  display: flex;
  align-items: center;
  gap: 4px;
  margin-top: 18px;
  padding: 6px 8px;
  border-radius: var(--hbos-radius-control);
  background: var(--hbos-bg-surface);
  border: 1px solid var(--hbos-border-default);
  overflow-x: auto;
  scrollbar-width: none;
}
.att-tabs::-webkit-scrollbar { display: none; }

.att-tab {
  flex: 0 0 auto;
  padding: 7px 14px;
  border-radius: var(--hbos-radius-sm);
  color: var(--hbos-text-secondary);
  font-size: 14px;
  line-height: 22px;
  text-decoration: none;
  transition: background var(--hbos-motion-fast) var(--hbos-ease-standard);
}
.att-tab:hover { background: rgba(65, 91, 138, .06); }
.att-tab.on {
  background: rgba(103, 95, 255, .10);
  color: var(--hbos-status-processing);
  font-weight: 500;
}
.att-tab:focus-visible { outline: 2px solid var(--hbos-brand-violet); outline-offset: 1px; }

.att-tabs-spacer { flex: 1 1 auto; min-width: 8px; }

.att-console {
  flex: 0 0 auto;
  padding: 7px 12px;
  font-size: 12px;
  line-height: 20px;
  color: var(--hbos-text-muted);
  text-decoration: none;
  border-left: 1px solid var(--hbos-border-default);
  margin-left: 4px;
}
.att-console:hover { color: var(--hbos-brand-violet); }

@media (max-width: 720px) {
  .att-console { border-left: none; }
}
</style>
