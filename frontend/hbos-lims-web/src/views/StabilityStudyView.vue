<template>
  <div class="page">
    <StbGateBanner
      mode="live"
      note="通知单、方案与主数据均来自 hb_lims_app 稳定性业务服务（R8A）；按钮显隐按会话角色，实际准入由后端硬校验。"
    />

    <div class="page-head">
      <div>
        <h1>考察申请与方案</h1>
        <p class="page-desc">通知单、方案、批次、储存条件和重点考察项目</p>
      </div>
      <div class="page-actions">
        <a-button :disabled="!can('create_notice')" @click="noticeRef?.show()">
          <template #icon><PlusOutlined /></template>
          新建通知
        </a-button>
      </div>
    </div>

    <div class="stb-subnav">
      <button v-for="t in TABS" :key="t.key" :class="{ active: tab === t.key }" @click="switchTab(t.key)">
        {{ t.label }}
      </button>
    </div>

    <!-- ============ 通知单 ============ -->
    <div v-if="tab === 'notice'" class="stb-split">
      <div class="stb-list-panel">
        <div class="stb-list-panel-head">
          <b>考察通知</b>
          <span class="stb-list-count">共 {{ noticeRows.length }} 条</span>
        </div>
        <div class="stb-list-filter">
          <a-input v-model:value="keyword" placeholder="搜索通知单 / 产品" allow-clear @press-enter="loadNotices" />
          <a-select
            v-model:value="statusFilter"
            :options="noticeStatusOptions"
            style="width: 150px"
            @change="loadNotices"
          />
        </div>
        <a-spin :spinning="loadingNotices">
          <div
            v-for="n in noticeRows"
            :key="n.name"
            class="stb-list-row"
            :class="{ active: noticeDetail?.name === n.name }"
            @click="selectNotice(n.name)"
          >
            <div class="stb-list-row-top">
              <span class="stb-list-row-title mono">{{ n.name }}</span>
              <span :class="toneClass(statusTone(n.status))">{{ n.status }}</span>
            </div>
            <div class="stb-list-row-sub">
              {{ n.product_name || n.stability_product }} · {{ n.category || '—' }}<br />
              {{ n.conditions_count }} 个条件 · 申请 {{ n.apply_date || '—' }}
            </div>
          </div>
          <a-empty
            v-if="!loadingNotices && !noticeRows.length"
            description="无匹配通知单"
            :image="Empty.PRESENTED_IMAGE_SIMPLE"
            style="padding: 20px 0"
          />
        </a-spin>
      </div>

      <div class="stb-detail-panel">
        <template v-if="noticeDetail">
          <div class="stb-detail-head">
            <div>
              <h2 class="mono">{{ noticeDetail.name }}</h2>
              <p>{{ noticeDetail.product_name }} · 稳定性考察申请通知单</p>
            </div>
            <div class="page-actions">
              <a-button size="small" @click="auditRef?.show(noticeDetail.name)">审计</a-button>
            </div>
          </div>

          <div class="stb-detail-body">
            <div class="stb-flow">
              <template v-for="(f, i) in noticeFlow" :key="f.label">
                <div class="stb-flow-step" :class="f.state">
                  <div class="stb-flow-dot">{{ f.state === 'done' ? '✓' : i + 1 }}</div>
                  <div class="stb-flow-label">{{ f.label }}</div>
                </div>
                <div v-if="i < noticeFlow.length - 1" class="stb-flow-line"></div>
              </template>
            </div>

            <div class="stb-kv-grid">
              <div class="stb-kv"><label>考察分类</label><b>{{ noticeDetail.category || '—' }}</b></div>
              <div class="stb-kv"><label>剂型</label><b>{{ noticeDetail.dosage_form || '—' }}</b></div>
              <div class="stb-kv"><label>条件数</label><b>{{ noticeDetail.conditions_count }}</b></div>
              <div class="stb-kv"><label>批次</label><b>{{ noticeDetail.batches.length }} 批</b></div>
              <div class="stb-kv"><label>用量</label><b class="mono">{{ noticeDetail.qty ?? '—' }} {{ noticeDetail.qty_uom || '' }}</b></div>
              <div class="stb-kv"><label>包装</label><b>{{ noticeDetail.pack_desc || '—' }}</b></div>
              <div class="stb-kv"><label>申请人</label><b>{{ noticeDetail.signoff.qa_applicant || '—' }}</b></div>
              <div class="stb-kv"><label>批准人</label><b>{{ noticeDetail.signoff.approver_by || '—' }}</b></div>
            </div>

            <div class="panel" style="box-shadow: none">
              <div class="panel-head">
                <div>
                  <div class="panel-title">考察原因与条件</div>
                  <div class="panel-sub">{{ noticeDetail.study_reason }}</div>
                </div>
              </div>
              <div class="panel-body no-pad">
                <a-table
                  :columns="conditionColumns"
                  :data-source="noticeDetail.study_conditions"
                  size="small"
                  row-key="storage_cond"
                  :pagination="false"
                >
                  <template #bodyCell="{ column, record }">
                    <template v-if="column.key === 'type'"><span class="pill pill-info">{{ record.condition_type }}</span></template>
                    <template v-else-if="column.key === 'cond'"><span class="mono">{{ record.storage_cond }}</span></template>
                  </template>
                </a-table>
              </div>
            </div>

            <div class="panel" style="box-shadow: none">
              <div class="panel-head">
                <div>
                  <div class="panel-title">冻结快照</div>
                  <div class="panel-sub">批准后只读，变更通过新版本或变更实施入口完成</div>
                </div>
                <span :class="noticeDetail.snapshot.frozen ? 'pill pill-pass' : 'pill pill-muted'">
                  {{ noticeDetail.snapshot.frozen ? '已冻结' : '未冻结' }}
                </span>
              </div>
              <div class="panel-body">
                <div class="stb-kv-grid">
                  <div class="stb-kv"><label>质量标准</label><b class="mono">{{ noticeDetail.snapshot.spec_ref || '—' }}</b></div>
                  <div class="stb-kv"><label>标准版本</label><b class="mono">{{ noticeDetail.snapshot.spec_version || '—' }}</b></div>
                  <div class="stb-kv"><label>方法版本</label><b class="mono">{{ noticeDetail.snapshot.method_version || '—' }}</b></div>
                  <div class="stb-kv"><label>有效期快照</label><b>{{ noticeDetail.snapshot.vd_months_snapshot ?? '—' }} 月</b></div>
                </div>
                <div v-if="noticeDetail.extra_condition_reason" class="stb-notice" style="margin-top: 12px">
                  补充原因：{{ noticeDetail.extra_condition_reason }}
                  <span v-if="noticeDetail.register_review_by" class="dim">
                    · 已由 {{ noticeDetail.register_review_by }} 于 {{ noticeDetail.register_review_date }} 复核
                  </span>
                </div>
              </div>
            </div>

            <div class="panel" style="box-shadow: none">
              <div class="panel-head">
                <div>
                  <div class="panel-title">可执行动作</div>
                  <div class="panel-sub">{{ SOD_NOTE }}</div>
                </div>
              </div>
              <div class="panel-body">
                <a-space wrap>
                  <a-button
                    v-for="a in noticeActions"
                    :key="a.action"
                    :type="a.primary ? 'primary' : 'default'"
                    :danger="a.danger"
                    size="small"
                    @click="runNoticeAction(a)"
                  >
                    {{ a.label }}
                  </a-button>
                  <span v-if="!noticeActions.length" class="dim">当前状态 / 角色下无可执行动作</span>
                </a-space>
              </div>
            </div>

            <div v-if="noticeDetail.protocols.length" class="panel" style="box-shadow: none">
              <div class="panel-head">
                <div>
                  <div class="panel-title">关联方案</div>
                  <div class="panel-sub">该通知单下的稳定性方案</div>
                </div>
              </div>
              <div class="panel-body no-pad">
                <a-table
                  :columns="protocolColumns"
                  :data-source="noticeDetail.protocols"
                  size="small"
                  row-key="name"
                  :pagination="false"
                >
                  <template #bodyCell="{ column, record }">
                    <template v-if="column.key === 'name'">
                      <a class="mono" @click="protocolRef?.showDetail(record.name)">{{ record.name }}</a>
                    </template>
                    <template v-else-if="column.key === 'status'">
                      <span :class="toneClass(statusTone(record.status))">{{ record.status }}</span>
                    </template>
                  </template>
                </a-table>
              </div>
            </div>
          </div>
        </template>
        <a-empty v-else description="从左侧选择一份考察通知查看" style="padding: 48px 0" />
      </div>
    </div>

    <!-- ============ 稳定性方案 ============ -->
    <div v-else-if="tab === 'protocol'" class="panel">
      <div class="panel-head">
        <div>
          <div class="panel-title">稳定性方案</div>
          <div class="panel-sub">方案从「已批准」的通知单起草；批准后快照冻结</div>
        </div>
        <a-button size="small" @click="loadProtocols">刷新</a-button>
      </div>
      <div class="panel-body no-pad">
        <a-table
          :columns="protocolColumns"
          :data-source="protocolRows"
          size="small"
          row-key="name"
          :loading="loadingProtocols"
          :scroll="{ x: 900 }"
        >
          <template #bodyCell="{ column, record }">
            <template v-if="column.key === 'name'">
              <a class="mono" @click="protocolRef?.showDetail(record.name)">{{ record.name }}</a>
              <div class="dim mono">v{{ record.version }}</div>
            </template>
            <template v-else-if="column.key === 'product'">
              <div class="stb-cell-strong">{{ record.product_name || '—' }}</div>
              <div class="dim mono">{{ record.notice }}</div>
            </template>
            <template v-else-if="column.key === 'status'">
              <span :class="toneClass(statusTone(record.status))">{{ record.status }}</span>
            </template>
            <template v-else-if="column.key === 'actions'">
              <a-space wrap>
                <a-button
                  v-for="a in protocolActions(record)"
                  :key="a.action"
                  size="small"
                  :type="a.primary ? 'primary' : 'default'"
                  :danger="a.danger"
                  @click="runProtocolAction(a, record)"
                >
                  {{ a.label }}
                </a-button>
                <span v-if="!protocolActions(record).length" class="dim">—</span>
              </a-space>
            </template>
          </template>
        </a-table>
        <a-empty
          v-if="!loadingProtocols && !protocolRows.length"
          description="暂无稳定性方案"
          :image="Empty.PRESENTED_IMAGE_SIMPLE"
          style="padding: 40px 0"
        />
      </div>
    </div>

    <!-- ============ 产品规则 ============ -->
    <div v-else-if="tab === 'product'" class="panel">
      <div class="panel-head">
        <div>
          <div class="panel-title">稳定性产品</div>
          <div class="panel-sub">建档时可选的已启用产品（停用改用 is_active=0）</div>
        </div>
      </div>
      <div class="panel-body no-pad">
        <a-table
          :columns="productColumns"
          :data-source="productRows"
          size="small"
          row-key="name"
          :loading="loadingProducts"
          :scroll="{ x: 900 }"
        >
          <template #bodyCell="{ column, record }">
            <template v-if="column.key === 'product'">
              <div class="stb-cell-strong">{{ record.product_name }}</div>
              <div class="dim mono">{{ record.product_code }}</div>
            </template>
            <template v-else-if="column.key === 'cond'">
              <span class="dim mono">{{ record.storage_cond_long || '—' }}</span>
            </template>
          </template>
        </a-table>
      </div>
    </div>

    <!-- ============ 条件与项目 ============ -->
    <div v-else class="grid-2">
      <div class="panel">
        <div class="panel-head">
          <div>
            <div class="panel-title">储存条件</div>
            <div class="panel-sub">HBOS Stability Condition</div>
          </div>
        </div>
        <div class="panel-body no-pad">
          <a-table
            :columns="conditionMasterColumns"
            :data-source="conditionRows"
            size="small"
            row-key="name"
            :loading="loadingMaster"
            :pagination="false"
          >
            <template #bodyCell="{ column, record }">
              <template v-if="column.key === 'type'"><span class="pill pill-info">{{ record.condition_type }}</span></template>
              <template v-else-if="column.key === 'range'">
                <span class="mono">{{ record.temp_min }}~{{ record.temp_max }} ℃ / {{ record.humidity_min }}~{{ record.humidity_max }} %RH</span>
              </template>
            </template>
          </a-table>
        </div>
      </div>
      <div class="panel">
        <div class="panel-head">
          <div>
            <div class="panel-title">检验项目</div>
            <div class="panel-sub">HBOS Stability Test Item（含显著变化判定规则与业务项目映射）</div>
          </div>
        </div>
        <div class="panel-body no-pad">
          <a-table
            :columns="itemMasterColumns"
            :data-source="itemRows"
            size="small"
            row-key="name"
            :loading="loadingMaster"
            :pagination="false"
          >
            <template #bodyCell="{ column, record }">
              <template v-if="column.key === 'key'">
                <span :class="record.is_key_item ? 'pill pill-pass' : 'pill pill-muted'">
                  {{ record.is_key_item ? '重点' : '一般' }}
                </span>
              </template>
              <template v-else-if="column.key === 'rule'">
                <span class="dim">{{ record.significant_change_rule }}</span>
              </template>
              <template v-else-if="column.key === 'mapping'">
                <span :class="record.base_test_item ? 'mono' : 'pill pill-warn'">
                  {{ record.base_test_item || '未配置' }}
                </span>
              </template>
              <template v-else-if="column.key === 'actions'">
                <a-button
                  v-if="can('manage_stability_master')"
                  size="small"
                  type="link"
                  @click="openMapping(record)"
                >
                  维护映射
                </a-button>
                <span v-else class="dim">—</span>
              </template>
            </template>
          </a-table>
        </div>
      </div>
    </div>

    <StbNoticeDrawer ref="noticeRef" @created="onNoticeCreated" />
    <StbAuditDrawer ref="auditRef" />
    <StbProtocolDrawer ref="protocolRef" @created="onProtocolCreated" />

    <a-modal
      v-model:open="reasonOpen"
      :title="reasonTitle"
      :confirm-loading="reasonSaving"
      @ok="confirmReason"
    >
      <a-textarea v-model:value="reasonText" :rows="3" placeholder="请填写原因（必填）" />
    </a-modal>

    <a-modal
      v-model:open="mappingOpen"
      title="维护业务检验项目映射"
      :confirm-loading="mappingSaving"
      @ok="saveMapping"
    >
      <div v-if="mappingItem" class="stb-kv-grid" style="grid-template-columns: repeat(2, minmax(0, 1fr)); margin-bottom: 14px">
        <div class="stb-kv"><label>稳定性项目</label><b>{{ mappingItem.item_name || mappingItem.name }}</b></div>
        <div class="stb-kv"><label>项目编码</label><b class="mono">{{ mappingItem.item_code || mappingItem.name }}</b></div>
      </div>
      <a-select
        v-model:value="mappingBase"
        :options="mappingOptions"
        allow-clear
        show-search
        style="width: 100%"
        placeholder="请选择业务检验项目"
        option-filter-prop="label"
      />
      <div class="dim" style="margin-top: 8px">一个业务检验项目只能映射一个稳定性项目；已产生稳定性结果的项目不可修改映射。</div>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { Empty, message } from 'ant-design-vue'
