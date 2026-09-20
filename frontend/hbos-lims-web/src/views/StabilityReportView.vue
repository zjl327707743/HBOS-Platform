<template>
  <div class="page">
    <StbGateBanner mode="live"
              :note="'报告起草 / 审核链与外推建议来自 R8C 稳定性业务服务；QA 判定有效期为独立批准动作（须先审核，审核人 ≠ 批准人）。'" />

    <div class="page-head">
      <div>
        <h1>报告与有效期</h1>
        <p class="page-desc">稳定性报告审核批准、版本链和有效期外推辅助（真实后端）</p>
      </div>
      <div class="page-actions">
        <a-button v-if="can('create_stability_report')" @click="createOpen = true">
          <template #icon><FileTextOutlined /></template>
          新建报告
        </a-button>
      </div>
    </div>

    <div class="filter-bar">
      <a-input v-model:value="keyword" placeholder="搜索单号 / 产品" allow-clear style="flex: 1; min-width: 200px" @press-enter="load" />
      <a-select v-model:value="typeFilter" :options="typeOptions" style="width: 180px" @change="load" />
      <a-select v-model:value="statusFilter" :options="statusOptions" style="width: 150px" @change="load" />
    </div>

    <div class="stb-three-col">
      <!-- 报告列表 -->
      <div class="panel" style="margin-bottom: 0">
        <div class="panel-head">
          <div>
            <div class="panel-title">报告列表</div>
            <div class="panel-sub">{{ rows.length }} 份报告</div>
          </div>
        </div>
        <a-spin :spinning="loading">
          <div
            v-for="r in filteredRows"
            :key="r.name"
            class="stb-list-row"
            :class="{ active: selected?.name === r.name }"
            @click="openReport(r)"
          >
            <div class="stb-list-row-top">
              <span class="stb-list-row-title mono">{{ r.name }}</span>
              <span :class="toneClass(statusTone(r.status))">{{ r.status }}</span>
            </div>
            <div class="stb-list-row-sub">
              {{ r.product_name || r.stability_product }} · {{ r.report_type }}<br />
              {{ r.year || '—' }} 年
              <template v-if="r.customer">· {{ r.customer }}#{{ r.seq }}</template>
            </div>
          </div>
          <a-empty v-if="!loading && !filteredRows.length" description="无匹配报告" :image="Empty.PRESENTED_IMAGE_SIMPLE" style="padding: 20px 0" />
        </a-spin>
      </div>

      <!-- 报告摘要 -->
      <div class="panel" style="margin-bottom: 0">
        <div class="panel-head">
          <div>
            <div class="panel-title">报告摘要</div>
            <div class="panel-sub" v-if="detail">{{ detail?.name }} · {{ detail?.report_type }}</div>
          </div>
        </div>
        <a-spin :spinning="detailLoading">
          <div class="panel-body" v-if="detail">
            <div class="stb-kv-grid">
              <div class="stb-kv"><label>产品</label><b>{{ detail.product_name || detail.stability_product }}</b></div>
              <div class="stb-kv"><label>状态</label><b>{{ detail.status }}</b></div>
              <div class="stb-kv"><label>考察周期</label><b>{{ detail.period_from || '—' }} ~ {{ detail.period_to || '—' }}</b></div>
              <div class="stb-kv"><label>来源</label><b class="mono">{{ detail.source_doctype || '—' }}<br />{{ detail.source_name || '' }}</b></div>
              <div class="stb-kv"><label>外推建议</label><b>{{ detail.proposed_validity_months || '—' }} 个月（{{ detail.proposed_validity_type || '—' }}）</b></div>
              <div class="stb-kv"><label>QA 判定有效期</label><b>{{ detail.final_validity_months ? `${detail.final_validity_months} 个月至 ${detail.final_validity_date}` : '待批准' }}</b></div>
              <div class="stb-kv"><label>起草</label><b>{{ detail.drafted_by || '—' }} · {{ detail.draft_date || '—' }}</b></div>
              <div class="stb-kv"><label>QA 批准</label><b>{{ detail.qa_approve_by || '—' }} · {{ detail.approve_date || '—' }}</b></div>
            </div>
            <div class="stb-flow">
              <div class="stb-flow-step" :class="{ done: stepDone('草稿') }"><div class="stb-flow-dot">✓</div><div class="stb-flow-label">起草</div></div>
              <div class="stb-flow-line"></div>
              <div class="stb-flow-step" :class="{ done: stepDone('待QA审核') }"><div class="stb-flow-dot">2</div><div class="stb-flow-label">审核</div></div>
              <div class="stb-flow-line"></div>
              <div class="stb-flow-step" :class="{ done: stepDone('已批准') }"><div class="stb-flow-dot">3</div><div class="stb-flow-label">批准</div></div>
            </div>
            <div class="stb-notice" v-if="detail.proposed_validity_basis">
              外推依据：{{ detail.proposed_validity_basis }}
            </div>
            <div class="page-actions" style="margin-top: 14px" v-if="detail">
              <a-button v-if="can('save_report_draft') && detail.status === '草稿'" size="small"
                        @click="draftOpen = true">编辑报告内容</a-button>
              <a-button v-if="can('submit_report') && detail.status === '草稿'" size="small" type="primary"
                        @click="runAction('提交报告', () => submitReport(detail!.name))">提交</a-button>
              <a-button v-if="can('review_report') && detail.status === '待QA审核'" size="small"
                        @click="runAction('审核报告', () => reviewReport(detail!.name))">审核</a-button>
              <a-button v-if="can('approve_report') && detail.status === '待QA审核'" size="small" type="primary"
                        @click="approveOpen = true">批准（定有效期）</a-button>
              <a-button v-if="can('reject_report') && detail.status === '待QA审核'" size="small" danger
                        @click="askReason('驳回报告', 'reject')">驳回</a-button>
              <a-button v-if="can('void_report') && (detail.status === '草稿' || detail.status === '已批准')" size="small" danger
                        @click="askReason('作废报告', 'void')">作废</a-button>
            </div>
          </div>
          <a-empty v-else-if="!detailLoading" description="从左侧选择报告" style="padding: 40px 0" />
        </a-spin>
      </div>

      <!-- 有效期外推助手 -->
      <div class="panel" style="margin-bottom: 0">
        <div class="panel-head">
          <div>
            <div class="panel-title">有效期外推助手</div>
            <div class="panel-sub">只提供建议，不自动确定有效期</div>
          </div>
          <span class="pill pill-warn">建议态</span>
        </div>
        <div class="panel-body">
          <div class="stb-form-grid" style="padding: 0">
            <div class="stb-form-field">
              <label>产品</label>
              <a-select v-model:value="adviceProduct" :options="productOptions" style="width: 100%" @change="loadAdvice" />
            </div>
          </div>
          <div class="stb-assistant">
            <template v-if="advice.advised_months">
              <h3>建议 {{ advice.advised_months }} 个月</h3>
              <p>{{ advice.branch }}</p>
              <div class="stb-notice amber" style="margin-top: 10px">依据：{{ advice.basis }}</div>
            </template>
            <template v-else>
              <p>选择产品后展示 ICH Q1E 简化外推建议。外推助手只给建议区间，QA 判定与报告批准为独立动作。</p>
            </template>
            <div class="page-actions" style="margin-top: 12px">
              <router-link to="/stability/results"><a-button size="small">查看趋势</a-button></router-link>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 新建报告 -->
    <a-drawer v-model:open="createOpen" title="新建稳定性报告" :width="560" placement="right">
      <div class="stb-form-grid">
        <div class="stb-form-field">
          <label>报告类型 *</label>
          <a-select v-model:value="createForm.report_type" :options="typeOptions.slice(1)" style="width: 100%" />
        </div>
        <div class="stb-form-field">
          <label>产品 *</label>
          <a-select v-model:value="createForm.stability_product" :options="productOptions" style="width: 100%" show-search />
        </div>
        <div class="stb-form-field">
          <label>年度</label>
          <a-input v-model:value="createForm.year" placeholder="2026" />
        </div>
        <div class="stb-form-field">
          <label>来源单据类型</label>
          <a-select v-model:value="createForm.source_doctype" :options="sourceTypeOptions" style="width: 100%" allow-clear />
        </div>
        <div class="stb-form-field">
          <label>来源单据编号</label>
          <a-input v-model:value="createForm.source_name" placeholder="HBOS-STB-..." />
        </div>
        <div class="stb-form-field full">
          <label>研究范围</label>
          <a-input v-model:value="createForm.study_scope" />
        </div>
        <div class="stb-form-field">
          <label>周期起</label>
          <a-input v-model:value="createForm.period_from" placeholder="YYYY-MM-DD" />
        </div>
        <div class="stb-form-field">
          <label>周期止</label>
          <a-input v-model:value="createForm.period_to" placeholder="YYYY-MM-DD" />
        </div>
      </div>
      <div class="stb-notice">
        非专项报告不得填写客户；专项（客户要求）报告须在 Frappe Desk 由有权限角色补充客户 Link。
        外推建议由服务端在建档时计算写入。
      </div>
      <template #footer>
        <a-button @click="createOpen = false">取消</a-button>
        <a-button type="primary" :loading="busy" @click="submitCreate">建档</a-button>
      </template>
    </a-drawer>

    <!-- 批准（QA 判定有效期） -->
    <a-modal v-model:open="approveOpen" title="批准报告（QA 判定有效期）" :confirm-loading="busy" @ok="confirmApprove">
      <div class="stb-form-grid">
        <div class="stb-form-field">
          <label>有效期月数 *</label>
          <a-input v-model:value="approveForm.months" placeholder="24" />
        </div>
        <div class="stb-form-field">
          <label>有效期至 *</label>
          <a-input v-model:value="approveForm.date" placeholder="YYYY-MM-DD" />
        </div>
        <div class="stb-form-field full">
          <label>类型 *</label>
          <a-select v-model:value="approveForm.type" :options="[{ value: '有效期', label: '有效期' }, { value: '复检期', label: '复检期' }]" style="width: 100%" />
        </div>
      </div>
      <div class="stb-notice amber">批准即确定有效期；须先完成审核且审核人 ≠ 批准人（SoD，后端硬校验）。</div>
    </a-modal>

    <!-- 草稿内容编辑（评价与结论 / 趋势分析 / 杂质概况 / 趋势图引用） -->
    <a-modal v-model:open="draftOpen" title="编辑报告内容（草稿）" :confirm-loading="busy" width="640px" @ok="saveDraft">
      <div class="stb-form-field full">
        <label>评价与结论 *</label>
        <a-textarea v-model:value="draftForm.conclusion" :rows="4" placeholder="提交报告的前置必填项（方案 4.6.4）" />
      </div>
      <div class="stb-form-field full" style="margin-top: 10px">
        <label>趋势分析</label>
        <a-textarea v-model:value="draftForm.trend_analysis" :rows="3" />
      </div>
      <div class="stb-form-field full" style="margin-top: 10px">
        <label>杂质概况分析</label>
        <a-textarea v-model:value="draftForm.impurity_profile" :rows="3" />
      </div>
      <div class="stb-form-field full" style="margin-top: 10px">
        <label>趋势图引用</label>
        <a-input v-model:value="draftForm.trend_chart_ref" />
      </div>
      <div class="stb-notice">仅「草稿」可修改；保存后即可提交（方案 8.6：报告对 LIMS 角色只读，须经业务服务写入）。</div>
    </a-modal>

    <!-- 原因弹窗 -->
    <a-modal v-model:open="reasonOpen" :title="reasonTitle" :confirm-loading="busy" @ok="confirmReason">
      <a-textarea v-model:value="reasonText" :rows="3" placeholder="原因必填" />
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { Empty, message } from 'ant-design-vue'
import { FileTextOutlined } from '@ant-design/icons-vue'
import StbGateBanner from '@/components/stability/StbGateBanner.vue'
import { useAuthStore } from '@/stores/auth'
import {
  approveReport, canAction, createReport, products, rejectReport, reportDetail, reports,
  reviewReport, saveReportDraft, submitReport, voidReport, validityAdvice,
  type ReportRow, type ReportDetail, type ProductRow,
} from '@/api/stability'
import { toneClass } from '@/demo/stabilityDemo'

