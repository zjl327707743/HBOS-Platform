<template>
  <div class="page">
    <div class="page-head">
      <div>
        <h1>使用申请</h1>
        <p class="page-desc">库存确认即预占 · QC / QA / QM 三级批准 · 取样执行原子扣减</p>
      </div>
      <div class="page-actions">
        <a-button @click="reset">
          <template #icon><ReloadOutlined /></template>
          刷新
        </a-button>
        <a-button type="primary" @click="openCreate">
          <template #icon><PlusOutlined /></template>
          发起使用申请
        </a-button>
      </div>
    </div>

    <DemoBar />

    <div class="alert-strip">
      <ExclamationCircleOutlined />
      <span>1 份申请已批准但 15 天未执行，Manager 可取消释放预占。</span>
      <a class="alert-link" @click="goEscape">查看取消逃生口</a>
    </div>

    <div ref="layoutRef" class="detail-layout">
      <!-- 左：申请列表 -->
      <div class="panel list-panel">
        <div class="panel-head">
          <div>
            <div class="panel-title">申请列表</div>
            <div class="panel-sub">{{ listSub }}</div>
          </div>
          <div class="panel-filter">
            <a-button
              v-for="c in filterChips"
              :key="c.key"
              size="small"
              shape="round"
              :type="filter === c.key ? 'primary' : 'default'"
              @click="filter = c.key"
            >{{ c.label }}</a-button>
          </div>
        </div>
        <div class="panel-body no-pad">
          <a-table
            :columns="columns"
            :data-source="filteredRows"
            :pagination="false"
            size="small"
            row-key="name"
            :scroll="{ x: 860 }"
            :custom-row="customRow"
          >
            <template #bodyCell="{ column, record }">
              <template v-if="column.key === 'order'">
                <span class="mono">{{ record.name }}</span>
              </template>
              <template v-else-if="column.key === 'retention'">
                <div class="ret-main">{{ record.product }} <span class="dim">/ {{ record.batch }}</span></div>
                <div class="ret-sub mono">{{ record.retentionName }}</div>
              </template>
              <template v-else-if="column.key === 'qty'">
                <span class="mono">{{ usageQtyLabel(record) }}</span>
              </template>
              <template v-else-if="column.key === 'scenario'">
                {{ record.scenario }}
              </template>
              <template v-else-if="column.key === 'status'">
                <span class="pill" :class="statusPillClass(record.status)">{{ record.status }}</span>
              </template>
              <template v-else-if="column.key === 'action'">
                <a-button type="link" size="small" @click.stop="selectRow(record)">{{ rowActionText(record) }}</a-button>
              </template>
            </template>
          </a-table>
          <a-empty
            v-if="!filteredRows.length"
            description="当前筛选无申请"
            :image="Empty.PRESENTED_IMAGE_SIMPLE"
            style="padding: 24px 0"
          />
        </div>
      </div>

      <!-- 右：申请详情 -->
      <div class="panel detail-panel">
        <div class="panel-head">
          <div>
            <div class="panel-title">申请详情</div>
            <div class="panel-sub mono">{{ selected ? selected.name : '未选择' }}</div>
          </div>
        </div>
        <div class="panel-body">
          <a-empty v-if="!selected" description="从左侧选择一份申请查看" :image="Empty.PRESENTED_IMAGE_SIMPLE" />
          <template v-else>
            <div class="hero">
              <div>
                <div class="hero-title">{{ selected.product }} <span class="dim">/ {{ selected.batch }}</span></div>
                <div class="hero-sub">留样编号 <span class="mono">{{ selected.retentionName }}</span></div>
              </div>
              <span class="pill" :class="statusPillClass(selected.status)">{{ selected.status }}</span>
            </div>

            <div class="divider"></div>

            <div class="stat-row cols-3" style="gap: 10px">
              <div class="stat-card" style="padding: 8px 10px">
                <div class="stat-label">结存</div>
                <div class="qty mono">{{ selected.currentQty }} {{ selected.uom }}</div>
              </div>
              <div class="stat-card" style="padding: 8px 10px">
                <div class="stat-label">预占</div>
                <div class="qty mono warn">{{ selected.reservedQty }} {{ selected.uom }}</div>
              </div>
              <div class="stat-card" style="padding: 8px 10px">
                <div class="stat-label">可用量</div>
                <div class="qty mono good">{{ selected.currentQty - selected.reservedQty }} {{ selected.uom }}</div>
              </div>
            </div>

            <div class="section-label">申请信息</div>
            <div class="field">
              <label>申请量</label>
              <div class="static">{{ usageQtyLabel(selected) }}（{{ selected.uom }} 为产品默认单位）</div>
            </div>
            <div class="field">
              <label>触发场景 / 原因</label>
              <div class="static">{{ selected.scenario }} · {{ selected.reason }}</div>
            </div>
            <div class="field">
              <label>申请部门 / 申请人</label>
              <div class="static">{{ selected.dept }} · {{ selected.applicant }}（{{ selected.applicantDate }}）</div>
            </div>

            <div class="section-label">审批链</div>
            <div class="chain">
              <template v-for="(st, idx) in selectedChain" :key="st.key">
                <div
                  class="step"
                  :class="{ done: st.state === 'done', active: st.state === 'active' }"
                >
                  <span class="dot">{{ st.state === 'done' ? '✓' : String(idx) }}</span>
                  <div>
                    <div class="step-name">{{ st.label }}</div>
                    <div class="step-who">{{ st.who }}</div>
                  </div>
                </div>
                <span v-if="idx < selectedChain.length - 1" class="chain-arrow">→</span>
              </template>
            </div>

            <div class="soe red">{{ SOD_NOTE }}</div>

            <div v-if="detailActions.length" class="detail-actions">
              <a-button
                v-for="b in detailActions"
                :key="b.key"
                :type="b.primary ? 'primary' : 'default'"
                :danger="b.danger"
                @click="runDetail(b.key)"
              >
                <template #icon v-if="b.danger"><CloseCircleOutlined /></template>
                {{ b.label }}
              </a-button>
            </div>
            <div v-else class="dim" style="margin-top: 10px">当前状态与演示身份下无可用操作，仅查看。</div>
          </template>
        </div>
      </div>
    </div>

    <!-- 创建使用申请 -->
    <a-modal
      v-model:open="createOpen"
      title="发起使用申请"
      ok-text="发起申请"
      cancel-text="取消"
      width="620"
      @ok="confirmCreate"
    >
      <a-form layout="vertical">
        <a-form-item label="留样批次" required>
          <a-select
            v-model:value="createForm.retentionName"
            placeholder="选择留样批次（仅可用量 &gt; 0）"
            :options="batchOptionList"
          />
        </a-form-item>
        <template v-if="pickedBatch">
          <div class="field">
            <label>批次库存快照（只读）</label>
            <div class="static">
              结存 {{ pickedBatch.currentQty }} {{ pickedBatch.uom }} · 预占 {{ pickedBatch.reservedQty }}
              {{ pickedBatch.uom }} · 可用 {{ pickedBatch.currentQty - pickedBatch.reservedQty }} {{ pickedBatch.uom }}
            </div>
          </div>
        </template>
        <a-row :gutter="12">
          <a-col :span="12">
            <a-form-item label="申请量" required>
              <a-input-number
                v-model:value="createForm.qty"
                :min="1"
                :disabled="!pickedBatch"
                style="width: 100%"
                placeholder="大于 0"
              />
            </a-form-item>
          </a-col>
          <a-col :span="12">
            <a-form-item label="申请单位（UOM · 只读）">
              <div class="static-readonly">{{ pickedBatch ? pickedBatch.uom : '—' }}</div>
            </a-form-item>
          </a-col>
        </a-row>
        <a-form-item label="触发场景">
          <a-select v-model:value="createForm.scenario" placeholder="五选一 / 其他" :options="scenarioOptions" />
        </a-form-item>
        <a-form-item label="原因" required>
          <a-textarea v-model:value="createForm.reason" :rows="3" placeholder="必填：填写使用目的（将随申请记录与审计）" />
        </a-form-item>
        <a-row :gutter="12">
          <a-col :span="10">
            <a-form-item label="申请部门">
              <a-input v-model:value="createForm.dept" placeholder="默认 QC 检验室" />
            </a-form-item>
          </a-col>
          <a-col :span="14">
            <a-form-item label="申请人 / 申请日期">
              <div class="static-readonly">{{ APPLICANT }} · {{ TODAY }}（演示固定）</div>
            </a-form-item>
          </a-col>
        </a-row>
      </a-form>
    </a-modal>

    <!-- 驳回 -->
    <a-modal
      v-model:open="rejectOpen"
      title="驳回申请"
      ok-text="确认驳回"
      cancel-text="返回"
      :ok-button-props="{ danger: true }"
      width="460"
      @ok="confirmReject"
    >
      <p style="margin-bottom: 12px">
        即将驳回 <span class="mono">{{ selected ? selected.name : '' }}</span>，请填写原因。
      </p>
      <a-textarea
        v-model:value="rejectReason"
        :rows="3"
        placeholder="驳回原因（必填，将写入审批链与审计）"
      />
      <div class="soe red" style="margin: 12px 0 0">确认前驳回不释放预占：本单预占仍占用可用量。</div>
    </a-modal>

    <!-- Manager 取消逃生口 -->
    <a-modal
      v-model:open="cancelOpen"
      title="Manager 取消（释放预占）"
      ok-text="确认取消"
      cancel-text="返回"
      :ok-button-props="{ danger: true }"
      width="460"
      @ok="confirmCancel"
    >
      <p style="margin-bottom: 12px">
        取消 <span class="mono">{{ selected ? selected.name : '' }}</span>
        {{ selected ? `（当前预占 ${selected.reservedQty} ${selected.uom}）` : '' }}，请填写原因。
      </p>
      <a-textarea
        v-model:value="cancelReason"
        :rows="3"
        placeholder="取消原因（必填，将写入审计）"
      />
      <div class="soe red" style="margin: 12px 0 0">确认后将释放本单预占并写审计（演示）。</div>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, reactive, ref } from 'vue'
