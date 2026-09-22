<template>
  <div class="page">
    <a-alert
      type="info"
      show-icon
      class="mode-bar"
      message="真实数据模式：已连接 hb_lims_app retention_service——处理申请、QC/QA/QM 逐级审批（4/5 级）、销毁双签与续留改期均写入真实数据库，审批受 SoD 硬校验约束。"
    />

    <div class="page-head">
      <div>
        <h1>处理申请</h1>
        <p class="page-desc">季度到期清单 · QC/QA/QM 审批链 · 销毁双签与续留改期</p>
      </div>
      <div class="page-actions">
        <a-button :loading="loading" @click="reload()">
          <template #icon><ReloadOutlined /></template>
          刷新
        </a-button>
        <a-button type="primary" @click="openCreate()">
          <template #icon><PlusOutlined /></template>
          新建处理申请
        </a-button>
      </div>
    </div>
    <a-alert
      v-if="targetDisposalName"
      :type="targetDisposalMissing ? 'warning' : 'info'"
      show-icon
      :message="targetDisposalMissing ? `来源处理申请 ${targetDisposalName} 未找到` : `已定位处理申请 ${targetDisposalName}`"
      style="margin-bottom: 12px"
    />

    <!-- 季度到期处理清单（非完结处理单投影） -->
    <div class="panel">
      <div class="panel-head">
        <div>
          <div class="panel-title">季度到期处理清单</div>
          <div class="panel-sub">
            到期 / 在途处理单（草稿 · 审批中 · 待执行 · 待续留）· 销毁超期按 deadline 派生（后端无该状态）
          </div>
        </div>
        <div class="panel-filter">
          <span class="pill pill-warn">临期 {{ quarterCounts.lin }}</span>
          <span class="pill pill-primary">待执行 {{ quarterCounts.ready }}</span>
          <span class="pill pill-danger">销毁超期 {{ quarterCounts.overdue }}</span>
        </div>
      </div>
      <div class="panel-body no-pad">
        <a-table
          :columns="quarterColumns"
          :data-source="quarterRows"
          :loading="loading"
          :pagination="false"
          size="small"
          row-key="name"
          :scroll="{ x: 1060 }"
          :custom-row="customRow"
        >
          <template #bodyCell="{ column, record }">
            <template v-if="column.key === 'name'">
              <span class="mono">{{ record.name }}</span>
            </template>
            <template v-else-if="column.key === 'sample'">
              <div class="ret-main">{{ record.product }} <span class="dim">/ {{ record.batch }}</span></div>
            </template>
            <template v-else-if="column.key === 'type'">
              {{ record.type }}
            </template>
            <template v-else-if="column.key === 'level'">
              {{ record.qa_manager_required ? '5 级' : '4 级·跳过' }}
            </template>
            <template v-else-if="column.key === 'deadline'">
              <span class="mono" :class="{ 'danger-text': isOverdue(record) }">{{ record.deadline || '—' }}</span>
            </template>
            <template v-else-if="column.key === 'status'">
              <div>
                <span class="pill" :class="displayStatus(record).cls">{{ displayStatus(record).text }}</span>
                <div v-if="displayStatus(record).note" class="pill-note danger-text">{{ displayStatus(record).note }}</div>
              </div>
            </template>
            <template v-else-if="column.key === 'action'">
              <a-button type="link" size="small" @click.stop="selectRow(record)">{{ rowActionLabel(record) }}</a-button>
            </template>
          </template>
        </a-table>
        <a-empty
          v-if="!quarterRows.length && !loading"
          description="当前无到期 / 在途处理单"
          :image="Empty.PRESENTED_IMAGE_SIMPLE"
          style="padding: 24px 0"
        />
      </div>
    </div>

    <div ref="layoutRef" class="detail-layout">
      <!-- 左：处理申请列表 -->
      <div class="panel list-panel">
        <div class="panel-head">
          <div>
            <div class="panel-title">处理申请列表</div>
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
            :loading="loading"
            :pagination="false"
            size="small"
            row-key="name"
            :scroll="{ x: 900 }"
            :row-class-name="rowClassName"
            :custom-row="customRow"
          >
            <template #bodyCell="{ column, record }">
              <template v-if="column.key === 'order'">
                <span class="mono">{{ record.name }}</span>
              </template>
              <template v-else-if="column.key === 'retention'">
                <div class="ret-main">{{ record.product }} <span class="dim">/ {{ record.batch }}</span></div>
                <div class="ret-sub mono">{{ record.retention_name }}</div>
              </template>
              <template v-else-if="column.key === 'type'">
                {{ record.type }}
              </template>
              <template v-else-if="column.key === 'level'">
                {{ record.qa_manager_required ? '5 级' : '4 级·跳过' }}
              </template>
              <template v-else-if="column.key === 'deadline'">
                <span class="mono" :class="{ 'danger-text': isOverdue(record) }">{{ record.deadline || '—' }}</span>
              </template>
              <template v-else-if="column.key === 'status'">
                <span class="pill" :class="displayStatus(record).cls">{{ displayStatus(record).text }}</span>
              </template>
              <template v-else-if="column.key === 'action'">
                <a-button type="link" size="small" @click.stop="selectRow(record)">{{ rowActionLabel(record) }}</a-button>
              </template>
            </template>
          </a-table>
          <a-empty
            v-if="!filteredRows.length && !loading"
            description="当前筛选无处理申请"
            :image="Empty.PRESENTED_IMAGE_SIMPLE"
            style="padding: 24px 0"
          />
        </div>
      </div>

      <!-- 右：审批详情 -->
      <div class="panel detail-panel">
        <div class="panel-head">
          <div>
            <div class="panel-title">审批详情</div>
            <div class="panel-sub mono">{{ selected ? selected.name : '未选择' }}</div>
          </div>
        </div>
        <div class="panel-body">
          <a-empty v-if="!selected" description="从左侧选择一份处理申请查看" :image="Empty.PRESENTED_IMAGE_SIMPLE" />
          <template v-else>
            <div class="hero">
              <div>
                <div class="hero-title">{{ selected.product }} <span class="dim">/ {{ selected.batch }}</span></div>
                <div class="hero-sub">留样编号 <span class="mono">{{ selected.retention_name }}</span></div>
                <div class="hero-sub">
                  处理量 <span class="num">{{ selected.qty }}</span> {{ selected.uom }}
                  · 结存 <span class="num">{{ selected.current_qty }}</span> {{ selected.uom }}
                  · 预占 <span class="num">{{ selected.reserved_qty }}</span>
                </div>
              </div>
              <div>
                <span class="pill" :class="displayStatus(selected).cls">{{ displayStatus(selected).text }}</span>
                <div v-if="displayStatus(selected).note" class="pill-note danger-text" style="text-align: right">
                  {{ displayStatus(selected).note }}
                </div>
              </div>
            </div>

            <div class="divider"></div>

            <div class="section-label">处理要求</div>
            <div class="field">
              <label>处理类型 / 原因</label>
              <div class="static">{{ selected.type }} · {{ selected.reason || '—' }}</div>
            </div>
            <div class="field">
              <label>方式 / 地点</label>
              <div class="static">{{ selected.method || '—' }} · {{ selected.location || '—' }}</div>
            </div>
            <div class="field">
              <label>申请人 / 申请日期</label>
              <div class="static">{{ selected.applicant || '—' }}（{{ selected.applicant_date || '—' }}）</div>
            </div>
            <div v-if="selected.type !== DSP_CONTINUE && selected.deadline" class="field">
              <label>处理 deadline</label>
              <div class="static" :class="{ 'danger-text': isOverdue(selected) }">
                QM 批准 {{ (selected.qm_approved_at || '').slice(0, 10) || '—' }} + 3 个月 → {{ selected.deadline }}
              </div>
            </div>
            <div v-if="selected.type === DSP_CONTINUE && selected.new_retention_due_date" class="field">
              <label>新留样期至</label>
              <div class="static mono">{{ selected.new_retention_due_date }}</div>
            </div>
            <div v-if="isOverdue(selected)" class="soe red">
              <ExclamationCircleOutlined style="margin-right: 6px" />
              销毁 deadline（{{ selected.deadline }}）已过 {{ -dayDiff(selected.deadline || '') }} 天，请 Manager 立即决策：督导销毁双签或取消。
            </div>

            <div class="section-label">
              审批链 · {{ selected.qa_manager_required ? '5 级' : '4 级（跳过 QA 负责人）' }}
            </div>
            <div class="chain">
              <template v-for="(st, idx) in selectedChain" :key="st.key">
                <div
                  class="step"
                  :class="{ done: st.state === 'done', active: st.state === 'active', skipped: st.state === 'skipped' }"
                >
                  <span class="dot">{{ st.dot }}</span>
                  <div>
                    <div class="step-name">{{ st.label }}</div>
                    <div class="step-who">{{ st.who }}</div>
                  </div>
                </div>
                <span v-if="idx < selectedChain.length - 1" class="chain-arrow">→</span>
              </template>
            </div>

            <!-- 销毁 / 其他：待执行双签 -->
            <template v-if="selected.type !== DSP_CONTINUE && selected.status === '待执行'">
              <div class="section-label">执行双签（双签齐备自动出库）</div>
              <div class="dual">
                <div class="field">
                  <label>处理人（Analyst / Manager）</label>
                  <div v-if="!selected.disposal_by">
                    <a-button
                      v-if="can('disposal_handler')"
                      size="small"
                      type="primary"
                      :loading="signing"
                      @click="sign('handler')"
                    >处理人签名</a-button>
                    <div v-else class="dim">待签名</div>
                  </div>
                  <div v-else class="static">{{ selected.disposal_by }}</div>
                </div>
                <div class="field">
                  <label>监督人（QA / Manager）</label>
                  <div v-if="!selected.monitor_by">
                    <a-button
                      v-if="can('disposal_monitor')"
                      size="small"
                      type="primary"
                      :loading="signing"
                      @click="sign('monitor')"
                    >监督人签名</a-button>
                    <div v-else class="dim">待签名 · 需 QA 角色</div>
                  </div>
                  <div v-else class="static">{{ selected.monitor_by }}</div>
                </div>
              </div>
              <div class="soe">
                <ExclamationCircleOutlined style="margin-right: 6px" />
                双签完成后系统自动写入销毁出库流水并置「已完成」；deadline 为 QM 批准日 + 3 个月，须在此期限内完成。
              </div>
            </template>

            <!-- 续留：执行改期 -->
            <template v-else-if="selected.type === DSP_CONTINUE && (selected.status === '已批准' || selected.status === '待执行')">
              <div class="section-label">续留执行</div>
              <div class="field">
                <label>新留样期至（QM 已批准）</label>
                <div class="static mono">{{ selected.new_retention_due_date || '—' }}</div>
              </div>
              <div class="soe">
                <ExclamationCircleOutlined style="margin-right: 6px" />
                续留将把留样期至回写为 {{ selected.new_retention_due_date || '—' }} 并恢复样品状态，无需 QA 监督双签。
              </div>
              <a-button
                v-if="can('disposal_handler')"
                type="primary"
                :loading="signing"
                @click="sign('continue')"
              >续留执行</a-button>
              <div v-else class="dim">续留执行需 Analyst / Manager 角色。</div>
            </template>

            <!-- 已完成：静态双签落位 -->
            <template v-else-if="selected.status === '已完成'">
              <div class="section-label">{{ selected.type === DSP_CONTINUE ? '续留执行' : '销毁双签' }}</div>
              <div class="dual">
                <div class="field">
                  <label>{{ selected.type === DSP_CONTINUE ? '执行人' : '处理人' }}</label>
                  <div class="static">{{ selected.disposal_by || '—' }}</div>
                </div>
                <div v-if="selected.type !== DSP_CONTINUE" class="field">
                  <label>监督人（QA）</label>
                  <div class="static">{{ selected.monitor_by || '—' }}</div>
                </div>
              </div>
            </template>

            <div class="soe red">{{ SOD_NOTE }}</div>

            <div v-if="detailActions.length" class="detail-actions">
              <a-button
                v-for="b in detailActions"
                :key="b.key"
                :type="b.primary ? 'primary' : 'default'"
                :danger="b.danger"
                :loading="acting && b.key === actingKey"
                @click="runDetail(b.key)"
              >
                <template #icon v-if="b.danger"><CloseCircleOutlined /></template>
                {{ b.label }}
              </a-button>
            </div>
            <div v-else-if="noActionHint" class="dim" style="margin-top: 10px">当前状态与您的角色下无可用审批 / 执行操作，仅查看。</div>
          </template>
        </div>
      </div>
    </div>

    <!-- 新建处理申请 -->
    <a-modal
      v-model:open="createOpen"
      title="新建处理申请"
      ok-text="创建并提交"
      cancel-text="取消"
      width="640"
      :confirm-loading="creating"
      @ok="confirmCreate"
    >
      <a-form layout="vertical">
        <a-form-item label="留样批次" required>
          <a-select
            v-model:value="createForm.retention_name"
            placeholder="选择留样（在库 / 部分使用）"
            show-search
            option-filter-prop="label"
            :options="createOptions"
            @change="onPickCandidate"
          />
          <div v-if="!createOptions.length" class="dim" style="margin-top: 6px">当前无可用留样批次。</div>
        </a-form-item>
        <template v-if="pickedCandidate">
          <div class="field">
            <label>批次信息（只读带出）</label>
            <div class="static">
              {{ createForm.product }} · 批号 {{ createForm.batch }} · 状态 {{ createForm.status }}
            </div>
          </div>
          <div class="dim" style="margin: -2px 0 12px">
            结存 {{ pickedCandidate.current_qty }} {{ pickedCandidate.qty_uom }}
            · 预占 {{ pickedCandidate.reserved_qty }} · 可用 {{ pickedCandidate.available_qty }} {{ pickedCandidate.qty_uom }}
          </div>
        </template>
        <a-form-item label="处理类型" required>
          <a-select v-model:value="createForm.disposal_type" :options="typeOptions" />
          <div v-if="createForm.disposal_type === DSP_DESTROY" class="dim" style="margin-top: 6px">
            销毁申请 QM 批准后按批准日 + 3 个月生成销毁 deadline，留样进入「待处理」直至双签出库。
          </div>
          <div v-if="createForm.disposal_type === DSP_CONTINUE" class="dim" style="margin-top: 6px">
            续留申请 QM 批准后回写留样期至，无需销毁双签。
          </div>
        </a-form-item>
        <a-row :gutter="12">
          <a-col :span="12">
            <a-form-item label="数量" required>
              <a-input-number
                v-model:value="createForm.qty"
                :min="1"
                :disabled="!pickedCandidate"
                style="width: 100%"
                placeholder="默认取该留样结存"
              />
            </a-form-item>
          </a-col>
          <a-col :span="12">
            <a-form-item label="UOM（只读）">
              <div class="static-readonly">{{ pickedCandidate ? pickedCandidate.qty_uom : '—' }}</div>
            </a-form-item>
          </a-col>
        </a-row>
        <a-form-item label="审批层级">
          <div class="level-row">
            <a-switch v-model:checked="createForm.qa_manager_required" size="small" />
            <span>{{ createForm.qa_manager_required ? '5 级（含 QA 负责人审核）' : '4 级（跳过 QA 负责人）' }}</span>
          </div>
        </a-form-item>
        <a-form-item label="原因" required>
          <a-textarea v-model:value="createForm.reason" :rows="2" placeholder="必填：处理原因（如留样期届满按规程处理）" />
        </a-form-item>
        <a-row :gutter="12">
          <a-col :span="12">
            <a-form-item label="方式" required>
              <a-input v-model:value="createForm.disposal_method" placeholder="如高温焚烧" />
            </a-form-item>
          </a-col>
          <a-col :span="12">
            <a-form-item label="地点" required>
              <a-input v-model:value="createForm.disposal_location" placeholder="如危废暂存间（QA 现场监督）" />
            </a-form-item>
          </a-col>
        </a-row>
        <template v-if="createForm.disposal_type === DSP_CONTINUE">
          <a-form-item label="新留样期至" required>
            <a-date-picker
              v-model:value="createForm.new_retention_due_date"
              value-format="YYYY-MM-DD"
              style="width: 100%"
            />
          </a-form-item>
        </template>
      </a-form>
    </a-modal>

    <!-- 驳回 -->
    <a-modal
      v-model:open="rejectOpen"
      title="驳回处理申请"
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
        placeholder="驳回原因（必填，将写入审计）"
      />
      <div class="soe red" style="margin: 12px 0 0">驳回后申请终止，留样不进入待处理、按原状留存，可重新发起处理申请。</div>
    </a-modal>

    <!-- Manager 取消逃生口 -->
    <a-modal
      v-model:open="cancelOpen"
      title="Manager 取消（逃生口）"
      ok-text="确认取消"
      cancel-text="返回"
      :ok-button-props="{ danger: true }"
      width="460"
      @ok="confirmCancel"
    >
      <p style="margin-bottom: 12px">
        取消 <span class="mono">{{ selected ? selected.name : '' }}</span>
        {{ selected ? `（当前状态 ${selected.status}）` : '' }}，请填写原因。
      </p>
      <a-textarea
        v-model:value="cancelReason"
        :rows="3"
        placeholder="取消原因（必填，将写入审计）"
      />
      <div class="soe red" style="margin: 12px 0 0">
        待执行取消将按进入处理前的状态快照恢复留样（草稿 / 审批中取消不改动留样）。
      </div>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, reactive, ref } from 'vue'