const auth = useAuthStore()
const can = (action: string): boolean => canAction(auth.user?.roles, action)

const loading = ref(false)
const detailLoading = ref(false)
const rows = ref<ReportRow[]>([])
const selected = ref<ReportRow | null>(null)
const detail = ref<ReportDetail | null>(null)

const keyword = ref('')
const typeFilter = ref<string | undefined>(undefined)
const statusFilter = ref<string | undefined>(undefined)

const typeOptions = [
  { value: '年度趋势分析报告', label: '年度趋势分析报告' },
  { value: '工艺验证稳定性报告', label: '工艺验证稳定性报告' },
  { value: '专项（客户要求）', label: '专项（客户要求）' },
  { value: 'APQR 年度稳定性汇总', label: 'APQR 年度稳定性汇总' },
]
const sourceTypeOptions = [
  { value: 'HBOS Stability Notice', label: '考察通知单' },
  { value: 'HBOS Stability Protocol', label: '稳定性方案' },
  { value: 'HBOS Stability Sample', label: '稳定性样品' },
]
const statusOptions = ['草稿', '待QA审核', '已批准', '已驳回', '已作废'].map((v) => ({ value: v, label: v }))

const filteredRows = computed(() => {
  const kw = keyword.value.trim().toLowerCase()
  if (!kw) return rows.value
  return rows.value.filter((r) =>
    r.name.toLowerCase().includes(kw) || (r.product_name || r.stability_product).toLowerCase().includes(kw))
})