import { message, Empty } from 'ant-design-vue'
import type { TableColumnsType } from 'ant-design-vue'
import {
  CloseCircleOutlined, ExclamationCircleOutlined, PlusOutlined, ReloadOutlined,
} from '@ant-design/icons-vue'
import DemoBar from '@/components/retention/DemoBar.vue'
import {
  DEMO_ROLES, demo, can, seedUsageApplies,
  usageActionNeeded, usageQtyLabel, usageChainSteps, advanceUsage, SOD_NOTE,
  type UsageApply, type UsageStatus,
} from '@/demo/retentionDemo'

const APPLICANT = '王敏'
const TODAY = '2026-09-07'

// ---------- 列表数据 ----------
const rows = ref<UsageApply[]>(seedUsageApplies())
const selected = ref<UsageApply | null>(null)
const filter = ref<'all' | 'mine' | 'done'>('all')

type FilterKey = 'all' | 'mine' | 'done'
const mineRows = computed<UsageApply[]>(() =>
  rows.value.filter((a) => {
    const act = usageActionNeeded(a.status)
    return !!act && can(demo.role, act)
  }),
)

const roleLabel = computed(() => DEMO_ROLES.find((r) => r.value === demo.role)?.label ?? demo.role)
const listSub = computed(() => `当前演示身份「${roleLabel.value}」待我处理 ${mineRows.value.length} 份`)
const filterChips = computed<{ key: FilterKey; label: string }[]>(() => [
  { key: 'all', label: '全部' },
  { key: 'mine', label: `待我处理 ${mineRows.value.length}` },
  { key: 'done', label: '已执行' },
])

