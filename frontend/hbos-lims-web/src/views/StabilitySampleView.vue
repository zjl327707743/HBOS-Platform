<template>
  <div class="page">
    <StbGateBanner
      mode="live"
      note="样品台账、库存流水与入箱登记均来自 hb_lims_app 稳定性业务服务（R8B）；按钮显隐按会话角色，实际准入由后端硬校验。"
    />

    <div class="page-head">
      <div>
        <h1>样品入箱与台账</h1>
        <p class="page-desc">入箱登记、标签打印、样品状态和库存流水</p>
      </div>
      <div class="page-actions">
        <a-button :disabled="!selected" @click="printLabel(selected!.name)">
          <template #icon><PrinterOutlined /></template>
          标签打印
        </a-button>
        <a-button type="primary" :disabled="!can('register_stability_sample')" @click="inboxRef?.show()">
          <template #icon><PlusOutlined /></template>
          登记入箱
        </a-button>
      </div>
    </div>

    <a-spin :spinning="loading">
      <div class="stb-kpi-grid">
        <div v-for="k in kpis" :key="k.label" class="stb-kpi">
          <div>
            <div class="stb-kpi-label">{{ k.label }}</div>
            <div class="stb-kpi-value">{{ k.value }} <small v-if="k.unit">{{ k.unit }}</small></div>
            <div class="stb-kpi-hint" :class="k.hintClass">{{ k.hint }}</div>
          </div>
          <div class="stb-kpi-icon" :class="k.iconClass">
            <component :is="k.icon" />
          </div>
        </div>
      </div>

      <div class="filter-bar">
        <a-input v-model:value="keyword" placeholder="搜索稳定性样品 / 产品 / 批号" allow-clear
                 style="flex: 1; min-width: 200px" @press-enter="load" />
        <a-select v-model:value="statusFilter" :options="statusOptions" style="width: 150px" @change="load" />
        <a-button size="small" @click="reset">重置</a-button>
      </div>

      <div class="panel">
        <div class="panel-head">
          <div>
            <div class="panel-title">稳定性样品台账</div>
            <div class="panel-sub">共 {{ rows.length }} 个样品；状态变化通过 Sample Log 追加记录</div>
          </div>
          <span class="pill pill-muted">只读投影</span>
        </div>
        <div class="panel-body no-pad">
          <a-table
            :columns="columns"
            :data-source="rows"
            size="small"
            row-key="name"
            :loading="loading"
            :pagination="{ pageSize: 10 }"
            :scroll="{ x: 1080 }"
          >
            <template #bodyCell="{ column, record }">
              <template v-if="column.key === 'name'"><span class="mono">{{ record.name }}</span></template>
              <template v-else-if="column.key === 'product'">
                <div class="stb-cell-strong">{{ record.product_name || '—' }}</div>
                <div class="dim">{{ record.batch_no }} · {{ record.sample_name || '' }}</div>
              </template>
              <template v-else-if="column.key === 'room'">
                <div>{{ record.condition_snapshot || '—' }}</div>
                <div class="dim mono">{{ record.storage_location || record.room || '' }}</div>
              </template>
              <template v-else-if="column.key === 'inDate'"><span class="mono">{{ record.in_date || '—' }}</span></template>
              <template v-else-if="column.key === 'qty'">
                <span class="mono">{{ record.current_qty ?? '—' }} / {{ record.init_qty ?? '—' }} {{ record.qty_uom || '' }}</span>
              </template>
              <template v-else-if="column.key === 'status'">
                <span :class="toneClass(statusTone(record.status))">{{ record.status }}</span>
              </template>
              <template v-else-if="column.key === 'eval'">
                <span v-if="record.need_evaluation" :class="toneClass('warn')">强制评估</span>
                <span v-else class="dim">无需</span>
              </template>
              <template v-else-if="column.key === 'action'">
                <a-button type="link" size="small" @click="openSample(record)">查看</a-button>
              </template>
            </template>
          </a-table>
          <a-empty v-if="!loading && !rows.length" description="暂无稳定性样品" :image="Empty.PRESENTED_IMAGE_SIMPLE"
                   style="padding: 40px 0" />
        </div>
      </div>
    </a-spin>

    <!-- 样品详情 -->
    <a-drawer v-model:open="sampleOpen" :title="detail?.name || '稳定性样品详情'" :width="640" placement="right">
      <p class="stb-gate-sub">Sample Log 仅追加；结存变更只经业务方法。</p>
      <a-spin :spinning="detailLoading">
        <template v-if="detail">
          <div class="stb-drawer-section">
            <h3>样品摘要</h3>
            <div class="stb-drawer-kv">
              <div><label>产品 / 批号</label><b>{{ detail.product_name }} / {{ detail.batch_no }}</b></div>
              <div><label>条件 / 位置</label><b>{{ detail.condition_snapshot || '—' }} / {{ detail.storage_location || '—' }}</b></div>
              <div><label>入箱 / 开始考察</label><b class="mono">{{ detail.in_date }} / {{ detail.start_date }}</b></div>
              <div><label>结存 / 初始</label><b class="mono">{{ detail.current_qty }} / {{ detail.init_qty }} {{ detail.qty_uom }}</b></div>
              <div><label>方向 / 包装</label><b>{{ detail.inverted_flag || '—' }} / {{ detail.pack_desc || '—' }}</b></div>
              <div><label>状态</label><b><span :class="toneClass(statusTone(detail.status))">{{ detail.status }}</span></b></div>
              <div><label>储存人 / 复核</label><b>{{ detail.stored_by || '—' }} / {{ detail.reviewed_by || '—' }}</b></div>
              <div><label>强制评估</label><b>{{ detail.need_evaluation ? '是' : '否' }}</b></div>
            </div>
            <div v-if="detail.need_evaluation && detail.evaluation_conclusion" class="stb-notice" style="margin-top: 10px">
              评估结论：{{ detail.evaluation_conclusion }}
              <span class="dim">· {{ detail.evaluated_by }} · {{ detail.evaluation_date }}</span>
            </div>
            <div v-if="detail.timepoint_gen_error" class="stb-notice amber" style="margin-top: 10px">
              时间点生成告警：{{ detail.timepoint_gen_error }}
              <a-button size="small" type="link" :disabled="!can('generate_timepoints')"
                        @click="runGenerate(detail.name)">手动重跑</a-button>
            </div>
            <div v-if="detail.pre_disposal_status" class="stb-notice amber" style="margin-top: 10px">
              待处置原因：{{ detail.disposal_mark_reason || '—' }}
              <span class="dim">· 进入前状态 {{ detail.pre_disposal_status }}</span>
            </div>
          </div>

          <div class="stb-drawer-section">
            <h3>可执行动作</h3>
            <a-space wrap>
              <a-button
                v-for="a in sampleActions"
                :key="a.action"
                size="small"
                :type="a.primary ? 'primary' : 'default'"
                :danger="a.danger"
                @click="runAction(a)"
              >
                {{ a.label }}
              </a-button>
              <span v-if="!sampleActions.length" class="dim">当前状态 / 角色下无可执行动作</span>
            </a-space>
            <div class="stb-form-hint">{{ SOD_NOTE }}</div>
          </div>

          <div class="stb-drawer-section">
            <h3>Sample Log · 仅追加（{{ detail.logs.length }}）</h3>
            <a-empty v-if="!detail.logs.length" description="暂无流水" :image="Empty.PRESENTED_IMAGE_SIMPLE" />
            <div v-for="(l, i) in detail.logs" :key="i" class="stb-audit-line">
              <span class="stb-audit-dot" :class="logDot(l.transaction_type)"></span>
              <div>
                <strong>{{ l.transaction_type }} {{ (l.qty_delta ?? 0) > 0 ? '+' : '' }}{{ l.qty_delta ?? 0 }} → {{ l.remaining_qty ?? 0 }} {{ l.qty_uom || '' }}</strong>
                <span>{{ l.transaction_date }} · {{ l.operator || '—' }}{{ l.reviewer ? ' · 复核 ' + l.reviewer : '' }}{{ l.remarks ? ' · ' + l.remarks : '' }}</span>
              </div>
            </div>
          </div>

          <div class="stb-drawer-section">
            <h3>时间点（{{ detail.timepoints.length }}）</h3>
            <a-empty v-if="!detail.timepoints.length" description="尚无时间点" :image="Empty.PRESENTED_IMAGE_SIMPLE" />
            <a-table
              v-else
              :columns="tpColumns"
              :data-source="detail.timepoints"
              size="small"
              row-key="name"
              :pagination="false"
            >
              <template #bodyCell="{ column, record }">
                <template v-if="column.key === 'label'"><span class="mono">{{ record.time_point_label }}</span></template>
                <template v-else-if="column.key === 'status'">
                  <span :class="toneClass(statusTone(record.status))">{{ record.status }}</span>
                </template>
              </template>
            </a-table>
          </div>
        </template>
      </a-spin>
      <template #footer>
        <a-button @click="sampleOpen = false">关闭</a-button>
        <a-button v-if="detail" type="primary" @click="printLabel(detail.name)">打印样品标签</a-button>
      </template>
    </a-drawer>

    <!-- 动作弹窗 -->
    <a-modal v-model:open="actionOpen" :title="actionTitle" :confirm-loading="actionSaving" @ok="confirmAction">
      <template v-if="currentAction?.action === 'record_sampling'">
        <a-form layout="vertical" size="small">
          <a-form-item label="取样数量 *"><a-input-number v-model:value="actionForm.qty" :min="0" style="width: 100%" /></a-form-item>
          <a-form-item label="取样日期"><a-date-picker v-model:value="actionForm.sample_date" style="width: 100%" value-format="YYYY-MM-DD" /></a-form-item>
          <a-form-item label="取样原因"><a-input v-model:value="actionForm.sampling_reason" /></a-form-item>
          <a-form-item label="取样号码"><a-input v-model:value="actionForm.sample_no_out" /></a-form-item>
        </a-form>
      </template>
      <template v-else-if="currentAction?.action === 'return_sample'">
        <a-form layout="vertical" size="small">
          <a-form-item label="返还数量 *"><a-input-number v-model:value="actionForm.qty" :min="0" style="width: 100%" /></a-form-item>
          <a-form-item label="返回样品号码"><a-input v-model:value="actionForm.return_sample_no" /></a-form-item>
          <a-form-item label="复核人"><a-input v-model:value="actionForm.reviewer" /></a-form-item>
        </a-form>
      </template>
      <template v-else-if="currentAction?.action === 'adjust_stock'">
        <a-form layout="vertical" size="small">
          <a-form-item label="调整量（可负）*"><a-input-number v-model:value="actionForm.qty_delta" style="width: 100%" /></a-form-item>
          <a-form-item label="原因 *"><a-textarea v-model:value="actionForm.remarks" :rows="2" /></a-form-item>
        </a-form>
      </template>
      <template v-else-if="currentAction?.action === 'dispose_sample'">
        <a-form layout="vertical" size="small">
          <a-form-item label="销毁数量（须等于当前结存）"><a-input-number v-model:value="actionForm.qty" :min="0" style="width: 100%" /></a-form-item>
          <a-form-item label="销毁监督人"><a-input v-model:value="actionForm.reviewer" /></a-form-item>
          <a-form-item label="备注"><a-textarea v-model:value="actionForm.remarks" :rows="2" /></a-form-item>
        </a-form>
      </template>
      <template v-else-if="currentAction?.action === 'transfer_out'">
        <a-form layout="vertical" size="small">
          <a-form-item label="转出备注"><a-textarea v-model:value="actionForm.remarks" :rows="2" /></a-form-item>
        </a-form>
      </template>
      <template v-else-if="currentAction?.needReason">
        <a-textarea v-model:value="actionForm.reason" :rows="3" placeholder="请填写原因（必填）" />
      </template>
    </a-modal>

    <StbInboxDrawer ref="inboxRef" @created="onCreated" />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import type { Component } from 'vue'
