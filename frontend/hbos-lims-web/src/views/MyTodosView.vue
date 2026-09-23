<template>
  <div class="todo-page">
    <div class="page-heading">
      <div>
        <div class="eyebrow">MY WORK</div>
        <h1>我的待办</h1>
        <p class="muted">
          {{ auth.user?.full_name || auth.user?.name || '当前会话' }} · 按当前身份汇总指派任务与角色待处理事项
        </p>
      </div>
      <div class="heading-actions">
        <span v-if="todoStore.generatedAt" class="updated-at">更新于 {{ formatDateTime(todoStore.generatedAt) }}</span>
        <a-button :loading="todoStore.loading" @click="refreshWhenVisible">刷新</a-button>
      </div>
    </div>

    <a-alert v-if="todoStore.error" type="warning" show-icon class="state-alert">
      <template #message>{{ todoStore.listLoaded ? '待办刷新失败，已保留上次成功数据' : '待办加载失败' }}</template>
      <template #description>{{ todoStore.error }}</template>
    </a-alert>

    <div class="summary-grid">
      <a-card v-for="card in summaryCards" :key="card.key" class="summary-card" :class="card.tone">
        <div class="summary-label">{{ card.label }}</div>
        <div class="summary-value">{{ card.value }}</div>
      </a-card>
    </div>

    <a-card class="filter-card">
      <div class="filter-grid">
        <a-select
          :value="todoStore.filters.module"
          allow-clear
          placeholder="全部模块"
          @change="onModuleChange"
        >
          <a-select-option v-for="option in moduleOptions" :key="option.value" :value="option.value">
            {{ option.label }}
          </a-select-option>
        </a-select>
        <a-select
          :value="todoStore.filters.owner_type"
          allow-clear
          placeholder="全部归属"
          @change="onOwnerChange"
        >
          <a-select-option value="user">指派给我</a-select-option>
          <a-select-option value="role">我的角色待处理</a-select-option>
        </a-select>
        <a-select
          :value="todoStore.filters.status"
          allow-clear
          placeholder="全部状态"
          @change="onStatusChange"
        >
          <a-select-option v-for="status in statusOptions" :key="status" :value="status">
            {{ status }}
          </a-select-option>
        </a-select>
        <a-select
          :value="todoStore.filters.priority"
          allow-clear
          placeholder="全部优先级"
          @change="onPriorityChange"
        >
          <a-select-option v-for="priority in priorityOptions" :key="priority" :value="priority">
            {{ priority }}
          </a-select-option>
        </a-select>
        <a-input
          v-model:value="keyword"
          allow-clear
          placeholder="搜索标题、来源单号或动作"
          @press-enter="applyFilters"
        />
        <a-button type="primary" @click="applyFilters">查询</a-button>
        <a-button @click="resetFilters">重置</a-button>
        <a-checkbox :checked="Boolean(todoStore.filters.overdue)" @change="toggleOverdue">
          仅逾期
        </a-checkbox>
      </div>
    </a-card>

    <a-card class="list-card" :body-style="{ padding: 0 }">
      <div class="list-toolbar">
        <div class="list-title">待处理清单 <span>{{ todoStore.filteredSummary.total }} 项</span></div>
        <div class="identity-hint">身份：{{ auth.user?.name || 'Guest' }}</div>
      </div>

      <a-spin :spinning="todoStore.loading && todoStore.items.length === 0">
        <div v-if="todoStore.items.length === 0" class="empty-state">
          <template v-if="todoStore.error && !todoStore.listLoaded">
            <div class="empty-icon error-icon">!</div>
            <div class="empty-title">待办加载失败，请刷新重试</div>
            <div class="muted">{{ todoStore.error }}</div>
          </template>
          <template v-else>
            <div class="empty-icon">✓</div>
            <div class="empty-title">当前没有匹配的待办</div>
            <div class="muted">新的任务会根据你的指派和业务角色自动出现在这里</div>
          </template>
        </div>

        <div v-else class="table-wrap">
          <a-table
            class="desktop-table"
            :data-source="todoStore.items"
            :columns="columns"
            :pagination="pagination"
            row-key="todo_key"
            @change="onTableChange"
          >
            <template #bodyCell="{ column, record }">
              <template v-if="column.key === 'title'">
                <button type="button" class="title-button" @click="openTodo(record)">{{ record.title }}</button>
                <div class="source-name">{{ record.source_doctype }} · {{ record.source_name }}</div>
              </template>
              <template v-else-if="column.key === 'context'">
                <div class="tag-row">
                  <span class="context-tag module-tag">{{ record.module_label }}</span>
                  <span class="context-tag" :class="record.owner_type === 'user' ? 'user-tag' : 'role-tag'">
                    {{ record.owner_label }}
                  </span>
                </div>
                <div v-if="record.owner_type === 'role' && record.candidate_roles?.length" class="owner-detail">
                  候选：{{ record.candidate_roles.join('、') }}
                </div>
              </template>
              <template v-else-if="column.key === 'status'">
                <a-tag>{{ record.status_label || record.status }}</a-tag>
              </template>
              <template v-else-if="column.key === 'due_at'">
                <span :class="{ overdue: record.is_overdue }">{{ record.due_at || '—' }}</span>
              </template>
              <template v-else-if="column.key === 'priority'">
                <a-tag :color="priorityColor(record.priority)">{{ record.priority || '常规' }}</a-tag>
              </template>
              <template v-else-if="column.key === 'action'">
                <div class="action-cell">
                  <span class="action-label">{{ record.action_label }}</span>
                  <a-button type="link" size="small" :loading="actionLoadingKey === record.todo_key" @click.stop="handleAction(record)">
                    {{ record.execute_mode === 'direct' ? '立即处理' : '打开处理页' }}
                  </a-button>
                </div>
              </template>
            </template>
          </a-table>

          <div class="mobile-list">
            <div v-for="record in todoStore.items" :key="record.todo_key" class="todo-card" role="button" tabindex="0" @click="openTodo(record)">
              <div class="todo-card-top">
                <span class="context-tag module-tag">{{ record.module_label }}</span>
                <span class="context-tag" :class="record.owner_type === 'user' ? 'user-tag' : 'role-tag'">{{ record.owner_label }}</span>
              </div>
              <div class="todo-card-title">{{ record.title }}</div>
              <div class="source-name">{{ record.source_name }} · {{ record.action_label }}</div>
              <div class="todo-card-meta">
                <span>{{ record.priority || '常规' }}</span>
                <span>{{ record.status_label || record.status }}</span>
                <span :class="{ overdue: record.is_overdue }">{{ record.due_at || '无截止日' }}</span>
              </div>
              <a-button size="small" :loading="actionLoadingKey === record.todo_key" @click.stop="handleAction(record)">
                {{ record.execute_mode === 'direct' ? '立即处理' : '打开处理页' }}
              </a-button>
            </div>
          </div>
        </div>
      </a-spin>
    </a-card>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { message } from 'ant-design-vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useTodoStore } from '@/stores/todo'
