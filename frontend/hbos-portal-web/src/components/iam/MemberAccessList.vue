<script setup lang="ts">
import { computed, ref } from 'vue'
import { SearchOutlined } from '@ant-design/icons-vue'
import StatusTag from './StatusTag.vue'
import EntityName from './EntityName.vue'
import { sourceLabel, type MemberSource, type MemberStatus } from '@/services/assignmentPresentation'

// Members answer one question: who follows the department, who is set
// separately, who cannot use the role yet, and what the next step is. Every
// action here is per person — there is no batch confirm and no auto-advance.
export interface MemberRow {
  employee: string
  name: string
  employeeNumber?: string
  source: MemberSource
  roleName: string
  scopeText: string
  status: MemberStatus
  canConfirm: boolean
  canRevoke: boolean
  personalException: boolean
  reason?: string
}
const props = withDefaults(defineProps<{
  rows: MemberRow[]
  loading?: boolean
  error?: string
  unavailable?: boolean
  total?: number | null
}>(), { loading: false, error: '', unavailable: false, total: null })
const emit = defineEmits<{ confirm: [row: MemberRow]; revoke: [row: MemberRow]; view: [row: MemberRow]; retry: [] }>()

const search = ref(''), sourceFilter = ref('all'), statusFilter = ref('all'), page = ref(1)
const pageSize = 10
const sourceOptions = computed(() => {
  const found = new Set(props.rows.map(row => row.source))
  const rows = [
    { value: 'all', label: '全部来源' },
    { value: 'FOLLOW_DEPARTMENT', label: '跟随部门' },
    { value: 'DIRECT', label: '单独设置' },
    { value: 'NONE', label: '不分配' },
    { value: 'LEGACY', label: '历史安排' },
    { value: 'UNKNOWN', label: '来源待核对' },
  ]
  return rows.filter(row => row.value === 'all' || found.has(row.value as MemberSource))
})
const statusOptions = computed(() => {
  const found = new Set(props.rows.map(row => row.status.label))
  return [{ value: 'all', label: '全部状态' }, ...[...found].map(label => ({ value: label, label }))]
})
const filtered = computed(() => {
  const query = search.value.trim().toLowerCase()
  return props.rows.filter(row => {
    if (sourceFilter.value !== 'all' && row.source !== sourceFilter.value) return false
    if (statusFilter.value !== 'all' && row.status.label !== statusFilter.value) return false
    if (!query) return true
    return [row.name, row.employeeNumber, row.employee].join(' ').toLowerCase().includes(query)
  })
})
const pages = computed(() => Math.max(1, Math.ceil(filtered.value.length / pageSize)))
const visible = computed(() => filtered.value.slice((page.value - 1) * pageSize, page.value * pageSize))
const missingCount = computed(() => props.total !== null && props.total !== undefined ? Math.max(0, props.total - props.rows.length) : 0)
function resetPage() { page.value = 1 }
function changePage(next: number) { if (Number.isInteger(next) && next >= 1 && next <= pages.value) page.value = next }
</script>
<template>
  <div class="r6-members">
    <div class="r6-members__toolbar">
      <a-input v-model:value="search" allow-clear class="r6-members__search" placeholder="搜索姓名或工号" aria-label="搜索部门成员" @update:value="resetPage">
        <template #prefix><SearchOutlined /></template>
      </a-input>
      <a-select v-model:value="sourceFilter" :options="sourceOptions" aria-label="按权限来源筛选" class="r6-members__filter" @update:value="resetPage" />
      <a-select v-model:value="statusFilter" :options="statusOptions" aria-label="按当前状态筛选" class="r6-members__filter" @update:value="resetPage" />
    </div>
    <div v-if="error" class="r6-resource-error" role="alert">
      <a-alert :message="error" type="warning" show-icon />
      <a-button @click="emit('retry')">重新读取成员权限</a-button>
    </div>
    <a-skeleton v-else-if="loading" active />
    <template v-else-if="!rows.length">
      <a-empty :description="unavailable ? '暂无法读取本部门成员权限' : '当前没有可见成员'" />
      <p v-if="unavailable" class="r6-members__empty">当前账号不能核对本部门的成员权限；未按 0 人处理，也不沿用旧结果。</p>
      <p v-else class="r6-members__empty">没有成员不等于不能设置默认；系统不会因此创建员工。</p>
    </template>
    <template v-else>
      <table class="r6-members__table">
        <caption class="r6-visually-hidden">部门成员的权限来源、角色范围与当前状态</caption>
        <thead>
          <tr><th scope="col">员工</th><th scope="col">权限来源</th><th scope="col">角色与范围</th><th scope="col">当前状态</th><th scope="col">操作</th></tr>
        </thead>
        <tbody>
          <tr v-for="row in visible" :key="row.employee">
            <td data-label="员工">
              <div class="r6-members__person">
                <a-avatar :size="34">{{ row.name.slice(-1) }}</a-avatar>
                <EntityName :name="row.name" :meta="row.employeeNumber || '工号待核对'" />
              </div>
            </td>
            <td data-label="权限来源"><span class="r6-members__source">{{ sourceLabel(row.source) }}</span></td>
            <td data-label="角色与范围">
              <strong class="r6-members__role">{{ row.roleName }}</strong>
              <small class="r6-members__scope">{{ row.scopeText }}</small>
            </td>
            <td data-label="当前状态">
              <StatusTag :tone="row.status.tone">{{ row.status.label }}</StatusTag>
              <details v-if="row.status.detail" class="r6-members__reason">
                <summary>查看原因</summary>
                <p>{{ row.status.detail }}</p>
              </details>
            </td>
            <td data-label="操作">
              <div class="r6-members__actions">
                <a-button v-if="row.canConfirm" type="primary" size="small" @click="emit('confirm', row)">{{ row.personalException ? '重新确认角色' : '确认角色' }}</a-button>
                <a-button v-else-if="row.canRevoke" size="small" @click="emit('revoke', row)">撤销角色确认</a-button>
                <a-button type="link" size="small" @click="emit('view', row)">{{ row.source === 'DIRECT' ? '查看个人设置' : '查看安排' }}</a-button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
      <div class="r6-members__cards">
        <article v-for="row in visible" :key="row.employee" class="r6-members__card">
          <div class="r6-members__card-head">
            <div class="r6-members__person"><a-avatar :size="34">{{ row.name.slice(-1) }}</a-avatar><EntityName :name="row.name" :meta="row.employeeNumber || '工号待核对'" /></div>
            <StatusTag :tone="row.status.tone">{{ row.status.label }}</StatusTag>
          </div>
          <dl>
            <div><dt>权限来源</dt><dd>{{ sourceLabel(row.source) }}</dd></div>
            <div><dt>角色与范围</dt><dd>{{ row.roleName }} · {{ row.scopeText }}</dd></div>
            <div v-if="row.status.detail"><dt>说明</dt><dd>{{ row.status.detail }}</dd></div>
          </dl>
          <div class="r6-members__actions">
            <a-button v-if="row.canConfirm" type="primary" size="small" @click="emit('confirm', row)">确认角色</a-button>
            <a-button v-else-if="row.canRevoke" size="small" @click="emit('revoke', row)">撤销角色确认</a-button>
            <a-button type="link" size="small" @click="emit('view', row)">查看安排</a-button>
          </div>
        </article>
      </div>
      <footer class="r6-members__foot">
        <span>显示 {{ filtered.length }} 位{{ missingCount ? `，另有 ${missingCount} 位未返回权限明细` : '' }}</span>
        <a-pagination v-if="pages > 1" :current="page" :total="filtered.length" :page-size="pageSize" :show-size-changer="false" @change="changePage" />
      </footer>
    </template>
  </div>
</template>
