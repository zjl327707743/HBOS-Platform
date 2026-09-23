<template>
  <aside class="sidebar" :class="{ collapsed }">
    <div class="brand">
      <div class="brand-mark">
        <img src="/joincare-mark.png" alt="健康元" class="brand-logo" />
      </div>
      <div v-if="!collapsed">
        <div class="brand-name">海滨LIMS</div>
        <div class="brand-sub">Laboratory Information System</div>
      </div>
    </div>

    <nav class="nav" aria-label="LIMS 主导航">
      <section class="work-section" aria-labelledby="work-section-label">
        <div v-if="!collapsed" id="work-section-label" class="section-label">我的工作</div>
        <router-link
          to="/dashboard"
          class="nav-item work-item"
          :class="{ active: isSidebarItemActive(route.path, '/dashboard') }"
          :title="collapsed ? '工作台总览' : ''"
        >
          <DashboardOutlined />
          <span v-if="!collapsed">工作台总览</span>
        </router-link>
        <router-link
          to="/tasks"
          class="nav-item work-item"
          :class="{ active: isSidebarItemActive(route.path, '/tasks') }"
          :title="collapsed ? '待检任务看板' : ''"
        >
          <CarryOutOutlined />
          <span v-if="!collapsed">待检任务看板</span>
        </router-link>
        <button type="button" class="nav-item work-item shortcut-button" title="我的待办" @click="goToTasks">
          <UnorderedListOutlined />
          <span v-if="!collapsed">我的待办</span>
          <span v-if="!collapsed && todoStore.summary.total > 0" class="nav-badge danger">{{ todoStore.summary.total }}</span>
        </button>
      </section>

      <div v-if="!collapsed" class="module-heading">
        <span class="section-label">全部模块</span>
        <span class="module-heading-actions">
          <button type="button" @click="expandAll">全部展开</button>
          <span aria-hidden="true">|</span>
          <button type="button" @click="collapseAll">全部收起</button>
        </span>
      </div>

      <section v-for="group in sidebarGroups" :key="group.key" class="nav-group">
        <button
          type="button"
          class="nav-group-toggle"
          :class="{ 'active-group': isGroupCurrent(group.key) }"
          :title="collapsed ? group.label : ''"
          :aria-expanded="!collapsed && isGroupExpanded(group.key)"
          @click="toggleGroup(group.key)"
        >
          <component :is="groupIcons[group.key]" />
          <span v-if="!collapsed" class="nav-group-label">{{ group.label }}</span>
          <span v-if="!collapsed" class="nav-count">{{ group.children.length }}</span>
          <span v-if="!collapsed && groupBadge() > 0" class="nav-badge module-badge">
            {{ groupBadge() }}
          </span>
          <DownOutlined v-if="!collapsed && isGroupExpanded(group.key)" class="group-chevron" />
          <RightOutlined v-else-if="!collapsed" class="group-chevron" />
        </button>

        <div v-if="!collapsed" v-show="isGroupExpanded(group.key)" class="subnav">
          <router-link
            v-for="item in group.children"
            :key="item.key"
            :to="item.path"
            class="nav-item child-item"
            :class="{ active: isSidebarItemActive(route.path, item.path) }"
          >
            <component :is="itemIcons[item.key]" />
            <span>{{ item.label }}</span>
            <span v-if="itemBadge(item) !== null" class="nav-badge amber">{{ itemBadge(item) }}</span>
          </router-link>
        </div>
      </section>
    </nav>

    <div class="sidebar-foot">
      <button class="collapse-btn" :title="collapsed ? '展开侧边栏' : '收缩侧边栏'" @click="$emit('toggle')">
        <MenuFoldOutlined v-if="!collapsed" />
        <MenuUnfoldOutlined v-else />
        <span v-if="!collapsed">收缩侧边栏</span>
      </button>
      <div v-if="!collapsed" class="foot-meta">
        <div>HBOS · 海滨药业</div>
        <div>版本 0.1.0</div>
      </div>
    </div>
  </aside>
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch, type Component } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  AuditOutlined,
  CalendarOutlined,
  CarryOutOutlined,
  DashboardOutlined,
  DatabaseOutlined,
  DownOutlined,
  ExperimentOutlined,
  ExportOutlined,
  EyeOutlined,
  FileAddOutlined,
  FileProtectOutlined,
  FileTextOutlined,
  FormOutlined,
  FundProjectionScreenOutlined,
  HistoryOutlined,
  InboxOutlined,
  LineChartOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  ProfileOutlined,
  ReadOutlined,
  RightOutlined,
  SearchOutlined,
  TagsOutlined,
  ToolOutlined,
  UnorderedListOutlined,
} from '@ant-design/icons-vue'
import { dashboard as stabilityDashboard } from '@/api/stability'
import { useAuthStore } from '@/stores/auth'
import { useTodoStore } from '@/stores/todo'
import {
  getGroupForPath,
  getInitialExpandedGroup,
  isSidebarItemActive,
  sidebarGroups,
  type SidebarGroupKey,
  type SidebarNavItem,
} from './sidebarNavigation'