import { Empty, message } from 'ant-design-vue'
import {
  AlertOutlined, CheckCircleOutlined, PrinterOutlined, PlusOutlined, SafetyCertificateOutlined,
} from '@ant-design/icons-vue'
import StbGateBanner from '@/components/stability/StbGateBanner.vue'
import StbInboxDrawer from '@/components/stability/StbInboxDrawer.vue'
import { useAuthStore } from '@/stores/auth'
import {
  SOD_NOTE, adjustStock, cancelDisposal, canAction, disposeSample, generateTimepoints,
  markForDisposal, recordSampling, returnSample, reviewSampleStorage, sampleDetail,
  samples, transferOut,
  type SampleDetail, type SampleRow,
} from '@/api/stability'

const auth = useAuthStore()
const can = (action: string): boolean => canAction(auth.user?.roles, action)

const inboxRef = ref<InstanceType<typeof StbInboxDrawer> | null>(null)
const loading = ref(false)
const rows = ref<SampleRow[]>([])
const keyword = ref('')
const statusFilter = ref<string | undefined>(undefined)

const detail = ref<SampleDetail | null>(null)
const detailLoading = ref(false)
const sampleOpen = ref(false)
const selected = computed(() => (sampleOpen.value ? detail.value : null))

const statusOptions = ['全部状态', '在箱', '部分取样', '已取尽', '待处理', '已销毁', '已转出']
  .map((v) => ({ value: v, label: v }))

