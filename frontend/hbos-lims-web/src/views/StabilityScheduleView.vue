<template>
  <div class="page">
    <StbGateBanner />

    <div class="page-head">
      <div>
        <h1>取样与检测计划</h1>
        <p class="page-desc">按时间点管理计划日、实际日、有效截止日和延期审批</p>
      </div>
      <div class="page-actions">
        <a-button @click="delayOpen = true">
          <template #icon><CalendarOutlined /></template>
          申请延期
        </a-button>
        <a-button type="primary" @click="toast('已打开时间点生成入口（原型）')">
          <template #icon><PlusOutlined /></template>
          生成时间点
        </a-button>
      </div>
    </div>

    <div class="stb-subnav">
      <button :class="{ active: tab === 'board' }" @click="tab = 'board'">月度看板</button>
      <button :class="{ active: tab === 'ledger' }" @click="tab = 'ledger'">计划台账</button>
      <button :class="{ active: tab === 'delay' }" @click="tab = 'delay'">延期审批</button>
    </div>

    <!-- 月度看板 -->
    <template v-if="tab === 'board'">
      <div class="filter-bar">
        <a-select v-model:value="conditionFilter" :options="conditionOptions" style="width: 150px" />
        <a-select v-model:value="stateFilter" :options="stateOptions" style="width: 170px" />
        <span class="dim" style="margin-left: auto">当前视角：计划检测日期 · 截止日不随取样延期顺延</span>
      </div>
      <div class="panel">
        <div class="panel-head">
          <div>
            <div class="panel-title">{{ monthTitle }}时间点看板</div>
            <div class="panel-sub">按产品 / 条件查看本月时间点；演示节点为固定样例</div>
          </div>
          <div class="month-switch">
            <a-button size="small" @click="shiftMonth(-1)">
              <template #icon><ArrowLeftOutlined /></template>
            </a-button>
            <span class="month-title">{{ monthLabel }}</span>
            <a-button size="small" @click="shiftMonth(1)">
              <template #icon><ArrowRightOutlined /></template>
            </a-button>
          </div>
        </div>
        <div class="panel-body">
          <div class="stb-plan-board">
            <div class="stb-plan-grid">
              <div class="head">产品 / 条件</div>
              <div v-for="d in dayHeaders" :key="d" class="head">{{ d }}</div>
              <template v-for="row in visibleRows" :key="row.product + row.condition">
                <div class="row-label">
                  <b>{{ row.product }}</b>
                  <span>{{ row.condition }} · {{ row.batch }}</span>
                </div>
                <div
                  v-for="(cell, i) in row.cells"
                  :key="i"
                  class="stb-plan-cell"
                  :class="{ 'has-dot': !!cell.point, warn: cell.tone === 'warn', danger: cell.tone === 'danger' }"
                >
                  <span v-if="cell.point" class="tiny">{{ cell.point }}</span>
                </div>
              </template>
            </div>
          </div>
          <div class="stb-plan-legend">
            <span><i style="background: var(--primary)"></i>正常时间点</span>
            <span><i style="background: var(--warn)"></i>临近计划日</span>
            <span><i style="background: var(--danger)"></i>延期 / 风险</span>
            <span>点击节点查看计划与日期链</span>
          </div>
        </div>
      </div>

      <div class="grid-2" style="margin-top: 16px">
        <div class="panel">
          <div class="panel-head">
            <div>
              <div class="panel-title">时间点日期链</div>
              <div class="panel-sub">{{ DATE_CHAIN.name }}</div>
            </div>
            <span class="pill pill-warn">{{ DATE_CHAIN.status }}</span>
          </div>
          <div class="panel-body">
            <div class="stb-kv-grid">
              <div v-for="f in DATE_CHAIN.fields" :key="f.label" class="stb-kv">
                <label>{{ f.label }}</label>
                <b :class="{ mono: f.mono !== false }">{{ f.value }}</b>
              </div>
            </div>
            <div class="stb-notice">{{ DATE_CHAIN.note }}</div>
          </div>
        </div>

        <div class="panel">
          <div class="panel-head">
            <div>
              <div class="panel-title">本周到期清单</div>
              <div class="panel-sub">按有效截止日排序</div>
            </div>
          </div>
          <div class="panel-body no-pad">
            <a-table
              :columns="dueColumns"
              :data-source="WEEK_DUE"
              size="small"
              row-key="point"
              :pagination="false"
              :scroll="{ x: 420 }"
            >
              <template #bodyCell="{ column, record }">
                <template v-if="column.key === 'point'"><span class="mono">{{ record.point }}</span></template>
                <template v-else-if="column.key === 'due'"><span class="mono">{{ record.due }}</span></template>
                <template v-else-if="column.key === 'status'">
                  <span :class="toneClass(record.tone)">{{ record.status }}</span>
                </template>
              </template>
            </a-table>
          </div>
        </div>
      </div>
    </template>

    <!-- 计划台账 -->
    <div v-else-if="tab === 'ledger'" class="panel">
      <div class="panel-head">
        <div>
          <div class="panel-title">时间点计划台账</div>
          <div class="panel-sub">计划检测日 / 有效截止日 / 政策硬上限三层日期与延期状态并列展示</div>
        </div>
        <span class="pill pill-muted">只读投影</span>
      </div>
      <div class="panel-body no-pad">
        <a-table
          :columns="ledgerColumns"
          :data-source="SCHEDULE_LEDGER"
          size="small"
          row-key="point"
          :pagination="{ pageSize: 10 }"
          :scroll="{ x: 1240 }"
        >
          <template #bodyCell="{ column, record }">
            <template v-if="column.key === 'point'"><span class="mono">{{ record.point }}</span></template>
            <template v-else-if="column.key === 'product'">
              <div class="stb-cell-strong">{{ record.product }}</div>
              <div class="dim mono">{{ record.batch }}</div>
            </template>
            <template v-else-if="column.key === 'planned'"><span class="mono">{{ record.planned }}</span></template>
            <template v-else-if="column.key === 'effective'"><span class="mono">{{ record.effective }}</span></template>
            <template v-else-if="column.key === 'policyLatest'"><span class="mono dim">{{ record.policyLatest }}</span></template>
            <template v-else-if="column.key === 'sampleDate'">
              <span class="mono" :class="{ dim: record.sampleDate === '未登记' }">{{ record.sampleDate }}</span>
            </template>
            <template v-else-if="column.key === 'delay'">
              <span :class="toneClass(record.delayTone)">{{ record.delay }}</span>
            </template>
            <template v-else-if="column.key === 'status'">
              <span :class="toneClass(record.statusTone)">{{ record.status }}</span>
            </template>
          </template>
        </a-table>
      </div>
    </div>

    <!-- 延期审批 -->
    <div v-else class="panel">
      <div class="panel-head">
        <div>
          <div class="panel-title">延期申请与审批</div>
          <div class="panel-sub">申请与批准为独立动作；批准前有效截止日不被改写</div>
        </div>
        <a-button size="small" type="primary" @click="delayOpen = true">申请延期</a-button>
      </div>
      <div class="panel-body no-pad">
        <a-table
          :columns="delayColumns"
          :data-source="DELAY_APPLIES"
          size="small"
          row-key="name"
          :pagination="{ pageSize: 10 }"
          :scroll="{ x: 1280 }"
        >
          <template #bodyCell="{ column, record }">
            <template v-if="column.key === 'name'"><span class="mono">{{ record.name }}</span></template>
            <template v-else-if="column.key === 'product'">
              <div class="stb-cell-strong">{{ record.product }}</div>
              <div class="dim mono">{{ record.point }}</div>
            </template>
            <template v-else-if="column.key === 'planned'"><span class="mono">{{ record.planned }}</span></template>
            <template v-else-if="column.key === 'requested'"><span class="mono">{{ record.requested }}</span></template>
            <template v-else-if="column.key === 'approved'">
              <span class="mono" :class="{ dim: record.approved === '—' }">{{ record.approved }}</span>
            </template>
            <template v-else-if="column.key === 'status'">
              <span :class="toneClass(record.statusTone)">{{ record.status }}</span>
            </template>
          </template>
        </a-table>
      </div>
    </div>

    <!-- 申请延期抽屉 -->
    <a-drawer v-model:open="delayOpen" title="申请取样延期" :width="560" placement="right">
      <p class="stb-gate-sub">独立延期动作 · 不直接改写时间点状态</p>
      <div class="stb-drawer-section">
        <h3>时间点</h3>
        <div class="stb-drawer-kv">
          <div><label>时间点</label><b>TEST 片剂 A · M3</b></div>
          <div><label>原计划日</label><b class="mono">2026-09-16</b></div>
          <div><label>政策硬上限</label><b class="mono">2026-09-20</b></div>
          <div><label>申请类型</label><b>取样延期</b></div>
        </div>
      </div>
      <div class="stb-drawer-section">
        <h3>延期申请</h3>
        <div class="stb-form-grid">
          <div class="stb-form-field">
            <label>申请日期 *</label>
            <a-input v-model:value="delay.applyDate" />
          </div>
          <div class="stb-form-field">
            <label>申请至 *</label>
            <a-input v-model:value="delay.requestTo" />
          </div>
          <div class="stb-form-field full">
            <label>原因 *</label>
            <a-textarea v-model:value="delay.reason" :rows="3" />
          </div>
        </div>
      </div>
      <div class="stb-notice">
        提交后由 QA Manager 独立审批；批准日期链需满足 planned ≤ requested ≤ approved ≤ policy_latest。
      </div>
      <template #footer>
        <a-button @click="delayOpen = false">取消</a-button>
        <a-button type="primary" @click="submitDelay">提交延期申请</a-button>
      </template>
    </a-drawer>
  </div>
