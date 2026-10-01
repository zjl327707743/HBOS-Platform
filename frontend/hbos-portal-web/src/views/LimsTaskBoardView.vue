<template>
  <section class="product-page lims-task-board">
    <div class="lims-task-board-heading">
      <div>
        <span class="page-kicker">LIMS · 任务中心</span>
        <h1>{{ viewLabel }}</h1>
        <p>按检验角色查看待处理任务，状态由 LIMS 服务返回。</p>
      </div>
      <a-button :loading="loading" @click="loadTasks">
        <ReloadOutlined /> 刷新任务
      </a-button>
    </div>

    <a-alert
      v-if="errorMessage"
      class="lims-task-board-alert"
      type="error"
      show-icon
      closable
      :message="errorMessage"
      @close="errorMessage = ''"
    />

    <section class="lims-task-views glass-surface" aria-label="任务视图">
      <div class="lims-task-view-copy">
        <span>我的工作</span>
        <small>切换后会保留在当前 URL，方便刷新和返回。</small>
      </div>
      <div class="lims-task-view-tabs" role="tablist" aria-label="任务角色视图">
        <button
          v-for="item in viewOptions"
          :key="item.value"
          type="button"
          role="tab"
          :aria-selected="activeView === item.value"
          :class="{ active: activeView === item.value }"
          @click="setView(item.value)"
        >
          <component :is="item.icon" />
          <span>{{ item.label }}</span>
        </button>
      </div>
    </section>

    <section class="lims-task-filters glass-surface" aria-label="任务筛选">
      <a-input-search
        v-model:value="searchInput"
        class="lims-task-search"
        placeholder="搜索样品、批次、任务或动作"
        enter-button="搜索"
        allow-clear
        @search="applySearch"
      >
        <template #prefix><SearchOutlined /></template>
      </a-input-search>
      <label>
        <span>状态</span>
        <a-select :value="statusFilter" aria-label="按状态筛选" @change="setStatus">
          <a-select-option value="">全部状态</a-select-option>
          <a-select-option v-for="status in statusOptions" :key="status" :value="status">{{ status }}</a-select-option>
        </a-select>
      </label>
      <label>
        <span>优先级</span>
        <a-select :value="priorityFilter" aria-label="按优先级筛选" @change="setPriority">
          <a-select-option value="">全部优先级</a-select-option>
          <a-select-option value="critical">紧急</a-select-option>
          <a-select-option value="high">高</a-select-option>
          <a-select-option value="normal">普通</a-select-option>
          <a-select-option value="low">低</a-select-option>
        </a-select>
      </label>
      <label>
        <span>截止时间</span>
        <a-select :value="dueFilter" aria-label="按截止时间筛选" @change="setDue">
          <a-select-option value="">全部时间</a-select-option>
          <a-select-option value="today">今天截止</a-select-option>
          <a-select-option value="week">本周截止</a-select-option>
          <a-select-option value="overdue">已超期</a-select-option>
        </a-select>
      </label>
    </section>

    <section class="lims-task-status-strip" aria-label="任务状态统计">
      <button
        v-for="status in statusOptions"
        :key="status"
        type="button"
        :class="['lims-task-status-chip', statusTone(status), { active: statusFilter === status }]"
        @click="setStatus(statusFilter === status ? '' : status)"
      >
        <span>{{ status }}</span><b>{{ statusCounts[status] || 0 }}</b>
      </button>
    </section>

    <section class="lims-task-board-panel glass-surface" aria-live="polite">
      <div class="section-head">
        <div>
          <h2>任务清单</h2>
          <p>{{ visibleTasks.length }} 项任务 · 当前视图只读</p>
        </div>
        <span class="lims-readonly-badge">业务状态由 LIMS 控制</span>
      </div>

      <div v-if="loading" class="lims-task-board-loading">
        <div v-for="item in 5" :key="item" class="lims-task-row-skeleton"></div>
      </div>

      <div v-else-if="visibleTasks.length" class="lims-task-board-table" role="table" aria-label="LIMS 任务清单">
        <div class="lims-task-board-row lims-task-board-head" role="row">
          <span>任务 / 样品</span><span>状态</span><span>优先级</span><span>截止时间</span><span>下一步</span>
        </div>
        <RouterLink
          v-for="(task, index) in visibleTasks"
          :key="task.taskId"
          :ref="(element) => setRowRef(element, index)"
          class="lims-task-board-row"
          role="row"
          :to="task.deepLink"
          tabindex="0"
          @keydown="handleRowKeydown($event, index)"
        >
          <span class="lims-task-board-main">
            <span class="lims-task-icon" :class="`priority-${task.priority}`"><ExperimentOutlined /></span>
            <span>
              <strong>{{ task.title }}</strong>
              <small>{{ task.description || 'LIMS 检验任务' }}</small>
            </span>
          </span>
          <span><a-tag :color="statusTagColor(task.domainStatus)">{{ task.domainStatus || '待处理' }}</a-tag></span>
          <span><a-tag :color="priorityTagColor(task.priority)">{{ priorityLabel(task.priority) }}</a-tag></span>
          <span :class="{ overdue: task.overdue }">{{ task.dueLabel }}</span>
          <span class="lims-task-board-action">{{ task.actionLabel || '查看任务' }} <ArrowRightOutlined /></span>
        </RouterLink>
      </div>

      <div v-else class="lims-task-board-empty">
        <InboxOutlined />
        <h3>{{ hasActiveFilters ? '没有匹配的任务' : '当前视图暂无待处理任务' }}</h3>
        <p>{{ hasActiveFilters ? '可以清除筛选条件，或换一个关键词。' : 'LIMS 服务没有返回当前权限范围内的任务。' }}</p>
        <a-button v-if="hasActiveFilters" @click="clearFilters">清除筛选</a-button>
      </div>
    </section>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter, RouterLink } from 'vue-router'