const filteredRows = computed<UsageApply[]>(() => {
  if (filter.value === 'all') return rows.value
  if (filter.value === 'done') return rows.value.filter((a) => a.status === '已执行')
  return mineRows.value
})

const columns: TableColumnsType<UsageApply> = [
  { title: '申请单号', key: 'order', width: 190 },
  { title: '留样 / 批号', key: 'retention', width: 220 },
  { title: '申请量', key: 'qty', width: 90 },
  { title: '触发场景', key: 'scenario', width: 130 },
  { title: '当前状态', key: 'status', width: 110 },
  { title: '操作', key: 'action', width: 110 },
]

function statusPillClass(s: UsageStatus): string {
  if (s === '已执行') return 'pill-pass'
  if (s === '已批准') return 'pill-primary'
  if (s === '已驳回' || s === '已取消') return 'pill-muted'
  return 'pill-warn'
}

function rowActionText(a: UsageApply): string {
  const act = usageActionNeeded(a.status)
  if (act && can(demo.role, act)) {
    if (a.status === '草稿') return '提交'
    if (a.status === '待库存确认') return '库存确认'
    if (a.status === '待QC批准' || a.status === '待QA批准' || a.status === '待QM批准') return '审批'
    if (a.status === '已批准') return '取样执行'
  }
  return '查看'
}

// 选择行：加载右侧详情并把双栏顶部滚入视口
const layoutRef = ref<HTMLElement | null>(null)
function selectRow(a: UsageApply) {
  selected.value = a
  layoutRef.value?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}
function customRow(record: UsageApply) {
  return {
    onClick: () => selectRow(record),
    style: { cursor: 'pointer' },
  }
}

// ---------- 审批链与详情动作 ----------
const selectedChain = computed(() => (selected.value ? usageChainSteps(selected.value) : []))