import type { TodoItem, TodoModule, TodoOwnerType } from '@/api/todo'
import { buildTodoRoute } from '@/features/todos/todoModel'
import { runTodoAction } from '@/features/todos/todoActions'

const POLL_INTERVAL_MS = 60_000
const router = useRouter()
const auth = useAuthStore()
const todoStore = useTodoStore()
const keyword = ref('')
const actionLoadingKey = ref<string | null>(null)
let timer: number | undefined

const moduleOptions: { value: TodoModule; label: string }[] = [
  { value: 'testing', label: '检验业务' },
  { value: 'stability', label: '稳定性' },
  { value: 'retention', label: '留样' },
]

const statusOptions = [
  '已分配', '草稿', '已提交', '已复核', '待取样', '待检测', '检测中', '已完成',
  '应观察', '已逾期', '待审核', '待库存确认', '待QC批准', '待QA批准', '待QM批准',
  '已批准', '待QC主管审核', '待QC负责人审核', '待QA审核', '待QA负责人审核', '待执行',
]
const priorityOptions = ['特急', '紧急', '加急', '高', '中', '常规', '普通', '低']

const summaryCards = computed(() => [
  { key: 'total', label: '全部待办', value: todoStore.summary.total, tone: 'tone-blue' },
  { key: 'assigned', label: '指派给我', value: todoStore.summary.assigned_to_me, tone: 'tone-green' },
  { key: 'role', label: '角色待处理', value: todoStore.summary.role_pending, tone: 'tone-purple' },
  { key: 'overdue', label: '已逾期', value: todoStore.summary.overdue, tone: 'tone-red' },
])