import { PlusOutlined } from '@ant-design/icons-vue'
import StbGateBanner from '@/components/stability/StbGateBanner.vue'
import StbNoticeDrawer from '@/components/stability/StbNoticeDrawer.vue'
import StbAuditDrawer from '@/components/stability/StbAuditDrawer.vue'
import StbProtocolDrawer from '@/components/stability/StbProtocolDrawer.vue'
import { useAuthStore } from '@/stores/auth'
import {
  SOD_NOTE, approveNotice, approveProtocol, cancelNotice, canAction, closeNotice,
  confirmNoticeQc, master, noticeDetail as fetchNoticeDetail, notices,
  products, protocols, registerReview,
  rejectNotice, rejectProtocol, reviewProtocol, submitNotice, submitProtocol, voidProtocol,
  updateStabilityTestItemMapping,
  type MasterRow, type NoticeDetail, type NoticeRow, type ProductRow, type ProtocolRow,
} from '@/api/stability'

const auth = useAuthStore()
const can = (action: string): boolean => canAction(auth.user?.roles, action)

const TABS = [
  { key: 'notice', label: '通知单' },
  { key: 'protocol', label: '稳定性方案' },
  { key: 'product', label: '产品规则' },
  { key: 'condition', label: '条件与项目' },
] as const

