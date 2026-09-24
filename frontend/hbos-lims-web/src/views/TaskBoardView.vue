<template>
  <div class="page">
    <div class="page-head">
      <div>
        <h1>待检任务看板</h1>
        <p>按检验任务状态流转，支持超时预警与 OOS 候选标记</p>
      </div>
      <div class="page-actions">
        <a-button type="primary" @click="openGenerate">生成检验任务</a-button>
      </div>
    </div>

    <div class="filter-bar">
      <a-select v-model:value="filters.priority" placeholder="全部优先级" allow-clear style="width:140px">
        <a-select-option value="常规">常规</a-select-option>
        <a-select-option value="加急">加急</a-select-option>
        <a-select-option value="特急">特急</a-select-option>
      </a-select>
      <a-input v-model:value="filters.search" placeholder="搜索样品 / 任务编号" allow-clear style="width:240px" />
      <span class="pill muted total-pill">{{ tasks.length }} 项任务</span>
    </div>
    <a-alert
      v-if="targetTaskName"
      :type="targetTaskMissing ? 'warning' : 'info'"
      show-icon
      :message="targetTaskMissing ? `来源任务 ${targetTaskName} 当前不在我的待办范围内` : `已定位来源任务 ${targetTaskName}`"
      style="margin-bottom: 12px"
    />

    <div class="panel board-panel">
      <a-tabs v-model:activeKey="activeTab" type="card" size="small" class="task-tabs">
        <a-tab-pane v-for="col in columns" :key="col.key" :force-render="true">
          <template #tab>
            <span class="tab-label">
              <span class="dot" :style="{ background: col.color }"></span>
              {{ col.title }}
              <a-badge
                :count="colTasks(col.key).length"
                :number-style="badgeStyle(col)"
                :offset="[6, -4]"
                :show-zero="false"
              />
            </span>
          </template>

          <div class="tab-body">
            <div v-for="task in colTasks(col.key)" :key="task.task_name" class="task-card" :class="{ 'todo-target': targetTaskName === task.task_name }">
              <div class="task-head">
                <span class="no mono">{{ task.task_name }}</span>
                <span class="pill" :class="priorityClass(task.priority)">{{ task.priority }}</span>
                <span v-if="task.overdue === '是'" class="due late">已超时</span>
              </div>
              <div class="name">{{ task.item_name }}</div>
              <div class="meta">
                <span class="mono">{{ task.sample }}</span>
                <span>{{ task.lab_department }} · {{ task.material_name }}</span>
                <span v-if="task.assignee">检验员：{{ task.assignee }}</span>
              </div>
              <div class="actions">
                <a-button v-if="task.status === '待分配'" type="primary" size="small" @click="assignTask(task)">分配</a-button>
                <a-button v-if="task.status === '已分配'" type="primary" size="small" :loading="actionLoading" @click="startTask(task)">开始检验</a-button>
                <a-button v-if="task.status === '检验中'" type="warning" size="small" @click="goResult(task)">录入结果</a-button>
                <a-button v-if="task.status === '已提交'" type="default" size="small" :loading="actionLoading" @click="reviewTask(task)">复核</a-button>
                <a-button v-if="task.status === '已复核'" type="primary" size="small" :loading="actionLoading" @click="approveTask(task)">批准</a-button>
                <a-button v-if="['已提交','已复核','已批准'].includes(task.status)" type="link" size="small" @click="goResult(task)">查看</a-button>
              </div>
            </div>
            <a-empty v-if="colTasks(col.key).length === 0" description="暂无任务" :image="emptyImage" />
          </div>
        </a-tab-pane>
      </a-tabs>
    </div>

    <a-modal v-model:open="showAssign" title="分配检验任务" :footer="null" width="420">
      <a-form :model="assignForm" layout="vertical">
        <a-form-item label="检验任务">
          <a-input :value="assignForm.task" disabled />
        </a-form-item>
        <a-form-item label="检验员">
          <a-select v-model:value="assignForm.assignee" style="width:100%" show-search placeholder="选择检验员">
            <a-select-option v-for="u in analystUsers" :key="u.name" :value="u.name">
              {{ u.full_name || u.name }}（{{ u.name }}）
            </a-select-option>
          </a-select>
        </a-form-item>
        <div class="modal-footer">
          <a-button @click="showAssign = false">取消</a-button>
          <a-button type="primary" :loading="actionLoading" @click="confirmAssign">确认分配</a-button>
        </div>
      </a-form>
    </a-modal>

    <a-modal v-model:open="showGenerate" title="生成检验任务" :footer="null" width="420">
      <a-form :model="generateForm" layout="vertical">
        <a-form-item label="样品编号">
          <a-select v-model:value="generateForm.sample" style="width:100%" show-search placeholder="选择已登记样品">
            <a-select-option v-for="s in registeredSamples" :key="s.name" :value="s.name">{{ s.name }}（{{ s.material_name }}）</a-select-option>
          </a-select>
        </a-form-item>
        <a-form-item label="检验组">
          <a-input v-model:value="generateForm.department" placeholder="请输入检验组" />
        </a-form-item>
        <div class="modal-footer">
          <a-button @click="showGenerate = false">取消</a-button>
          <a-button type="primary" :loading="actionLoading" @click="doGenerate">生成任务</a-button>
        </div>
      </a-form>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import { Empty } from 'ant-design-vue'