interface DetailBtn { key: string; label: string; primary?: boolean; danger?: boolean }
const detailActions = computed<DetailBtn[]>(() => {
  const s = selected.value
  if (!s) return []
  const list: DetailBtn[] = []
  const st = s.status
  if (st === '草稿') {
    if (can(demo.role, 'usage_submit')) list.push({ key: 'advance', label: '提交申请', primary: true })
  } else if (st === '待库存确认') {
    if (can(demo.role, 'usage_confirm')) list.push({ key: 'advance', label: `库存确认（预占 ${s.qty} ${s.uom}）`, primary: true })
  } else if (st === '待QC批准' || st === '待QA批准' || st === '待QM批准') {
    const approveKey = st === '待QC批准' ? 'usage_qc' : st === '待QA批准' ? 'usage_qa' : 'usage_qm'
    const approveLabel = st === '待QC批准' ? 'QC 批准' : st === '待QA批准' ? 'QA 批准' : 'QM 批准'
    if (can(demo.role, approveKey)) list.push({ key: 'advance', label: approveLabel, primary: true })
    if (can(demo.role, 'usage_reject')) list.push({ key: 'reject', label: '驳回', danger: true })
  } else if (st === '已批准') {
    if (can(demo.role, 'usage_execute')) list.push({ key: 'advance', label: '取样执行', primary: true })
    if (can(demo.role, 'usage_cancel')) list.push({ key: 'cancel', label: 'Manager 取消', danger: true })
  }
  return list
})

function syncRows(name: string) {
  rows.value = [...rows.value]
  selected.value = rows.value.find((r) => r.name === name) ?? selected.value
}

function advanceNote(s: UsageApply): string {
  switch (s.status) {
    case '待库存确认': return '已提交，等待库存确认（暂未预占）'
    case '待QC批准': return `库存确认即预占：已预占 ${s.qty} ${s.uom}`
    case '待QA批准': return 'QC 批准完成'
    case '待QM批准': return 'QA 批准完成'
    case '已批准': return 'QM 批准完成，可取样执行'
    case '已执行': return `取样执行完成：结存与预占已按 ${s.qty} ${s.uom} 原子扣减`
    default: return ''
  }
}

function advanceOne() {
  const s = selected.value
  if (!s) return
  const from = s.status
  advanceUsage(s)
  if (s.status === '已执行') {
    s.currentQty = Math.max(0, s.currentQty - s.qty)
    s.reservedQty = Math.max(0, s.reservedQty - s.qty)
  } else if (from === '待库存确认' && s.status === '待QC批准') {
    s.reservedQty = s.qty // 库存确认即预占
  }
  syncRows(s.name)
  message.success(`${s.name} → ${s.status}：${advanceNote(s)}（演示）`)
}

function runDetail(key: string) {
  if (key === 'advance') {
    advanceOne()
  } else if (key === 'reject') {
    rejectReason.value = ''
    rejectOpen.value = true
  } else if (key === 'cancel') {
    cancelReason.value = ''
    cancelOpen.value = true
  }
}

// ---------- 驳回 / Manager 取消 ----------
const rejectOpen = ref(false)
const rejectReason = ref('')
function confirmReject() {
  const s = selected.value
  if (!s) return
  if (!rejectReason.value.trim()) {
    message.warning('请填写驳回原因')
    return
  }
  s.status = '已驳回' // 确认前驳回不释放预占：reservedQty 保留
  syncRows(s.name)
  rejectOpen.value = false
  message.info('已驳回：确认前驳回不释放预占，本单预占仍占用可用量（演示）')
}

const cancelOpen = ref(false)
const cancelReason = ref('')
function confirmCancel() {
  const s = selected.value
  if (!s) return
  if (!cancelReason.value.trim()) {
    message.warning('请填写取消原因')
    return
  }
  s.status = '已取消'
  s.reservedQty = 0 // 释放本单预占
  syncRows(s.name)
  cancelOpen.value = false
  message.success('已取消：释放本单预占并写审计（演示）')
}

// ---------- 发起使用申请 ----------
const createOpen = ref(false)
const createForm = reactive({
  retentionName: undefined as string | undefined,
  qty: undefined as number | undefined,
  scenario: undefined as string | undefined,
  reason: '',
  dept: 'QC 检验室',
})

const scenarioOptions = ['检验结果分析', '生产异常', '用户投诉', '上市前研发', '稳定性考察', '其他']
  .map((v) => ({ value: v, label: v }))

