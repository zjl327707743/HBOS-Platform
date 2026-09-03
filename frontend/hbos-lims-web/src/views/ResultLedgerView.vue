<template>
  <div class="page">
    <div class="page-head">
      <div>
        <h1>检验结果台账</h1>
        <p>检验项目、限度、结果、判定均为受控记录，随录入与任务流转更新，可下钻签名与修订链</p>
      </div>
      <div class="page-actions">
        <a-button @click="exportLedger"><template #icon><DownloadOutlined /></template>导出</a-button>
        <a-button @click="loadData"><template #icon><ReloadOutlined /></template>刷新</a-button>
      </div>
    </div>

    <div class="ledger-mode-tabs" role="tablist">
      <button class="ledger-tab" :class="{ active: mode === 'detail' }" @click="mode = 'detail'">明细台账 <span class="tag">受控记录</span></button>
      <button class="ledger-tab" :class="{ active: mode === 'table' }" @click="mode = 'table'">样品表 <span class="tag">每样品一表</span></button>
    </div>

    <!-- ===== 明细台账（受控记录视角） ===== -->
    <div v-show="mode === 'detail'" class="ledger-detail-layout">
      <div class="ledger-master">
        <div class="filter-bar">
          <a-input v-model:value="search" placeholder="搜索名称 / 批号 / 检验编号" allow-clear style="width:100%" />
          <a-select v-model:value="typeFilter" placeholder="全部类型" allow-clear style="width:100%">
            <a-select-option v-for="t in typeOptions" :key="t" :value="t">{{ t }}</a-select-option>
          </a-select>
        </div>
        <div class="master-list">
          <div
            v-for="s in filteredSamples"
            :key="s.name"
            class="ledger-item"
            :class="{ active: s.name === selectedNo }"
            @click="selectSample(s.name)"
          >
            <div class="li-top">
              <span class="name">{{ s.material_name || s.name }}</span>
              <span class="pill" :class="sampleStatusClass(s.status)">{{ s.status }}</span>
            </div>
            <div class="li-meta"><span>{{ s.name }}</span><span>批号 {{ s.batch_no }}</span><span>{{ s.sample_type }}</span></div>
            <div class="li-foot">
              <span class="summary-badge" :class="sumClsClass(summaryOf(s).cls)">{{ summaryOf(s).icon }} 汇总 {{ summaryOf(s).label }}</span>
            </div>
          </div>
          <div v-if="!loading && filteredSamples.length === 0" class="ledger-empty">无匹配样品</div>
        </div>
      </div>

      <div class="ledger-detail-pane">
        <div v-if="selectedSample" class="panel ledger-sample-card">
          <div class="card-head">
            <div>
              <h2>{{ selectedSample.material_name || selectedSample.name }} <span class="pill" :class="sampleStatusClass(selectedSample.status)">{{ selectedSample.status }}</span></h2>
              <div class="sub">
                <span>{{ selectedSample.name }}</span><span>批号 {{ selectedSample.batch_no }}</span>
                <span>{{ selectedSample.sample_type }}</span><span>质量标准 {{ selectedSample.spec_version || selectedSample.specification || '—' }}</span>
              </div>
            </div>
            <div><span class="summary-badge" :class="sumClsClass(summaryOf(selectedSample).cls)">{{ summaryOf(selectedSample).icon }} 汇总判定：{{ summaryOf(selectedSample).label }}</span></div>
          </div>
          <div class="ledger-reg-grid">
            <div v-for="r in regFields" :key="r[0]" class="rg"><span class="k">{{ r[0] }}</span><span class="v mono">{{ r[1] }}</span></div>
          </div>
          <div class="ledger-section-title">
            检验项目 <span class="tag">限度冻结快照 · 判定引擎计算</span>
            <span class="count">{{ resultsOf(selectedSample.name).length }} 项 · 点击行查看受控记录</span>
          </div>
          <table class="ledger-item-table">
            <thead><tr><th>检验项目</th><th>限度要求</th><th>结果</th><th>判定</th><th>检验人</th><th>记录状态</th></tr></thead>
            <tbody>
              <tr v-for="it in resultsOf(selectedSample.name)" :key="it.name" class="item-row" @click="openDrawer(it)">
                <td><div class="i-name">{{ it.item_name }}<span v-if="hasRev(it.name)" class="hist-dot" title="有修订记录"></span></div></td>
                <td><span class="limit-text">{{ limitsText(it) }}</span></td>
                <td><span class="res-value" :class="{ oos: it.verdict === 'OOS候选' }">{{ resultDisplay(it) }}</span></td>
                <td><span class="verdict-badge" :class="verdictCls(it)">{{ verdictIcon(it) }} {{ it.verdict || '待判定' }}</span></td>
                <td>{{ it.analyst || '—' }}</td>
                <td><span class="status-pill" :class="resultStatusClass(it.result_status)">{{ it.result_status }}</span></td>
              </tr>
            </tbody>
          </table>
        </div>
        <div v-else-if="!loading" class="ledger-empty">请选择左侧样品</div>

        <div class="ledger-gmp-note">
          <SafetyOutlined />
          <div>本台账为只读受控视图：限度为规格冻结快照，判定由引擎计算，修改结果必须走「提交 → 复核 → 批准 → 修订」流程，原记录不可覆盖（ALCOA+）。</div>
        </div>
      </div>
    </div>

    <!-- ===== 样品表（每样品种类一张表，数据表统计形式） ===== -->
    <div v-show="mode === 'table'" class="ledger-bitable">
      <div class="bitable-sidebar">
        <div class="bitable-sidebar-head"><span>检验台账</span><span class="bi-count">{{ tableGroups.length }} 个样品</span></div>
        <div class="bitable-group-list">
          <div v-for="g in tableGroups" :key="g.type" class="bitable-group" :class="{ collapsed: collapsedMap[g.type] }">
            <button class="bitable-group-title" @click="toggleGroup(g.type)">
              <span>{{ g.type }}</span><span class="bi-count">{{ g.items.length }}</span><span class="arrow"></span>
            </button>
            <div class="bitable-items">
              <button
                v-for="item in g.items"
                :key="item.material"
                class="bitable-item"
                :class="{ active: item.material === tableMaterial }"
                @click="selectTableMaterial(item.material)"
              >
                <span class="bi-icon">{{ typeIcon(g.type) }}</span>
                <span class="bi-text"><span class="bi-name">{{ item.material }}</span><span class="bi-meta">{{ item.count }} 批检验记录</span></span>
              </button>
            </div>
          </div>
        </div>
      </div>

      <div class="bitable-main">
        <div v-if="selectedMaterialGroup" class="bitable-head">
          <div>
            <h2>{{ selectedMaterialGroup.material }}</h2>
            <div class="sub">
              <span>{{ selectedMaterialGroup.type }}</span>
              <span>质量标准 {{ selectedMaterialGroup.spec || '—' }}</span>
              <span>检验批次 {{ selectedMaterialGroup.samples.length }} 批</span>
            </div>
          </div>
        </div>
        <div v-if="selectedMaterialGroup" class="bitable-filter">
          <span class="bf-label">列筛选</span>
          <a-select v-model:value="tableVerdictFilter" placeholder="判定：全部" allow-clear style="width:140px" @change="tableVerdictFilter = $event || ''">
            <a-select-option v-for="v in tableVerdictOptions" :key="v" :value="v">{{ v }}</a-select-option>
          </a-select>
          <a-select v-model:value="tableStatusFilter" placeholder="记录状态：全部" allow-clear style="width:150px" @change="tableStatusFilter = $event || ''">
            <a-select-option v-for="s in tableStatusOptions" :key="s" :value="s">{{ s }}</a-select-option>
          </a-select>
          <span class="bf-count">{{ tableFilteredRows.length }} / {{ selectedMaterialGroup.samples.length }} 批</span>
        </div>
        <div class="panel">
          <div class="panel-body bitable-table-wrap">
            <table v-if="selectedMaterialGroup" class="bitable-table">
              <thead>
                <tr>
                  <th>序号</th><th class="reg-th">样品批号</th>
                  <th v-for="l in tableRegLabels" :key="l" class="reg-th">{{ l }}</th>
                  <th v-for="p in selectedMaterialGroup.projects" :key="p"><div class="th-name"><b>{{ p }}</b></div></th>
                  <th>判定</th><th>记录状态</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(row, idx) in tableFilteredRows" :key="row.name">
                  <td class="row-num">{{ idx + 1 }}</td>
                  <td class="p-batch">{{ row.batch_no }}</td>
                  <td v-for="k in tableRegKeys" :key="k">{{ regValue(row, k) }}</td>
                  <td v-for="p in selectedMaterialGroup.projects" :key="p">
                    <span v-if="cellOf(row, p)" class="res-value" :class="{ oos: cellOf(row, p)!.oos }">{{ cellOf(row, p)!.text }}</span>
                    <span v-else class="res-desc">待录入</span>
                  </td>
                  <td><span class="verdict-badge" :class="sumClsClass(summaryOf(row).cls)">{{ summaryOf(row).icon }} {{ summaryOf(row).label }}</span></td>
                  <td><span class="status-pill" :class="sampleStatusClass(row.status)">{{ row.status }}</span></td>
                </tr>
              </tbody>
            </table>
            <div v-if="selectedMaterialGroup && tableFilteredRows.length === 0" class="ledger-empty">无匹配筛选条件的批次</div>
            <div v-else-if="!loading && !selectedMaterialGroup" class="ledger-empty">请选择左侧样品</div>
          </div>
        </div>
      </div>
    </div>

    <!-- 下钻抽屉：单条受控记录详情 -->
    <a-drawer
      v-model:open="drawerOpen"
      :width="440"
      placement="right"
      :closable="false"
    >
      <template #title>
        <div v-if="drawerResult">
          <div class="drawer-title">{{ drawerResult.item_name }}</div>
          <div class="drawer-sub">{{ drawerResult.sample }} · {{ sampleOf(drawerResult.sample)?.material_name || '' }}</div>
        </div>
      </template>
      <div v-if="drawerResult" class="drawer-body">
        <div class="drawer-sec">
          <div class="ds-title">标准限度（冻结快照）</div>
          <div class="drawer-row"><span class="k">限度模式</span><span class="v zh">{{ drawerResult.limits_type || '—' }}</span></div>
          <div class="drawer-row"><span class="k">限度要求</span><span class="v zh">{{ limitsText(drawerResult) }}</span></div>
        </div>
        <div class="drawer-sec">
          <div class="ds-title">结果与判定</div>
          <div class="drawer-row"><span class="k">检验结果</span><span class="v">{{ resultDisplay(drawerResult) }}</span></div>
          <div class="drawer-row"><span class="k">判定</span><span class="v zh">{{ drawerResult.verdict || '待判定' }}<template v-if="drawerResult.verdict === 'OOS候选'">（样品锁定）</template></span></div>
          <div class="drawer-row"><span class="k">记录状态</span><span class="v zh">{{ drawerResult.result_status }}</span></div>
          <div class="drawer-row"><span class="k">检验编号</span><span class="v">{{ drawerResult.name }}</span></div>
        </div>
        <div class="drawer-sec">
          <div class="ds-title">电子签名</div>
          <div class="sig-card" :class="{ pending: !drawerResult.submitted_at }">
            <div class="sig-top"><span class="sig-role">检验人</span><span class="sig-sign">{{ drawerResult.analyst || '待检验' }}</span></div>
            <div class="sig-who">{{ drawerResult.analyst || '—' }}</div>
            <div class="sig-when">{{ drawerResult.submitted_at || '提交时生成' }}</div>
          </div>
          <div class="sig-card" :class="{ pending: !drawerResult.reviewed_at }">
            <div class="sig-top"><span class="sig-role">复核人</span><span class="sig-sign">{{ drawerResult.reviewer || '待复核' }}</span></div>
            <div class="sig-who">{{ drawerResult.reviewer || '—' }}</div>
            <div class="sig-when">{{ drawerResult.reviewed_at || '第二人独立审核' }}</div>
          </div>
          <div class="sig-card" :class="{ pending: !drawerResult.approved_at }">
            <div class="sig-top"><span class="sig-role">批准人</span><span class="sig-sign">{{ drawerResult.approver || '待批准' }}</span></div>
            <div class="sig-who">{{ drawerResult.approver || '—' }}</div>
            <div class="sig-when">{{ drawerResult.approved_at || '批准后放行' }}</div>
          </div>
        </div>
        <div v-if="drawerRevs.length" class="drawer-sec">
          <div class="ds-title">修订记录</div>
          <div class="rev-chain">
            <div v-for="rev in drawerRevs" :key="rev.name" class="rev-item">
              <div class="rev-no">{{ rev.name }} · 修订 {{ rev.field_changed }}</div>
              <div class="rev-change"><span class="old">{{ rev.old_value }}</span> → <span class="new">{{ rev.new_value }}</span></div>
              <div class="rev-reason">原因：{{ rev.change_reason }}</div>
              <div class="rev-when">{{ rev.changed_by }} · {{ rev.changed_at }}</div>
            </div>
          </div>
        </div>
        <div v-else class="drawer-sec">
          <div class="ds-title">修订记录</div>
          <div class="rev-none">暂无修订，该记录为原始受控记录</div>
        </div>
      </div>
    </a-drawer>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { DownloadOutlined, ReloadOutlined, SafetyOutlined } from '@ant-design/icons-vue'
