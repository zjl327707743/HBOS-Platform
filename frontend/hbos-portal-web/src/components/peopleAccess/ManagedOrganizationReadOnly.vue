<template>
  <section aria-label="岗位与任职只读查询">
    <p class="iam-note">{{ kind === 'positions' ? '只显示当前账号获准查看的具体岗位。' : '只显示当前账号获准查看的员工任职。' }} 岗位授权与资料维护尚未开放。</p>
    <form class="iam-toolbar" @submit.prevent="search">
      <input v-if="kind === 'positions'" v-model="draftQuery" aria-label="具体岗位名称筛选" placeholder="搜索具体岗位名称" maxlength="80" />
      <button class="iam-btn" type="submit" :disabled="loading">{{ kind === 'positions' ? '搜索' : '刷新任职' }}</button>
    </form>
    <p v-if="loading" class="iam-note" role="status">正在读取{{ kind === 'positions' ? '岗位' : '任职' }}资料…</p>
    <p v-else-if="notice" class="iam-note" role="status">{{ notice }}</p>
    <template v-else-if="ready">
      <div class="iam-table-wrap" tabindex="0" :aria-label="kind === 'positions' ? '具体岗位表，可横向滚动' : '员工任职表，可横向滚动'">
        <table v-if="kind === 'positions'" class="iam-table iam-mapping-table" aria-label="具体岗位">
          <thead><tr><th v-for="label in ['岗位名称', '公司', '部门', '岗位类别', '状态', '版本']" :key="label" scope="col">{{ label }}</th></tr></thead>
          <tbody><tr v-for="position in positions" :key="position.record_id"><td>{{ position.title }}</td><td>{{ position.company_id }}</td><td>{{ position.department_id }}</td><td>{{ position.designation_id || '—' }}</td><td>{{ statusName(position.status) }}</td><td>{{ position.revision }}</td></tr><tr v-if="!positions.length"><td colspan="6" class="iam-empty">暂无可查看的具体岗位</td></tr></tbody>
        </table>
        <table v-else class="iam-table iam-mapping-table" aria-label="员工任职">
          <thead><tr><th v-for="label in ['岗位标识', '主岗', '状态', '开始时间（UTC）', '结束时间（UTC）']" :key="label" scope="col">{{ label }}</th></tr></thead>
          <tbody><tr v-for="assignment in assignments" :key="assignment.record_id"><td>{{ assignment.position_id }}</td><td>{{ assignment.is_primary ? '是' : '否' }}</td><td>{{ statusName(assignment.status) }}</td><td>{{ assignment.valid_from_utc }}</td><td>{{ assignment.valid_until_utc || '—' }}</td></tr><tr v-if="!assignments.length"><td colspan="5" class="iam-empty">暂无可查看的任职资料</td></tr></tbody>
        </table>
      </div>
      <a-pagination v-model:current="page" v-model:page-size="pageSize" class="iam-pagination" :total="total" :show-size-changer="true" :page-size-options="['10', '20', '50']" :show-total="(n: number) => `共 ${n} 条`" size="small" />
    </template>
  </section>
</template>
<script setup lang="ts">
import { onUnmounted, ref, watch } from 'vue'
import { getManagementContext, getManagedPersonAssignments, listManagedPositions, type ManagedPosition, type ManagedPersonAssignment } from '@/services/organizationManagementApi'
import { portalErrorMessage } from '@/services/portalErrors'
const props = defineProps<{ kind: 'positions' | 'assignments'; employeeId?: string }>()
const positions = ref<ManagedPosition[]>([]), assignments = ref<ManagedPersonAssignment[]>([])
const page = ref(1), pageSize = ref(10), total = ref(0), ready = ref(false), loading = ref(false), notice = ref(''), draftQuery = ref(''), query = ref('')
let generation = 0, alive = true
function clearRows() { positions.value = []; assignments.value = []; total.value = 0; ready.value = false }
function statusName(status: string) { return ({ active: '启用', inactive: '停用', revoked: '已撤销' } as Record<string, string>)[status] || status }
function errorCode(error: unknown) { return error && typeof error === 'object' && 'code' in error ? error.code : undefined }
async function load() {
  const current = ++generation, kind = props.kind, employee = props.employeeId
  clearRows(); notice.value = ''; loading.value = true
  if (kind === 'assignments' && !employee) { notice.value = '尚未关联员工资料，无法查询任职。'; loading.value = false; return }
  try {
    const context = await getManagementContext()
    if (!alive || current !== generation) return
    const operation = kind === 'positions' ? 'hbos.organization.position.read' : 'hbos.organization.assignment.read'
    if (!context.operation_ids.includes(operation)) { notice.value = '当前账号没有查看这些资料的权限。'; return }
    if (kind === 'positions') {
      const result = await listManagedPositions({ page: page.value, page_size: pageSize.value, ...(query.value ? { q: query.value } : {}) })
      if (alive && current === generation) { positions.value = result.items; total.value = result.total; ready.value = true }
    } else {
      const result = await getManagedPersonAssignments({ employee_id: employee!, page: page.value, page_size: pageSize.value })
      if (alive && current === generation) { assignments.value = result.items; total.value = result.total; ready.value = true }
    }
  } catch (cause) {
    if (alive && current === generation) {
      clearRows()
      notice.value = errorCode(cause) === 'NOT_SUPPORTED' ? '岗位与任职查询尚未启用。'
        : errorCode(cause) === 'FORBIDDEN' ? '当前账号没有查看这些资料的权限。'
        : portalErrorMessage(cause, '岗位与任职资料暂时无法读取，请稍后重试。')
    }
  } finally { if (alive && current === generation) loading.value = false }
}
function search() { query.value = draftQuery.value.trim(); if (page.value === 1) void load(); else page.value = 1 }
watch([page, pageSize], () => { void load() })
watch(() => [props.kind, props.employeeId], () => {
  generation += 1; clearRows(); query.value = draftQuery.value = ''
  if (page.value !== 1) page.value = 1
  else void load()
}, { immediate: true, flush: 'sync' })
onUnmounted(() => { alive = false; generation += 1; clearRows() })
</script>