const tab = ref<(typeof TABS)[number]['key']>('notice')
const noticeRef = ref<InstanceType<typeof StbNoticeDrawer> | null>(null)
const auditRef = ref<InstanceType<typeof StbAuditDrawer> | null>(null)
const protocolRef = ref<InstanceType<typeof StbProtocolDrawer> | null>(null)

const noticeRows = ref<NoticeRow[]>([])
const noticeDetail = ref<NoticeDetail | null>(null)
const keyword = ref('')
const statusFilter = ref<string | undefined>(undefined)
const loadingNotices = ref(false)

const protocolRows = ref<ProtocolRow[]>([])
const loadingProtocols = ref(false)

const productRows = ref<ProductRow[]>([])
const loadingProducts = ref(false)

const conditionRows = ref<MasterRow[]>([])
const itemRows = ref<MasterRow[]>([])
const baseItemRows = ref<MasterRow[]>([])
const loadingMaster = ref(false)
const mappingOpen = ref(false)
const mappingSaving = ref(false)
const mappingItem = ref<MasterRow | null>(null)
const mappingBase = ref<string | undefined>(undefined)
const mappingOptions = computed(() => baseItemRows.value.map((row) => ({
  value: row.name,
  label: `${String(row.item_name || row.name)} · ${String(row.item_code || row.name)}`,
})))

