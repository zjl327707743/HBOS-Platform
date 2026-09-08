<template>
  <div class="page">
    <div class="page-head">
      <div>
        <h1>处理申请</h1>
        <p class="page-desc">季度到期清单 · QC/QA/QM 审批链 · 销毁双签与续留改期</p>
      </div>
      <div class="page-actions">
        <a-button @click="scrollToQuarter">
          <template #icon><CalendarOutlined /></template>
          季度清单
        </a-button>
        <a-button type="primary" @click="openCreate()">
          <template #icon><PlusOutlined /></template>
          新建处理申请
        </a-button>
      </div>
    </div>

    <DemoBar />

    <!-- 季度到期清单 -->
    <div ref="quarterRef" class="panel">
      <div class="panel-head">
        <div>
          <div class="panel-title">季度到期清单 · Q3 2026</div>
          <div class="panel-sub">留样期至 ≤ 2026-09-30 且未完成 · 以季度台账为准</div>
        </div>
        <div class="panel-filter">
          <span class="pill pill-warn">临期 {{ quarterCounts.lin }}</span>
          <span class="pill pill-primary">已批准待执行 {{ quarterCounts.ready }}</span>
          <span class="pill pill-danger">销毁超期 {{ quarterCounts.overdue }}</span>
        </div>
      </div>
      <div class="panel-body no-pad">
        <a-table
          :columns="quarterColumns"
          :data-source="quarterRows"
          :pagination="false"
          size="small"
          row-key="retentionName"
          :scroll="{ x: 900 }"
        >
          <template #bodyCell="{ column, record }">
            <template v-if="column.key === 'name'">
              <span class="mono">{{ record.retentionName }}</span>
            </template>
            <template v-else-if="column.key === 'sample'">
              <div class="ret-main">{{ record.product }} <span class="dim">/ {{ record.batch }}</span></div>
            </template>
            <template v-else-if="column.key === 'category'">
              {{ record.category }}
            </template>
            <template v-else-if="column.key === 'dueDate'">
              <span class="mono">{{ record.dueDate }}</span>
            </template>
            <template v-else-if="column.key === 'remain'">
              <span :class="record.remainDays < 0 ? 'danger-text' : 'dim'">
                {{ record.remainDays < 0 ? `超期 ${-record.remainDays} 天` : `${record.remainDays} 天` }}
              </span>
            </template>
            <template v-else-if="column.key === 'state'">
              <span class="pill" :class="quarterPillClass(record.state)">{{ record.state }}</span>
            </template>
            <template v-else-if="column.key === 'suggest'">
              <a-button
                v-if="quarterSuggestText(record)"
                type="link"
                size="small"
                @click.stop="onQuarterSuggest(record)"
              >{{ quarterSuggestText(record) }}</a-button>
              <span v-else class="dim">{{ record.suggestion || '—' }}</span>
            </template>
          </template>
        </a-table>
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
            :pagination="false"
            size="small"
            row-key="name"
            :scroll="{ x: 900 }"
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
              <template v-else-if="column.key === 'type'">
                {{ record.type }}
              </template>
              <template v-else-if="column.key === 'level'">
                {{ record.qaManagerRequired ? '5 级' : '4 级' }}
              </template>
              <template v-else-if="column.key === 'deadline'">
                <span class="mono" :class="{ 'danger-text': record.status === '销毁超期' }">
                  {{ record.deadline || '—' }}
                </span>
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
                <div class="hero-sub">留样编号 <span class="mono">{{ selected.retentionName }}</span></div>
                <div class="hero-sub">
                  销毁量 = 当前结存 <span class="num">{{ selected.currentQty }}</span> {{ selected.uom }}
                  · 预占 <span class="num">{{ selected.reservedQty }}</span>
                </div>
              </div>
              <span class="pill" :class="statusPillClass(selected.status)">{{ selected.status }}</span>
            </div>

            <div class="divider"></div>

            <div class="section-label">处理要求</div>
            <div class="field">
              <label>处理类型 / 原因</label>
              <div class="static">{{ selected.type }} · {{ selected.reason }}</div>
            </div>
            <div class="field">
              <label>方式 / 地点</label>
              <div class="static">{{ selected.method }} · {{ selected.location }}</div>
            </div>
            <div class="field">
              <label>申请人 / 日期</label>
              <div class="static">{{ selected.applicant }}（{{ selected.applicantDate }}）</div>
            </div>
            <div v-if="deadlineField(selected)" class="field">
              <label>销毁时限</label>
              <div class="static" :class="{ 'danger-text': selected.status === '销毁超期' }">
                {{ deadlineField(selected) }}
              </div>
            </div>
            <div v-if="selected.type === '期满续留' && selected.newDueDate" class="field">
              <label>新留样期至</label>
              <div class="static mono">{{ selected.newDueDate }}</div>
            </div>
            <div v-if="selected.status === '销毁超期'" class="soe red">
              <ExclamationCircleOutlined style="margin-right: 6px" />
              销毁 deadline（{{ selected.deadline }}）已过，请 Manager 立即决策：督导销毁或取消。
            </div>

            <div class="section-label">审批链 · {{ disposalLevelLabel(selected) }}</div>
            <div class="chain">
              <template v-for="(st, idx) in selectedChain" :key="st.key">
                <div
                  class="step"
                  :class="{ done: st.state === 'done', active: st.state === 'active', skipped: st.state === 'skipped' }"
                >
                  <span class="dot">
                    {{ st.state === 'done' ? '✓' : st.state === 'skipped' ? '—' : String(idx) }}
                  </span>
                  <div>
                    <div class="step-name">{{ st.label }}</div>
                    <div class="step-who">{{ st.who }}</div>
                  </div>
                </div>
                <span v-if="idx < selectedChain.length - 1" class="chain-arrow">→</span>
              </template>
            </div>

            <!-- 执行双签 / 续留双签 -->
            <template v-if="pendingExec(selected)">
              <div class="section-label">{{ selected.type === '期满销毁' ? '执行双签' : '续留双签' }}</div>
              <div class="dual">
                <div class="field">
                  <label>处理人</label>
                  <a-input v-model:value="execForm.handler" placeholder="默认检验员王敏" />
                </div>
                <div class="field">
                  <label>监督人（QA）</label>
                  <a-input v-model:value="execForm.supervisor" placeholder="默认 QA 刘洋" />
                </div>
              </div>
              <div v-if="selected.type === '期满续留'" class="field">
                <label>新留样期至</label>
                <a-date-picker
                  v-model:value="execForm.newDueDate"
                  value-format="YYYY-MM-DD"
                  style="width: 100%"
                />
              </div>
              <div v-if="selected.type === '期满销毁'" class="soe">
                <ExclamationCircleOutlined style="margin-right: 6px" />
                销毁 deadline：{{ selected.deadline || '—' }}，须在处理期限内由处理人执行、QA 现场监督，双签后写入销毁出库流水。
              </div>
              <div v-if="can(demo.role, 'disposal_execute')" class="detail-actions">
                <a-button type="primary" @click="doExecute">
                  {{ selected.type === '期满销毁' ? '完成销毁双签' : '完成续留双签' }}
                </a-button>
              </div>
              <div v-else class="dim" style="margin-top: 8px">当前演示身份不可执行，需检验员 / QA / Manager 完成双签。</div>
            </template>
            <template v-else-if="selected.status === '已销毁' || selected.status === '已完成续留'">
              <div class="section-label">执行双签</div>
              <div class="dual">
                <div class="field">
                  <label>处理人</label>
                  <div class="static">{{ selected.handler }}</div>
                </div>
                <div class="field">
                  <label>监督人（QA）</label>
                  <div class="static">{{ selected.supervisor }}</div>
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

    <!-- 新建处理申请 -->
    <a-modal
      v-model:open="createOpen"
      title="新建处理申请"
      ok-text="创建申请"
      cancel-text="取消"
      width="640"
      @ok="confirmCreate"
    >
      <a-form layout="vertical">
        <a-form-item label="留样批次" required>
          <a-select
            v-model:value="createForm.retentionName"
            placeholder="选择季度清单中临期 / 超期未处理留样"
            :options="createOptions"
            @change="onPickRetention"
          />
          <div v-if="!createOptions.length" class="dim" style="margin-top: 6px">当前无未发起处理申请的临期 / 超期留样。</div>
        </a-form-item>
        <template v-if="pickedQuarter">
          <div class="field">
            <label>留样信息（只读带出）</label>
            <div class="static">
              {{ createForm.product }} · {{ createForm.batch }} · 类别 {{ createForm.category }}
              · 留样期至 <span class="mono">{{ createForm.dueDate }}</span>
            </div>
          </div>
          <div class="dim" style="margin: -2px 0 12px">
            结存 {{ pickedStock ? `${pickedStock.currentQty} ${pickedStock.uom}` : '—' }}
            <template v-if="pickedStock">· 预占 {{ pickedStock.reservedQty }} {{ pickedStock.uom }}</template>
            <template v-else>（未匹配到处理单库存快照，数量请按台账填写）</template>
          </div>
        </template>
        <a-form-item label="处理类型" required>
          <a-radio-group v-model:value="createForm.type">
            <a-radio-button value="期满销毁">期满销毁</a-radio-button>
            <a-radio-button value="期满续留">期满续留</a-radio-button>
            <a-radio-button value="其他">其他</a-radio-button>
          </a-radio-group>
          <div v-if="createForm.type === '期满销毁'" class="dim" style="margin-top: 6px">
            销毁申请批准后按 QM 批准日 + 3 个月生成销毁 deadline。
          </div>
        </a-form-item>
        <a-row :gutter="12">
          <a-col :span="12">
            <a-form-item label="数量" required>
              <a-input-number
                v-model:value="createForm.qty"
                :min="1"
                style="width: 100%"
                :disabled="!pickedQuarter"
                placeholder="默认取该留样结存"
              />
            </a-form-item>
          </a-col>
          <a-col :span="12">
            <a-form-item label="UOM">
              <a-input v-model:value="createForm.uom" :disabled="!pickedQuarter" placeholder="如 g / 瓶" />
            </a-form-item>
          </a-col>
        </a-row>
        <a-form-item label="审批层级">
          <div class="level-row">
            <a-switch v-model:checked="createForm.qaManagerRequired" size="small" />
            <span>{{ createForm.qaManagerRequired ? '5 级（含 QA 负责人审核）' : '4 级（跳过 QA 负责人）' }}</span>
          </div>
        </a-form-item>
        <a-form-item label="原因" required>
          <a-textarea v-model:value="createForm.reason" :rows="2" placeholder="必填：处理原因（如留样期届满按规程处理）" />
        </a-form-item>
        <a-row :gutter="12">
          <a-col :span="12">
            <a-form-item label="方式" required>
              <a-input v-model:value="createForm.method" placeholder="如高温焚烧 / 延期续留" />
            </a-form-item>
          </a-col>
          <a-col :span="12">
            <a-form-item label="地点" required>
              <a-input v-model:value="createForm.location" placeholder="如危废暂存间（QA 现场监督）" />
            </a-form-item>
          </a-col>
        </a-row>
        <div class="field">
          <label>申请人 / 申请日期</label>
          <div class="static-readonly">{{ APPLICANT }} · {{ TODAY }}（演示固定）</div>
        </div>
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
        placeholder="驳回原因（必填，将写入审批链与审计）"
      />
      <div class="soe red" style="margin: 12px 0 0">驳回后申请终止，留样不释放、按原状留存，可重新发起处理。</div>
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
        确认后将取消并按进入处理前的状态快照恢复留样（演示）。
      </div>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, reactive, ref } from 'vue'