import { listDoctype } from '@/api/lims'
import { message } from 'ant-design-vue'
interface LedgerResult {
  name: string
  sample: string
  item_name: string
  result_value: number | null
  result_text: string
  raw_value: string
  unit: string
  verdict: string
  result_status: string
  limits_type: string
  lower_limit: number | null
  upper_limit: number | null
  analyst: string
  submitted_at: string
  reviewer: string
  reviewed_at: string
  approver: string
  approved_at: string
  superseded_by: string
  creation: string
}

interface LedgerSample {
  name: string
  material_name: string
  material_code: string
  batch_no: string
  sample_type: string
  sample_source: string
  specification: string
  spec_version: string
  priority: string
  status: string
  requestor: string
  received_date: string
  test_due_date: string
  creation: string
  remarks: string
}

interface Revision {
  name: string
  result: string
  field_changed: string
  old_value: string
  new_value: string
  changed_by: string
  changed_at: string
  change_reason: string
}

const loading = ref(false)
const mode = ref<'detail' | 'table'>('detail')
const search = ref('')
const typeFilter = ref('')
const selectedNo = ref('')
const tableMaterial = ref('')
const collapsedMap = ref<Record<string, boolean>>({})
const tableVerdictFilter = ref('')
const tableStatusFilter = ref('')

