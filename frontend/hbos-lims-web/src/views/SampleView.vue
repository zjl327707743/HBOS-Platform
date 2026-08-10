<template>
  <div class="page">
    <el-tabs v-model="activeTab">
      <el-tab-pane label="样品登记" name="register">
        <div class="page-head">
          <div>
            <h1>样品登记</h1>
            <p>登记样品后自动匹配已生效质量标准，并生成检验项目快照</p>
          </div>
          <div class="page-actions">
            <el-button @click="resetForm">重置</el-button>
            <el-button type="primary" :loading="submitting" @click="submitSample">
              <el-icon><DocumentAdd /></el-icon>&nbsp;登记样品
            </el-button>
          </div>
        </div>

        <div class="reg-grid">
          <div class="panel">
            <div class="panel-head">
              <div><h3>样品基础信息</h3><div class="sub">带 * 为必填项</div></div>
            </div>
            <div class="panel-body">
              <el-form :model="form" label-position="top" size="default">
                <div class="form-grid">
                  <el-form-item label="样品类型 *">
                    <el-select v-model="form.sample_type" placeholder="选择类型" style="width:100%" filterable>
                      <el-option v-for="t in sampleTypes" :key="t" :label="t" :value="t" />
                    </el-select>
                  </el-form-item>
                  <el-form-item label="检验优先级 *">
                    <el-select v-model="form.priority" placeholder="选择优先级" style="width:100%">
                      <el-option label="常规" value="常规" />
                      <el-option label="加急" value="加急" />
                      <el-option label="特急" value="特急" />
                    </el-select>
                  </el-form-item>
                  <el-form-item label="物料编码 *">
                    <el-input v-model="form.material_code" placeholder="TEST-HBOS-M2-RM-001" />
                  </el-form-item>
                  <el-form-item label="物料名称 *">
                    <el-input v-model="form.material_name" placeholder="TEST-HBOS-M2-原料A-01" />
                  </el-form-item>
                  <el-form-item label="批号 *">
                    <el-input v-model="form.batch_no" placeholder="TEST-HBOS-M2-B240801" />
                  </el-form-item>
                  <el-form-item label="样品来源 *">
                    <el-select v-model="form.sample_source" style="width:100%">
                      <el-option label="生产取样" value="生产取样" />
                      <el-option label="来样送检" value="来样送检" />
                      <el-option label="稳定性取样" value="稳定性取样" />
                      <el-option label="环境监测" value="环境监测" />
                    </el-select>
                  </el-form-item>
                  <el-form-item label="质量标准 *">
                    <el-select v-model="form.specification" style="width:100%" @change="onSpecChange" filterable>
                      <el-option v-for="s in specifications" :key="s.name" :label="`${s.name}（${s.status}）`" :value="s.name" />
                    </el-select>
                  </el-form-item>
                  <el-form-item label="检验时限">
                    <el-date-picker v-model="form.test_due_date" type="date" placeholder="选择日期" style="width:100%" value-format="YYYY-MM-DD" />
                  </el-form-item>
                  <el-form-item label="备注" class="full">
                    <el-input v-model="form.remarks" type="textarea" :rows="3" placeholder="登记备注（可选）" />
                  </el-form-item>
                </div>
              </el-form>
            </div>
          </div>

          <div>
            <div class="spec-match">
              <div class="k">已匹配质量标准</div>
              <div class="v mono">{{ form.specification || '—' }}</div>
              <div class="meta">{{ matchedSpec ? `版本 V${matchedSpec.version} · 状态 ${matchedSpec.status}` : '选择质量标准后自动载入' }}</div>
            </div>

            <div class="panel spec-items">
              <div class="panel-head"><div><h3>检验项目快照</h3><div class="sub">登记后冻结标准与限度</div></div></div>
              <div class="panel-body">
                <el-table :data="specItems" size="small" stripe v-loading="specLoading">
                  <el-table-column prop="item" label="项目" min-width="90" />
                  <el-table-column prop="limits" label="限度" min-width="100" />
                  <el-table-column prop="unit" label="单位" width="60" />
                </el-table>
              </div>
            </div>
          </div>
        </div>
      </el-tab-pane>

      <el-tab-pane label="样品台账" name="ledger">
        <div class="page-head">
          <div>
            <h1>样品台账</h1>
            <p>全部登记样品的状态跟踪</p>
          </div>
        </div>
        <div class="panel">
          <div class="panel-body">
            <el-table :data="ledgerRows" size="small" stripe v-loading="ledgerLoading">
              <el-table-column prop="sample_name" label="样品编号" width="190">
                <template #default="{ row }"><span class="mono">{{ row.sample_name }}</span></template>
              </el-table-column>
              <el-table-column prop="material_name" label="物料名称" min-width="150" />
              <el-table-column prop="batch_no" label="批号" width="140">
                <template #default="{ row }"><span class="mono">{{ row.batch_no }}</span></template>
              </el-table-column>
              <el-table-column prop="sample_type" label="类型" width="100" />
              <el-table-column prop="status" label="状态" width="110">
                <template #default="{ row }">
                  <span class="pill" :class="statusClass(row.status)">{{ row.status }}</span>
                </template>
              </el-table-column>
              <el-table-column prop="priority" label="优先级" width="80">
                <template #default="{ row }">
                  <span class="pill" :class="priorityClass(row.priority)">{{ row.priority }}</span>
                </template>
              </el-table-column>
              <el-table-column prop="requestor" label="请验人" width="110" />
            </el-table>
          </div>
        </div>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { DocumentAdd } from '@element-plus/icons-vue'
import { registerSample, listDoctype, getDoc, runReport } from '@/api/lims'

