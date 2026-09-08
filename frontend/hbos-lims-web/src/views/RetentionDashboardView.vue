<template>
  <div class="page">
    <div class="page-head">
      <div>
        <h1>留样工作台总览</h1>
        <p class="page-desc">留样生命周期待办与到期态势 · 演示数据 TEST-HBOS-M2-RET-*</p>
      </div>
      <div class="page-actions">
        <a-button @click="reset">
          <template #icon><ReloadOutlined /></template>
          刷新
        </a-button>
        <router-link to="/retention/samples">
          <a-button type="primary">
            <template #icon><PlusOutlined /></template>
            留样登记
          </a-button>
        </router-link>
      </div>
    </div>

    <DemoBar />

    <div class="alert-strip">
      <ExclamationCircleOutlined />
      <span>{{ alertText }}</span>
      <a-button class="alert-link" type="link" @click="goDisposal">去处理</a-button>
    </div>

    <div class="kpi-grid">
      <div class="kpi-card" v-for="k in kpis" :key="k.label">
        <div class="kpi-label">{{ k.label }}</div>
        <div class="kpi-num" :class="k.tone">{{ k.value }}</div>
        <div class="kpi-sub">{{ k.sub }}</div>
      </div>
    </div>

    <div class="grid-2">
      <div class="panel">
        <div class="panel-head">
          <div>
            <div class="panel-title">观察计划完整性</div>
            <div class="panel-sub">{{ currentYear }} 年各产品已选观察批 N/3</div>
          </div>
          <router-link to="/retention/observations"><a-button type="link">观察任务 →</a-button></router-link>
        </div>
        <div class="panel-body">
          <div class="progress-row" v-for="c in completeness" :key="c.product">
            <div class="progress-main">
              <div class="progress-top">
                <span><strong>{{ c.product }}</strong> <span class="dim">· {{ c.rule }}</span></span>
                <span class="num">{{ c.cap ? `${c.selected}/${c.cap}` : '每批' }}</span>
              </div>
              <div class="progress-track">
                <i :class="pctClass(c)" :style="{ width: pct(c) + '%' }"></i>
              </div>
            </div>
            <span class="pill" :class="c.cap && c.selected < c.cap ? 'pill-warn' : 'pill-pass'">
              {{ c.cap && c.selected < c.cap ? `可补选 ${c.cap - c.selected} 批` : '完整' }}
            </span>
          </div>
        </div>
      </div>

      <div class="panel">
        <div class="panel-head">
          <div>
            <div class="panel-title">审批待办</div>
            <div class="panel-sub">{{ roleDesc }}</div>
          </div>
        </div>
        <div class="panel-body no-pad">
          <div class="mini-list" style="padding: 2px 16px">
            <div class="mini-row" v-for="p in pendingList" :key="p.key">
              <div class="mini-main">
                <div class="mini-title">
                  <span class="mono">{{ p.name }}</span>
                  <span class="pill" :class="statusPill(p.status)">{{ p.status }}</span>
                </div>
                <div class="mini-sub">{{ p.desc }}</div>
              </div>
              <router-link :to="p.link">
                <a-button size="small">{{ p.actionText }}</a-button>
              </router-link>
            </div>
            <a-empty v-if="!pendingList.length" description="当前角色无审批待办" :image="Empty.PRESENTED_IMAGE_SIMPLE" style="margin: 8px 0" />
          </div>
        </div>
      </div>
    </div>

    <div class="panel">
      <div class="panel-head">
        <div>
          <div class="panel-title">季度到期处理清单</div>
          <div class="panel-sub">Q3 {{ currentYear }} · 留样期至 ≤ 2026-09-30 且未完成</div>
        </div>
        <div class="page-actions">
          <span class="pill pill-warn">临期 {{ quarterCounts.linQi }}</span>
          <span class="pill pill-primary">已批准待执行 {{ quarterCounts.ready }}</span>
          <span class="pill pill-danger">销毁超期 {{ quarterCounts.overdue }}</span>
        </div>
      </div>
      <div class="panel-body no-pad">
        <a-table
          :columns="qColumns"
          :data-source="quarterRows"
          size="small"
          row-key="retentionName"
          :pagination="false"
          :scroll="{ x: 880 }"
        >
          <template #bodyCell="{ column, record }">
            <template v-if="column.key === 'name'"><span class="mono">{{ record.retentionName }}</span></template>
            <template v-else-if="column.key === 'sample'">
              {{ record.product }} <span class="dim">/ {{ record.batch }}</span>
            </template>
            <template v-else-if="column.key === 'remain'">
              <span :class="record.remainDays < 0 ? 'danger-text' : 'dim'">
                {{ record.remainDays < 0 ? `超期 ${-record.remainDays} 天` : `${record.remainDays} 天` }}
              </span>
            </template>
            <template v-else-if="column.key === 'state'">
              <span class="pill" :class="statePill(record.state)">{{ record.state }}</span>
            </template>
            <template v-else-if="column.key === 'action'">
              <router-link v-if="record.disposalName" :to="'/retention/disposal?focus=' + record.disposalName">
                <a-button type="link" size="small">{{ record.state === '销毁超期' ? 'Manager 决策' : '查看处理单' }}</a-button>
              </router-link>
              <router-link v-else-if="record.state === '临期'" to="/retention/disposal">
                <a-button type="link" size="small">发起处理</a-button>
              </router-link>
              <span v-else class="dim">—</span>
            </template>
          </template>
        </a-table>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { message } from 'ant-design-vue'