import { message, Empty } from 'ant-design-vue'
import type { TableColumnsType } from 'ant-design-vue'
import {
  CloseCircleOutlined, ExclamationCircleOutlined, PlusOutlined, ReloadOutlined,
} from '@ant-design/icons-vue'
import { useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { readScalarQuery } from '@/features/todos/todoModel'
import {
  disposalList,
  createDisposalApply,
  submitDisposalApply,
  approveDisposal,
  rejectDisposal,
  cancelDisposalApply,
  disposalHandle,
  disposalMonitor,
  continueRetention,
  retentionCandidates,
  canAction,
  SOD_NOTE,
  type DisposalRow,
  type RetentionCandidate,
} from '@/api/retention'

const DSP_DESTROY = '留样期满销毁'
const DSP_CONTINUE = '留样期满继续留样'

// ---------- 日期工具 ----------
function pad(n: number): string {
  return String(n).padStart(2, '0')
}
function localToday(): string {
  const d = new Date()
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
}
function dayDiff(dateStr: string): number {
  const now = new Date()
  now.setHours(0, 0, 0, 0)
  const t = new Date(`${dateStr}T00:00:00`).getTime()
  return Math.round((t - now.getTime()) / 86400_000)
}

// ---------- 角色 ----------
const auth = useAuthStore()
const roles = computed(() => auth.user?.roles ?? [])
function can(action: string): boolean {
  return canAction(roles.value, action)
}

// ---------- 列表数据（真实后端） ----------
const loading = ref(false)
const rows = ref<DisposalRow[]>([])
const selected = ref<DisposalRow | null>(null)
const filter = ref<'all' | 'mine' | 'overdue'>('all')
const targetDisposalName = ref('')
const targetDisposalMissing = ref(false)

type FilterKey = 'all' | 'mine' | 'overdue'
const TERMINAL = ['已完成', '已驳回', '已取消']

function isTerminal(d: DisposalRow): boolean {
  return TERMINAL.includes(d.status)
}
function isOverdue(d: DisposalRow): boolean {
  if (d.type === DSP_CONTINUE || !d.deadline) return false
  if (isTerminal(d)) return false
  return d.deadline < localToday()
}
const isDestroyClass = (d: DisposalRow): boolean => d.type !== DSP_CONTINUE

// 当前状态所需的审批动作键（与后端 _DSP_APPROVE_MAP / ACTION_ROLES 对齐）
function approvalKey(d: DisposalRow): string {
  if (d.status === '草稿') return 'create_disposal_apply'
  switch (d.status) {
    case '待QC主管审核':
    case '待QC负责人审核':
      return 'disposal_qc'
    case '待QA审核':
    case '待QA负责人审核':
      return 'disposal_qa'
    case '待QM批准':
      return 'disposal_qm'
    default:
      return ''
  }
}

// 执行/续留阶段我还可做的动作：'' | 'handler' | 'monitor' | 'continue'
function execKeyFor(d: DisposalRow): string {
  if (d.type === DSP_CONTINUE && (d.status === '已批准' || d.status === '待执行')) {
    return can('disposal_handler') ? 'continue' : ''
  }
  if (isDestroyClass(d) && d.status === '待执行') {
    if (!d.disposal_by && can('disposal_handler')) return 'handler'
    if (!d.monitor_by && can('disposal_monitor')) return 'monitor'
  }
  return ''
}

const mineRows = computed<DisposalRow[]>(() =>
  rows.value.filter((d) => {
    const ak = approvalKey(d)
    if (ak && can(ak)) return true
    return execKeyFor(d).length > 0
  }),
)
const overdueRows = computed<DisposalRow[]>(() => rows.value.filter((d) => isOverdue(d)))

const listSub = computed(() => `共 ${rows.value.length} 份处理单 · 待我处理 ${mineRows.value.length} 份`)
const filterChips = computed<{ key: FilterKey; label: string }[]>(() => [
  { key: 'all', label: '全部' },
  { key: 'mine', label: `待我处理 ${mineRows.value.length}` },
  { key: 'overdue', label: `超期 ${overdueRows.value.length}` },
])

const filteredRows = computed<DisposalRow[]>(() => {
  if (filter.value === 'all') return rows.value
  if (filter.value === 'overdue') return overdueRows.value
  return mineRows.value
})

const columns: TableColumnsType<DisposalRow> = [
  { title: '处理单号', key: 'order', width: 190 },
  { title: '留样 / 批号', key: 'retention', width: 235 },
  { title: '类型', key: 'type', width: 155 },
  { title: '层级', key: 'level', width: 100 },
  { title: 'deadline', key: 'deadline', width: 110 },
  { title: '状态', key: 'status', width: 130 },
  { title: '操作', key: 'action', width: 110 },
]

// ---------- 季度到期处理清单（非完结单投影） ----------
const IN_FLIGHT = ['待QC主管审核', '待QC负责人审核', '待QA审核', '待QA负责人审核', '待QM批准']

const quarterRows = computed<DisposalRow[]>(() =>
  rows.value
    .filter((d) => !isTerminal(d))
    .slice()
    .sort((a, b) => (isOverdue(b) ? 1 : 0) - (isOverdue(a) ? 1 : 0)),
)
const quarterCounts = computed(() => ({
  lin: quarterRows.value.filter((d) => IN_FLIGHT.includes(d.status)).length,
  ready: quarterRows.value.filter(
    (d) => d.status === '待执行' || (d.status === '已批准' && d.type === DSP_CONTINUE),
  ).length,
  overdue: quarterRows.value.filter((d) => isOverdue(d)).length,
}))

const quarterColumns: TableColumnsType<DisposalRow> = [
  { title: '处理单号', key: 'name', width: 200 },
  { title: '产品 / 批号', key: 'sample', width: 215 },
  { title: '类型', key: 'type', width: 160 },
  { title: '层级', key: 'level', width: 115 },
  { title: 'deadline', key: 'deadline', width: 115 },
  { title: '状态', key: 'status', width: 165 },
  { title: '操作', key: 'action', width: 120 },
]

// ---------- 状态展示 ----------
function statusPillClass(s: string): string {
  if (s === '已完成') return 'pill-pass'
  if (s === '已批准') return 'pill-primary'
  if (s === '草稿' || s === '已驳回' || s === '已取消') return 'pill-muted'
  return 'pill-warn'
}
function displayStatus(d: DisposalRow): { text: string; cls: string; note: string } {
  if (isOverdue(d)) {
    return { text: '销毁超期', cls: 'pill-danger', note: `deadline ${d.deadline} 已过 ${-dayDiff(d.deadline || '')} 天` }
  }
  return { text: d.status, cls: statusPillClass(d.status), note: '' }
}

function rowActionLabel(d: DisposalRow): string {
  const ak = approvalKey(d)
  if (ak && can(ak)) return d.status === '草稿' ? '提交' : '审批'
  const ek = execKeyFor(d)
  if (ek === 'handler') return '处理人签名'
  if (ek === 'monitor') return '监督人签名'
  if (ek === 'continue') return '续留执行'
  return '查看'
}

// ---------- 行选择与滚动 ----------
const layoutRef = ref<HTMLElement | null>(null)

function selectRow(d: DisposalRow) {
  selected.value = d
  layoutRef.value?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}
function customRow(record: DisposalRow) {
  return { onClick: () => selectRow(record), style: { cursor: 'pointer' } }
}
function rowClassName(record: DisposalRow): string {
  return selected.value && selected.value.name === record.name ? 'sel-row' : ''
}

// ---------- 审批链（真实签名位） ----------
interface ChainStep {
  key: string
  label: string
  who: string
  dot: string
  state: 'done' | 'active' | 'skipped' | 'todo'
}

const selectedChain = computed<ChainStep[]>(() => {
  const d = selected.value
  if (!d) return []
  const steps: ChainStep[] = []
  const add = (key: string, label: string, who: string, state: ChainStep['state'], dot: string) =>
    steps.push({ key, label, who, dot, state })
  const node = (key: string, label: string, sign: string | undefined, pending: string, seq: number) => {
    if (sign) {
      add(key, label, sign, 'done', '✓')
    } else if (d.status === pending) {
      add(key, label, '待签', 'active', String(seq))
    } else {
      add(key, label, '—', 'todo', String(seq))
    }
  }

  add('applicant', '申请人', d.applicant || '—', 'done', '✓')
  node('qc_supervisor', 'QC 主管', d.qc_supervisor_sign, '待QC主管审核', 2)
  node('qc_manager', 'QC 负责人', d.qc_manager_sign, '待QC负责人审核', 3)
  node('qa_review', 'QA 审核', d.qa_review_sign, '待QA审核', 4)
  if (d.qa_manager_required) {
    node('qa_manager', 'QA 负责人', d.qa_manager_sign, '待QA负责人审核', 5)
  } else {
    add('qa_manager', 'QA 负责人', '审批层跳过', 'skipped', '—')
  }
  node('qm', 'QM 批准', d.qm_sign, '待QM批准', d.qa_manager_required ? 6 : 5)
  return steps
})

// ---------- 详情动作（提交 / 逐级批准 / 驳回 / Manager 取消） ----------
interface DetailBtn { key: string; label: string; primary?: boolean; danger?: boolean }

const approveLabel: Record<string, string> = {
  待QC主管审核: 'QC 主管通过',
  待QC负责人审核: 'QC 负责人通过',
  待QA审核: 'QA 审核通过',
  待QA负责人审核: 'QA 负责人通过',
  待QM批准: 'QM 批准',
}

const detailActions = computed<DetailBtn[]>(() => {
  const d = selected.value
  if (!d) return []
  const list: DetailBtn[] = []
  const ak = approvalKey(d)
  if (ak && can(ak)) {
    if (d.status === '草稿') list.push({ key: 'approve', label: '提交审核', primary: true })
    else {
      list.push({ key: 'approve', label: approveLabel[d.status] ?? '通过', primary: true })
      list.push({ key: 'reject', label: '驳回', danger: true })
    }
  }
  if (!isTerminal(d) && can('disposal_cancel')) {
    list.push({ key: 'cancel', label: 'Manager 取消', danger: true })
  }
  return list
})

const noActionHint = computed(() => {
  const d = selected.value
  if (!d) return false
  return !detailActions.value.length && !execKeyFor(d)
})

const acting = ref(false)
const actingKey = ref('')
async function runDetail(key: string) {
  const d = selected.value
  if (!d) return
  if (key === 'approve') {
    acting.value = true
    actingKey.value = 'approve'
    try {
      const res = await approveDisposal(d.name)
      message.success(`${d.name} → ${res.status}`)
      await reload(d.name)
    } catch {
      /* 错误提示已由 client 拦截器给出 */
    } finally {
      acting.value = false
      actingKey.value = ''
    }
  } else if (key === 'reject') {
    rejectReason.value = ''
    rejectOpen.value = true
  } else if (key === 'cancel') {
    cancelReason.value = ''
    cancelOpen.value = true
  }
}

// ---------- 执行：销毁双签 / 续留执行 ----------
const signing = ref(false)
async function sign(kind: 'handler' | 'monitor' | 'continue') {
  const d = selected.value
  if (!d) return
  signing.value = true
  try {
    let res: { name: string; status: string }
    if (kind === 'handler') res = await disposalHandle(d.name)
    else if (kind === 'monitor') res = await disposalMonitor(d.name)
    else res = await continueRetention(d.name)
    if (res.status === '已完成') {
      message.success(`${res.name}：${kind === 'continue' ? '续留改期完成，留样期至已回写' : '双签齐备，已写入销毁出库流水'}`)
    } else {
      message.success(`${res.name} 已签署${kind === 'monitor' ? '（监督人）' : kind === 'handler' ? '（处理人）' : ''}，等待${kind === 'continue' ? '完成' : '另一方双签'}`)
    }
    await reload(d.name)
  } catch {
    /* 错误提示已由 client 拦截器给出 */
  } finally {
    signing.value = false
  }
}

// ---------- 驳回 / Manager 取消 ----------
const rejectOpen = ref(false)
const rejectReason = ref('')
async function confirmReject() {
  const d = selected.value
  if (!d) return
  if (!rejectReason.value.trim()) {
    message.warning('请填写驳回原因')
    return
  }
  acting.value = true
  actingKey.value = 'reject'
  try {
    await rejectDisposal(d.name, rejectReason.value.trim())
    message.info(`${d.name} 已驳回：留样按原状留存，可重新发起处理`)
    rejectOpen.value = false
    await reload(d.name)
  } catch {
    /* client 已提示 */
  } finally {
    acting.value = false
    actingKey.value = ''
  }
}

const cancelOpen = ref(false)
const cancelReason = ref('')
async function confirmCancel() {
  const d = selected.value
  if (!d) return
  if (!cancelReason.value.trim()) {
    message.warning('请填写取消原因')
    return
  }
  acting.value = true
  actingKey.value = 'cancel'
  try {
    await cancelDisposalApply(d.name, cancelReason.value.trim())
    message.success(`${d.name} 已取消${d.status === '待执行' ? '，并按进入处理前快照恢复留样' : ''}`)
    cancelOpen.value = false
    await reload(d.name)
  } catch {
    /* client 已提示 */
  } finally {
    acting.value = false
    actingKey.value = ''
  }
}

// ---------- 新建处理申请 ----------
const createOpen = ref(false)
const creating = ref(false)
const candidates = ref<RetentionCandidate[]>([])
const createForm = reactive({
  retention_name: undefined as string | undefined,
  disposal_type: DSP_DESTROY,
  product: '',
  batch: '',
  status: '',
  qty: undefined as number | undefined,
  qa_manager_required: true,
  reason: '',
  disposal_method: '',
  disposal_location: '',
  new_retention_due_date: undefined as string | undefined,
})

const typeOptions = [
  { value: DSP_DESTROY, label: DSP_DESTROY },
  { value: DSP_CONTINUE, label: DSP_CONTINUE },
  { value: '其他', label: '其他' },
]

const createOptions = computed(() =>
  candidates.value.map((c) => ({
    value: c.name,
    label: `${c.product_name} · 批 ${c.batch_no}（结存 ${c.current_qty} ${c.qty_uom} / 可用 ${c.available_qty} ${c.qty_uom}）`,
  })),
)

const pickedCandidate = computed<RetentionCandidate | undefined>(
  () => candidates.value.find((c) => c.name === createForm.retention_name),
)

function onPickCandidate() {
  const c = pickedCandidate.value
  createForm.product = c?.product_name ?? ''
  createForm.batch = c?.batch_no ?? ''
  createForm.status = c?.status ?? ''
  createForm.qty = c?.current_qty ?? undefined
}

async function openCreate() {
  Object.assign(createForm, {
    retention_name: undefined, disposal_type: DSP_DESTROY, product: '', batch: '', status: '',
    qty: undefined, qa_manager_required: true, reason: '',
    disposal_method: '', disposal_location: '', new_retention_due_date: undefined,
  })
  createOpen.value = true
  try {
    candidates.value = await retentionCandidates(['在库', '部分使用'])
  } catch {
    candidates.value = []
  }
}

async function confirmCreate() {
  const c = pickedCandidate.value
  if (!c) {
    message.error('请选择留样批次')
    return
  }
  const qty = createForm.qty
  if (!qty || qty <= 0) {
    message.error('数量须大于 0（默认取该留样结存）')
    return
  }
  if (c.available_qty <= 0) {
    message.error('该留样可用量为 0，不可发起处理')
    return
  }
  const destroyLike = createForm.disposal_type !== DSP_CONTINUE
  if (destroyLike && c.reserved_qty > 0) {
    message.error('该留样存在在途预占，不可发起销毁/其他类处理申请')
    return
  }
  if (destroyLike && qty !== c.current_qty) {
    message.error(`销毁/其他类处理数量必须等于当前结存（结存 ${c.current_qty} ${c.qty_uom}）`)
    return
  }
  if (qty > c.available_qty) {
    message.error(`数量超过可用量（可用 ${c.available_qty} ${c.qty_uom}）`)
    return
  }
  if (!createForm.reason.trim()) {
    message.error('请填写处理原因')
    return
  }
  if (!createForm.disposal_method.trim() || !createForm.disposal_location.trim()) {
    message.error('请填写处理方式与地点')
    return
  }
  if (createForm.disposal_type === DSP_CONTINUE && !createForm.new_retention_due_date) {
    message.error('续留类型必须填写新留样期至')
    return
  }
  creating.value = true
  try {
    const created = await createDisposalApply({
      retention_name: c.name,
      disposal_type: createForm.disposal_type,
      qty,
      reason: createForm.reason.trim(),
      disposal_method: createForm.disposal_method.trim(),
      disposal_location: createForm.disposal_location.trim(),
      qa_manager_required: createForm.qa_manager_required ? 1 : 0,
      new_retention_due_date: createForm.disposal_type === DSP_CONTINUE ? createForm.new_retention_due_date : undefined,
    })
    await submitDisposalApply(created.name)
    message.success(`处理申请 ${created.name} 已创建并提交审批`)
    createOpen.value = false
    filter.value = 'all'
    await reload(created.name)
  } catch {
    /* client 已提示 */
  } finally {
    creating.value = false
  }
}

// ---------- 载入与路由 focus ----------
async function reload(preferName?: string) {
  loading.value = true
  try {
    const res = await disposalList()
    rows.value = res.rows || []
    const keepName = preferName || selected.value?.name
    if (keepName) {
      selected.value = rows.value.find((r) => r.name === keepName) ?? selected.value
    } else {
      selected.value = null
    }
  } catch {
    /* client 已提示 */
  } finally {
    loading.value = false
  }
}

async function initialLoad() {
  await reload()
  targetDisposalName.value = readScalarQuery(route.query.disposal) || ''
  targetDisposalMissing.value = false
  const focusName = typeof route.query.focus === 'string' ? route.query.focus : ''
  const targetRow = targetDisposalName.value
    ? rows.value.find((r) => r.name === targetDisposalName.value)
    : undefined
  targetDisposalMissing.value = Boolean(targetDisposalName.value && !targetRow)
  const focusRow = (focusName ? rows.value.find((r) => r.name === focusName) : undefined) || targetRow
  selected.value = focusRow ?? mineRows.value[0] ?? rows.value[0] ?? null
  if (focusName && selected.value) {
    nextTick(() => layoutRef.value?.scrollIntoView({ behavior: 'smooth', block: 'start' }))
  }
}

const route = useRoute()
onMounted(initialLoad)
</script>

<style scoped>
.list-panel { min-width: 0; }
.detail-panel { min-width: 0; }
.ret-main { color: var(--ink); }
.ret-sub { font-size: 11px; color: var(--muted); margin-top: 2px; }

.mode-bar { margin-bottom: 14px; }

.hero { display: flex; align-items: flex-start; justify-content: space-between; gap: 10px; }
.hero-title { font-size: 15px; font-weight: 700; color: var(--ink); }
.hero-sub { font-size: 11px; color: var(--muted); margin-top: 3px; }

.level-row { display: flex; align-items: center; gap: 10px; }

.pill-note { font-size: 11px; margin-top: 2px; line-height: 1.4; }

.dual {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}
.dual .field { margin-bottom: 0; }

.detail-actions { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 4px; }
.static-readonly {
  background: var(--surface-2);
  border: 1px solid var(--line);
  border-radius: 6px;
  padding: 7px 10px;
  font-size: 12px;
  color: var(--ink);
}

:deep(.sel-row > td) {
  background: var(--primary-soft) !important;
}
</style>