// ---- 状态语义 ----
function statusTone(status: string): 'pass' | 'warn' | 'danger' | 'info' | 'muted' {
  if (status === '已批准') return 'pass'
  if (status === '已驳回' || status === '已作废') return 'danger'
  if (status === '待QC经理确认' || status === '待批准' || status === '待QA审核') return 'warn'
  if (status === '草稿') return 'info'
  return 'muted'
}
function toneClass(tone: ReturnType<typeof statusTone>): string {
  return `pill pill-${tone}`
}

const noticeStatusOptions = ['全部状态', '草稿', '待QC经理确认', '待批准', '已批准', '已驳回', '已关闭', '已取消']
  .map((v) => ({ value: v, label: v }))

const conditionColumns = [
  { title: '条件类型', key: 'type', width: 150 },
  { title: '储存条件', key: 'cond', width: 220 },
  { title: '备注', dataIndex: 'remark', key: 'remark' },
]
const protocolColumns = [
  { title: '方案', key: 'name', width: 200 },
  { title: '产品 / 通知单', key: 'product', width: 220 },
  { title: '状态', key: 'status', width: 110 },
  { title: '生效日', dataIndex: 'effective_date', key: 'effective_date', width: 110 },
  { title: '动作', key: 'actions', width: 260 },
]
const productColumns = [
  { title: '产品', key: 'product', width: 200 },
  { title: '考察分类', dataIndex: 'category', key: 'category', width: 170 },
  { title: '剂型', dataIndex: 'dosage_form', key: 'dosage_form', width: 110 },
  { title: '单位', dataIndex: 'default_uom', key: 'uom', width: 80 },
  { title: '有效期(月)', dataIndex: 'vd_months', key: 'vd_months', width: 100 },
  { title: '长期条件', key: 'cond', width: 200 },
]
const conditionMasterColumns = [
  { title: '编码', dataIndex: 'condition_code', key: 'code', width: 150 },
  { title: '类型', key: 'type', width: 130 },
  { title: '温湿度区间', key: 'range' },
]
const itemMasterColumns = [
  { title: '编码', dataIndex: 'item_code', key: 'code', width: 140 },
  { title: '名称', dataIndex: 'item_name', key: 'name', width: 120 },
  { title: '等级', key: 'key', width: 80 },
  { title: '显著变化规则', key: 'rule', width: 180 },
  { title: '关联业务项目', key: 'mapping', width: 180 },
  { title: '操作', key: 'actions', width: 100 },
]