import { message, Empty } from 'ant-design-vue'
import type { TableColumnsType } from 'ant-design-vue'
import { CalendarOutlined, CloseCircleOutlined, ExclamationCircleOutlined, PlusOutlined } from '@ant-design/icons-vue'
import { useRoute } from 'vue-router'
import DemoBar from '@/components/retention/DemoBar.vue'
import {
  DEMO_ROLES, demo, can, demoPerson, SOD_NOTE,
  seedDisposalApplies, seedQuarterRows,
  advanceDisposal, executeDisposal,
  disposalActionNeeded, disposalChainSteps, disposalLevelLabel,
  type DisposalApply, type DisposalStatus, type DisposalType, type QuarterRow,
} from '@/demo/retentionDemo'

const APPLICANT = demoPerson('analyst') // 王敏
const TODAY = '2026-09-07'
const route = useRoute()

// ---------- 列表数据 ----------
const rows = ref<DisposalApply[]>(seedDisposalApplies())
const quarterRows = ref<QuarterRow[]>(seedQuarterRows())
const selected = ref<DisposalApply | null>(null)
const filter = ref<'all' | 'mine' | 'overdue'>('all')

const mineRows = computed<DisposalApply[]>(() =>
  rows.value.filter((d) => {
    const act = disposalActionNeeded(d.status)
    return !!act && can(demo.role, act)
  }),
)