</template>

<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import { message } from 'ant-design-vue'
import { ArrowLeftOutlined, ArrowRightOutlined, CalendarOutlined, PlusOutlined } from '@ant-design/icons-vue'
import StbGateBanner from '@/components/stability/StbGateBanner.vue'
import {
  DATE_CHAIN, DELAY_APPLIES, SCHEDULE_LEDGER, SCHEDULE_ROWS, WEEK_DUE, toneClass,
} from '@/demo/stabilityDemo'

const tab = ref<'board' | 'ledger' | 'delay'>('board')
const conditionFilter = ref('全部条件')
const stateFilter = ref('全部执行状态')

const conditionOptions = ['全部条件', '长期', '加速', '中间'].map((v) => ({ value: v, label: v }))
const stateOptions = ['全部执行状态', '待取样', '检测中', '已完成'].map((v) => ({ value: v, label: v }))

const visibleRows = computed(() =>
  SCHEDULE_ROWS.filter((r) => {
    if (conditionFilter.value !== '全部条件' && r.condition !== conditionFilter.value) return false
    if (stateFilter.value !== '全部执行状态' && !r.states.includes(stateFilter.value)) return false
    return true
  }),
)

// ---- 月份切换：按所选月份的 15 日起生成 7 天列头（9 月即为原型中的 09-15 ~ 09-21）----
const cursor = ref(new Date(2026, 8, 1))
const monthLabel = computed(() => `${cursor.value.getFullYear()} 年 ${String(cursor.value.getMonth() + 1).padStart(2, '0')} 月`)
const monthTitle = computed(() => `${cursor.value.getFullYear()} 年 ${cursor.value.getMonth() + 1} 月`)

