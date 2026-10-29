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
        <a-table-column title="考勤" key="records" :width="120"><template #default="{record}"><a-button type="link" @click="openRecords(record)">查看考勤</a-button></template></a-table-column>
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
    <a-modal v-model:open="recordsOpen" :title="selectedEmployee?.employee_name + ' · 员工考勤'" :footer="null" width="800px"><p>按当前负责范围核验所选员工在查询期间的部门归属。</p><a-space wrap><a-input v-model:value="fromDate" type="date" aria-label="员工考勤开始日期"/><a-input v-model:value="toDate" type="date" aria-label="员工考勤结束日期"/><a-button :loading="recordsBusy" @click="loadRecords()">查询</a-button></a-space><a-alert v-if="recordsError" :message="recordsError" type="warning"/><p v-if="recordData">查询期间 {{recordData.date_from}} 至 {{recordData.date_to}} · 共 {{recordData.total}} 条</p><a-table v-if="recordData" :data-source="recordData.rows" :columns="recordColumns" row-key="id" :pagination="{current:recordData.page,pageSize:recordData.page_size,total:recordData.total,onChange:(value:number)=>loadRecords(value)}" :loading="recordsBusy"/></a-modal>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { iamQuery, iamMessage } from '@/services/iamAccess'
import type { MyAttendance } from '@/types/iam'
const recordsOpen=ref(false),recordsBusy=ref(false),recordsError=ref(''),selectedEmployee=ref<EmployeeRow|null>(null),recordData=ref<MyAttendance|null>(null),fromDate=ref(''),toDate=ref('')
const recordColumns=[{title:'日期',dataIndex:'date'},{title:'时间',dataIndex:'time'},{title:'状态',dataIndex:'status'},{title:'来源',dataIndex:'source'}]
async function openRecords(row:EmployeeRow){selectedEmployee.value=row;recordData.value=null;recordsError.value='';recordsOpen.value=true;await loadRecords()}
let recordGeneration=0
async function loadRecords(page=1){if(!selectedEmployee.value)return;recordsBusy.value=true;recordsError.value='';const run=++recordGeneration,target=selectedEmployee.value.name;try{const result=await iamQuery<MyAttendance>('hb_attendance_app.hbos_attendance.page.hbos_employee_management.employee_management_data.get_department_attendance',{employee:selectedEmployee.value.name,department:selectedEmployee.value.department,...(fromDate.value?{date_from:fromDate.value}:{}),...(toDate.value?{date_to:toDate.value}:{}),page,page_size:20});if(run===recordGeneration&&selectedEmployee.value?.name===target)recordData.value=result}catch(e){if(run===recordGeneration){recordsError.value=iamMessage(e);recordData.value=null}}finally{if(run===recordGeneration)recordsBusy.value=false}}

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