const productRows = ref<ProductRow[]>([])
const productOptions = computed(() =>
  productRows.value.map((p) => ({ value: p.name, label: `${p.product_name}（${p.product_code}）` })))

const adviceProduct = ref('')
const advice = ref<Record<string, any>>({})

async function load() {
  loading.value = true
  try {
    const res = await reports({
      report_type: typeFilter.value, status: statusFilter.value,
      keyword: keyword.value.trim() || undefined,
    })
    rows.value = res.rows
    if (!selected.value && rows.value.length) void openReport(rows.value[0])
  } finally {
    loading.value = false
  }
}

async function loadAdvice() {
  if (!adviceProduct.value) return
  try {
    advice.value = (await validityAdvice(adviceProduct.value)) as Record<string, any>
  } catch {
    advice.value = {}
  }
}

async function openReport(r: ReportRow) {
  selected.value = r
  detailLoading.value = true
  try {
    detail.value = await reportDetail(r.name)
    fillDraftForm()
  } finally {
    detailLoading.value = false
  }
}

// 草稿内容（评价与结论等四项在建档时不收，须经 save_report_draft 写入）
const draftOpen = ref(false)
const draftForm = reactive({
  conclusion: '',
  trend_analysis: '',
  impurity_profile: '',
  trend_chart_ref: '',
})
function fillDraftForm() {
  const d = detail.value
  draftForm.conclusion = d?.conclusion || ''
  draftForm.trend_analysis = d?.trend_analysis || ''
  draftForm.impurity_profile = d?.impurity_profile || ''
  draftForm.trend_chart_ref = d?.trend_chart_ref || ''
}
async function saveDraft() {
  const d = detail.value
  if (!d) return
  if (!draftForm.conclusion.trim()) { message.warning('评价与结论必填（提交报告的前置）'); return }
  await runAction('保存报告内容', async () => {
    await saveReportDraft(d.name, {
      conclusion: draftForm.conclusion,
      trendAnalysis: draftForm.trend_analysis,
      impurityProfile: draftForm.impurity_profile,
      trendChartRef: draftForm.trend_chart_ref,
    })
    draftOpen.value = false
    await openReport({ name: d.name } as ReportRow)
  })
}