const roleLabel = computed(() => DEMO_ROLES.find((r) => r.value === demo.role)?.label ?? demo.role)
const listSub = computed(() => `当前演示身份「${roleLabel.value}」待我审批 ${mineRows.value.length} 份`)

const overdueCount = computed(() => rows.value.filter((d) => d.status === '销毁超期').length)

const filterChips = computed<{ key: 'all' | 'mine' | 'overdue'; label: string }[]>(() => [
  { key: 'all', label: '全部' },
  { key: 'mine', label: `待我审批 ${mineRows.value.length}` },
  { key: 'overdue', label: `超期 ${overdueCount.value}` },
])

const filteredRows = computed<DisposalApply[]>(() => {
  if (filter.value === 'all') return rows.value
  if (filter.value === 'overdue') return rows.value.filter((d) => d.status === '销毁超期')
  return mineRows.value
})

const columns: TableColumnsType<DisposalApply> = [
  { title: '处理单号', key: 'order', width: 175 },
  { title: '留样 / 批号', key: 'retention', width: 205 },
  { title: '类型', key: 'type', width: 90 },
  { title: '层级', key: 'level', width: 80 },
  { title: 'deadline', key: 'deadline', width: 110 },
  { title: '状态', key: 'status', width: 120 },
  { title: '操作', key: 'action', width: 100 },
]