import { Empty } from 'ant-design-vue'
import { PlusOutlined, ReloadOutlined, ExclamationCircleOutlined } from '@ant-design/icons-vue'
import { useRouter } from 'vue-router'
import DemoBar from '@/components/retention/DemoBar.vue'
import {
  DEMO_ROLES, demo, can, seedObsCompleteness, seedObsBoard,
  seedUsageApplies, seedDisposalApplies, seedQuarterRows,
  usageActionNeeded, disposalActionNeeded,
  type ObsCompleteness, type QuarterRow,
} from '@/demo/retentionDemo'

const router = useRouter()
const currentYear = 2026

const completeness = ref<ObsCompleteness[]>(seedObsCompleteness())
const quarterRows = ref<QuarterRow[]>(seedQuarterRows())

// 待办面板由使用/处理申请推导（受演示角色影响）
const pendingList = computed(() => {
  const list: {
    key: string; name: string; status: string; desc: string; link: string; actionText: string; tone: 'warn' | 'danger' | 'pass'
  }[] = []
  for (const a of seedUsageApplies()) {
    const action = usageActionNeeded(a.status)
    if (action && can(demo.role, action)) {
      list.push({
        key: `u-${a.name}`, name: a.name, status: a.status,
        desc: `${a.product} · ${a.batch} · 使用 ${a.qty} ${a.uom} · ${a.scenario}`,
        link: '/retention/usage', actionText: a.status === '已批准' ? '取样执行' : a.status === '草稿' ? '提交' : '去审批',
        tone: a.status === '已批准' ? 'pass' : 'warn',
      })
    }
  }
  for (const d of seedDisposalApplies()) {
    const action = disposalActionNeeded(d.status)
    if (action && can(demo.role, action)) {
      list.push({
        key: `d-${d.name}`, name: d.name, status: d.status,
        desc: `${d.product} · ${d.batch} · ${d.type}`,
        link: '/retention/disposal', actionText: d.status === '待执行' ? '双签执行' : '去审批',
        tone: d.status === '销毁超期' ? 'danger' : 'warn',
      })
    }
  }
  return list
})

const roleLabel = computed(() => DEMO_ROLES.find((r) => r.value === demo.role)?.label ?? demo.role)
const roleDesc = computed(() => `按当前演示身份「${roleLabel.value}」可办事项`)

function statusPill(s: string): string {
  if (s === '已批准' || s === '待执行') return 'pill-primary'
  if (s === '销毁超期') return 'pill-danger'
  return 'pill-warn'
}

// KPI 由上述种子聚合（保持与面板数字一致）
const kpis = computed(() => {
  const obs = seedObsBoard()
  const usage = seedUsageApplies()
  const disposal = seedDisposalApplies()
  const qrows = seedQuarterRows()
  const inApproval = (s: string) => s.startsWith('待')
  const quarterOverdue = qrows.filter((r) => r.state === '销毁超期').length
  return [
    { label: '在库留样', value: 42, sub: '含部分使用 9 批', tone: 'good' },
    { label: '待处理', value: usage.filter((a) => a.status === '已批准').length + disposal.filter((d) => d.status === '待执行' || d.status === '销毁超期').length, sub: '等待处理申请批复', tone: 'warn' },
    { label: '临期 30 天内', value: qrows.filter((r) => r.remainDays >= 0 && r.remainDays <= 30).length, sub: '90 天内按台账另计', tone: 'danger' },
    { label: '应观察未观察', value: obs.filter((o) => o.due === '应观察' || o.due === '已逾期').length, sub: `本月计划 ${obs.length} 项`, tone: 'info' },
    { label: '待审批', value: usage.filter((a) => inApproval(a.status)).length + disposal.filter((d) => inApproval(d.status)).length, sub: `使用 ${usage.filter((a) => inApproval(a.status)).length} · 处理 ${disposal.filter((d) => inApproval(d.status)).length}`, tone: 'warn' },
    { label: '销毁超期', value: quarterOverdue, sub: 'deadline 已过', tone: 'danger' },
  ]
})

const alertText = computed(() => {
  const k = kpis.value
  const obsDue = seedObsBoard().filter((o) => o.due === '应观察' || o.due === '已逾期').length
  return `${k[2].value} 条留样进入 30 天临期，${obsDue} 条观察计划应观察未完成，${k[5].value} 份销毁申请已超期，${k[4].value} 份审批滞留。`
})

const quarterCounts = computed(() => ({
  linQi: kpis.value[2].value,
  overdue: kpis.value[5].value,
  ready: quarterRows.value.filter((r) => r.state === '已批准待执行').length,
}))

const qColumns = [
  { title: '留样编号', key: 'name', dataIndex: 'retentionName', width: 190 },
  { title: '样品 / 批号', key: 'sample', width: 200 },
  { title: '类别', key: 'category', dataIndex: 'category', width: 110 },
  { title: '留样期至', key: 'dueDate', dataIndex: 'dueDate', width: 100 },
  { title: '剩余时间', key: 'remain', width: 100 },
  { title: '处理状态', key: 'state', width: 110 },
  { title: '建议', key: 'action', width: 130 },
]

function pct(c: ObsCompleteness): number {
  if (!c.cap) return 100
  return Math.min(100, Math.round((c.selected / c.cap) * 100))
}
function pctClass(c: ObsCompleteness): string {
  if (!c.cap || c.selected >= c.cap) return 'green'
  return 'amber'
}
function statePill(s: string): string {
  if (s === '销毁超期') return 'pill-danger'
  if (s === '临期' || s === '已批准待执行') return 'pill-warn'
  if (s === '已完成') return 'pill-pass'
  return 'pill-muted'
}

function reset() {
  completeness.value = seedObsCompleteness()
  quarterRows.value = seedQuarterRows()
  message.info('演示数据已复位')
}

function goDisposal() {
  router.push('/retention/disposal')
}
</script>