// ---- 通知单状态机步骤 ----
const NOTICE_STEPS = ['草稿', '待QC经理确认', '待批准', '已批准', '已关闭']
const noticeFlow = computed(() => {
  const cur = noticeDetail.value?.status || ''
  const terminal = ['已驳回', '已取消']
  const idx = NOTICE_STEPS.indexOf(cur)
  return NOTICE_STEPS.map((label, i) => ({
    label,
    state: terminal.includes(cur)
      ? (i === 0 ? 'done' : 'todo')
      : (i < idx ? 'done' : i === idx ? 'current' : 'todo'),
  }))
})

// ---- 动作矩阵（状态 × 角色；实际准入仍由后端 _check_action + SoD 判定） ----
interface UiAction {
  action: string
  label: string
  primary?: boolean
  danger?: boolean
  needReason?: boolean
}

const noticeActions = computed<UiAction[]>(() => {
  const d = noticeDetail.value
  if (!d) return []
  const all: UiAction[] = []
  const push = (a: UiAction) => { if (can(a.action)) all.push(a) }

  if (d.status === '草稿') {
    if (d.conditions_count > 2 && !d.register_review_by) {
      push({ action: 'register_review', label: '注册人员复核' })
    }
    // 条件 >2 时后端强制要求已复核，前端同样先拦住
    if (!(d.conditions_count > 2 && !d.register_review_by)) {
      push({ action: 'submit_notice', label: '提交', primary: true })
    }
    push({ action: 'cancel_notice', label: '取消', danger: true, needReason: false })
  } else if (d.status === '待QC经理确认') {
    push({ action: 'confirm_notice_qc', label: 'QC 经理确认', primary: true })
    push({ action: 'reject_notice', label: '驳回', danger: true, needReason: true })
  } else if (d.status === '待批准') {
    push({ action: 'approve_notice', label: '批准', primary: true })
    push({ action: 'reject_notice', label: '驳回', danger: true, needReason: true })
  } else if (d.status === '已批准') {
    if (can('submit_protocol')) push({ action: 'create_protocol', label: '起草方案', primary: true })
    push({ action: 'close_notice', label: '关闭' })
  }
  return all
})