const samples = ref<LedgerSample[]>([])
const results = ref<LedgerResult[]>([])
const revisions = ref<Revision[]>([])

const drawerOpen = ref(false)
const drawerResult = ref<LedgerResult | null>(null)

const typeOptions = computed(() => {
  const seen: string[] = []
  samples.value.forEach((s) => {
    if (s.sample_type && !seen.includes(s.sample_type)) seen.push(s.sample_type)
  })
  return seen
})

const filteredSamples = computed(() => {
  return samples.value.filter((s) => {
    const kw = String(s.material_name || '') + String(s.batch_no || '') + String(s.name)
    const hitKw = !search.value || kw.includes(search.value)
    const hitType = !typeFilter.value || s.sample_type === typeFilter.value
    return hitKw && hitType
  })
})

const resultsBySample = computed(() => {
  const map = new Map<string, LedgerResult[]>()
  results.value.forEach((r) => {
    if (!r.sample) return
    if (!map.has(r.sample)) map.set(r.sample, [])
    map.get(r.sample)!.push(r)
  })
  return map
})

const coaDateMap = computed(() => {
  const map = new Map<string, string>()
  coas.forEach((c: any) => {
    if (c.report_status === '已发布' && c.published_at) map.set(c.sample, String(c.published_at).slice(0, 10))
  })
  return map
})