const activeTab = ref('register')
const submitting = ref(false)
const specLoading = ref(false)
const ledgerLoading = ref(false)

const sampleTypes = ref<string[]>([])
const specifications = ref<{ name: string; status: string; version: string }[]>([])
const specItems = ref<{ item: string; limits: string; unit: string }[]>([])
const ledgerRows = ref<Record<string, unknown>[]>([])

const form = reactive({
  sample_type: '',
  priority: '常规',
  material_code: '',
  material_name: '',
  batch_no: '',
  sample_source: '生产取样',
  specification: '',
  test_due_date: '',
  remarks: '',
})

const matchedSpec = computed(() => specifications.value.find((s) => s.name === form.specification))

async function loadReferenceData() {
  try {
    const [types, specs] = await Promise.all([
      listDoctype('HBOS Sample Type', ['name'], {}, 50),
      listDoctype('HBOS Specification', ['name', 'status', 'version'], {}, 50),
    ])
    sampleTypes.value = types.map((t: { name: string }) => t.name)
    specifications.value = specs as { name: string; status: string; version: string }[]
    // 默认选中已生效标准
    const active = specifications.value.find((s) => s.status === '已生效')
    if (active) {
      form.specification = active.name
      await loadSpecItems(active.name)
    }
  } catch {
    ElMessage.warning('无法加载质量标准数据')
  }
}

async function loadSpecItems(specName: string) {
  specLoading.value = true
  try {
    const spec = await getDoc<any>('HBOS Specification', specName)
    const items = spec.items || []
    specItems.value = items.map((row: any) => ({
      item: row.item_name || row.test_item || row.item || '',
      limits: formatLimits(row),
      unit: row.unit || '—',
    }))
  } catch {
    specItems.value = []
  } finally {
    specLoading.value = false
  }
}

function formatLimits(row: any): string {
  const type = row.limits_type
  if (type === '记录型') return '记录型'
  if (type === '上限' && row.upper_limit != null) return `≤ ${row.upper_limit}`
  if (type === '下限' && row.lower_limit != null) return `≥ ${row.lower_limit}`
  if (row.lower_limit != null && row.upper_limit != null) return `${row.lower_limit} - ${row.upper_limit}`
  return '—'
}

async function onSpecChange(val: string) {
  await loadSpecItems(val)
}

async function loadLedger() {
  ledgerLoading.value = true
  try {
    const res = await runReport('样品台账')
    ledgerRows.value = res.result || []
  } catch {
    ledgerRows.value = []
  } finally {
    ledgerLoading.value = false
  }
}

function resetForm() {
  Object.assign(form, {
    sample_type: sampleTypes.value[0] || '',
    priority: '常规', material_code: '', material_name: '', batch_no: '',
    sample_source: '生产取样', specification: '', test_due_date: '', remarks: '',
  })
  const active = specifications.value.find((s) => s.status === '已生效')
  if (active) {
    form.specification = active.name
    loadSpecItems(active.name)
  }
}

async function submitSample() {
  if (!form.material_name || !form.batch_no || !form.sample_type || !form.specification) {
    ElMessage.warning('请填写样品类型、物料名称、批号和质量标准')
    return
  }
  submitting.value = true
  try {
    const name = await registerSample({
      sample_type: form.sample_type,
      material_code: form.material_code,
      material_name: form.material_name,
      batch_no: form.batch_no,
      sample_source: form.sample_source,
      specification: form.specification,
      priority: form.priority,
      test_due_date: form.test_due_date,
      remarks: form.remarks,
    })
    ElMessage.success(`样品登记成功：${name}`)
    resetForm()
    await loadLedger()
  } catch {
    // 错误已由拦截器提示
  } finally {
    submitting.value = false
  }
}

function priorityClass(p: string) {
  return { 特急: 'pill-danger', 加急: 'pill-warn', 常规: 'pill-info' }[p] || 'pill-muted'
}
function statusClass(s: string) {
  return {
    已批准: 'pill-pass', 检验中: 'pill-info', 待复核: 'pill-warn',
    'OOS 候选': 'pill-danger', 已登记: 'pill-muted', 已放行: 'pill-pass',
  }[s] || 'pill-muted'
}

onMounted(async () => {
  await loadReferenceData()
  await loadLedger()
})
</script>

<style scoped>
.page-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 14px; }
.page-head h1 { font-size: 20px; color: var(--ink); }
.page-head p { font-size: 12px; color: var(--muted); margin-top: 4px; }
.page-actions { display: flex; gap: 8px; }

.reg-grid { display: grid; grid-template-columns: 1.5fr 1fr; gap: 14px; align-items: start; }
.panel { background: var(--surface); border: 1px solid var(--line); border-radius: var(--radius); }
.panel-head { display: flex; align-items: center; justify-content: space-between; padding: 12px 16px; border-bottom: 1px solid var(--line); }
.panel-head h3 { font-size: 14px; }
.panel-head .sub { font-size: 11px; color: var(--muted); margin-top: 2px; }
.panel-body { padding: 16px; }
.panel.spec-items .panel-body { padding: 0; }
.form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 0 16px; }
.form-grid .full { grid-column: 1 / -1; }
.spec-match { background: var(--primary-soft); border: 1px solid #bfe0d6; border-radius: var(--radius); padding: 14px 16px; }
.spec-match .k { font-size: 11px; color: var(--primary); font-weight: 600; }
.spec-match .v { font-size: 15px; font-weight: 700; color: var(--primary-strong); margin-top: 6px; }
.spec-match .meta { font-size: 11px; color: var(--muted); margin-top: 4px; }
@media (max-width: 1180px) { .reg-grid { grid-template-columns: 1fr; } }
</style>