function protocolActions(row: ProtocolRow): UiAction[] {
  const all: UiAction[] = []
  const push = (a: UiAction) => { if (can(a.action)) all.push(a) }
  if (row.status === '草稿') {
    push({ action: 'submit_protocol', label: '提交', primary: true })
    push({ action: 'void_protocol', label: '作废', danger: true, needReason: true })
  } else if (row.status === '待QA审核') {
    if (!row.qa_review_by) push({ action: 'review_protocol', label: '记录审核' })
    push({ action: 'approve_protocol', label: '批准', primary: true })
    push({ action: 'reject_protocol', label: '驳回', danger: true, needReason: true })
  } else if (row.status === '已批准') {
    push({ action: 'void_protocol', label: '作废', danger: true, needReason: true })
  }
  return all
}

// ---- 原因弹窗 ----
const reasonOpen = ref(false)
const reasonTitle = ref('')
const reasonText = ref('')
const reasonSaving = ref(false)
let pendingAction: (() => Promise<unknown>) | null = null

function askReason(title: string, run: () => Promise<unknown>) {
  reasonTitle.value = title
  reasonText.value = ''
  pendingAction = run
  reasonOpen.value = true
}

async function confirmReason() {
  if (!reasonText.value.trim()) return message.warning('原因必填')
  reasonSaving.value = true
  try {
    await pendingAction?.()
    reasonOpen.value = false
    message.success('操作已完成')
    await Promise.all([loadNotices(), loadProtocols()])
    if (noticeDetail.value) await selectNotice(noticeDetail.value.name)
  } catch {
    // 具体错误已由 client 拦截层弹出
  } finally {
    reasonSaving.value = false
    pendingAction = null
  }
}

// ---- 动作执行 ----
async function afterActionSuccess() {
  message.success('操作已完成')
  await Promise.all([loadNotices(), loadProtocols()])
  if (noticeDetail.value) await selectNotice(noticeDetail.value.name)
}

async function runNoticeAction(a: UiAction) {
  const d = noticeDetail.value
  if (!d) return

  if (a.action === 'create_protocol') {
    protocolRef.value?.showCreate(d)
    return
  }
  const runners: Record<string, () => Promise<unknown>> = {
    register_review: () => registerReview(d.name),
    submit_notice: () => submitNotice(d.name),
    confirm_notice_qc: () => confirmNoticeQc(d.name),
    approve_notice: () => approveNotice(d.name),
    close_notice: () => closeNotice(d.name),
    cancel_notice: () => cancelNotice(d.name, reasonText.value || undefined),
    reject_notice: () => rejectNotice(d.name, reasonText.value.trim()),
  }
  const run = runners[a.action]
  if (!run) return
  if (a.needReason) {
    askReason(`${a.label} · ${d.name}`, run)
    return
  }
  try {
    await run()
    await afterActionSuccess()
  } catch {
    // 具体错误已由 client 拦截层弹出（含 SoD / 越权 / 状态机）
  }
}