const quarterColumns: TableColumnsType<QuarterRow> = [
  { title: '留样编号', key: 'name', dataIndex: 'retentionName', width: 200 },
  { title: '样品 / 批号', key: 'sample', width: 195 },
  { title: '类别', key: 'category', dataIndex: 'category', width: 110 },
  { title: '留样期至', key: 'dueDate', dataIndex: 'dueDate', width: 105 },
  { title: '剩余天数', key: 'remain', dataIndex: 'remainDays', width: 100 },
  { title: '处理状态', key: 'state', dataIndex: 'state', width: 110 },
  { title: '建议', key: 'suggest', width: 150 },
]

const quarterCounts = computed(() => {
  const q = quarterRows.value
  return {
    lin: q.filter((r) => r.state === '临期').length,
    ready: q.filter((r) => r.state === '已批准待执行').length,
    overdue: q.filter((r) => r.state === '销毁超期').length,
  }
})

function statusPillClass(s: DisposalStatus): string {
  if (s === '销毁超期') return 'pill-danger'
  if (s === '已销毁' || s === '已完成续留') return 'pill-pass'
  if (s === '已批准') return 'pill-primary'
  if (s === '草稿' || s === '已驳回' || s === '已取消') return 'pill-muted'
  return 'pill-warn'
}

function quarterPillClass(s: QuarterRow['state']): string {
  if (s === '销毁超期') return 'pill-danger'
  if (s === '临期' || s === '已批准待执行') return 'pill-warn'
  if (s === '已完成') return 'pill-pass'
  return 'pill-muted'
}

function rowActionText(d: DisposalApply): string {
  const act = disposalActionNeeded(d.status)
  if (act && can(demo.role, act)) {
    if (d.status === '草稿') return '提交'
    if (d.status === '待QC主管审核' || d.status === '待QC负责人审核' || d.status === '待QA审核' || d.status === '待QM批准') return '审批'
    if (d.status === '待执行') return '双签执行'
  }
  return d.status === '销毁超期' ? '决策' : '查看'
}

// 季度清单建议列的按钮文案 / 点击行为
function quarterSuggestText(r: QuarterRow): string {
  if (r.disposalName) return r.state === '销毁超期' ? 'Manager 决策' : '查看处理单'
  if (r.state === '临期' || r.state === '销毁超期') return '发起处理'
  return ''
}

