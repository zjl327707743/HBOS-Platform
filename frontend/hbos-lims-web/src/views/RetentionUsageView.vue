<template>
  <div class="page">
    <div class="page-head">
      <div>
        <h1>使用申请</h1>
        <p class="page-desc">库存确认即预占 · QC / QA / QM 三级批准 · 取样执行原子扣减</p>
      </div>
      <div class="page-actions">
        <a-button @click="load">
          <template #icon><ReloadOutlined /></template>
          刷新
        </a-button>
        <a-button type="primary" :disabled="!can('create_usage_apply')" @click="openCreate">
          <template #icon><PlusOutlined /></template>
          发起使用申请
        </a-button>
      </div>
    </div>
    <a-alert
      v-if="targetUsageName"
      :type="targetUsageMissing ? 'warning' : 'info'"
      show-icon
      :message="targetUsageMissing ? `来源使用申请 ${targetUsageName} 未找到` : `已定位使用申请 ${targetUsageName}`"
      style="margin-bottom: 12px"
    />

    <a-alert type="info" show-icon :message="realNote" style="margin-bottom: 14px" />

    <div ref="layoutRef" class="detail-layout">
      <!-- 左：申请列表 -->
      <div class="panel list-panel">
        <div class="panel-head">
          <div>
            <div class="panel-title">使用申请列表</div>
            <div class="panel-sub">共 {{ rows.length }} 份 · 后端 workflow 状态投影（草稿 → 库存确认 → QC/QA/QM → 执行）</div>
          </div>
        </div>
        <div class="panel-body no-pad">
          <a-table
            :columns="columns"
            :data-source="rows"
            :loading="loading"
            :pagination="{ pageSize: 12, showTotal: (t: number) => `共 ${t} 条` }"
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
                <div class="ret-sub mono">留样 {{ record.retention_name }}</div>
              </template>
              <template v-else-if="column.key === 'qty'">
                <span class="mono">{{ record.qty }} {{ record.uom }}</span>
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
            v-if="!rows.length && !loading"
            description="暂无使用申请"
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
          <a-empty v-if="!selected" description="从左侧选择一份使用申请查看" :image="Empty.PRESENTED_IMAGE_SIMPLE" />
          <template v-else>
            <div class="hero">
              <div>
                <div class="hero-title">{{ selected.product }} <span class="dim">/ {{ selected.batch }}</span></div>
                <div class="hero-sub">留样编号 <span class="mono">{{ selected.retention_name }}</span></div>
              </div>
              <span class="pill" :class="statusPillClass(selected.status)">{{ selected.status }}</span>
            </div>

            <div class="divider"></div>

            <div class="stat-row cols-3" style="gap: 10px">
              <div class="stat-card" style="padding: 8px 10px">
                <div class="stat-label">当前结存</div>
                <div class="qty mono">{{ selected.current_qty }} {{ selected.uom }}</div>
              </div>
              <div class="stat-card" style="padding: 8px 10px">
                <div class="stat-label">预占</div>
                <div class="qty mono warn">{{ selected.reserved_qty }} {{ selected.uom }}</div>
              </div>
              <div class="stat-card" style="padding: 8px 10px">
                <div class="stat-label">可用量</div>
                <div class="qty mono good">{{ available(selected) }} {{ selected.uom }}</div>
              </div>
            </div>

            <div class="section-label">申请信息</div>
            <div class="field">
              <label>申请量</label>
              <div class="static">{{ selected.qty }} {{ selected.uom }}</div>
            </div>
            <div class="field">
              <label>触发场景 / 原因</label>
              <div class="static">{{ selected.scenario }} · {{ selected.reason || '—' }}</div>
            </div>
            <div class="field">
              <label>申请部门 / 申请人</label>
              <div class="static">{{ selected.dept || '—' }} · {{ selected.applicant }}（{{ selected.applicant_date || '—' }}）</div>
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
            <div v-else class="dim" style="margin-top: 10px">当前状态与会话角色下无可用操作，仅查看；如确需放行请联系 LIMS Manager。</div>
          </template>
        </div>
      </div>
    </div>

    <!-- 发起使用申请 -->
    <a-modal
      v-model:open="createOpen"
      title="发起使用申请"
      ok-text="发起申请"
      cancel-text="取消"
      width="640"
      :confirm-loading="savingCreate"
      @ok="confirmCreate"
    >
      <a-form layout="vertical" style="margin-top: 8px">
        <a-form-item label="留样批次" required>
          <a-select
            v-model:value="createForm.retention_name"
            show-search
            option-filter-prop="label"
            placeholder="选择可用留样（在库 / 部分使用）"
            :options="candidateOptions"
            :loading="loadingCandidates"
            @change="onPickCandidate"
          />
          <div v-if="!candidateOptions.length && !loadingCandidates" class="dim" style="margin-top: 6px">
            当前无可申请留样（结存 0 或已被预占占用）。
          </div>
        </a-form-item>
        <template v-if="picked">
          <div class="field">
            <label>批次库存快照（只读）</label>
            <div class="static">
              结存 {{ picked.current_qty }} {{ picked.qty_uom }} · 预占 {{ picked.reserved_qty }} {{ picked.qty_uom }}
              · 可用 {{ picked.available_qty }} {{ picked.qty_uom }}
              <span class="dim">· 留样编号 <span class="mono">{{ picked.name }}</span></span>
            </div>
          </div>
        </template>
        <a-row :gutter="12">
          <a-col :span="12">
            <a-form-item label="申请量" required>
              <a-input-number
                v-model:value="createForm.apply_qty"
                :min="1"
                :max="picked ? picked.available_qty : undefined"
                :disabled="!picked"
                style="width: 100%"
                placeholder="大于 0 且不超过可用量"
              />
            </a-form-item>
          </a-col>
          <a-col :span="12">
            <a-form-item label="单位（UOM · 只读带出）">
              <div class="static-readonly">{{ picked ? picked.qty_uom : '—' }}</div>
            </a-form-item>
          </a-col>
        </a-row>
        <a-form-item label="触发场景" required>
          <a-select v-model:value="createForm.reason_type" placeholder="选择使用目的场景" :options="scenarioOptions" />
        </a-form-item>
        <a-form-item label="原因" required>
          <a-textarea v-model:value="createForm.reason_detail" :rows="3" placeholder="必填：填写使用目的与依据（将随申请记录与审计）" />
        </a-form-item>
        <a-form-item label="申请部门">
          <a-input v-model:value="createForm.apply_dept" placeholder="如 QC 检验室（申请人角色自动记录）" />
        </a-form-item>
      </a-form>
    </a-modal>

    <!-- 驳回 / Manager 取消（共用原因弹窗） -->
    <a-modal
      v-model:open="reasonOpen"
      :title="reasonKind === 'reject' ? '驳回申请' : 'Manager 取消（逃生口）'"
      :ok-text="reasonKind === 'reject' ? '确认驳回' : '确认取消'"
      cancel-text="返回"
      :ok-button-props="{ danger: true }"
      width="480"
      :confirm-loading="savingReason"
      @ok="confirmReason"
    >
      <p style="margin-bottom: 12px">
        <template v-if="selected">
          <span v-if="reasonKind === 'reject'">
            即将驳回 <span class="mono">{{ selected.name }}</span>（当前状态：{{ selected.status }}），驳回为终态；
            若本单已库存确认预占将一并释放。
          </span>
          <span v-else>
            取消 <span class="mono">{{ selected.name }}</span>（当前状态：{{ selected.status }}）。
            {{ selected.status === '已批准' ? '取消将释放本单预占并写审计。' : '草稿取消无需释放预占（尚未预占）。' }}
          </span>
        </template>
      </p>
      <a-textarea
        v-model:value="reasonText"
        :rows="3"
        placeholder="原因（必填，将写入审计记录）"
      />
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { message, Empty } from 'ant-design-vue'
import type { TableColumnsType } from 'ant-design-vue'
import { CloseCircleOutlined, PlusOutlined, ReloadOutlined } from '@ant-design/icons-vue'
import { useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import {
  usageList, createUsageApply, submitUsageApply, confirmUsageStock,
  approveUsage, executeUsage, rejectUsage, cancelUsageApply,
  retentionCandidates, canAction, SOD_NOTE,
  type UsageRow, type RetentionCandidate,
} from '@/api/retention'
import { readScalarQuery } from '@/features/todos/todoModel'

const auth = useAuthStore()
const route = useRoute()
const realNote = '已接入真实后端（R7C）· 使用申请数据与流转均来自后端业务方法；提交、审批、驳回、取消等操作受会话角色与后端 SoD 约束。'

function can(key: string): boolean {
  return canAction(auth.user?.roles, key)
}

// ---------- 列表 ----------
const rows = ref<UsageRow[]>([])
const loading = ref(false)
const selected = ref<UsageRow | null>(null)
const layoutRef = ref<HTMLElement | null>(null)
const targetUsageName = ref('')
const targetUsageMissing = ref(false)

const STATUS_ACTION: Record<string, string> = {
  草稿: 'create_usage_apply',
  待库存确认: 'usage_confirm',
  待QC批准: 'usage_qc',
  待QA批准: 'usage_qa',
  待QM批准: 'usage_qm',
  已批准: 'usage_execute',
}
const STATUS_PRIMARY: Record<string, string> = {
  草稿: '提交',
  待库存确认: '库存确认',
  待QC批准: 'QC 批准',
  待QA批准: 'QA 批准',
  待QM批准: 'QM 批准',
  已批准: '取样执行',
}

const columns: TableColumnsType<UsageRow> = [
  { title: '申请单号', key: 'order', width: 190 },
  { title: '留样 / 批号', key: 'retention', width: 230 },
  { title: '申请量', key: 'qty', width: 100 },
  { title: '触发场景', key: 'scenario', width: 130 },
  { title: '当前状态', key: 'status', width: 110 },
  { title: '操作', key: 'action', width: 100 },
]

function statusPillClass(s: string): string {
  if (s === '已执行') return 'pill-pass'
  if (s === '已批准') return 'pill-primary'
  if (s === '已驳回' || s === '已取消') return 'pill-muted'
  if (s.startsWith('待')) return 'pill-warn'
  return 'pill-muted' // 草稿
}

function available(r: UsageRow): number {
  return (r.current_qty || 0) - (r.reserved_qty || 0)
}

function rowActionText(r: UsageRow): string {
  const action = STATUS_ACTION[r.status]
  if (action && can(action)) return STATUS_PRIMARY[r.status] || '查看'
  return '查看'
}

function selectRow(r: UsageRow) {
  selected.value = r
  layoutRef.value?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}
function customRow(record: UsageRow) {
  return {
    onClick: () => selectRow(record),
    style: { cursor: 'pointer' },
  }
}

async function load() {
  loading.value = true
  try {
    const res = await usageList()
    rows.value = res.rows
    targetUsageName.value = readScalarQuery(route.query.usage) || ''
    targetUsageMissing.value = false
    keepSelection()
    if (targetUsageName.value) {
      const target = rows.value.find((row) => row.name === targetUsageName.value)
      targetUsageMissing.value = !target
      if (target) selected.value = target
    }
  } catch {
    if (!auth.user) message.warning('未登录（Guest）：使用申请只读亦不可用，请先在 Frappe Desk 登录后刷新。')
    else if (!auth.user?.roles?.length) message.warning('当前会话尚未取到角色，列表加载可能受限。')
    else message.error('加载使用申请列表失败')
  } finally {
    loading.value = false
  }
}

function keepSelection() {
  const cur = selected.value?.name
  selected.value = rows.value.find((r) => r.name === cur) ?? rows.value[0] ?? null
}

/** 动作成功后重新拉取列表，并仍选中刚操作的那份申请。 */
async function reloadSelect(name: string) {
  await load()
  selected.value = rows.value.find((r) => r.name === name) ?? selected.value
}

// ---------- 审批链与详情动作 ----------
interface ChainStep { key: string; label: string; who: string; state: 'done' | 'active' | 'todo' }

const selectedChain = computed<ChainStep[]>(() => {
  const r = selected.value
  if (!r) return []
  const steps: { key: string; label: string; done: boolean; active: boolean; who: string }[] = [
    {
      key: 'stock', label: `库存确认（预占 ${r.qty} ${r.uom}）`,
      done: !!r.stock_confirm_by, active: r.status === '待库存确认',
      who: r.stock_confirm_by || (r.status === '待库存确认' ? '待确认并预占' : ''),
    },
    {
      key: 'qc', label: 'QC 批准',
      done: !!r.qc_approval, active: r.status === '待QC批准',
      who: r.qc_approval || (r.status === '待QC批准' ? '待 QC 签署' : ''),
    },
    {
      key: 'qa', label: 'QA 批准',
      done: !!r.qa_approval, active: r.status === '待QA批准',
      who: r.qa_approval || (r.status === '待QA批准' ? '待 QA 签署' : ''),
    },
    {
      key: 'qm', label: 'QM 批准',
      done: !!r.qm_approval, active: r.status === '待QM批准',
      who: r.qm_approval || (r.status === '待QM批准' ? '待 QM 签署' : ''),
    },
  ]
  return [
    { key: 'applicant', label: '申请人', who: r.applicant || '—', state: 'done' as const },
    ...steps.map((s) => ({
      key: s.key, label: s.label, who: s.who,
      state: (s.done ? 'done' : s.active ? 'active' : 'todo') as ChainStep['state'],
    })),
  ]
})

interface DetailBtn { key: string; label: string; primary?: boolean; danger?: boolean }

const detailActions = computed<DetailBtn[]>(() => {
  const s = selected.value
  if (!s) return []
  const list: DetailBtn[] = []
  const st = s.status
  if (st === '草稿') {
    if (can('create_usage_apply')) list.push({ key: 'submit', label: '提交申请', primary: true })
    if (can('usage_cancel')) list.push({ key: 'cancel', label: 'Manager 取消', danger: true })
  } else if (st === '待库存确认') {
    if (can('usage_confirm')) list.push({ key: 'confirm', label: `库存确认（预占 ${s.qty} ${s.uom}）`, primary: true })
  } else if (st === '待QC批准' || st === '待QA批准' || st === '待QM批准') {
    const approve: Record<string, { key: string; label: string }> = {
      待QC批准: { key: 'usage_qc', label: 'QC 批准' },
      待QA批准: { key: 'usage_qa', label: 'QA 批准' },
      待QM批准: { key: 'usage_qm', label: 'QM 批准' },
    }
    const act = approve[st]
    if (can(act.key)) list.push({ key: 'approve', label: act.label, primary: true })
    if (can('usage_reject')) list.push({ key: 'reject', label: '驳回', danger: true })
  } else if (st === '已批准') {
    if (can('usage_execute')) list.push({ key: 'execute', label: '取样执行', primary: true })
    if (can('usage_cancel')) list.push({ key: 'cancel', label: 'Manager 取消', danger: true })
  }
  return list
})

async function runDetail(key: string) {
  const s = selected.value
  if (!s) return
  if (key === 'reject' || key === 'cancel') {
    openReason(key as 'reject' | 'cancel')
    return
  }
  const name = s.name
  try {
    if (key === 'submit') {
      await submitUsageApply(name)
      message.success(`${name} 已提交 → 待库存确认`)
    } else if (key === 'confirm') {
      await confirmUsageStock(name)
      message.success(`${name} 库存确认并预占 ${s.qty} ${s.uom} → 待 QC 批准`)
    } else if (key === 'approve') {
      const res = (await approveUsage(name)) as { status: string }
      message.success(`${name} → ${res.status}`)
    } else if (key === 'execute') {
      await executeUsage(name)
      message.success(`${name} 取样执行完成：结存与预占已按 ${s.qty} ${s.uom} 原子扣减`)
    }
  } catch {
    // 具体错误已由 client 拦截层弹出
  }
  await reloadSelect(name)
}

// ---------- 驳回 / Manager 取消 ----------
const reasonOpen = ref(false)
const reasonKind = ref<'reject' | 'cancel'>('reject')
const reasonText = ref('')
const savingReason = ref(false)

function openReason(kind: 'reject' | 'cancel') {
  if (!selected.value) return
  reasonKind.value = kind
  reasonText.value = ''
  reasonOpen.value = true
}

async function confirmReason() {
  const s = selected.value
  if (!s) return
  const text = reasonText.value.trim()
  if (!text) {
    message.warning('请填写原因（必填）')
    return
  }
  savingReason.value = true
  try {
    if (reasonKind.value === 'reject') {
      await rejectUsage(s.name, text)
      message.info(`已驳回 ${s.name}：${s.status} → 已驳回`)
    } else {
      await cancelUsageApply(s.name, text)
      message.success(`已取消 ${s.name}：${s.status} → 已取消`)
    }
    reasonOpen.value = false
    await reloadSelect(s.name)
  } catch {
    // 具体错误已由 client 拦截层弹出
  } finally {
    savingReason.value = false
  }
}

// ---------- 发起使用申请 ----------
const createOpen = ref(false)
const savingCreate = ref(false)
const loadingCandidates = ref(false)
const candidates = ref<RetentionCandidate[]>([])
const createForm = reactive({
  retention_name: undefined as string | undefined,
  apply_qty: undefined as number | undefined,
  reason_type: undefined as string | undefined,
  reason_detail: '',
  apply_dept: '',
})

const scenarioOptions = ['用户投诉', '检验结果分析', '生产异常', '上市前研发', '其他']
  .map((v) => ({ value: v, label: v }))

const candidateOptions = computed(() =>
  candidates.value
    .filter((c) => c.available_qty > 0)
    .map((c) => ({
      value: c.name,
      label: `${c.product_name}(${c.batch_no}) · 结存 ${c.current_qty} 可用 ${c.available_qty}`,
    })),
)
const picked = computed<RetentionCandidate | null>(
  () => candidates.value.find((c) => c.name === createForm.retention_name) ?? null,
)

function onPickCandidate() {
  createForm.apply_qty = undefined
}

function resetCreateForm() {
  Object.assign(createForm, {
    retention_name: undefined, apply_qty: undefined,
    reason_type: undefined, reason_detail: '', apply_dept: '',
  })
}

async function openCreate() {
  resetCreateForm()
  createOpen.value = true
  loadingCandidates.value = true
  try {
    candidates.value = await retentionCandidates(['在库', '部分使用'])
  } catch {
    message.error('加载可用留样批次失败（需 LIMS 会话角色）')
  } finally {
    loadingCandidates.value = false
  }
}

async function confirmCreate() {
  const c = picked.value
  if (!c) {
    message.error('请选择可用留样批次')
    return
  }
  const q = createForm.apply_qty
  if (!q || q <= 0) {
    message.error('申请量须大于 0')
    return
  }
  if (!createForm.reason_type) {
    message.error('请选择触发场景')
    return
  }
  if (!createForm.reason_detail.trim()) {
    message.error('请填写使用原因')
    return
  }
  if (q > c.available_qty) {
    message.error(`申请量超过可用量（可用 ${c.available_qty} ${c.qty_uom}）`)
    return
  }
  savingCreate.value = true
  try {
    const res = (await createUsageApply({
      retention_name: c.name,
      apply_qty: q,
      reason_type: createForm.reason_type,
      reason_detail: createForm.reason_detail.trim(),
      apply_dept: createForm.apply_dept.trim() || undefined,
    })) as { name: string }
    message.success(`使用申请 ${res.name} 已创建（草稿），提交后进入库存确认`)
    createOpen.value = false
    await reloadSelect(res.name)
  } catch {
    // 具体错误已由 client 拦截层弹出
  } finally {
    savingCreate.value = false
  }
}

onMounted(load)
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