async function runProtocolAction(a: UiAction, row: ProtocolRow) {
  const runners: Record<string, () => Promise<unknown>> = {
    submit_protocol: () => submitProtocol(row.name),
    review_protocol: () => reviewProtocol(row.name),
    approve_protocol: () => approveProtocol(row.name),
    reject_protocol: () => rejectProtocol(row.name, reasonText.value.trim()),
    void_protocol: () => voidProtocol(row.name, reasonText.value.trim()),
  }
  const run = runners[a.action]
  if (!run) return
  if (a.needReason) {
    askReason(`${a.label} · ${row.name}`, run)
    return
  }
  try {
    await run()
    await afterActionSuccess()
  } catch {
    // 具体错误已由 client 拦截层弹出
  }
}

// ---- 数据加载 ----
async function loadNotices() {
  loadingNotices.value = true
  try {
    const status = statusFilter.value === '全部状态' ? undefined : statusFilter.value
    const res = await notices({ keyword: keyword.value.trim() || undefined, status, limit: 200 })
    noticeRows.value = res.rows
    if (!noticeDetail.value && res.rows.length) await selectNotice(res.rows[0].name)
  } catch {
    if (!auth.user) message.warning('未登录（Guest）：通知单不可用，请先在 Frappe Desk 登录后刷新。')
    else if (!auth.user?.roles?.length) message.warning('当前会话尚未取到角色，列表加载可能受限。')
    else message.error('加载通知单列表失败')
  } finally {
    loadingNotices.value = false
  }
}

async function selectNotice(name: string) {
  try {
    noticeDetail.value = await fetchNoticeDetail(name)
  } catch {
    // 具体错误已由 client 拦截层弹出
  }
}

async function loadProtocols() {
  loadingProtocols.value = true
  try {
    const res = await protocols({ limit: 200 })
    protocolRows.value = res.rows
  } catch {
    // 具体错误已由 client 拦截层弹出
  } finally {
    loadingProtocols.value = false
  }
}

async function loadProducts() {
  loadingProducts.value = true
  try {
    productRows.value = (await products()).rows
  } catch {
    // 具体错误已由 client 拦截层弹出
  } finally {
    loadingProducts.value = false
  }
}

async function loadMaster() {
  loadingMaster.value = true
  try {
    const [c, i, b] = await Promise.all([
      master('HBOS Stability Condition'),
      master('HBOS Stability Test Item'),
      master('HBOS Test Item'),
    ])
    conditionRows.value = c.rows
    itemRows.value = i.rows
    baseItemRows.value = b.rows
  } catch {
    // 具体错误已由 client 拦截层弹出
  } finally {
    loadingMaster.value = false
  }
}

function openMapping(row: MasterRow) {
  mappingItem.value = row
  mappingBase.value = typeof row.base_test_item === 'string' ? row.base_test_item : undefined
  mappingOpen.value = true
}

async function saveMapping() {
  if (!mappingItem.value) return
  mappingSaving.value = true
  try {
    await updateStabilityTestItemMapping(mappingItem.value.name, mappingBase.value)
    mappingOpen.value = false
    message.success('业务检验项目映射已保存')
    await loadMaster()
  } catch {
    // 具体错误已由 client 拦截层弹出
  } finally {
    mappingSaving.value = false
  }
}

function switchTab(key: (typeof TABS)[number]['key']) {
  tab.value = key
  if (key === 'notice') void loadNotices()
  if (key === 'protocol') void loadProtocols()
  if (key === 'product') void loadProducts()
  if (key === 'condition') void loadMaster()
}

async function onNoticeCreated(name: string) {
  await loadNotices()
  await selectNotice(name)
}

async function onProtocolCreated(name: string) {
  await loadProtocols()
  protocolRef.value?.showDetail(name)
  await loadNotices()
  if (noticeDetail.value) await selectNotice(noticeDetail.value.name)
}

onMounted(() => {
  void auth.checkSession()
  void loadNotices()
})
</script>

<style scoped>
.stb-list-filter {
  display: flex;
  gap: 8px;
  padding: 10px;
  border-bottom: 1px solid var(--line);
  flex-wrap: wrap;
}
.stb-cell-strong { color: var(--ink); font-weight: 700; }
.stb-kv-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 10px; }
.stb-flow-step.todo .stb-flow-dot { background: var(--line); color: var(--muted); }
.stb-flow-step.current .stb-flow-dot { background: var(--primary); color: #fff; }
@media (max-width: 900px) {
  .stb-kv-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}
</style>
