<template>
  <div class="page">
    <StbGateBanner
      mode="live"
      note="工作台 KPI 与各板块汇总均来自 hb_lims_app 稳定性业务服务（R8A~R8D 后端全量交付，7 视图已全部接入真实 API）。"
    />

    <div class="page-head">
      <div>
        <h1>稳定性工作台</h1>
        <p class="page-desc">稳定性考察申请与方案的执行态势</p>
      </div>
      <div class="page-actions">
        <a-button :disabled="!can('create_notice')" @click="noticeRef?.show()">
          <template #icon><PlusOutlined /></template>
          新建考察通知
        </a-button>
        <router-link to="/stability/study">
          <a-button type="primary">
            <template #icon><FileTextOutlined /></template>
            考察申请与方案
          </a-button>
        </router-link>
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

      <div class="grid-2">
        <div class="panel">
          <div class="panel-head">
            <div>
              <div class="panel-title">待办考察通知</div>
              <div class="panel-sub">草稿与在途审批的通知单</div>
            </div>
            <router-link to="/stability/study"><a-button size="small">查看全部</a-button></router-link>
          </div>
          <div class="panel-body">
            <a-empty v-if="!pendingNotices.length" description="当前没有待办通知单" :image="Empty.PRESENTED_IMAGE_SIMPLE" />
            <div v-else class="stb-risk-list">
              <div v-for="n in pendingNotices" :key="n.name" class="stb-risk-item">
                <span class="stb-risk-mark" :class="riskClass(statusTone(n.status))"></span>
                <div class="stb-risk-main">
                  <div class="stb-risk-title mono">{{ n.name }}</div>
                  <div class="stb-risk-sub">{{ n.product_name || n.stability_product }} · {{ n.category || '—' }}</div>
                </div>
                <span :class="toneClass(statusTone(n.status))">{{ n.status }}</span>
              </div>
            </div>
          </div>
        </div>

        <div class="panel">
          <div class="panel-head">
            <div>
              <div class="panel-title">待审稳定性方案</div>
              <div class="panel-sub">草稿与待 QA 审核的方案</div>
            </div>
            <router-link to="/stability/study"><a-button size="small">查看全部</a-button></router-link>
          </div>
          <div class="panel-body">
            <a-empty v-if="!pendingProtocols.length" description="当前没有待审方案" :image="Empty.PRESENTED_IMAGE_SIMPLE" />
            <div v-else class="stb-risk-list">
              <div v-for="p in pendingProtocols" :key="p.name" class="stb-risk-item">
                <span class="stb-risk-mark" :class="riskClass(statusTone(p.status))"></span>
                <div class="stb-risk-main">
                  <div class="stb-risk-title mono">{{ p.name }}</div>
                  <div class="stb-risk-sub">{{ p.product_name || p.stability_product }} · 通知单 {{ p.notice }}</div>
                </div>
                <span :class="toneClass(statusTone(p.status))">{{ p.status }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div class="stb-three-col">
        <div class="panel">
          <div class="panel-head">
            <div>
              <div class="panel-title">主数据概况</div>
              <div class="panel-sub">已启用的稳定性主数据</div>
            </div>
          </div>
          <div class="panel-body">
            <div class="stb-legend-row"><span class="stb-legend-dot" style="background: #0c7c6a"></span>稳定性产品<b>{{ kpi?.product_count ?? '—' }}</b></div>
            <div class="stb-legend-row"><span class="stb-legend-dot" style="background: #3a86c8"></span>储存条件<b>{{ kpi?.master.condition ?? '—' }}</b></div>
            <div class="stb-legend-row"><span class="stb-legend-dot" style="background: #d1871d"></span>稳定性室<b>{{ kpi?.master.room ?? '—' }}</b></div>
            <div class="stb-legend-row"><span class="stb-legend-dot" style="background: #7a6cc4"></span>检验项目<b>{{ kpi?.master.test_item ?? '—' }}</b></div>
          </div>
        </div>

        <div class="panel">
          <div class="panel-head">
            <div>
              <div class="panel-title">稳定性产品</div>
              <div class="panel-sub">建档时可选的启用产品</div>
            </div>
          </div>
          <div class="panel-body no-pad">
            <a-table
              :columns="productColumns"
              :data-source="productRows"
              size="small"
              row-key="name"
              :pagination="false"
              :scroll="{ x: 420 }"
            >
              <template #bodyCell="{ column, record }">
                <template v-if="column.key === 'product'">
                  <div class="stb-cell-strong">{{ record.product_name }}</div>
                  <div class="dim mono">{{ record.product_code }}</div>
                </template>
                <template v-else-if="column.key === 'category'"><span class="dim">{{ record.category }}</span></template>
                <template v-else-if="column.key === 'uom'"><span class="mono">{{ record.default_uom }}</span></template>
              </template>
            </a-table>
          </div>
        </div>

        <div class="panel">
          <div class="panel-head">
            <div>
              <div class="panel-title">时间点执行结构</div>
              <div class="panel-sub">全部稳定性时间点的执行状态分布</div>
            </div>
            <router-link to="/stability/schedule"><a-button size="small">查看计划</a-button></router-link>
          </div>
          <div class="panel-body">
            <div class="stb-legend-row"><span class="stb-legend-dot" style="background: #3a86c8"></span>待取样<b>{{ kpi?.timepoint_by_status.wait_sample ?? '—' }}</b></div>
            <div class="stb-legend-row"><span class="stb-legend-dot" style="background: #d1871d"></span>待检测<b>{{ kpi?.timepoint_by_status.wait_test ?? '—' }}</b></div>
            <div class="stb-legend-row"><span class="stb-legend-dot" style="background: #0c7c6a"></span>检测中<b>{{ kpi?.timepoint_by_status.testing ?? '—' }}</b></div>
            <div class="stb-legend-row"><span class="stb-legend-dot" style="background: #2f855a"></span>已完成<b>{{ kpi?.timepoint_by_status.done ?? '—' }}</b></div>
            <div class="stb-legend-row"><span class="stb-legend-dot" style="background: #94a3b8"></span>已取消<b>{{ kpi?.timepoint_by_status.cancelled ?? '—' }}</b></div>
          </div>
        </div>
      </div>
    </a-spin>

    <StbNoticeDrawer ref="noticeRef" @created="reload" />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import type { Component } from 'vue'
import { Empty, message } from 'ant-design-vue'
import {
  AlertOutlined, CalendarOutlined, CheckCircleOutlined, ExperimentOutlined,
  FileTextOutlined, LineChartOutlined, PlusOutlined, SafetyCertificateOutlined,
} from '@ant-design/icons-vue'
import StbGateBanner from '@/components/stability/StbGateBanner.vue'
import StbNoticeDrawer from '@/components/stability/StbNoticeDrawer.vue'
import { useAuthStore } from '@/stores/auth'
import {
  canAction, dashboard, notices, products, protocols,
  type NoticeRow, type ProductRow, type ProtocolRow, type StabilityKpi,
} from '@/api/stability'

const auth = useAuthStore()
const can = (action: string): boolean => canAction(auth.user?.roles, action)

const noticeRef = ref<InstanceType<typeof StbNoticeDrawer> | null>(null)
const loading = ref(false)
const kpi = ref<StabilityKpi | null>(null)
const noticeRows = ref<NoticeRow[]>([])
const protocolRows = ref<ProtocolRow[]>([])
const productRows = ref<ProductRow[]>([])

const productColumns = [
  { title: '产品', key: 'product', width: 180 },
  { title: '考察分类', key: 'category', width: 160 },
  { title: '单位', key: 'uom', width: 70 },
]

/** 稳定性状态 → 语义色（pill-* 全局类） */
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
function riskClass(tone: ReturnType<typeof statusTone>): string {
  if (tone === 'danger') return 'red'
  if (tone === 'warn' || tone === 'info') return 'amber'
  return 'blue'
}

const pendingNotices = computed(() =>
  noticeRows.value.filter((n) => ['草稿', '待QC经理确认', '待批准'].includes(n.status)),
)
const pendingProtocols = computed(() =>
  protocolRows.value.filter((p) => ['草稿', '待QA审核'].includes(p.status)),
)

interface KpiCard {
  label: string
  value: string | number
  unit?: string
  hint: string
  hintClass: string
  iconClass: string
  icon: Component
}

const kpis = computed<KpiCard[]>(() => {
  const k = kpi.value
  return [
    {
      label: '通知单待批', value: k ? k.notice_pending : '—', hint: '待 QC 确认或待批准',
      hintClass: k && k.notice_pending > 0 ? 'warn' : 'good', iconClass: 'amber', icon: AlertOutlined,
    },
    {
      label: '通知单已批准', value: k ? k.notice_approved : '—', hint: '批准后快照冻结',
      hintClass: 'good', iconClass: 'green', icon: CheckCircleOutlined,
    },
    {
      label: '方案待审', value: k ? k.protocol_pending : '—', hint: '待 QA 审核',
      hintClass: k && k.protocol_pending > 0 ? 'warn' : 'good', iconClass: 'amber', icon: FileTextOutlined,
    },
    {
      label: '方案已批准', value: k ? k.protocol_approved : '—', hint: '生效方案',
      hintClass: 'good', iconClass: 'green', icon: SafetyCertificateOutlined,
    },
    {
      label: '稳定性产品', value: k ? k.product_count : '—', hint: '已启用产品主数据',
      hintClass: '', iconClass: 'teal', icon: SafetyCertificateOutlined,
    },
    {
      label: '稳定性样品', value: k ? k.sample_count : '—', hint: '已登记样品（含已转出/销毁）',
      hintClass: '', iconClass: 'teal', icon: ExperimentOutlined,
    },
    {
      label: '时间点', value: k ? k.timepoint_count : '—', hint: '按方案 / 通知单逐条件生成',
      hintClass: '', iconClass: 'blue', icon: CalendarOutlined,
    },
    {
      label: '检测结果', value: k ? k.result_count : '—', hint: '含在途与历史修订版本',
      hintClass: '', iconClass: 'green', icon: LineChartOutlined,
    },
  ]
})

async function load() {
  loading.value = true
  try {
    const [k, n, p, prod] = await Promise.all([
      dashboard(),
      notices({ limit: 100 }),
      protocols({ limit: 100 }),
      products(),
    ])
    kpi.value = k
    noticeRows.value = n.rows
    protocolRows.value = p.rows
    productRows.value = prod.rows
  } catch {
    if (!auth.user) message.warning('未登录（Guest）：稳定性数据不可用，请先在 Frappe Desk 登录后刷新。')
    else if (!auth.user?.roles?.length) message.warning('当前会话尚未取到角色，页面动作可能受限。')
    else message.error('加载稳定性工作台失败')
  } finally {
    loading.value = false
  }
}

function reload() {
  void load()
}

onMounted(() => {
  void auth.checkSession()
  void load()
})
</script>

<style scoped>
.stb-cell-strong { color: var(--ink); font-weight: 700; }
</style>
