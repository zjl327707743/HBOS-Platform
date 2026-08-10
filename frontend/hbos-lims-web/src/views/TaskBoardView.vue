<template>
  <div class="page">
    <div class="page-head">
      <div>
        <h1>待检任务看板</h1>
        <p>按检验任务状态流转，支持超时预警与 OOS 候选标记</p>
      </div>
      <div class="page-actions">
        <el-button type="primary" @click="openGenerate">生成检验任务</el-button>
      </div>
    </div>

    <div class="filter-bar">
      <el-select v-model="filters.priority" placeholder="全部优先级" clearable style="width:140px" size="default">
        <el-option label="常规" value="常规" />
        <el-option label="加急" value="加急" />
        <el-option label="特急" value="特急" />
      </el-select>
      <el-input v-model="filters.search" placeholder="搜索样品 / 任务编号" clearable style="width:240px" size="default" />
      <span class="pill muted total-pill">{{ tasks.length }} 项任务</span>
    </div>

    <div v-loading="loading" class="kanban">
      <div v-for="col in columns" :key="col.key" class="kb-col">
        <div class="kb-head">
          <span class="dot" :style="{ background: col.color }"></span>
          <b>{{ col.title }}</b>
          <span class="count">{{ colTasks(col.key).length }}</span>
        </div>
        <div class="kb-body">
          <div v-for="task in colTasks(col.key)" :key="task.task_name" class="task-card">
            <div class="no mono">{{ task.task_name }}</div>
            <div class="name">{{ task.item_name }}</div>
            <div class="meta">
              <span class="mono">{{ task.sample }}</span>
              <span>{{ task.lab_department }} · {{ task.material_name }}</span>
              <span v-if="task.assignee">{{ task.assignee }}</span>
            </div>
            <div class="foot">
              <span class="pill" :class="priorityClass(task.priority)">{{ task.priority }}</span>
              <span v-if="task.overdue === '是'" class="due late">已超时</span>
            </div>
            <div class="actions">
              <el-button v-if="canAssign(task)" type="primary" size="small" @click="assignTask(task)">分配</el-button>
              <el-button v-if="canStart(task)" type="success" size="small" :loading="actionLoading" @click="startTask(task)">开始检验</el-button>
              <el-button v-if="canSubmit(task)" type="warning" size="small" @click="goResult(task)">录入结果</el-button>
            </div>
          </div>
          <div v-if="colTasks(col.key).length === 0" class="kb-empty">暂无任务</div>
        </div>
      </div>
    </div>

    <el-dialog v-model="showGenerate" title="生成检验任务" width="420">
      <el-form label-position="top">
        <el-form-item label="样品编号">
          <el-select v-model="generateForm.sample" style="width:100%" filterable placeholder="选择已登记样品">
            <el-option v-for="s in registeredSamples" :key="s.name" :label="`${s.name}（${s.material_name}）`" :value="s.name" />
          </el-select>
        </el-form-item>
        <el-form-item label="检验组">
          <el-input v-model="generateForm.department" placeholder="TEST-HBOS-M2-DEP-PH" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showGenerate = false">取消</el-button>
        <el-button type="primary" :loading="actionLoading" @click="doGenerate">生成任务</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useTaskStore, type TaskRow } from '@/stores/task'
import { useSampleStore } from '@/stores/sample'
import { assignTask as apiAssign, startTask as apiStart, generateTasks } from '@/api/lims'

const router = useRouter()
const taskStore = useTaskStore()
const sampleStore = useSampleStore()
const loading = computed(() => taskStore.loading)
const tasks = computed(() => taskStore.tasks)

const actionLoading = ref(false)
const showGenerate = ref(false)
const generateForm = reactive({ sample: '', department: 'TEST-HBOS-M2-DEP-PH' })

const columns = [
  { key: '待分配', title: '待分配', color: '#9aa8a3' },
  { key: '已分配', title: '已分配', color: '#5f8d80' },
  { key: '检验中', title: '检验中', color: '#2b8a73' },
  { key: '已提交', title: '已提交', color: '#d1871d' },
  { key: '已复核', title: '已复核', color: '#2b6cb0' },
  { key: '已批准', title: '已批准', color: '#1d8a5b' },
  { key: 'OOS候选', title: 'OOS 候选', color: '#c24d3f' },
]

const filters = reactive({ priority: '', search: '' })