const revByResult = computed(() => {
  const map = new Map<string, Revision[]>()
  revisions.value.forEach((r) => {
    if (!r.result) return
    if (!map.has(r.result)) map.set(r.result, [])
    map.get(r.result)!.push(r)
  })
  return map
})

let coas: any[] = []

function resultsOf(sample: string): LedgerResult[] {
  return (resultsBySample.value.get(sample) || []).filter((r) => !r.superseded_by)
}
function hasRev(resultName: string): boolean {
  return (revByResult.value.get(resultName) || []).length > 0
}
function sampleOf(name: string): LedgerSample | undefined {
  return samples.value.find((s) => s.name === name)
}
function summaryOf(sample: LedgerSample) {
  const valid = resultsOf(sample.name).filter((r) => r.verdict)
  const bad = valid.some((r) => r.verdict === '不合格')
  const ok = valid.length > 0 && valid.every((r) => r.verdict === '合格')
  if (bad) return { label: '不合格', cls: 'bad', icon: '✗' }
  if (ok) return { label: '合格', cls: 'ok', icon: '✓' }
  if (valid.length) return { label: '待判定', cls: 'na', icon: '·' }
  return { label: '—', cls: 'na', icon: '·' }
}

const selectedSample = computed(() => samples.value.find((s) => s.name === selectedNo.value))

const regFields = computed<[string, string][]>(() => {
  const s = selectedSample.value
  if (!s) return []
  return [
    ['物料编码', s.material_code || '—'],
    ['样品类型', s.sample_type || '—'],
    ['样品来源', s.sample_source || '—'],
    ['优先级', s.priority || '—'],
    ['请验日期', s.creation ? String(s.creation).slice(0, 10) : '—'],
    ['报告日期', coaDateMap.value.get(s.name) || '—'],
    ['检验时限', s.test_due_date || '—'],
    ['请验人', s.requestor || '—'],
    ['接收日期', s.received_date ? String(s.received_date).slice(0, 10) : '—'],
    ['批数量', '—'],
    ['有效期/复验期至', '—'],
    ['备注', s.remarks || '—'],
  ]
})

function selectSample(name: string) {
  selectedNo.value = name
}

function openDrawer(r: LedgerResult) {
  drawerResult.value = r
  drawerRevs.value = revByResult.value.get(r.name) || []
  drawerOpen.value = true
}
const drawerRevs = ref<Revision[]>([])

// ---- 样品表 ----
interface TableGroup {
  type: string
  items: { material: string; count: number }[]
}
interface MaterialGroup {
  type: string
  material: string
  spec: string
  samples: LedgerSample[]
  projects: string[]
}

const tableGroups = computed<TableGroup[]>(() => {
  const byType = new Map<string, Map<string, LedgerSample[]>>()
  samples.value.forEach((s) => {
    if (!s.sample_type || !s.material_name) return
    if (!byType.has(s.sample_type)) byType.set(s.sample_type, new Map())
    const typeMap = byType.get(s.sample_type)!
    if (!typeMap.has(s.material_name)) typeMap.set(s.material_name, [])
    typeMap.get(s.material_name)!.push(s)
  })
  const groups: TableGroup[] = []
  byType.forEach((materials, type) => {
    groups.push({
      type,
      items: Array.from(materials.entries()).map(([material, list]) => ({ material, count: list.length })),
    })
  })
  return groups
})

const tableRegLabels = ['物料编码', '样品来源', '优先级', '检验时限', '请验日期', '报告日期', '请验人']
const tableRegKeys = ['material_code', 'sample_source', 'priority', 'test_due_date', 'creation', 'report_date', 'requestor']