function stepDone(status: string): boolean {
  const order = ['草稿', '待QA审核', '已批准']
  if (!detail.value) return false
  return order.indexOf(detail.value.status) >= order.indexOf(status)
}

function statusTone(status: string): 'pass' | 'warn' | 'muted' {
  if (status === '已批准') return 'pass'
  if (status === '已驳回' || status === '已作废') return 'muted'
  return 'warn'
}

const createOpen = ref(false)
const createForm = reactive({
  report_type: '年度趋势分析报告',
  stability_product: '',
  year: '',
  source_doctype: undefined as string | undefined,
  source_name: '',
  study_scope: '',
  period_from: '',
  period_to: '',
})
async function submitCreate() {
  if (!createForm.stability_product) { message.warning('请选择产品'); return }
  await runAction('建档', async () => {
    const res = await createReport({
      report_type: createForm.report_type,
      stability_product: createForm.stability_product,
      year: createForm.year ? Number(createForm.year) : undefined,
      source_doctype: createForm.source_doctype,
      source_name: createForm.source_name || undefined,
      study_scope: createForm.study_scope || undefined,
      period_from: createForm.period_from || undefined,
      period_to: createForm.period_to || undefined,
    })
    message.info(`外推建议 ${res.advised_months ?? '—'} 个月`)
    createOpen.value = false
    await load()
  })
}

