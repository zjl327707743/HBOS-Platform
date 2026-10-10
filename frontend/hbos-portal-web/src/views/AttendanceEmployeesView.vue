<template>
  <section class="product-page app-product-page">
    <div class="emp-hero glass-hero">
      <div>
        <span class="page-kicker">ATTENDANCE · 人员管理</span>
        <h1>人员管理</h1>
        <p>在职员工名录与固定班次绑定；只读展示，数据来自 HRMS Employee 主数据</p>
      </div>
    </div>

    <section class="section-panel glass-surface">
      <div class="emp-toolbar">
        <a-select
          v-model:value="department"
          style="width: 220px"
          :options="deptOptions"
          placeholder="全部部门"
          allow-clear
          @change="load"
        />
        <a-input-search
          v-model:value="search"
          style="width: 240px"
          placeholder="搜索姓名 / 工号"
          @search="load"
        />
        <a-button type="primary" :loading="loading" @click="load">查询</a-button>
        <span class="emp-count">共 {{ employees.length }} 人</span>
      </div>

      <a-alert v-if="error" type="error" show-icon :message="error" />
      <a-table
        v-else
        :data-source="employees"
        :loading="loading"
        :pagination="{ pageSize: 20, size: 'small', showSizeChanger: false }"
        row-key="name"
        size="middle"
        :scroll="{ y: 560 }"
      >
        <a-table-column title="工号" data-index="employee_number" key="num" :width="130" />
        <a-table-column title="姓名" data-index="employee_name" key="name" :width="130" />
        <a-table-column title="部门" data-index="department" key="dept" />
        <a-table-column title="联系方式" key="cell" :width="150">
          <template #default="{ record }">{{ record.cell_number || '—' }}</template>
        </a-table-column>
        <a-table-column title="入职日期" key="join" :width="130">
          <template #default="{ record }">{{ record.date_of_joining || '—' }}</template>
        </a-table-column>
        <a-table-column title="固定班次" key="shift" :width="180">
          <template #default="{ record }">
            <a-tag v-if="record.hbos_fixed_shift" color="blue">{{ shiftLabel(record) }}</a-tag>
            <span v-else class="emp-none">未绑定</span>
          </template>
        </a-table-column>
      </a-table>
    </section>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import {
  fetchDepartments,
  fetchEmployees,
  type DepartmentCount,
  type EmployeeRow,
} from '@/services/attendanceEmployees'

const employees = ref<EmployeeRow[]>([])
const departments = ref<DepartmentCount[]>([])
const department = ref<string | undefined>(undefined)
const search = ref('')
const loading = ref(false)
const error = ref('')

const deptOptions = computed(() =>
  departments.value.map((d) => ({ value: d.department, label: `${d.department}（${d.cnt}人）` })),
)

/** 班次列显示「班次类型 起-止」；只有 rule 没关联到种类时退回规则名。 */
function shiftLabel(row: EmployeeRow) {
  if (!row.shift_type) return row.hbos_fixed_shift || ''
  const span = row.start_time && row.end_time ? ` ${row.start_time}-${row.end_time}` : ''
  return `${row.shift_type}${span}`
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    employees.value = await fetchEmployees({
      department: department.value || undefined,
      search: search.value.trim() || undefined,
    })
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : '加载人员列表失败'
    employees.value = []
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  // 部门下拉是筛选项，失败不阻断列表
  try {
    departments.value = await fetchDepartments()
  } catch {
    departments.value = []
  }
  await load()
})
</script>

<style scoped>
.emp-hero {
  padding: 24px 26px;
  border-radius: var(--hbos-radius-hero);
  margin-bottom: 16px;
}
.emp-hero h1 { margin: 8px 0 6px; font-size: 30px; line-height: 38px; }
.emp-hero p { margin: 0; font-size: 14px; line-height: 22px; color: var(--hbos-text-secondary); }

.emp-toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
  margin-bottom: 16px;
}
.emp-count { margin-left: auto; font-size: 12px; color: var(--hbos-text-muted); }
.emp-none { color: var(--hbos-text-muted); opacity: .6; }

@media (max-width: 720px) {
  .emp-hero h1 { font-size: 20px; line-height: 28px; }
  .emp-count { margin-left: 0; }
}
</style>
