<template>
  <section class="v10-work-page">
    <div class="v10-page-heading">
      <div>
        <h1>我的工作</h1>
        <p>查看待办、关注进度，把每件事安排清楚。</p>
      </div>
      <a-button :loading="portal.tasksLoading" @click="portal.refreshTasks"><ReloadOutlined /> 刷新</a-button>
    </div>

    <section class="v10-work-summary" aria-label="待办摘要">
      <div><span>需要我处理</span><strong>{{ count(actionableCount) }}</strong></div>
      <div><span>已逾期</span><strong>{{ count(overdueCount) }}</strong></div>
      <div><span>今天截止</span><strong>{{ count(todayCount) }}</strong></div>
      <div><span>等待别人</span><strong>{{ count(waitingCount) }}</strong></div>
      <small>{{ portal.tasksError ? '仅汇总已读取的事项' : '待办仅在来源应用内办理' }}</small>
    </section>

    <section class="section-panel glass-surface work-surface v10-work-surface">
      <div class="v10-work-toolbar">
        <a-segmented v-model:value="scope" :options="scopeOptions" aria-label="工作事项状态" />
        <div class="v10-work-filters">
          <a-input v-model:value="keyword" allow-clear class="v10-search-field" placeholder="搜索工作事项" aria-label="搜索工作事项">
            <template #prefix><SearchOutlined aria-hidden="true" /></template>
          </a-input>
          <PortalSelect v-model:value="appFilter" :options="appOptions" aria-label="按应用筛选" />
        </div>
      </div>
      <div class="v10-work-list-head"><span>工作事项</span><span>截止 / 状态</span></div>
      <a-skeleton v-if="portal.tasksLoading && !filtered.length" active aria-label="正在读取工作事项" />
      <PortalState v-if="portal.tasksError" title="部分工作事项暂时无法读取" :description="portal.tasksError" kind="error" retry @retry="portal.refreshTasks" />
      <div class="work-list">
        <button
          v-for="task in filtered"
          :key="task.taskId"
          class="work-list-row"
          type="button"
          @click="selectedTask = task"
        >
          <div class="task-icon" :class="task.appId"><component :is="appIcon(task.appId)" /></div>
          <div class="work-list-copy">
            <div class="work-row-top">
              <strong>{{ task.title }}</strong>
              <a-tag :color="tagColor(task)">{{ label(task) }}</a-tag>
            </div>
            <span>{{ chineseApp(task.appId) }} · {{ task.description }}</span>
          </div>
          <div class="work-list-due">
            <b :class="{ overdue: task.overdue }">{{ task.dueLabel }}</b>
            <small>{{ stateLabel(task) }}</small>
          </div>
          <RightOutlined />
        </button>

        <PortalState v-if="!filtered.length && !portal.tasksLoading && !portal.tasksError"
          :title="filtering ? '没有匹配的工作事项' : scope === '需要我处理' ? '当前没有需要你处理的事项' : '当前没有此类工作事项'"
          :description="filtering ? '可以调整搜索词或应用范围。' : '这里会汇总当前账号可查看的工作事项。'">
          <a-button v-if="filtering" size="small" @click="appFilter = 'all'; keyword = ''">清除筛选</a-button>
        </PortalState>
      </div>
    </section>
    <p class="v10-work-foot"><InfoCircleOutlined /> 工作台汇总待办；审批、完成和批量处理请在对应应用中进行。</p>
    <PortalTaskDialog :task="selectedTask" @close="selectedTask = null" />
  </section>
</template>

<script setup lang="ts">
import { appIcon, chineseApp } from '@/components/appIcons'
import { computed, ref } from 'vue'
import {
  ReloadOutlined,
  RightOutlined,
  SearchOutlined,
  InfoCircleOutlined,
} from '@ant-design/icons-vue'
import { usePortalStore } from '@/stores/portal'
import type { UnifiedTaskDTO } from '@/contracts/portal'
import PortalSelect from '@/components/portal/PortalSelect.vue'
import PortalState from '@/components/portal/PortalState.vue'
import PortalTaskDialog from '@/components/portal/PortalTaskDialog.vue'

const portal = usePortalStore()
const selectedTask = ref<UnifiedTaskDTO | null>(null)
const taskApps = computed(() => portal.apps.filter((app) => portal.dataSource === 'mock' || app.capabilityTasks))
const scope = ref('需要我处理')
const appFilter = ref<string | undefined>('all')
const keyword = ref('')
const appOptions = computed(() => [{ value: 'all', label: '全部应用' }, ...taskApps.value.map(app => ({ value: app.id, label: app.title }))])
const filtering = computed(() => Boolean(keyword.value.trim() || (appFilter.value && appFilter.value !== 'all')))
const count = (value: number) => portal.tasksLoading || (portal.tasksError && !portal.tasks.length) ? '—' : value
const scopeOptions = ['需要我处理', '今天', '本周', '超期', '等待别人', '已完成']

const actionableCount = computed(() => portal.tasks.filter((t) => t.status === 'open').length)
const overdueCount = computed(() => portal.tasks.filter((t) => t.overdue && t.status === 'open').length)
const todayCount = computed(() => portal.tasks.filter((t) => t.dueGroup === 'today' && t.status === 'open').length)
const waitingCount = computed(() => portal.tasks.filter((t) => t.status === 'waiting').length)

const filtered = computed(() => portal.tasks.filter((task) => {
  if (appFilter.value && appFilter.value !== 'all' && task.appId !== appFilter.value) return false
  if (keyword.value.trim() && !`${task.title} ${task.description}`.toLowerCase().includes(keyword.value.trim().toLowerCase())) return false
  if (scope.value === '需要我处理' && task.status !== 'open') return false
  if (scope.value === '今天' && !(task.dueGroup === 'today' && task.status === 'open')) return false
  if (scope.value === '本周' && !(task.status === 'open' && ['today','week'].includes(task.dueGroup))) return false
  if (scope.value === '超期' && !(task.overdue && task.status === 'open')) return false
  if (scope.value === '等待别人' && task.status !== 'waiting') return false
  if (scope.value === '已完成' && task.status !== 'done') return false
  return true
}))

function label(task: UnifiedTaskDTO) {
  if (task.overdue) return '已超期'
  if (task.priority === 'high') return '高优先级'
  if (task.status === 'waiting') return '等待'
  if (task.status === 'done') return '已完成'
  return '待处理'
}
function tagColor(task: UnifiedTaskDTO) {
  if (task.overdue) return 'error'
  if (task.priority === 'high') return 'warning'
  if (task.status === 'done') return 'success'
  if (task.status === 'waiting') return 'default'
  return 'processing'
}
function stateLabel(task: UnifiedTaskDTO) {
  if (task.status === 'waiting') return '等待其他角色'
  if (task.status === 'done') return '已完成'
  return '点击进入处理'
}
</script>