function onQuarterSuggest(r: QuarterRow) {
  if (r.disposalName) {
    const d = rows.value.find((x) => x.name === r.disposalName)
    if (d) {
      filter.value = 'all'
      selectRow(d)
    } else {
      message.info('处理单不在当前列表中（演示数据）。')
    }
    return
  }
  if (r.state === '临期' || r.state === '销毁超期') openCreate(r.retentionName)
}

// 选择行：加载右侧详情并滚动到双栏区域
const layoutRef = ref<HTMLElement | null>(null)
const quarterRef = ref<HTMLElement | null>(null)

function scrollToQuarter() {
  quarterRef.value?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

function pendingExec(d: DisposalApply): boolean {
  return d.status === '待执行' || (d.type === '期满续留' && d.status === '已批准')
}

const execForm = reactive({ handler: '', supervisor: '', newDueDate: '' })

function addYears(iso: string, years: number): string {
  const [y, m, dd] = iso.split('-').map(Number)
  return `${y + years}-${String(m).padStart(2, '0')}-${String(dd).padStart(2, '0')}`
}

function seedExec(d: DisposalApply) {
  if (!pendingExec(d)) return
  execForm.handler = d.handler && d.handler !== '待签名' ? d.handler : demoPerson('analyst')
  execForm.supervisor = d.supervisor && d.supervisor !== '待签名' ? d.supervisor : demoPerson('qa')
  execForm.newDueDate = d.newDueDate || addYears(d.dueDate, 3)
}

function selectRow(d: DisposalApply) {
  selected.value = d
  seedExec(d)
  layoutRef.value?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

function customRow(record: DisposalApply) {
  return {
    onClick: () => selectRow(record),
    style: { cursor: 'pointer' },
  }
}

// ---------- 详情：审批链 / 双签 / 动作 ----------
const selectedChain = computed(() => (selected.value ? disposalChainSteps(selected.value) : []))

function deadlineField(d: DisposalApply): string | null {
  if (d.type !== '期满销毁') return null
  if (!['待执行', '已销毁', '销毁超期'].includes(d.status)) return null
  const qm = d.signedBy.qm
  return `QM 批准 ${qm ? qm.at : '—'} + 3 个月 → ${d.deadline || '—'}`
}

interface DetailBtn { key: string; label: string; primary?: boolean; danger?: boolean }

// Manager 取消逃生口适用的状态（草稿不在此列）
const CANCELABLE: DisposalStatus[] = [
  '待QC主管审核', '待QC负责人审核', '待QA审核', '待QM批准',
  '已批准', '待执行', '销毁超期',
]

const detailActions = computed<DetailBtn[]>(() => {
  const s = selected.value
  if (!s) return []
  const list: DetailBtn[] = []
  const st = s.status
  if (st === '草稿') {
    if (can(demo.role, 'disposal_create')) list.push({ key: 'advance', label: '提交审核', primary: true })
  } else if (st === '待QC主管审核' || st === '待QC负责人审核' || st === '待QA审核' || st === '待QM批准') {
    const approveKey =
      st === '待QC主管审核' || st === '待QC负责人审核' ? 'disposal_qclevel' : st === '待QA审核' ? 'disposal_qalevel' : 'disposal_qm'
    const approveLabel =
      st === '待QC主管审核' ? 'QC 主管通过'
        : st === '待QC负责人审核' ? 'QC 负责人通过'
          : st === '待QA审核' ? 'QA 通过' : 'QM 批准'
    if (can(demo.role, approveKey)) {
      list.push({ key: 'advance', label: approveLabel, primary: true })
      list.push({ key: 'reject', label: '驳回', danger: true })
    }
  }
  if (st !== '草稿' && CANCELABLE.includes(st) && can(demo.role, 'disposal_cancel')) {
    list.push({ key: 'cancel', label: 'Manager 取消', danger: true })
  }
  return list
})

function syncRows(name: string) {
  rows.value = [...rows.value]
  selected.value = rows.value.find((r) => r.name === name) ?? selected.value
}

function advanceNote(d: DisposalApply): string {
  switch (d.status) {
    case '待QC主管审核': return '已提交，进入 QC 主管审核'
    case '待QC负责人审核': return 'QC 主管审核通过，进入 QC 负责人审核'
    case '待QA审核': return 'QC 负责人审核通过，进入 QA 审核'
    case '待QM批准': return 'QA 审核通过，进入 QM 批准'
    case '待执行': return `QM 批准完成：销毁 deadline ${d.deadline}（QM 批准 + 3 个月）`
    case '已批准': return d.type === '期满续留' ? 'QM 批准完成，可办理续留双签' : 'QM 批准完成'
    default: return ''
  }
}

function advanceOne() {
  const s = selected.value
  if (!s) return
  advanceDisposal(s)
  syncRows(s.name)
  seedExec(s)
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

// ---------- 执行双签 ----------
function doExecute() {
  const s = selected.value
  if (!s) return
  const handler = execForm.handler.trim()
  const supervisor = execForm.supervisor.trim()
  if (!handler || !supervisor) {
    message.warning('请填写处理人与监督人（QA）')
    return
  }
  if (s.type !== '期满销毁') {
    const nd = execForm.newDueDate || ''
    if (!nd) {
      message.warning('请选择新留样期至')
      return
    }
    if (nd <= s.dueDate) {
      message.warning('新留样期至须晚于原留样期至')
      return
    }
    s.newDueDate = nd
  }
  const destroy = s.type === '期满销毁'
  executeDisposal(s, handler, supervisor)
  syncRows(s.name)
  if (destroy) {
    completeQuarter(s.name, '已销毁')
    message.success('已写入销毁出库流水（演示）')
  } else {
    completeQuarter(s.name, `已完成续留至 ${s.newDueDate}`)
    message.success(`续留完成：新留样期至 ${s.newDueDate}（演示）`)
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
  s.status = '已驳回'
  syncRows(s.name)
  rejectOpen.value = false
  message.info('已驳回：留样按原状留存，可重新发起处理（演示）')
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
  releaseQuarter(s.name)
  syncRows(s.name)
  cancelOpen.value = false
  message.success('已取消：按进入处理前的状态快照恢复留样（演示）')
}

// ---------- 季度清单联动 ----------
function linkQuarter(retentionName: string, name: string) {
  quarterRows.value = quarterRows.value.map((r) =>
    r.retentionName === retentionName ? { ...r, disposalName: name } : r,
  )
}

function completeQuarter(name: string, text: string) {
  quarterRows.value = quarterRows.value.map((r) =>
    r.disposalName === name ? { ...r, state: '已完成', suggestion: text } : r,
  )
}

function releaseQuarter(name: string) {
  quarterRows.value = quarterRows.value.map((r) => {
    if (r.disposalName !== name) return r
    const overdue = r.dueDate < TODAY
    const next: QuarterRow = { ...r }
    delete next.disposalName
    next.state = overdue ? '销毁超期' : '临期'
    next.suggestion = overdue ? 'Manager 决策' : '发起处理申请'
    return next
  })
}

// ---------- 新建处理申请 ----------
const createOpen = ref(false)
const createForm = reactive({
  retentionName: '',
  product: '',
  batch: '',
  category: '',
  dueDate: '',
  type: '期满销毁' as DisposalType,
  qty: undefined as number | undefined,
  uom: '',
  qaManagerRequired: true,
  reason: '',
  method: '',
  location: '',
})

const createOptions = computed(() =>
  quarterRows.value
    .filter((r) => !r.disposalName && (r.state === '临期' || r.state === '销毁超期'))
    .map((r) => ({
      value: r.retentionName,
      label: `${r.product} · ${r.batch} · 留样期至 ${r.dueDate}`,
    })),
)

const pickedQuarter = computed<QuarterRow | null>(
  () => quarterRows.value.find((r) => r.retentionName === createForm.retentionName) ?? null,
)

const pickedStock = computed<{ currentQty: number; reservedQty: number; uom: string } | null>(() => {
  const name = createForm.retentionName
  if (!name) return null
  const m = rows.value.find(
    (d) => d.retentionName === name && !['已取消', '已驳回', '已销毁', '已完成续留'].includes(d.status),
  )
  return m ? { currentQty: m.currentQty, reservedQty: m.reservedQty, uom: m.uom } : null
})

function openCreate(preRetention?: string) {
  Object.assign(createForm, {
    retentionName: '',
    product: '', batch: '', category: '', dueDate: '',
    type: '期满销毁' as DisposalType,
    qty: undefined,
    uom: '',
    qaManagerRequired: true,
    reason: '',
    method: '',
    location: '',
  })
  if (preRetention) {
    createForm.retentionName = preRetention
    onPickRetention(preRetention)
  }
  createOpen.value = true
}

function onPickRetention(val: string) {
  const r = quarterRows.value.find((x) => x.retentionName === val)
  if (!r) return
  createForm.product = r.product
  createForm.batch = r.batch
  createForm.category = r.category
  createForm.dueDate = r.dueDate
  createForm.qty = pickedStock.value?.currentQty ?? undefined
  createForm.uom = pickedStock.value?.uom ?? ''
}

function nextOrderNo(): string {
  const max = rows.value.reduce((m, d) => {
    const tail = Number(d.name.split('-').pop() ?? 0)
    return Number.isFinite(tail) ? Math.max(m, tail) : m
  }, 0)
  return `HBOS-RET-DSP-2026-${String(max + 1).padStart(5, '0')}`
}

function confirmCreate() {
  const q = pickedQuarter.value
  if (!q) {
    message.error('请选择留样批次')
    return
  }
  const qty = createForm.qty
  if (!qty || qty <= 0) {
    message.error('数量须大于 0（默认取该留样结存）')
    return
  }
  if (!createForm.uom.trim()) {
    message.error('请填写 UOM')
    return
  }
  if (!createForm.reason.trim()) {
    message.error('请填写处理原因')
    return
  }
  if (!createForm.method.trim() || !createForm.location.trim()) {
    message.error('请填写处理方式与地点')
    return
  }
  if (pickedStock.value && qty > pickedStock.value.currentQty) {
    message.error(`数量超过当前结存（${pickedStock.value.currentQty} ${pickedStock.value.uom}）`)
    return
  }
  const no = nextOrderNo()
  const na: DisposalApply = {
    name: no,
    retentionName: createForm.retentionName,
    product: createForm.product,
    batch: createForm.batch,
    category: createForm.category,
    dueDate: createForm.dueDate,
    type: createForm.type,
    reason: createForm.reason.trim(),
    method: createForm.method.trim(),
    location: createForm.location.trim(),
    applicant: APPLICANT,
    applicantDate: TODAY,
    qaManagerRequired: createForm.qaManagerRequired,
    status: '草稿',
    signedBy: {},
    qty,
    uom: createForm.uom.trim(),
    currentQty: pickedStock.value?.currentQty ?? qty,
    reservedQty: 0,
    deadline: '',
    newDueDate: '',
    handler: '',
    supervisor: '',
  }
  rows.value = [na, ...rows.value]
  selected.value = na
  filter.value = 'all'
  linkQuarter(na.retentionName, na.name)
  createOpen.value = false
  message.success(`处理申请 ${no} 已创建（草稿），申请人 ${APPLICANT}`)
}

// ---------- 初始选中 & focus 路由（来自工作台“去处理”） ----------
const focusName = typeof route.query.focus === 'string' ? route.query.focus : ''
selected.value =
  (focusName ? rows.value.find((d) => d.name === focusName) : undefined) ??
  mineRows.value[0] ??
  rows.value[0] ??
  null
if (selected.value) seedExec(selected.value)

onMounted(() => {
  if (focusName && selected.value) {
    nextTick(() => layoutRef.value?.scrollIntoView({ behavior: 'smooth', block: 'start' }))
  }
})
</script>

<style scoped>
.list-panel { min-width: 0; }
.detail-panel { min-width: 0; }
.ret-main { color: var(--ink); }
.ret-sub { font-size: 11px; color: var(--muted); margin-top: 2px; }

.hero { display: flex; align-items: flex-start; justify-content: space-between; gap: 10px; }
.hero-title { font-size: 15px; font-weight: 700; color: var(--ink); }
.hero-sub { font-size: 11px; color: var(--muted); margin-top: 3px; }

.level-row { display: flex; align-items: center; gap: 10px; }

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
</style>