const approveOpen = ref(false)
const approveForm = reactive({ months: '', date: '', type: '有效期' })
async function confirmApprove() {
  const d = detail.value
  if (!d) return
  const months = Number(approveForm.months)
  if (!months || months <= 0) { message.warning('有效期月数必须大于 0'); return }
  if (!approveForm.date.trim()) { message.warning('有效期至必填'); return }
  await runAction('批准报告', async () => {
    await approveReport(d.name, {
      finalValidityMonths: months,
      finalValidityDate: approveForm.date.trim(),
      finalValidityType: approveForm.type,
    })
    approveOpen.value = false
    await openReport({ name: d.name } as ReportRow)
  })
}

const reasonOpen = ref(false)
const reasonTitle = ref('')
const reasonText = ref('')
const reasonKind = ref<'reject' | 'void'>('reject')
function askReason(title: string, kind: 'reject' | 'void') {
  reasonTitle.value = title
  reasonKind.value = kind
  reasonText.value = ''
  reasonOpen.value = true
}
async function confirmReason() {
  const d = detail.value
  if (!d) return
  if (!reasonText.value.trim()) { message.warning('原因必填'); return }
  await runAction(reasonTitle.value, async () => {
    if (reasonKind.value === 'reject') await rejectReport(d.name, reasonText.value.trim())
    else await voidReport(d.name, reasonText.value.trim())
  })
  await openReport({ name: d.name } as ReportRow)
}

const busy = ref(false)
async function runAction(label: string, fn: () => Promise<unknown>) {
  busy.value = true
  try {
    await fn()
    message.success(`${label}已完成`)
  } catch {
    // 错误由 client 拦截层弹出
  } finally {
    busy.value = false
  }
}

onMounted(async () => {
  void auth.checkSession()
  await load()
  const prods = await products()
  productRows.value = prods.rows
  if (prods.rows.length && !adviceProduct.value) {
    adviceProduct.value = prods.rows[0].name
    void loadAdvice()
  }
})
</script>

<style scoped>
.stb-gate-sub { font-size: 12px; color: var(--muted); margin-bottom: 12px; }
</style>