import { useTaskStore, type TaskRow } from '@/stores/task'
import { useSampleStore } from '@/stores/sample'
import {
  assignTask as apiAssign, startTask as apiStart, generateTasks,
  reviewResult, approveResult, listDoctype,
} from '@/api/lims'
import { readScalarQuery } from '@/features/todos/todoModel'

const router = useRouter()
const route = useRoute()
const taskStore = useTaskStore()
const sampleStore = useSampleStore()
const tasks = computed(() => taskStore.tasks)

const actionLoading = ref(false)
const showGenerate = ref(false)
const showAssign = ref(false)
const generateForm = reactive({ sample: '', department: '' })
const assignForm = reactive({ task: '', assignee: '' })
const analystUsers = ref<Array<{ name: string; full_name?: string }>>([])

const emptyImage = Empty.PRESENTED_IMAGE_SIMPLE
const activeTab = ref('pending')
const targetTaskName = ref('')
const targetTaskMissing = ref(false)

const columns = [
  { key: 'pending', title: '待分配', status: '待分配', color: '#9aa8a3' },
  { key: 'assigned', title: '已分配', status: '已分配', color: '#5f8d80' },
  { key: 'testing', title: '检验中', status: '检验中', color: '#2b8a73' },
  { key: 'submitted', title: '已提交', status: '已提交', color: '#d1871d' },
  { key: 'reviewed', title: '已复核', status: '已复核', color: '#2b6cb0' },
  { key: 'approved', title: '已批准', status: '已批准', color: '#1d8a5b' },
  { key: 'oos', title: 'OOS 候选', status: 'OOS候选', color: '#c24d3f' },
]

const filters = reactive({ priority: '', search: '' })

const registeredSamples = computed(() => sampleStore.samples.filter((s) => ['已登记'].includes(s.status || '')))

const taskResultMap = ref<Record<string, string>>({})

function colTasks(statusKey: string) {
  const col = columns.find((c) => c.key === statusKey)
  if (!col) return []
  return tasks.value.filter((t) => {
    const matchStatus = t.status === col.status
    const matchPriority = !filters.priority || t.priority === filters.priority
    const matchSearch = !filters.search || t.task_name.includes(filters.search) || t.sample.includes(filters.search)
    return matchStatus && matchPriority && matchSearch
  })
}

/**
 * 徽标样式（按板块适配）：
 * - 无任务：灰色
 * - 有任务（常规流转）：绿色
 * - 有加急：橙色
 * - OOS 候选：红色
 */
function badgeStyle(col: { key: string; status: string }) {
  const list = colTasks(col.key)
  if (list.length === 0) {
    return { backgroundColor: '#8c8c8c', boxShadow: 'none' }
  }
  if (col.key === 'oos') {
    return { backgroundColor: '#c24d3f', boxShadow: 'none' }
  }
  // 加急/特急任务存在时用橙色提示
  const hasUrgent = list.some((t) => ['加急', '特急'].includes(t.priority))
  if (hasUrgent) {
    return { backgroundColor: '#fa8c16', boxShadow: 'none' }
  }
  return { backgroundColor: '#52c41a', boxShadow: 'none' }
}

function priorityClass(p: string) {
  return { 特急: 'pill-danger', 加急: 'pill-warn', 常规: 'pill-info' }[p] || 'pill-muted'
}

function getResultName(task: TaskRow): string | undefined {
  return taskResultMap.value[task.task_name]
}

async function assignTask(task: TaskRow) {
  assignForm.task = task.task_name
  assignForm.assignee = task.assignee || ''
  showAssign.value = true
}

async function confirmAssign() {
  if (!assignForm.assignee) {
    message.warning('请选择检验员')
    return
  }
  actionLoading.value = true
  try {
    await apiAssign(assignForm.task, assignForm.assignee)
    message.success(`任务 ${assignForm.task} 已分配给 ${assignForm.assignee}`)
    showAssign.value = false
    await loadBoard()
  } finally {
    actionLoading.value = false
  }
}

async function startTask(task: TaskRow) {
  actionLoading.value = true
  try {
    await apiStart(task.task_name)
    message.success(`任务 ${task.task_name} 已开始检验`)
    await loadBoard()
  } finally {
    actionLoading.value = false
  }
}

function goResult(task: TaskRow) {
  router.push(`/results/${task.task_name}`)
}