function statusTone(status: string): 'pass' | 'warn' | 'danger' | 'info' | 'muted' {
  if (status === '在箱') return 'pass'
  if (status === '部分取样') return 'info'
  if (status === '已取尽') return 'warn'
  if (status === '待处理') return 'danger'
  return 'muted'
}
function toneClass(tone: ReturnType<typeof statusTone>): string {
  return `pill pill-${tone}`
}
function logDot(type: string): string {
  if (type === '销毁') return 'red'
  if (type === '取样出库') return 'amber'
  if (type === '入库') return ''
  return 'gray'
}

const kpis = computed<{ label: string; value: number | string; unit?: string; hint: string; hintClass: string; iconClass: string; icon: Component }[]>(() => {
  const month = new Date().toISOString().slice(0, 7)
  return [
    { label: '在箱样品', value: rows.value.filter((r) => r.status === '在箱').length, unit: '个',
      hint: '当前有效', hintClass: 'good', iconClass: 'green', icon: SafetyCertificateOutlined },
    { label: '本月入箱', value: rows.value.filter((r) => String(r.in_date || '').startsWith(month)).length, unit: '个',
      hint: '按入箱日期统计', hintClass: '', iconClass: 'teal', icon: CheckCircleOutlined },
    { label: '强制评估', value: rows.value.filter((r) => r.need_evaluation).length, unit: '个',
      hint: '入箱超生产 1 个月', hintClass: 'warn', iconClass: 'amber', icon: AlertOutlined },
    { label: '待处置', value: rows.value.filter((r) => r.status === '待处理').length, unit: '个',
      hint: '需 QA 复核后销毁', hintClass: rows.value.some((r) => r.status === '待处理') ? 'bad' : '',
      iconClass: 'red', icon: AlertOutlined },
  ]
})