const selectedMaterialGroup = computed<MaterialGroup | null>(() => {
  const item = tableGroups.value
    .flatMap((g) => g.items.map((i) => ({ type: g.type, ...i })))
    .find((i) => i.material === tableMaterial.value)
  if (!item) return null
  const list = samples.value.filter((s) => s.sample_type === item.type && s.material_name === item.material)
  if (!list.length) return null
  const projectSet = new Set<string>()
  list.forEach((s) => {
    resultsOf(s.name).forEach((r) => {
      if (r.item_name) projectSet.add(r.item_name)
    })
  })
  const projects = Array.from(projectSet)
  return {
    type: item.type,
    material: item.material,
    spec: list[0].spec_version || list[0].specification || '',
    samples: list,
    projects,
  }
})

function selectTableMaterial(material: string) {
  tableMaterial.value = material
  tableVerdictFilter.value = ''
  tableStatusFilter.value = ''
}
function toggleGroup(type: string) {
  collapsedMap.value[type] = !collapsedMap.value[type]
}
const tableVerdictOptions = computed(() => {
  if (!selectedMaterialGroup.value) return []
  const seen: string[] = []
  selectedMaterialGroup.value.samples.forEach((s) => {
    const l = summaryOf(s).label
    if (l && !seen.includes(l)) seen.push(l)
  })
  return seen
})
const tableStatusOptions = computed(() => {
  if (!selectedMaterialGroup.value) return []
  const seen: string[] = []
  selectedMaterialGroup.value.samples.forEach((s) => {
    if (s.status && !seen.includes(s.status)) seen.push(s.status)
  })
  return seen
})
const tableFilteredRows = computed(() => {
  const list = selectedMaterialGroup.value?.samples || []
  return list.filter((s) => {
    const hitVerdict = !tableVerdictFilter.value || summaryOf(s).label === tableVerdictFilter.value
    const hitStatus = !tableStatusFilter.value || s.status === tableStatusFilter.value
    return hitVerdict && hitStatus
  })
})
function resultByItem(sample: LedgerSample, itemName: string): LedgerResult | undefined {
  return resultsOf(sample.name).find((r) => r.item_name === itemName)
}
function regValue(s: LedgerSample, key: string): string {
  if (key === 'creation') return s.creation ? String(s.creation).slice(0, 10) : '—'
  if (key === 'report_date') return coaDateMap.value.get(s.name) || '—'
  return (s as any)[key] || '—'
}

// ---- 展示辅助 ----
function limitsText(r: LedgerResult): string {
  if (!r.limits_type) return '—'
  if (r.limits_type === '记录型') return '记录型 · 应符合规定'
  if (r.limits_type === '区间') return `X ∈ [${r.lower_limit} , ${r.upper_limit}] ${r.unit || ''}`
  if (r.limits_type === '上限') return `≤ ${r.upper_limit} ${r.unit || ''}`
  if (r.limits_type === '下限') return `≥ ${r.lower_limit} ${r.unit || ''}`
  return '—'
}
function resultDisplay(r: LedgerResult): string {
  if (r.result_value != null) return `${r.result_value}${r.unit || ''}`
  if (r.result_text) return r.result_text
  if (r.raw_value) return r.raw_value
  return '—'
}
function cellOf(sample: LedgerSample, itemName: string): { text: string; oos: boolean } | undefined {
  const r = resultByItem(sample, itemName)
  if (!r) return undefined
  return { text: resultDisplay(r), oos: r.verdict === 'OOS候选' }
}
function verdictCls(r: LedgerResult): string {
  if (r.verdict === 'OOS候选') return 'oos'
  if (r.verdict === '不合格') return 'bad'
  if (r.verdict === '合格') return 'ok'
  if (r.verdict === '不适用') return 'na'
  return 'na'
}
function verdictIcon(r: LedgerResult): string {
  if (r.verdict === 'OOS候选') return '⛔'
  if (r.verdict === '不合格') return '✗'
  if (r.verdict === '合格') return '✓'
  return '·'
}
function sumClsClass(cls: string): string {
  return { bad: 'bad', ok: 'ok', na: 'na' }[cls] || 'na'
}
function sampleStatusClass(s: string): string {
  return {
    已放行: 'pill-pass', 已批准: 'pill-pass',
    检验完成: 'pill-info', 检验中: 'pill-info',
    已登记: 'pill-muted', 草稿: 'pill-muted',
    已拒绝: 'pill-danger', OOS锁定: 'pill-danger',
  }[s] || 'pill-muted'
}
function resultStatusClass(s: string): string {
  return {
    已批准: 'pill-pass', 已提交: 'pill-info', 已复核: 'pill-warn',
    草稿: 'pill-muted', 已修订: 'pill-danger',
  }[s] || 'pill-muted'
}
function typeIcon(t: string): string {
  const map: Record<string, string> = { 成品: '成', 原料: '原', 包装材料: '包', 工艺用水: '水', 水: '水', 中间体: '中', 环境样品: '环', 稳定性样品: '稳', 清洁验证样品: '清' }
  return map[t] || t.slice(0, 1)
}

function exportLedger() {
  message.info('导出功能待后端聚合 API 就绪后接入')
}