async function reviewTask(task: TaskRow) {
  const resultName = getResultName(task)
  if (!resultName) {
    message.warning('该任务暂无可复核的检测记录')
    return
  }
  actionLoading.value = true
  try {
    await reviewResult(resultName)
    message.success(`检测记录 ${resultName} 已复核`)
    await loadBoard()
  } finally {
    actionLoading.value = false
  }
}

async function approveTask(task: TaskRow) {
  const resultName = getResultName(task)
  if (!resultName) {
    message.warning('该任务暂无可批准的检测记录')
    return
  }
  actionLoading.value = true
  try {
    await approveResult(resultName)
    message.success(`检测记录 ${resultName} 已批准`)
    await loadBoard()
  } finally {
    actionLoading.value = false
  }
}

async function loadBoard() {
  targetTaskName.value = readScalarQuery(route.query.task) || ''
  targetTaskMissing.value = false
  await taskStore.fetchBoard(route.query.scope === 'mine' ? { scope: 'mine' } : {})
  if (targetTaskName.value) {
    const target = tasks.value.find((task) => task.task_name === targetTaskName.value)
    targetTaskMissing.value = !target
    if (target) {
      const targetColumn = columns.find((column) => column.status === target.status)
      if (targetColumn) activeTab.value = targetColumn.key
    }
  }
  const taskNames = tasks.value.map((t) => t.task_name)
  if (taskNames.length > 0) {
    try {
      const docs = await listDoctype<any>(
        'HBOS Sample Task',
        ['name', 'result'],
        { name: ['in', taskNames] },
        100,
      )
      const map: Record<string, string> = {}
      for (const d of docs) {
        if (d.result) map[d.name] = d.result
      }
      taskResultMap.value = map
    } catch {
      taskResultMap.value = {}
    }
  }
}

function openGenerate() {
  showGenerate.value = true
}

async function doGenerate() {
  if (!generateForm.sample) {
    message.warning('请选择样品')
    return
  }
  actionLoading.value = true
  try {
    const created = await generateTasks(generateForm.sample, generateForm.department)
    message.success(`已生成 ${created.length} 个检验任务`)
    showGenerate.value = false
    await loadBoard()
  } finally {
    actionLoading.value = false
  }
}

async function loadAnalystUsers() {
  try {
    const users = await listDoctype<{ name: string; full_name?: string }>(
      'User',
      ['name', 'full_name'],
      { enabled: 1, user_type: 'System' },
      200,
      'full_name asc',
    )
    analystUsers.value = users.filter((user) => user.name && user.name !== 'Guest')
  } catch {
    analystUsers.value = []
  }
}

onMounted(async () => {
  await Promise.all([sampleStore.fetchAll(), loadAnalystUsers()])
  await loadBoard()
})
</script>

<style scoped>
.page-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 14px; }
.page-head h1 { font-size: 20px; color: var(--ink); }
.page-head p { font-size: 12px; color: var(--muted); margin-top: 4px; }
.page-actions { display: flex; gap: 8px; }
.filter-bar { display: flex; gap: 10px; align-items: center; margin-bottom: 14px; flex-wrap: wrap; }
.total-pill { margin-left: auto; }

.panel { background: var(--surface); border: 1px solid var(--line); border-radius: var(--radius); }
.board-panel { padding: 14px; }

.tab-label {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  font-weight: 500;
}
.tab-label .dot { width: 8px; height: 8px; border-radius: 50%; display: inline-block; }

.task-tabs :deep(.ant-tabs-nav) { margin-bottom: 12px; }
.task-tabs :deep(.ant-tabs-tab) { padding: 6px 14px; }

.tab-body { display: flex; flex-direction: column; gap: 10px; min-height: 200px; }

.task-card {
  background: var(--surface-2);
  border: 1px solid var(--line);
  border-radius: 6px;
  padding: 12px 14px;
  transition: box-shadow 0.12s ease, border-color 0.12s ease;
}
.task-card:hover { box-shadow: 0 2px 8px rgba(13, 43, 40, 0.08); border-color: #b8c6c0; }
.task-card.todo-target { border-color: var(--primary); box-shadow: 0 0 0 2px rgba(43, 138, 115, 0.14); }

.task-head { display: flex; align-items: center; gap: 8px; }
.task-head .no { font-size: 11px; color: var(--muted); flex: 1; }
.task-head .due { font-size: 11px; color: var(--muted); }
.task-head .due.late { color: var(--danger); font-weight: 600; }

.task-card .name { font-size: 14px; font-weight: 600; color: var(--ink); margin-top: 6px; }
.task-card .meta { font-size: 12px; color: var(--muted); margin-top: 6px; display: flex; flex-direction: column; gap: 3px; }
.task-card .actions { display: flex; gap: 6px; margin-top: 10px; flex-wrap: wrap; }

.modal-footer { display: flex; justify-content: flex-end; gap: 8px; }
</style>