const registeredSamples = computed(() => sampleStore.samples.filter((s) => ['已登记'].includes(s.status || '')))

function colTasks(status: string) {
  return tasks.value.filter((t) => {
    const matchStatus = t.status === status
    const matchPriority = !filters.priority || t.priority === filters.priority
    const matchSearch = !filters.search || t.task_name.includes(filters.search) || t.sample.includes(filters.search)
    return matchStatus && matchPriority && matchSearch
  })
}

function priorityClass(p: string) {
  return { 特急: 'pill-danger', 加急: 'pill-warn', 常规: 'pill-info' }[p] || 'pill-muted'
}

function canAssign(task: TaskRow) {
  return task.status === '待分配'
}
function canStart(task: TaskRow) {
  return task.status === '已分配'
}
function canSubmit(task: TaskRow) {
  return ['检验中'].includes(task.status)
}

async function assignTask(task: TaskRow) {
  actionLoading.value = true
  try {
    await apiAssign(task.task_name)
    ElMessage.success(`任务 ${task.task_name} 已分配`)
    await taskStore.fetchBoard()
  } finally {
    actionLoading.value = false
  }
}

async function startTask(task: TaskRow) {
  actionLoading.value = true
  try {
    await apiStart(task.task_name)
    ElMessage.success(`任务 ${task.task_name} 已开始检验`)
    await taskStore.fetchBoard()
  } finally {
    actionLoading.value = false
  }
}

function goResult(task: TaskRow) {
  router.push(`/results/${task.task_name}`)
}

function openGenerate() {
  showGenerate.value = true
}

async function doGenerate() {
  if (!generateForm.sample) {
    ElMessage.warning('请选择样品')
    return
  }
  actionLoading.value = true
  try {
    const created = await generateTasks(generateForm.sample, generateForm.department)
    ElMessage.success(`已生成 ${created.length} 个检验任务`)
    showGenerate.value = false
    await taskStore.fetchBoard()
  } finally {
    actionLoading.value = false
  }
}

onMounted(async () => {
  await Promise.all([taskStore.fetchBoard(), sampleStore.fetchAll()])
})
</script>

<style scoped>
.page-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 14px; }
.page-head h1 { font-size: 20px; color: var(--ink); }
.page-head p { font-size: 12px; color: var(--muted); margin-top: 4px; }
.page-actions { display: flex; gap: 8px; }
.filter-bar { display: flex; gap: 10px; align-items: center; margin-bottom: 14px; flex-wrap: wrap; }
.total-pill { margin-left: auto; }

.kanban { display: grid; grid-template-columns: repeat(7, 1fr); gap: 10px; overflow-x: auto; min-height: 300px; }
.kb-col { background: var(--surface-2); border: 1px solid var(--line); border-radius: var(--radius); min-height: 300px; display: flex; flex-direction: column; }
.kb-head { display: flex; align-items: center; gap: 8px; padding: 10px 12px; border-bottom: 1px solid var(--line); font-size: 13px; }
.kb-head .dot { width: 8px; height: 8px; border-radius: 50%; }
.kb-head .count { margin-left: auto; background: var(--surface); border: 1px solid var(--line); border-radius: 9px; font-size: 11px; padding: 1px 7px; color: var(--muted); }
.kb-body { padding: 10px; flex: 1; overflow-y: auto; display: flex; flex-direction: column; gap: 8px; }

.task-card { background: var(--surface); border: 1px solid var(--line); border-radius: 6px; padding: 10px 12px; }
.task-card .no { font-size: 11px; color: var(--muted); }
.task-card .name { font-size: 13px; font-weight: 600; color: var(--ink); margin-top: 4px; }
.task-card .meta { font-size: 11px; color: var(--muted); margin-top: 6px; display: flex; flex-direction: column; gap: 2px; }
.task-card .foot { display: flex; align-items: center; justify-content: space-between; margin-top: 8px; }
.task-card .due { font-size: 11px; color: var(--muted); }
.task-card .due.late { color: var(--danger); font-weight: 600; }
.task-card .actions { display: flex; gap: 6px; margin-top: 8px; }
.kb-empty { color: var(--muted); font-size: 12px; text-align: center; padding: 24px 0; }
@media (max-width: 1180px) { .kanban { grid-template-columns: repeat(4, 260px); } }
</style>