async function loadData() {
  loading.value = true
  try {
    const [s, r, c, rev] = await Promise.all([
      listDoctype<LedgerSample>(
        'HBOS Sample',
        ['name', 'material_name', 'material_code', 'batch_no', 'sample_type', 'sample_source', 'specification', 'spec_version', 'priority', 'status', 'requestor', 'received_date', 'test_due_date', 'creation', 'remarks'],
        {},
        500,
        'creation asc',
      ),
      listDoctype<LedgerResult>(
        'HBOS Test Result',
        ['name', 'sample', 'item_name', 'result_value', 'result_text', 'raw_value', 'unit', 'verdict', 'result_status', 'limits_type', 'lower_limit', 'upper_limit', 'analyst', 'submitted_at', 'reviewer', 'reviewed_at', 'approver', 'approved_at', 'superseded_by', 'creation'],
        {},
        1000,
        'creation asc',
      ),
      listDoctype<any>('HBOS COA', ['sample', 'report_status', 'published_at'], {}, 500),
      listDoctype<Revision>(
        'HBOS Result Revision',
        ['name', 'result', 'field_changed', 'old_value', 'new_value', 'changed_by', 'changed_at', 'change_reason'],
        {},
        2000,
        'changed_at desc',
      ),
    ])
    samples.value = (s as any[]) || []
    results.value = (r as any[]) || []
    coas = (c as any[]) || []
    revisions.value = (rev as any[]) || []
    if (!selectedNo.value && samples.value.length) selectedNo.value = samples.value[0].name
    if (!tableMaterial.value) {
      const first = tableGroups.value[0]?.items[0]?.material
      if (first) tableMaterial.value = first
    }
  } finally {
    loading.value = false
  }
}

onMounted(loadData)
</script>

<style scoped>
.page-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 14px; }
.page-head h1 { font-size: 20px; color: var(--ink); }
.page-head p { font-size: 12px; color: var(--muted); margin-top: 4px; }
.page-actions { display: flex; gap: 8px; }

.ledger-mode-tabs { display: flex; gap: 8px; margin-bottom: 14px; background: var(--surface); border: 1px solid var(--line); border-radius: var(--radius); padding: 5px; width: fit-content; }
.ledger-tab { border: 0; background: transparent; font-family: inherit; font-size: 13px; color: var(--muted); padding: 7px 16px; border-radius: 6px; cursor: pointer; display: flex; align-items: center; gap: 8px; }
.ledger-tab .tag { font-size: 10px; color: var(--muted); background: var(--surface-2); border-radius: 4px; padding: 1px 6px; }
.ledger-tab.active { background: var(--primary); color: #fff; font-weight: 600; }
.ledger-tab.active .tag { background: rgba(255,255,255,.18); color: #fff; }

.ledger-detail-layout { display: grid; grid-template-columns: 300px 1fr; gap: 14px; align-items: start; }
.ledger-master .filter-bar { display: grid; grid-template-columns: 1fr; gap: 8px; margin-bottom: 10px; }
.master-list { background: var(--surface); border: 1px solid var(--line); border-radius: var(--radius); overflow: hidden; max-height: 72vh; overflow-y: auto; }
.ledger-item { padding: 11px 14px; border-bottom: 1px solid var(--surface-2); cursor: pointer; background: var(--surface); }
.ledger-item:hover { background: var(--surface-2); }
.ledger-item.active { background: var(--primary-soft); border-left: 3px solid var(--primary); }
.ledger-item .li-top { display: flex; align-items: center; justify-content: space-between; gap: 8px; }
.ledger-item .name { font-weight: 600; font-size: 12px; }
.ledger-item .li-meta { font-size: 10px; color: var(--muted); margin-top: 3px; display: flex; gap: 8px; flex-wrap: wrap; }
.ledger-item .li-foot { display: flex; align-items: center; margin-top: 7px; }
.ledger-item .li-foot .summary-badge { margin-left: auto; }
.summary-badge { display: inline-flex; align-items: center; gap: 4px; font-size: 11px; font-weight: 600; padding: 2px 8px; border-radius: 10px; }
.summary-badge.ok { background: var(--pass-soft); color: var(--pass); }
.summary-badge.bad { background: var(--danger-soft); color: var(--danger); }
.summary-badge.na { background: var(--surface-2); color: var(--muted); }
.ledger-empty { text-align: center; color: var(--muted); font-size: 12px; padding: 30px 0; }

.ledger-sample-card .card-head { display: flex; align-items: flex-start; justify-content: space-between; gap: 10px; padding: 14px 16px; border-bottom: 1px solid var(--surface-2); }
.ledger-sample-card .card-head h2 { font-size: 15px; display: inline-flex; align-items: center; gap: 8px; }
.ledger-sample-card .card-head .sub { font-size: 11px; color: var(--muted); margin-top: 3px; display: flex; gap: 12px; flex-wrap: wrap; }
.ledger-reg-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(140px, 1fr)); gap: 10px 16px; padding: 14px 16px; }
.ledger-reg-grid .rg { display: flex; flex-direction: column; gap: 2px; }
.ledger-reg-grid .rg .k { font-size: 10px; color: var(--muted); }
.ledger-reg-grid .rg .v { font-size: 12px; font-weight: 500; }
.ledger-section-title { font-size: 12px; font-weight: 700; padding: 10px 16px; background: var(--surface-2); border-top: 1px solid var(--surface-2); border-bottom: 1px solid var(--surface-2); display: flex; align-items: center; gap: 8px; }
.ledger-section-title .tag { font-size: 10px; color: var(--muted); font-weight: 500; }
.ledger-section-title .count { margin-left: auto; font-weight: 500; color: var(--muted); font-size: 11px; }