const props = defineProps<{ collapsed: boolean }>()
defineEmits<{ toggle: [] }>()

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const todoStore = useTodoStore()

const groupIcons: Record<SidebarGroupKey, Component> = {
  testing: CarryOutOutlined,
  quality: FileProtectOutlined,
  retention: FundProjectionScreenOutlined,
  stability: ExperimentOutlined,
  compliance: AuditOutlined,
}

const itemIcons: Record<string, Component> = {
  samples: FileAddOutlined,
  tasks: CarryOutOutlined,
  results: FormOutlined,
  'result-ledger': FileTextOutlined,
  coas: FileTextOutlined,
  specs: ReadOutlined,
  'retention-dashboard': FundProjectionScreenOutlined,
  'retention-samples': DatabaseOutlined,
  'retention-products': TagsOutlined,
  'retention-observations': EyeOutlined,
  'retention-usage': ExportOutlined,
  'retention-disposal': HistoryOutlined,
  'stability-dashboard': ExperimentOutlined,
  'stability-study': ProfileOutlined,
  'stability-samples': InboxOutlined,
  'stability-schedule': CalendarOutlined,
  'stability-results': LineChartOutlined,
  'stability-reports': FileProtectOutlined,
  'stability-ops': ToolOutlined,
  audit: SearchOutlined,
  'audit-log': AuditOutlined,
}

const GROUP_STATE_KEY = 'hbos_lims_sidebar_expanded_groups'

function readExpandedGroups(path: string): Set<SidebarGroupKey> {
  const expanded = new Set<SidebarGroupKey>()
  const activeGroup = getInitialExpandedGroup(path)
  if (activeGroup) expanded.add(activeGroup)

  if (typeof window === 'undefined') return expanded
  try {
    const saved = JSON.parse(window.localStorage.getItem(GROUP_STATE_KEY) || '[]') as unknown
    if (Array.isArray(saved)) {
      for (const key of saved) {
        if (sidebarGroups.some((group) => group.key === key)) expanded.add(key as SidebarGroupKey)
      }
    }
  } catch {
    // localStorage 不可用时退回当前路由自动展开。
  }
  return expanded
}

const expandedGroups = ref<Set<SidebarGroupKey>>(readExpandedGroups(route.path))

// 稳定性角标：取自真实时间点执行状态，无权限/未登录时不显示。
const stabilityCounts = ref({ schedule: 0, results: 0 })

function persistExpandedGroups() {
  if (typeof window === 'undefined') return
  window.localStorage.setItem(GROUP_STATE_KEY, JSON.stringify([...expandedGroups.value]))
}

function isGroupExpanded(key: SidebarGroupKey): boolean {
  return expandedGroups.value.has(key)
}

function isGroupCurrent(key: SidebarGroupKey): boolean {
  return getGroupForPath(route.path) === key
}

function toggleGroup(key: SidebarGroupKey) {
  if (props.collapsed) return
  const next = new Set(expandedGroups.value)
  if (next.has(key)) next.delete(key)
  else next.add(key)
  expandedGroups.value = next
  persistExpandedGroups()
}

