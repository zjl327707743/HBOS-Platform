<template>
  <section class="product-page">
    <div class="page-heading">
      <div>
        <span class="page-kicker">我的工作</span>
        <h1>需要我处理</h1>
        <p>这里只聚合“可执行动作”。等待别人、已完成和仅供参考的信息不混在主待办中。</p>
      </div>
      <a-space>
        <a-button :loading="portal.tasksLoading" @click="portal.refreshTasks"><ReloadOutlined /> 刷新</a-button>
        <a-button type="primary"><SettingOutlined /> 工作偏好</a-button>
      </a-space>
    </div>

    <div class="work-overview">
      <article class="work-stat glass-surface"><span>需要我处理</span><strong>{{ actionableCount }}</strong><small>来自 4 个业务应用</small></article>
      <article class="work-stat glass-surface critical-card"><span>已超期</span><strong>{{ overdueCount }}</strong><small>优先处理</small></article>
      <article class="work-stat glass-surface"><span>今天截止</span><strong>{{ todayCount }}</strong><small>按截止时间排序</small></article>
      <article class="work-stat glass-surface"><span>等待别人</span><strong>{{ waitingCount }}</strong><small>不计入“需要我处理”</small></article>
    </div>

    <section class="section-panel glass-surface work-surface">
      <div class="work-toolbar">
        <a-segmented v-model:value="scope" :options="scopeOptions" />
        <div class="toolbar-right">
          <a-select v-model:value="appFilter" style="width: 156px">
            <a-select-option value="all">全部应用</a-select-option>
            <a-select-option value="lims">LIMS</a-select-option>
            <a-select-option value="attendance">考勤</a-select-option>
            <a-select-option value="inventory">仓储</a-select-option>
            <a-select-option value="equipment">设备</a-select-option>
          </a-select>
          <a-input v-model:value="keyword" allow-clear placeholder="搜索工作事项" style="width: 220px">
            <template #prefix><SearchOutlined /></template>
          </a-input>
        </div>
      </div>

      <div class="work-list">
        <button
          v-for="task in filtered"
          :key="task.taskId"
          class="work-list-row"
          type="button"
          @click="openTask(task)"
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

        <a-empty v-if="!filtered.length" description="当前没有需要你处理的事项" />
      </div>
    </section>
  </section>
</template>

<script setup lang="ts">
import { computed, ref, type Component } from 'vue'
import { useRouter } from 'vue-router'
import {
  ClockCircleOutlined,
  ExperimentOutlined,
  InboxOutlined,
  ReloadOutlined,
  RightOutlined,
  SearchOutlined,
  SettingOutlined,
  ToolOutlined,
} from '@ant-design/icons-vue'
import { usePortalStore } from '@/stores/portal'
import type { UnifiedTaskDTO } from '@/contracts/portal'
import { openBusinessRoute } from '@/services/businessNavigation'

const portal = usePortalStore()
const router = useRouter()
const scope = ref('需要我处理')
const appFilter = ref('all')
const keyword = ref('')
const scopeOptions = ['需要我处理', '今天', '本周', '超期', '等待别人', '已完成']

const actionableCount = computed(() => portal.tasks.filter((t) => t.status === 'open').length)
const overdueCount = computed(() => portal.tasks.filter((t) => t.overdue && t.status === 'open').length)
const todayCount = computed(() => portal.tasks.filter((t) => t.dueGroup === 'today' && t.status === 'open').length)
const waitingCount = computed(() => portal.tasks.filter((t) => t.status === 'waiting').length)

const filtered = computed(() => portal.tasks.filter((task) => {
  if (appFilter.value !== 'all' && task.appId !== appFilter.value) return false
  if (keyword.value && !`${task.title} ${task.description}`.toLowerCase().includes(keyword.value.toLowerCase())) return false
  if (scope.value === '需要我处理' && task.status !== 'open') return false
  if (scope.value === '今天' && !(task.dueGroup === 'today' && task.status === 'open')) return false
  if (scope.value === '本周' && !(task.status === 'open' && ['today','week'].includes(task.dueGroup))) return false
  if (scope.value === '超期' && !(task.overdue && task.status === 'open')) return false
  if (scope.value === '等待别人' && task.status !== 'waiting') return false
  if (scope.value === '已完成' && task.status !== 'done') return false
  return true
}))

const icons: Record<string, Component> = {
  lims: ExperimentOutlined,
  attendance: ClockCircleOutlined,
  inventory: InboxOutlined,
  equipment: ToolOutlined,
}
function openTask(task: UnifiedTaskDTO) {
  void openBusinessRoute(router, task.appId, task.deepLink)
}

function appIcon(appId: string) { return icons[appId] || InboxOutlined }
function chineseApp(appId: string) {
  return ({ lims: 'LIMS', attendance: '考勤', inventory: '仓储', equipment: '设备' } as Record<string,string>)[appId] || appId
}
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