const WEEK_CN = ['周日', '周一', '周二', '周三', '周四', '周五', '周六']
const dayHeaders = computed(() => {
  const y = cursor.value.getFullYear()
  const m = cursor.value.getMonth()
  return Array.from({ length: 7 }, (_, i) => {
    const d = new Date(y, m, 15 + i)
    return `${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')} ${WEEK_CN[d.getDay()]}`
  })
})

function shiftMonth(step: number) {
  cursor.value = new Date(cursor.value.getFullYear(), cursor.value.getMonth() + step, 1)
}

function toast(msg: string) {
  message.success(msg)
}

const dueColumns = [
  { title: '时间点', key: 'point', width: 100 },
  { title: '产品', key: 'product', dataIndex: 'product', width: 140 },
  { title: '截止日', key: 'due', width: 90 },
  { title: '状态', key: 'status', width: 90 },
]

const ledgerColumns = [
  { title: '时间点', key: 'point', width: 90 },
  { title: '产品 / 批号', key: 'product', width: 180 },
  { title: '条件', key: 'condition', dataIndex: 'condition', width: 80 },
  { title: '计划检测日', key: 'planned', width: 115 },
  { title: '有效截止日', key: 'effective', width: 115 },
  { title: '政策硬上限', key: 'policyLatest', width: 115 },
  { title: '实际取样日', key: 'sampleDate', width: 115 },
  { title: '延期', key: 'delay', width: 90 },
  { title: '检测窗口', key: 'window', width: 120, customRender: () => '计划日后 30 天内' },
  { title: '状态', key: 'status', width: 90 },
]

const delayColumns = [
  { title: '延期单号', key: 'name', width: 210 },
  { title: '产品 / 时间点', key: 'product', width: 170 },
  { title: '类型', key: 'delayType', dataIndex: 'delayType', width: 100 },
  { title: '原计划日', key: 'planned', width: 110 },
  { title: '申请日', key: 'requested', width: 110 },
  { title: '批准日', key: 'approved', width: 110 },
  { title: '政策硬上限', key: 'policyLatest', dataIndex: 'policyLatest', width: 115 },
  { title: '申请人', key: 'applicant', dataIndex: 'applicant', width: 160 },
  { title: '状态', key: 'status', width: 160 },
]

// ---- 延期申请抽屉 ----
const delayOpen = ref(false)
const delay = reactive({
  applyDate: '2026-09-15',
  requestTo: '2026-09-17',
  reason: '稳定性室 02 设备临时评估，预计 09-17 完成取样。',
})

function submitDelay() {
  delayOpen.value = false
  message.success('原型入口：延期申请未落库，正式动作需由受控业务方法完成')
}
</script>

<style scoped>
.stb-cell-strong { color: var(--ink); font-weight: 700; }
.stb-gate-sub { font-size: 12px; color: var(--muted); margin-bottom: 12px; }
.month-switch {
  display: flex;
  align-items: center;
  gap: 7px;
}
.month-title {
  min-width: 96px;
  text-align: center;
  font-weight: 700;
  font-size: 12px;
  color: var(--ink);
}
</style>