const columns = [
  { title: '待办事项', key: 'title', width: 280 },
  { title: '模块 / 归属', key: 'context', width: 180 },
  { title: '状态', key: 'status', width: 100 },
  { title: '当前动作', key: 'action', width: 120 },
  { title: '优先级', key: 'priority', width: 90 },
  { title: '截止时间', key: 'due_at', width: 130 },
]

const pagination = computed(() => ({
  current: Math.floor((todoStore.filters.offset || 0) / (todoStore.filters.limit || 20)) + 1,
  pageSize: todoStore.filters.limit || 20,
  total: todoStore.filteredSummary.total,
  showSizeChanger: true,
  showTotal: (total: number) => `共 ${total} 项`,
}))

function refreshWhenVisible() {
  if (document.visibilityState === 'visible') return todoStore.refreshAll()
  return Promise.resolve()
}

function applyFilters() {
  todoStore.setFilters({ keyword: keyword.value.trim() || undefined, offset: 0 })
  void todoStore.fetchList()
}

function onModuleChange(value: TodoModule | undefined) {
  todoStore.setFilters({ module: value, offset: 0 })
  void todoStore.fetchList()
}

function onOwnerChange(value: TodoOwnerType | undefined) {
  todoStore.setFilters({ owner_type: value, offset: 0 })
  void todoStore.fetchList()
}

function onStatusChange(value: string | undefined) {
  todoStore.setFilters({ status: value, offset: 0 })
  void todoStore.fetchList()
}

function onPriorityChange(value: string | undefined) {
  todoStore.setFilters({ priority: value, offset: 0 })
  void todoStore.fetchList()
}

function resetFilters() {
  keyword.value = ''
  todoStore.resetFilters()
  void todoStore.fetchList()
}

function toggleOverdue(event: { target: { checked: boolean } }) {
  todoStore.setFilters({ overdue: event.target.checked, offset: 0 })
  void todoStore.fetchList()
}

function onTableChange(page: { current?: number; pageSize?: number }) {
  const pageSize = page.pageSize || 20
  todoStore.setFilters({
    limit: pageSize,
    offset: ((page.current || 1) - 1) * pageSize,
  })
  void todoStore.fetchList()
}

function openTodo(item: TodoItem) {
  const params = { ...item.route_params }
  if (item.route === '/retention/disposal' && params.disposal && !params.focus) {
    params.focus = params.disposal
  }
  void router.push(buildTodoRoute(item.route || '/tasks', params))
}

async function handleAction(item: TodoItem) {
  actionLoadingKey.value = item.todo_key
  try {
    await runTodoAction(item, {
      navigate: openTodo,
      refresh: () => todoStore.refreshAll(),
      notifySuccess: (text) => message.success(text),
      notifyError: (text) => message.error(text),
    })
  } finally {
    actionLoadingKey.value = null
  }
}

function priorityColor(priority: string | null) {
  if (priority === '特急' || priority === '紧急') return 'red'
  if (priority === '加急' || priority === '高') return 'orange'
  return 'default'
}

function formatDateTime(value: string) {
  return value.replace('T', ' ').slice(0, 16)
}

onMounted(() => {
  void auth.checkSession()
  void refreshWhenVisible()
  timer = window.setInterval(refreshWhenVisible, POLL_INTERVAL_MS)
  document.addEventListener('visibilitychange', refreshWhenVisible)
  window.addEventListener('focus', refreshWhenVisible)
})

onBeforeUnmount(() => {
  if (timer !== undefined) window.clearInterval(timer)
  document.removeEventListener('visibilitychange', refreshWhenVisible)
  window.removeEventListener('focus', refreshWhenVisible)
})
</script>