function expandAll() {
  expandedGroups.value = new Set(sidebarGroups.map((group) => group.key))
  persistExpandedGroups()
}

function collapseAll() {
  expandedGroups.value = new Set()
  persistExpandedGroups()
}

function groupBadge(): number {
  // 个人待办和模块全局工作量语义不同，分组不显示汇总角标。
  return 0
}

function itemBadge(item: SidebarNavItem): number | null {
  if (item.badge === 'schedule') return stabilityCounts.value.schedule > 0 ? stabilityCounts.value.schedule : null
  if (item.badge === 'results') return stabilityCounts.value.results > 0 ? stabilityCounts.value.results : null
  return null
}

function goToTasks() {
  void router.push('/my-todos')
}

function hasLimsRole(): boolean {
  const roles = auth.user?.roles || []
  return roles.some((role) => role.startsWith('LIMS ') || role === 'System Manager')
}

async function loadStabilityBadges() {
  if (!hasLimsRole()) return
  try {
    const counts = await stabilityDashboard()
    stabilityCounts.value = {
      schedule: counts.timepoint_by_status.wait_sample + counts.timepoint_by_status.wait_test,
      results: counts.timepoint_by_status.testing,
    }
  } catch {
    stabilityCounts.value = { schedule: 0, results: 0 }
  }
}

async function refreshTodoSummary() {
  if (await auth.checkSession()) await todoStore.fetchSummary()
}

function handleWindowFocus() {
  void refreshTodoSummary()
}

onMounted(() => {
  void refreshTodoSummary()
  window.addEventListener('focus', handleWindowFocus)
})

onBeforeUnmount(() => {
  window.removeEventListener('focus', handleWindowFocus)
})

watch(() => auth.user?.roles?.length ?? 0, () => { void loadStabilityBadges() }, { immediate: true })

watch(() => route.path, (path) => {
  const activeGroup = getGroupForPath(path)
  if (activeGroup && !expandedGroups.value.has(activeGroup)) {
    expandedGroups.value = new Set([...expandedGroups.value, activeGroup])
    persistExpandedGroups()
  }
  if (path.startsWith('/stability')) void loadStabilityBadges()
  if (auth.user) void todoStore.fetchSummary()
})
</script>

<style scoped>
.sidebar {
  width: 232px;
  flex: 0 0 232px;
  background: linear-gradient(180deg, var(--sidebar) 0%, var(--sidebar-2) 100%);
  color: var(--sidebar-text);
  display: flex;
  flex-direction: column;
  position: sticky;
  top: 0;
  height: 100vh;
  transition: width 0.2s ease, flex-basis 0.2s ease;
  overflow: hidden;
}

.sidebar.collapsed { width: 64px; flex: 0 0 64px; }

.brand {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 18px 16px 16px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}

.sidebar.collapsed .brand { justify-content: center; padding: 18px 0 16px; }

.brand-mark {
  width: 40px;
  height: 40px;
  border-radius: 8px;
  background: #ffffff;
  border: 1px solid var(--line);
  display: grid;
  place-items: center;
  flex: 0 0 40px;
  overflow: hidden;
}