import {
  ArrowRightOutlined,
  CheckCircleOutlined,
  ExperimentOutlined,
  InboxOutlined,
  ReloadOutlined,
  SafetyCertificateOutlined,
  SearchOutlined,
} from '@ant-design/icons-vue'
import type { Component, ComponentPublicInstance } from 'vue'
import type { LimsTaskQuery, LimsTaskView, UnifiedTaskDTO } from '@/contracts/portal'
import { getPortalTasks, portalDataSource } from '@/services/portalProvider'
import { usePortalStore } from '@/stores/portal'

const route = useRoute()
const router = useRouter()
const portal = usePortalStore()

const viewOptions: Array<{ value: LimsTaskView; label: string; icon: Component }> = [
  { value: 'my-testing', label: '我的待检', icon: ExperimentOutlined },
  { value: 'my-review', label: '我的复核', icon: CheckCircleOutlined },
  { value: 'my-approval', label: '我的审批', icon: SafetyCertificateOutlined },
]
const statusOptions = ['待分配', '已分配', '检验中', '已提交', '已复核', '已批准', 'OOS 候选']
const viewActions: Record<LimsTaskView, string[]> = {
  'my-testing': ['start_task', 'submit_result', 'start_testing', 'record_result', 'complete_sampling'],
  'my-review': ['review_result', 'review_observation', 'eval_trend'],
  'my-approval': ['approve_result', 'publish_coa', 'confirm_stock'],
}
const activeView = ref<LimsTaskView>('my-testing')
const statusFilter = ref('')
const priorityFilter = ref<UnifiedTaskDTO['priority'] | ''>('')
const dueFilter = ref('')
const searchInput = ref('')
const tasks = ref<UnifiedTaskDTO[]>([])
const loading = ref(true)
const errorMessage = ref('')
const rowRefs = ref<HTMLElement[]>([])

const viewLabel = computed(() => viewOptions.find((item) => item.value === activeView.value)?.label || '任务看板')
const statusCounts = computed(() => tasks.value.reduce<Record<string, number>>((counts, task) => {
  const status = task.domainStatus || '待分配'
  counts[status] = (counts[status] || 0) + 1
  return counts
}, {}))
const visibleTasks = computed(() => tasks.value.filter((task) => {
  if (statusFilter.value && task.domainStatus !== statusFilter.value) return false
  if (priorityFilter.value && task.priority !== priorityFilter.value) return false
  if (dueFilter.value === 'today' && task.dueGroup !== 'today') return false
  if (dueFilter.value === 'week' && !['today', 'week'].includes(task.dueGroup)) return false
  if (dueFilter.value === 'overdue' && !task.overdue) return false
  return true
}))
const hasActiveFilters = computed(() => Boolean(statusFilter.value || priorityFilter.value || dueFilter.value || searchInput.value.trim()))