<style scoped>
.todo-page { max-width: 1440px; min-width: 0; padding: 28px 32px 40px; margin: 0 auto; }
.page-heading { display: flex; align-items: flex-end; justify-content: space-between; gap: 20px; margin-bottom: 22px; }
.eyebrow { color: var(--primary); font-size: 11px; font-weight: 700; letter-spacing: .16em; }
h1 { margin: 5px 0 4px; color: var(--text-strong); font-size: 28px; }
.muted { color: var(--text-muted); font-size: 13px; }
.heading-actions { display: flex; align-items: center; gap: 12px; }
.updated-at { color: var(--text-muted); font-size: 12px; }
.state-alert { margin-bottom: 16px; }
.summary-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 14px; margin-bottom: 16px; }
.summary-card { border: 0; overflow: hidden; }
.summary-label { color: var(--text-muted); font-size: 13px; }
.summary-value { margin-top: 10px; color: var(--text-strong); font-size: 30px; font-weight: 700; }
.tone-blue { border-top: 3px solid #3b82f6; }
.tone-green { border-top: 3px solid #16a34a; }
.tone-purple { border-top: 3px solid #8b5cf6; }
.tone-red { border-top: 3px solid #dc2626; }
.filter-card { margin-bottom: 16px; }
.filter-grid { display: grid; grid-template-columns: 170px 170px 150px 120px minmax(220px, 1fr) auto auto auto; align-items: center; gap: 10px; }
.list-card { overflow: hidden; }
.list-toolbar { display: flex; align-items: center; justify-content: space-between; padding: 18px 20px; border-bottom: 1px solid var(--line); }
.list-title { color: var(--text-strong); font-weight: 700; }
.list-title span { margin-left: 5px; color: var(--text-muted); font-weight: 400; }
.identity-hint { color: var(--text-muted); font-size: 12px; }
.table-wrap { min-width: 0; }
.title-button { padding: 0; border: 0; color: var(--primary); background: transparent; cursor: pointer; font: inherit; font-weight: 600; text-align: left; }
.title-button:hover { text-decoration: underline; }
.source-name { margin-top: 4px; color: var(--text-muted); font-size: 11px; }
.tag-row, .todo-card-top { display: flex; flex-wrap: wrap; gap: 6px; }
.owner-detail { margin-top: 5px; color: var(--text-muted); font-size: 11px; line-height: 1.4; }
.context-tag { display: inline-flex; align-items: center; min-height: 22px; padding: 0 7px; border-radius: 4px; font-size: 11px; }
.module-tag { color: #176b64; background: #e4f6f1; }
.user-tag { color: #2459a6; background: #e8f0ff; }
.role-tag { color: #7041a1; background: #f2eafe; }
.action-label { color: var(--text-strong); }
.action-cell { display: flex; align-items: center; flex-wrap: wrap; gap: 2px; }
.overdue { color: #d4380d; font-weight: 700; }
.empty-state { padding: 76px 20px; text-align: center; }
.empty-icon { width: 42px; height: 42px; margin: 0 auto 12px; border-radius: 50%; color: #168b70; background: #e4f6f1; font-size: 24px; line-height: 42px; }
.error-icon { color: #d4380d; background: #fff1f0; }
.empty-title { margin-bottom: 6px; color: var(--text-strong); font-weight: 600; }
.mobile-list { display: none; }

@media (max-width: 900px) {
  .todo-page { padding: 22px 18px 32px; }
  .filter-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .filter-grid :deep(.ant-input), .filter-grid :deep(.ant-select) { width: 100%; }
}

@media (max-width: 600px) {
  .todo-page { padding: 18px 12px 28px; }
  .page-heading { align-items: flex-start; flex-direction: column; margin-bottom: 16px; }
  h1 { font-size: 24px; }
  .heading-actions { width: 100%; justify-content: space-between; }
  .summary-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 10px; }
  .summary-value { font-size: 25px; }
  .filter-grid { grid-template-columns: 1fr; }
  .list-toolbar { align-items: flex-start; flex-direction: column; gap: 6px; padding: 15px; }
  .desktop-table { display: none; }
  .mobile-list { display: grid; gap: 8px; padding: 10px; }
  .todo-card { display: block; width: 100%; padding: 13px; border: 1px solid var(--line); border-radius: 8px; background: #fff; cursor: pointer; text-align: left; }
  .todo-card:hover { border-color: var(--primary); }
  .todo-card-title { margin-top: 10px; color: var(--text-strong); font-size: 14px; font-weight: 600; }
  .todo-card-meta { display: flex; justify-content: space-between; margin-top: 12px; color: var(--text-muted); font-size: 12px; }
}
</style>