interface BatchOption {
  retentionName: string
  product: string
  batch: string
  uom: string
  currentQty: number
  reservedQty: number
  label: string
}
// 从演示使用列表抽取留样批次（去重、仅可用量 > 0），避免自造不一致库存
const batchOptions = computed<BatchOption[]>(() => {
  const seen = new Set<string>()
  const out: BatchOption[] = []
  for (const r of rows.value) {
    if (seen.has(r.retentionName)) continue
    seen.add(r.retentionName)
    if (r.currentQty - r.reservedQty <= 0) continue
    out.push({
      retentionName: r.retentionName,
      product: r.product,
      batch: r.batch,
      uom: r.uom,
      currentQty: r.currentQty,
      reservedQty: r.reservedQty,
      label: `${r.product} · ${r.batch}（结存 ${r.currentQty} ${r.uom} / 可用 ${r.currentQty - r.reservedQty} ${r.uom}）`,
    })
  }
  return out
})
const batchOptionList = computed(() => batchOptions.value.map((b) => ({ value: b.retentionName, label: b.label })))
const pickedBatch = computed<BatchOption | null>(
  () => batchOptions.value.find((b) => b.retentionName === createForm.retentionName) ?? null,
)

function openCreate() {
  Object.assign(createForm, { retentionName: undefined, qty: undefined, scenario: undefined, reason: '', dept: 'QC 检验室' })
  createOpen.value = true
}

function nextOrderNo(): string {
  const max = rows.value.reduce((m, r) => {
    const tail = Number(r.name.split('-').pop() ?? 0)
    return Number.isFinite(tail) ? Math.max(m, tail) : m
  }, 0)
  return `HBOS-RET-USE-2026-${String(max + 1).padStart(5, '0')}`
}

function confirmCreate() {
  const b = pickedBatch.value
  if (!b) {
    message.error('请选择留样批次')
    return
  }
  const q = createForm.qty
  if (!q || q <= 0) {
    message.error('申请量须大于 0')
    return
  }
  if (!createForm.scenario) {
    message.error('请选择触发场景')
    return
  }
  if (!createForm.reason.trim()) {
    message.error('请填写申请原因')
    return
  }
  const avail = b.currentQty - b.reservedQty
  if (q > avail) {
    message.error(`申请量超过可用量（可用 ${avail} ${b.uom}）`)
    return
  }
  const no = nextOrderNo()
  const na: UsageApply = {
    name: no,
    retentionName: b.retentionName,
    product: b.product,
    batch: b.batch,
    qty: q,
    uom: b.uom,
    scenario: createForm.scenario,
    reason: createForm.reason.trim(),
    dept: createForm.dept.trim() || 'QC 检验室',
    applicant: APPLICANT,
    applicantDate: TODAY,
    status: '草稿',
    signedBy: {},
    currentQty: b.currentQty,
    reservedQty: 0,
  }
  rows.value = [na, ...rows.value]
  selected.value = na
  filter.value = 'all'
  createOpen.value = false
  message.success(`使用申请 ${no} 已创建（草稿），申请人 ${APPLICANT}`)
}

// ---------- 刷新 / 逃生口 ----------
function reset() {
  rows.value = seedUsageApplies()
  filter.value = 'all'
  const mine = mineRows.value[0]
  selected.value = mine ?? rows.value[0] ?? null
  message.info('演示数据已复位')
}

function goEscape() {
  const target = rows.value.find((r) => r.status === '已批准') ?? rows.value[0]
  if (!target) return
  filter.value = 'all'
  selected.value = target
  nextTick(() => layoutRef.value?.scrollIntoView({ behavior: 'smooth', block: 'start' }))
}

selected.value = mineRows.value[0] ?? rows.value[0] ?? null
</script>

<style scoped>
.list-panel { min-width: 0; }
.detail-panel { min-width: 0; }
.ret-main { color: var(--ink); }
.ret-sub { font-size: 11px; color: var(--muted); margin-top: 2px; }

.hero { display: flex; align-items: flex-start; justify-content: space-between; gap: 10px; }
.hero-title { font-size: 15px; font-weight: 700; color: var(--ink); }
.hero-sub { font-size: 11px; color: var(--muted); margin-top: 3px; }

.qty {
  font-family: var(--mono);
  font-size: 15px;
  font-weight: 700;
  margin-top: 4px;
  color: var(--ink);
}
.qty.warn { color: var(--warn); }
.qty.good { color: var(--pass); }

.detail-actions { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 4px; }
.static-readonly {
  background: var(--surface-2);
  border: 1px solid var(--line);
  border-radius: 6px;
  padding: 7px 10px;
  font-size: 12px;
  color: var(--ink);
}
</style>