.brand-logo { width: 30px; height: 30px; object-fit: contain; display: block; }
.brand-name { font-size: 15px; font-weight: 700; color: #fff; white-space: nowrap; }
.brand-sub { font-size: 10px; color: #8eab9f; margin-top: 2px; white-space: nowrap; }

.nav { padding: 12px 10px; flex: 1; overflow-y: auto; overflow-x: hidden; }
.sidebar.collapsed .nav { padding: 12px 8px; }
.work-section { margin-bottom: 14px; }

.section-label {
  font-size: 10px;
  color: #71968b;
  padding: 6px 10px 5px;
  letter-spacing: 0.08em;
  white-space: nowrap;
}

.nav-item,
.nav-group-toggle {
  box-sizing: border-box;
  display: flex;
  align-items: center;
  width: 100%;
  border: 0;
  text-decoration: none;
  color: var(--sidebar-text);
  cursor: pointer;
  white-space: nowrap;
}

.nav-item {
  gap: 10px;
  padding: 8px 10px;
  border-radius: 6px;
  font-size: 13px;
  margin-bottom: 2px;
  background: transparent;
  transition: background 0.12s ease, color 0.12s ease;
}

.nav-item:hover { background: rgba(255, 255, 255, 0.07); color: #fff; }
.nav-item.active { background: var(--primary); color: #fff; font-weight: 600; }
.nav-item :deep(.anticon),
.nav-group-toggle :deep(.anticon) { flex: 0 0 16px; opacity: 0.85; font-size: 15px; }

.work-item { min-height: 34px; }
.shortcut-button { font-family: inherit; text-align: left; }

.module-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin: 6px 0 4px;
}

.module-heading .section-label { padding-right: 0; }

.module-heading-actions {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  color: #71968b;
  font-size: 10px;
  white-space: nowrap;
}

.module-heading-actions button {
  padding: 0;
  color: inherit;
  border: 0;
  background: transparent;
  cursor: pointer;
  font: inherit;
}

.module-heading-actions button:hover { color: #d6eee7; }
.nav-group { margin-bottom: 3px; }

.nav-group-toggle {
  gap: 10px;
  min-height: 38px;
  padding: 8px 10px;
  border-radius: 7px;
  color: var(--sidebar-text);
  background: transparent;
  font-size: 13px;
  text-align: left;
  transition: background 0.12s ease, color 0.12s ease;
}

.nav-group-toggle:hover,
.nav-group-toggle.active-group { background: rgba(255, 255, 255, 0.075); color: #fff; }
.nav-group-toggle.active-group :deep(.anticon:first-child) { color: #6ee8db; }
.nav-group-label { overflow: hidden; text-overflow: ellipsis; }

.nav-count { min-width: 18px; margin-left: auto; color: #91b1a5; font-size: 10px; text-align: center; }
.group-chevron { flex: 0 0 12px !important; font-size: 11px !important; color: #8eab9f; }

.subnav {
  position: relative;
  margin: 2px 0 5px 13px;
  padding: 1px 0 1px 9px;
  border-left: 1px solid rgba(188, 226, 214, 0.2);
}

.child-item { gap: 9px; min-height: 32px; padding: 7px 9px; font-size: 12px; border-radius: 5px; }
.child-item :deep(.anticon) { font-size: 13px; }
.child-item.active { box-shadow: inset 2px 0 0 #80e9dd; }

.nav-badge {
  flex: 0 0 auto;
  min-width: 18px;
  height: 18px;
  margin-left: auto;
  padding: 0 5px;
  border-radius: 9px;
  display: grid;
  place-items: center;
  color: #fff;
  font-size: 10px;
  line-height: 1;
}

.nav-badge.amber,
.nav-badge.module-badge { background: var(--warn); }
.nav-badge.danger { background: var(--danger); }

.sidebar-foot {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 14px 16px;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
  color: #73998c;
  font-size: 10px;
  line-height: 1.6;
  white-space: nowrap;
}

.collapse-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  padding: 8px 10px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 6px;
  color: var(--sidebar-text);
  background: rgba(255, 255, 255, 0.06);
  font-size: 12px;
  cursor: pointer;
  transition: background 0.12s ease;
}

.collapse-btn:hover { background: rgba(255, 255, 255, 0.12); color: #fff; }
.collapse-btn .anticon { font-size: 15px; }
.sidebar.collapsed .collapse-btn { justify-content: center; padding: 9px 0; }
.sidebar.collapsed .foot-meta { display: none; }

@media (max-width: 768px) {
  .sidebar,
  .sidebar.collapsed { width: 60px; flex: 0 0 60px; }

  .brand { justify-content: center; padding: 14px 0; }
  .brand-name,
  .brand-sub,
  .section-label,
  .module-heading,
  .nav-group-label,
  .nav-count,
  .group-chevron,
  .nav-item span,
  .foot-meta { display: none; }

  .nav { padding: 12px 8px; }
  .nav-item,
  .nav-group-toggle { justify-content: center; padding: 10px 0; }
  .subnav { display: none !important; }
  .nav-badge { margin-left: -12px; margin-top: -14px; }
}
</style>