.ledger-item-table { width: 100%; border-collapse: collapse; font-size: 12px; }
.ledger-item-table th { text-align: left; padding: 9px 16px; font-size: 11px; color: var(--muted); font-weight: 600; background: var(--surface-2); border-bottom: 1px solid var(--surface-2); white-space: nowrap; }
.ledger-item-table td { padding: 10px 16px; border-bottom: 1px solid var(--surface-2); vertical-align: middle; }
.ledger-item-table tr:last-child td { border-bottom: 0; }
.ledger-item-table tr.item-row { cursor: pointer; }
.ledger-item-table tr.item-row:hover td { background: var(--surface-2); }
.ledger-item-table .i-name { font-weight: 600; }
.ledger-item-table .hist-dot { display: inline-block; width: 6px; height: 6px; border-radius: 50%; background: var(--warn); margin-left: 5px; }
.limit-text { font-family: var(--mono); font-size: 11px; color: var(--muted); white-space: nowrap; }
.res-value { font-family: var(--mono); font-size: 13px; font-weight: 600; }
.res-value.oos { color: var(--danger); }
.res-unit { color: var(--muted); font-size: 11px; margin-left: 3px; }
.res-desc { font-size: 11px; color: var(--muted); }
.verdict-badge { display: inline-flex; align-items: center; gap: 4px; font-size: 12px; font-weight: 600; padding: 2px 8px; border-radius: 10px; white-space: nowrap; }
.verdict-badge.ok { background: var(--pass-soft); color: var(--pass); }
.verdict-badge.bad { background: var(--danger-soft); color: var(--danger); }
.verdict-badge.na { background: var(--surface-2); color: var(--muted); }
.verdict-badge.oos { background: var(--danger-soft); color: var(--oos); }
.status-pill { font-size: 12px; padding: 1px 8px; border-radius: 9px; background: var(--info-soft); color: var(--info); white-space: nowrap; }
.status-pill.pill-pass { background: var(--pass-soft); color: var(--pass); }
.status-pill.pill-info { background: var(--info-soft); color: var(--info); }
.status-pill.pill-warn { background: var(--warn-soft); color: var(--warn); }
.status-pill.pill-danger { background: var(--danger-soft); color: var(--danger); }
.status-pill.pill-muted { background: var(--surface-2); color: var(--muted); border: 1px solid var(--line); }