const columns = [
  { title: '样品编号', key: 'name', width: 200 },
  { title: '产品 / 批号', key: 'product', width: 190 },
  { title: '条件 / 位置', key: 'room', width: 150 },
  { title: '入箱日期', key: 'inDate', width: 120 },
  { title: '结存 / 初始', key: 'qty', width: 130 },
  { title: '状态', key: 'status', width: 110 },
  { title: '评估', key: 'eval', width: 110 },
  { title: '操作', key: 'action', width: 80, fixed: 'right' },
] as const

const tpColumns = [
  { title: '时间点', key: 'label', width: 90 },
  { title: '条件', dataIndex: 'condition_type', key: 'condition_type', width: 110 },
  { title: '计划取样', dataIndex: 'plan_sample_date', key: 'plan_sample_date', width: 110 },
  { title: '计划检测', dataIndex: 'plan_test_date', key: 'plan_test_date', width: 110 },
  { title: '状态', key: 'status', width: 100 },
]

// ---- 动作 ----
interface UiAction { action: string; label: string; primary?: boolean; danger?: boolean; needReason?: boolean }

const sampleActions = computed<UiAction[]>(() => {
  const d = detail.value
  if (!d) return []
  const out: UiAction[] = []
  const push = (a: UiAction) => { if (can(a.action)) out.push(a) }
  if (d.status === '在箱' || d.status === '部分取样') {
    push({ action: 'record_sampling', label: '取样', primary: true })
    push({ action: 'return_sample', label: '返还' })
  }
  if (['在箱', '部分取样', '已取尽'].includes(d.status)) {
    push({ action: 'review_sample_storage', label: '储存复核' })
    push({ action: 'adjust_stock', label: '手动调整' })
    push({ action: 'mark_for_disposal', label: '进入待处置', needReason: true })
    push({ action: 'transfer_out', label: '受托转出' })
  }
  if (d.status === '待处理') {
    push({ action: 'cancel_disposal', label: '取消待处置（回库）', needReason: true })
    push({ action: 'dispose_sample', label: '销毁', danger: true, primary: true })
  }
  return out
})

const actionOpen = ref(false)
const actionTitle = ref('')
const actionSaving = ref(false)
const currentAction = ref<UiAction | null>(null)
const actionForm = ref({
  qty: undefined as number | undefined,
  qty_delta: undefined as number | undefined,
  sample_date: undefined as string | undefined,
  sampling_reason: '',
  sample_no_out: '',
  return_sample_no: '',
  reviewer: '',
  remarks: '',
  reason: '',
})

/** 需要填写表单的动作（其余动作直接执行，不弹空确认框） */
const NEEDS_FORM = new Set(['record_sampling', 'return_sample', 'adjust_stock',
  'dispose_sample', 'transfer_out', 'mark_for_disposal', 'cancel_disposal'])