function stringQuery(value: unknown) {
  return typeof value === 'string' ? value : ''
}

function readRouteState() {
  const routeView = stringQuery(route.query.view) as LimsTaskView
  activeView.value = viewOptions.some((item) => item.value === routeView) ? routeView : 'my-testing'
  statusFilter.value = stringQuery(route.query.status)
  const priority = stringQuery(route.query.priority) as UnifiedTaskDTO['priority']
  priorityFilter.value = ['critical', 'high', 'normal', 'low'].includes(priority) ? priority : ''
  dueFilter.value = stringQuery(route.query.due)
  searchInput.value = stringQuery(route.query.keyword)
}

function currentQuery(): LimsTaskQuery {
  return {
    view: activeView.value,
    status: statusFilter.value || undefined,
    priority: priorityFilter.value || undefined,
    keyword: searchInput.value.trim() || undefined,
  }
}

function queryForRoute() {
  const query: Record<string, string> = { view: activeView.value }
  if (statusFilter.value) query.status = statusFilter.value
  if (priorityFilter.value) query.priority = priorityFilter.value
  if (dueFilter.value) query.due = dueFilter.value
  if (searchInput.value.trim()) query.keyword = searchInput.value.trim()
  return query
}

async function updateRoute() {
  await router.replace({ path: '/hbos/lims/tasks', query: queryForRoute() })
}

async function loadTasks() {
  loading.value = true
  errorMessage.value = ''
  rowRefs.value = []
  try {
    if (!portal.user) await portal.bootstrap()
    const limsApp = portal.apps.find((app) => app.id === 'lims')
    if (!limsApp) {
      tasks.value = []
      return
    }
    const loaded = await getPortalTasks([limsApp], currentQuery())
    tasks.value = loaded
      .filter((task) => task.appId === 'lims')
      .filter((task) => portalDataSource === 'frappe' || !task.action || viewActions[activeView.value].includes(task.action))
      .filter((task) => !task.domainStatus || statusOptions.includes(task.domainStatus) || portalDataSource === 'frappe')
  } catch {
    tasks.value = []
    errorMessage.value = '任务暂时无法加载，请稍后重试。'
  } finally {
    loading.value = false
  }
}

function setView(value: LimsTaskView) {
  activeView.value = value
  void updateRoute()
}

function setStatus(value: string) {
  statusFilter.value = value
  void updateRoute()
}

function setPriority(value: UnifiedTaskDTO['priority'] | '') {
  priorityFilter.value = value
  void updateRoute()
}

function setDue(value: string) {
  dueFilter.value = value
  void updateRoute()
}

function applySearch(value: string) {
  searchInput.value = value
  void updateRoute()
}

function clearFilters() {
  statusFilter.value = ''
  priorityFilter.value = ''
  dueFilter.value = ''
  searchInput.value = ''
  void updateRoute()
}

function statusTone(status: string) {
  if (status === 'OOS 候选') return 'critical'
  if (status === '已批准') return 'success'
  if (status === '已提交' || status === '已复核') return 'info'
  return 'neutral'
}

function statusTagColor(status?: string) {
  if (status === 'OOS 候选') return 'error'
  if (status === '已批准') return 'success'
  if (status === '已提交' || status === '已复核') return 'processing'
  return 'default'
}

function priorityLabel(priority: UnifiedTaskDTO['priority']) {
  return { critical: '紧急', high: '高', normal: '普通', low: '低' }[priority]
}

function priorityTagColor(priority: UnifiedTaskDTO['priority']) {
  return { critical: 'error', high: 'warning', normal: 'default', low: 'default' }[priority]
}

function setRowRef(element: Element | ComponentPublicInstance | null, index: number) {
  if (element instanceof HTMLElement) rowRefs.value[index] = element
}

function handleRowKeydown(event: KeyboardEvent, index: number) {
  if (event.key === 'Enter') return
  if (!['ArrowDown', 'ArrowUp'].includes(event.key)) return
  event.preventDefault()
  const next = event.key === 'ArrowDown' ? index + 1 : index - 1
  rowRefs.value[next]?.focus()
}

watch(() => route.fullPath, async () => {
  readRouteState()
  await loadTasks()
})

onMounted(async () => {
  readRouteState()
  await loadTasks()
})
</script>