.ledger-gmp-note { display: flex; gap: 10px; align-items: flex-start; margin-top: 14px; background: var(--primary-soft); border: 1px solid #cfe6df; border-radius: var(--radius); padding: 10px 14px; font-size: 11px; color: var(--primary-strong); }
.ledger-gmp-note :deep(svg) { width: 16px; height: 16px; flex: 0 0 16px; margin-top: 1px; }

/* 样品表 */
.ledger-bitable { display: grid; grid-template-columns: 264px 1fr; gap: 14px; align-items: start; }
.bitable-sidebar { background: var(--surface); border: 1px solid var(--line); border-radius: var(--radius); overflow: hidden; }
.bitable-sidebar-head { display: flex; align-items: center; justify-content: space-between; padding: 11px 14px; border-bottom: 1px solid var(--surface-2); font-weight: 700; font-size: 12px; }
.bitable-sidebar-head .bi-count { font-size: 10px; color: var(--muted); font-weight: 500; }
.bitable-group-list { max-height: 70vh; overflow-y: auto; }
.bitable-group { border-bottom: 1px solid var(--surface-2); }
.bitable-group-title { display: flex; align-items: center; gap: 8px; width: 100%; padding: 9px 14px; border: 0; background: var(--surface-2); cursor: pointer; font-family: inherit; font-size: 11px; font-weight: 700; color: var(--muted); text-align: left; }
.bitable-group-title .arrow { width: 0; height: 0; border-left: 4px solid transparent; border-right: 4px solid transparent; border-top: 5px solid var(--muted); transition: transform .15s ease; margin-left: auto; }
.bitable-group.collapsed .bitable-group-title .arrow { transform: rotate(-90deg); }
.bitable-group.collapsed .bitable-items { display: none; }
.bitable-item { display: flex; align-items: center; gap: 9px; width: 100%; padding: 9px 14px; border: 0; background: transparent; cursor: pointer; font-family: inherit; text-align: left; border-left: 3px solid transparent; transition: background .12s ease; }
.bitable-item:hover { background: var(--surface-2); }
.bitable-item.active { background: var(--primary-soft); border-left-color: var(--primary); }
.bitable-item .bi-icon { width: 26px; height: 26px; flex: 0 0 26px; border-radius: 6px; background: var(--surface-2); color: var(--primary); display: grid; place-items: center; font-size: 12px; }
.bitable-item.active .bi-icon { background: var(--primary); color: #fff; }
.bitable-item .bi-text { min-width: 0; }
.bitable-item .bi-name { font-size: 12px; font-weight: 600; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.bitable-item .bi-meta { font-size: 10px; color: var(--muted); margin-top: 2px; }

.bitable-main { min-width: 0; }
.bitable-head { display: flex; align-items: flex-start; justify-content: space-between; gap: 12px; background: var(--surface); border: 1px solid var(--line); border-radius: var(--radius); padding: 13px 16px; margin-bottom: 12px; }
.bitable-head h2 { font-size: 15px; }
.bitable-head .sub { font-size: 11px; color: var(--muted); margin-top: 3px; display: flex; gap: 12px; flex-wrap: wrap; }
.bitable-filter { display: flex; align-items: center; gap: 10px; margin-bottom: 10px; flex-wrap: wrap; }
.bitable-filter .bf-label { font-size: 11px; color: var(--muted); font-weight: 600; }
.bitable-filter .bf-count { margin-left: auto; font-size: 11px; color: var(--muted); }

.bitable-table-wrap { overflow-x: auto; }
.bitable-table { width: 100%; border-collapse: collapse; font-size: 12px; min-width: 780px; }
.bitable-table th { background: var(--surface-2); text-align: center; padding: 10px 14px; border-bottom: 1px solid var(--surface-2); font-size: 12px; color: var(--ink); font-weight: 600; white-space: nowrap; }
.bitable-table th.reg-th { color: var(--ink); font-weight: 600; background: var(--surface-2); }
.bitable-table td { padding: 9px 14px; border-bottom: 1px solid var(--surface-2); text-align: center; vertical-align: middle; white-space: nowrap; }
.bitable-table tr:last-child td { border-bottom: 0; }
.bitable-table tbody tr:hover td { background: var(--surface-2); }
.bitable-table td.row-num { color: var(--muted); font-family: var(--mono); }
.bitable-table td.p-batch { font-family: var(--mono); }
.bitable-table .th-name { display: inline-flex; flex-direction: column; align-items: center; gap: 2px; }
.bitable-table .th-name b { color: var(--ink); font-size: 12px; font-weight: 600; }

.drawer-title { font-size: 15px; font-weight: 700; }
.drawer-sub { font-size: 11px; color: var(--muted); margin-top: 2px; }
.drawer-body { padding: 4px 2px; }
.drawer-sec { margin-bottom: 18px; }
.drawer-sec .ds-title { font-size: 11px; font-weight: 700; color: var(--muted); margin-bottom: 8px; text-transform: uppercase; letter-spacing: .04em; }
.drawer-row { display: flex; justify-content: space-between; gap: 12px; padding: 7px 0; border-bottom: 1px dashed var(--surface-2); font-size: 12px; }
.drawer-row:last-child { border-bottom: 0; }
.drawer-row .k { color: var(--muted); flex: 0 0 84px; }
.drawer-row .v { text-align: right; font-family: var(--mono); font-size: 11px; }
.drawer-row .v.zh { font-family: inherit; font-size: 12px; }
.sig-card { border: 1px solid var(--line); border-radius: 6px; padding: 10px 12px; margin-bottom: 8px; }
.sig-card .sig-top { display: flex; align-items: center; justify-content: space-between; }
.sig-card .sig-role { font-size: 11px; font-weight: 600; }
.sig-card .sig-who { font-size: 13px; font-weight: 600; margin-top: 3px; }
.sig-card .sig-when { font-size: 10px; color: var(--muted); margin-top: 2px; font-family: var(--mono); }
.sig-card .sig-sign { font-size: 14px; font-family: 'Kaiti SC', 'KaiTi', cursive; color: var(--primary); }
.sig-card.pending { background: var(--surface-2); }
.sig-card.pending .sig-who { color: var(--muted); font-weight: 500; }
.rev-chain { border-left: 2px solid var(--surface-2); margin-left: 6px; padding-left: 14px; }
.rev-item { padding: 8px 0; border-bottom: 1px dashed var(--surface-2); font-size: 12px; }
.rev-item:last-child { border-bottom: 0; }
.rev-item .rev-no { font-family: var(--mono); font-size: 11px; color: var(--warn); font-weight: 600; }
.rev-item .rev-change { margin-top: 3px; }
.rev-item .rev-change .old { color: var(--danger); text-decoration: line-through; }
.rev-item .rev-change .new { color: var(--pass); font-weight: 600; }
.rev-item .rev-reason { color: var(--muted); font-size: 11px; margin-top: 3px; }
.rev-item .rev-when { color: var(--muted); font-size: 10px; font-family: var(--mono); margin-top: 2px; }
.rev-none { color: var(--muted); font-size: 12px; padding: 6px 0; }

@media (max-width: 1180px) {
  .ledger-detail-layout { grid-template-columns: 1fr; }
  .ledger-bitable { grid-template-columns: 1fr; }
  .bitable-group-list { max-height: 30vh; }
}
</style>