function runAction(a: UiAction) {
  currentAction.value = a
  actionTitle.value = `${a.label} · ${detail.value?.name || ''}`
  actionForm.value = {
    qty: a.action === 'dispose_sample' ? detail.value?.current_qty : undefined,
    qty_delta: undefined,
    sample_date: undefined,
    sampling_reason: '',
    sample_no_out: '',
    return_sample_no: '',
    reviewer: '',
    remarks: '',
    reason: '',
  }
  if (NEEDS_FORM.has(a.action)) {
    actionOpen.value = true
    return
  }
  void confirmAction()
}

async function confirmAction() {
  const a = currentAction.value
  const d = detail.value
  if (!a || !d) return
  const f = actionForm.value
  actionSaving.value = true
  try {
    if (a.action === 'record_sampling') {
      if (!f.qty || f.qty <= 0) { message.warning('取样数量必须大于 0'); return }
      await recordSampling(d.name, {
        qty: f.qty, sample_date: f.sample_date, sampling_reason: f.sampling_reason,
        sample_no_out: f.sample_no_out,
      })
    } else if (a.action === 'return_sample') {
      if (!f.qty || f.qty <= 0) { message.warning('返还数量必须大于 0'); return }
      await returnSample(d.name, {
        qty: f.qty, return_sample_no: f.return_sample_no, reviewer: f.reviewer || undefined,
      })
    } else if (a.action === 'review_sample_storage') {
      await reviewSampleStorage(d.name)
    } else if (a.action === 'adjust_stock') {
      if (!f.qty_delta) { message.warning('调整量必填'); return }
      if (!f.remarks.trim()) { message.warning('原因必填'); return }
      await adjustStock(d.name, f.qty_delta, f.remarks.trim())
    } else if (a.action === 'mark_for_disposal') {
      if (!f.reason.trim()) { message.warning('原因必填'); return }
      await markForDisposal(d.name, f.reason.trim())
    } else if (a.action === 'cancel_disposal') {
      if (!f.reason.trim()) { message.warning('原因必填'); return }
      await cancelDisposal(d.name, f.reason.trim())
    } else if (a.action === 'dispose_sample') {
      await disposeSample(d.name, { qty: f.qty, reviewer: f.reviewer || undefined, remarks: f.remarks })
    } else if (a.action === 'transfer_out') {
      await transferOut(d.name, f.remarks || undefined)
    }
    message.success('操作已完成')
    actionOpen.value = false
    await load()
    await openSample({ name: d.name } as SampleRow)
  } catch {
    // 具体错误已由 client 拦截层弹出（含 SoD / 越权 / 状态机 / 结存校验）
  } finally {
    actionSaving.value = false
  }
}

async function runGenerate(sampleName: string) {
  try {
    const res = await generateTimepoints(sampleName)
    message.success(`时间点生成完成，新增 ${res.created} 个`)
    await openSample({ name: sampleName } as SampleRow)
    await load()
  } catch {
    // 具体错误已由 client 拦截层弹出
  }
}

function printLabel(name: string) {
  const url = `/printview?doctype=${encodeURIComponent('HBOS Stability Sample')}`
    + `&name=${encodeURIComponent(name)}`
    + `&format=${encodeURIComponent('HBOS 稳定性样品标签')}&no_letterhead=0`
  window.open(url, '_blank')
}

// ---- 数据 ----
async function load() {
  loading.value = true
  try {
    const status = statusFilter.value === '全部状态' ? undefined : statusFilter.value
    const res = await samples({ keyword: keyword.value.trim() || undefined, status, limit: 300 })
    rows.value = res.rows
  } catch {
    if (!auth.user) message.warning('未登录（Guest）：样品台账不可用，请先在 Frappe Desk 登录后刷新。')
    else if (!auth.user?.roles?.length) message.warning('当前会话尚未取到角色，列表加载可能受限。')
    else message.error('加载稳定性样品失败')
  } finally {
    loading.value = false
  }
}

async function openSample(row: SampleRow) {
  sampleOpen.value = true
  detailLoading.value = true
  try {
    detail.value = await sampleDetail(row.name)
  } catch {
    // 具体错误已由 client 拦截层弹出
  } finally {
    detailLoading.value = false
  }
}

function reset() {
  keyword.value = ''
  statusFilter.value = undefined
  void load()
}

async function onCreated(name: string) {
  await load()
  await openSample({ name } as SampleRow)
}

onMounted(() => {
  void auth.checkSession()
  void load()
})
</script>

<style scoped>
.stb-cell-strong { color: var(--ink); font-weight: 700; }
.stb-gate-sub { font-size: 12px; color: var(--muted); margin-bottom: 12px; }
.stb-form-hint { font-size: 12px; color: var(--muted); margin-top: 8px; }
</style>
