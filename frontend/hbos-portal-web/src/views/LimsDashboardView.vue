<template>
  <section class="product-page lims-dashboard-v2">
    <div class="lims-dashboard-heading">
      <div>
        <span class="page-kicker">LIMS · 实验室工作台</span>
        <h1>今日工作</h1>
        <p>当前范围：{{ scopeLabel }} · 最近同步：{{ lastSyncLabel }}</p>
      </div>
      <a-button :loading="loading" @click="loadDashboard">
        <ReloadOutlined /> 刷新数据
      </a-button>
    </div>

    <a-alert
      v-if="errorMessage"
      type="error"
      show-icon
      closable
      class="lims-dashboard-alert"
      :message="errorMessage"
      @close="errorMessage = ''"
    />

    <div v-if="loading && !metrics.length" class="lims-dashboard-loading" aria-live="polite">
      <div v-for="item in 4" :key="item" class="lims-skeleton-card"></div>
      <div class="lims-skeleton-panel"></div>
    </div>

    <template v-else>
      <section class="lims-lab-hero glass-surface">
        <div class="lims-lab-hero-copy">
          <span class="lims-hero-eyebrow"><ExperimentOutlined /> {{ greeting }}</span>
          <h2>把今天的检验，<br />安排得更从容。</h2>
          <p>从任务分配到结果批准，每一步都有清晰的依据、进度和下一步动作。</p>
          <div class="lims-hero-actions">
            <RouterLink v-if="canOpenTasks" class="lims-primary-action" to="/hbos/lims/tasks?view=my-testing">
              继续检验 <ArrowRightOutlined />
            </RouterLink>
            <span class="lims-priority-badge"><ClockCircleOutlined /> 今天优先处理</span>
          </div>
        </div>
        <div class="lims-lab-hero-visual" aria-hidden="true">
          <img src="/assets/lims/lab-scene.svg" alt="" />
          <span class="lims-lab-orbit orbit-a"></span>
          <span class="lims-lab-orbit orbit-b"></span>
        </div>
      </section>

      <section v-if="metrics.length" class="lims-metrics" aria-label="LIMS 工作指标">
        <component
          v-for="metric in metrics"
          :key="metric.id"
          :is="canOpenTasks ? RouterLink : 'article'"
          class="lims-stat glass-surface"
          :class="[`metric-${metric.tone}`, { 'is-pending': !canOpenTasks }]"
          :to="canOpenTasks ? (metric.deepLink || '/hbos/lims/tasks?view=my-testing') : undefined"
        >
          <span>{{ metric.label }}</span>
          <strong>{{ metric.value }}</strong>
          <small>{{ metric.summaryStatus === 'attention' ? '需要关注' : '当前权限范围内' }}</small>
        </component>
      </section>

      <section v-else class="lims-dashboard-empty glass-surface" aria-live="polite">
        <ExperimentOutlined />
        <h2>当前范围暂无工作指标</h2>
        <p>没有可展示的 LIMS KPI，或服务还没有返回当前用户的工作范围。</p>
      </section>

      <section class="lims-process glass-surface" aria-label="检验流程">
        <div class="section-head">
          <div><h2>检验流程</h2><p>从任务分配到批准，每一步都保留可追溯上下文</p></div>
          <span class="lims-readonly-badge">只读概览</span>
        </div>
        <ol class="lims-process-strip">
          <li v-for="(stage, index) in processStages" :key="stage" :class="{ active: index === activeProcessIndex, done: index < activeProcessIndex }">
            <b>{{ index < activeProcessIndex ? '✓' : index + 1 }}</b><span>{{ stage }}</span>
          </li>
        </ol>
      </section>

      <div class="lims-dashboard-columns">
        <section class="section-panel glass-surface">
          <div class="section-head">
            <div><h2>接下来要做</h2><p>把样品、进度和下一步放在一起</p></div>
            <RouterLink v-if="canOpenTasks" class="lims-text-link" to="/hbos/lims/tasks?view=my-testing">查看全部任务</RouterLink>
            <span v-else class="lims-text-link pending">任务页面待接入</span>
          </div>

          <div v-if="tasks.length" class="lims-task-list">
            <component v-for="task in tasks.slice(0, 5)" :key="task.taskId" :is="canOpenTasks ? RouterLink : 'article'" class="lims-task-card" :class="{ 'is-pending': !canOpenTasks }" :to="canOpenTasks ? task.deepLink : undefined">
              <span class="lims-task-icon" :class="`priority-${task.priority}`"><ExperimentOutlined /></span>
              <span class="lims-task-content">
                <strong>{{ task.title }}</strong>
                <small>{{ task.description || 'LIMS 任务' }}</small>
                <span class="lims-task-tags">
                  <a-tag v-if="task.domainStatus" :color="task.overdue ? 'error' : 'processing'">{{ task.domainStatus }}</a-tag>
                  <a-tag v-if="task.actionLabel">{{ task.actionLabel }}</a-tag>
                </span>
              </span>
              <span class="lims-task-meta"><b :class="{ overdue: task.overdue }">{{ task.dueLabel }}</b><ArrowRightOutlined /></span>
            </component>
          </div>
          <div v-else class="lims-inline-empty">
            <InboxOutlined />
            <span>当前范围暂无待处理任务</span>
          </div>
        </section>

        <section class="section-panel glass-surface lims-context-panel">
          <div class="section-head">
            <div><h2>实验室态势</h2><p>{{ isMock ? '设计预览数据，用于检查工作节奏' : '后端字段接入后显示受控风险与分布' }}</p></div>
          </div>
          <div class="lims-context-grid">
            <article v-for="card in contextCards" :key="card.label">
              <span>{{ card.label }}</span><strong :class="`tone-${card.tone}`">{{ card.value }}</strong><small>{{ card.caption }}</small>
            </article>
          </div>
        </section>
      </div>

      <div class="lims-dashboard-lower">
        <section class="section-panel glass-surface lims-sample-panel">
          <div class="section-head">
            <div><h2>这份样品，进行到哪一步了？</h2><p>{{ currentSample ? `${currentSample.sample} · ${currentSample.material} · 批次 ${currentSample.batch}` : '等待 Provider 返回当前样品上下文' }}</p></div>
            <span v-if="currentSample" class="lims-state-pill">{{ currentSample.status }}</span>
          </div>
          <template v-if="currentSample">
            <div class="lims-sample-progress">
              <div class="lims-sample-label">
                <span>海滨实验室 · 样品标签 <DatabaseOutlined /></span>
                <strong>{{ currentSample.material }}</strong>
                <small>批号 {{ currentSample.batch }} · {{ currentSample.item }}</small>
                <i class="lims-barcode" aria-hidden="true"></i>
                <em>{{ currentSample.sample }}</em>
              </div>
              <div class="lims-sample-progress-copy">
                <span>检验进度</span><strong>{{ currentSample.progress }} / {{ currentSample.total }} 项</strong>
                <div class="lims-progress-track"><i :style="{ width: `${Math.round(currentSample.progress / currentSample.total * 100)}%` }"></i></div>
                <small>下一步：{{ currentSample.next }}</small>
              </div>
            </div>
          </template>
          <div v-else class="lims-inline-empty"><InboxOutlined /><span>当前没有返回样品详情</span></div>
        </section>

        <section class="section-panel glass-surface lims-schedule-panel">
          <div class="section-head"><div><h2>实验室日程</h2><p>{{ isMock ? '接下来需要关注的时间点' : '等待 Provider 返回日程字段' }}</p></div><CalendarOutlined /></div>
          <div v-if="scheduleItems.length" class="lims-schedule-list">
            <div v-for="item in scheduleItems" :key="item.title" class="lims-schedule-item"><span><b>{{ item.day }}</b>{{ item.when }}</span><div><strong>{{ item.title }}</strong><small>{{ item.description }}</small></div><ArrowRightOutlined /></div>
          </div>
          <div v-else class="lims-inline-empty"><CalendarOutlined /><span>当前没有可显示的日程</span></div>
        </section>
      </div>

      <section class="section-panel glass-surface lims-quick-panel">
        <div class="section-head"><div><h2>常用操作</h2><p>从这里直接进入检验员最常用的工作区域</p></div><span class="lims-readonly-badge">按权限显示</span></div>
        <div v-if="quickLinks.length" class="lims-quick-grid">
          <RouterLink v-for="link in quickLinks" :key="link.label" :to="link.path" class="lims-quick-link"><span :class="`quick-icon ${link.tone}`"><component :is="link.icon" /></span><span><strong>{{ link.label }}</strong><small>{{ link.description }}</small></span><ArrowRightOutlined /></RouterLink>
        </div>
        <div v-else class="lims-inline-empty"><SafetyCertificateOutlined /><span>当前权限范围内暂无可用操作</span></div>
      </section>
    </template>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import {
  ArrowRightOutlined,
  CalendarOutlined,
  ClockCircleOutlined,
  DatabaseOutlined,
  ExperimentOutlined,
  FileProtectOutlined,
  InboxOutlined,
  LineChartOutlined,
  ReloadOutlined,
  SafetyCertificateOutlined,
} from '@ant-design/icons-vue'
import { RouterLink } from 'vue-router'
import { usePortalStore } from '@/stores/portal'
import { resolveLimsShellCapabilities, type LimsShellCapability } from '@/services/limsCapabilities'
import { portalDataSource } from '@/services/portalProvider'
import type { SummaryMetricDTO, UnifiedTaskDTO } from '@/contracts/portal'

const portal = usePortalStore()
const errorMessage = ref('')
const loaded = ref(false)
const isMock = portalDataSource === 'mock'

const processStages = ['任务分配', '开展检验', '提交结果', '复核', '批准']
const rawMetrics = computed(() => portal.summaryMetrics.filter((metric) => metric.appId === 'lims'))
const previewMetrics: SummaryMetricDTO[] = [
  { id: 'preview-waiting', label: '待检', value: 2, appId: 'lims', tone: 'info', meta: '设计预览', scopeLabel: '检验员工作范围' },
  { id: 'preview-testing', label: '检验中', value: 1, appId: 'lims', tone: 'success', meta: '设计预览', scopeLabel: '检验员工作范围' },
  { id: 'preview-review', label: '待复核', value: 1, appId: 'lims', tone: 'warning', meta: '设计预览', scopeLabel: '检验员工作范围', summaryStatus: 'attention' },
  { id: 'preview-report', label: '待发布报告', value: 2, appId: 'lims', tone: 'neutral', meta: '设计预览', scopeLabel: '检验员工作范围' },
]
const metrics = computed(() => isMock ? previewMetrics : rawMetrics.value)
const limsCapabilities = computed(() => resolveLimsShellCapabilities(portal.apps.find((app) => app.id === 'lims'), portalDataSource))
const canOpenTasks = computed(() => limsCapabilities.value.has('tasks'))
const loading = computed(() => portal.loading || portal.summariesLoading || portal.tasksLoading || !loaded.value)
const scopeLabel = computed(() => metrics.value[0]?.scopeLabel || '由 LIMS 服务控制')
const greeting = computed(() => `上午好，${portal.user?.displayName || '检验员'}`)
const lastSyncLabel = computed(() => {
  const value = metrics.value[0]?.generatedAt
  if (!value) return '等待同步'
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString('zh-CN', { hour12: false })
})

const tasks = computed<UnifiedTaskDTO[]>(() => {
  if (isMock && portal.limsQueue.length) {
    return portal.limsQueue.map((item, index) => ({
      taskId: `preview:${item.id}`,
      appId: 'lims',
      appTitle: 'LIMS',
      title: `${item.material} · ${item.action}`,
      description: `${item.sample} · ${item.owner}`,
      priority: item.tone === 'critical' ? 'critical' : item.tone === 'warning' ? 'high' : 'normal',
      dueLabel: item.due,
      dueGroup: index < 2 ? 'today' : 'week',
      status: 'open',
      domainStatus: item.status,
      actionLabel: item.action,
      overdue: item.tone === 'critical',
      deepLink: canOpenTasks.value ? '/hbos/lims/tasks?view=my-testing' : '/hbos/lims',
    }))
  }
  return portal.tasks.filter((task) => task.appId === 'lims' && task.status !== 'done')
})

const activeProcessIndex = computed(() => {
  const status = tasks.value[0]?.domainStatus || ''
  if (status.includes('批准')) return 4
  if (status.includes('复核')) return 3
  if (status.includes('提交')) return 2
  if (status.includes('检验')) return 1
  return 0
})

const contextCards = computed(() => isMock ? [
  { label: '本周检验批量', value: '128', caption: '较上周提升 12%', tone: 'success' },
  { label: '质量放行率', value: '98.2%', caption: '较上周提升 1.1%', tone: 'info' },
  { label: '待关注样品', value: '1', caption: '优先核对 OOS 候选', tone: 'warning' },
  { label: '数据同步', value: '已同步', caption: '设计预览数据', tone: 'success' },
] : [
  { label: '超期 / OOS 风险', value: '数据待接入', caption: '等待 Provider 返回风险字段', tone: 'warning' },
  { label: '近期样品', value: '数据待接入', caption: '等待样品只读字段', tone: 'info' },
  { label: '检验组分布', value: '数据待接入', caption: '等待聚合字段', tone: 'info' },
  { label: '数据同步', value: lastSyncLabel.value, caption: '由 Provider 返回', tone: 'success' },
])

const currentSample = computed(() => isMock ? {
  sample: 'SAMPLE-001', material: '阿莫西林', batch: '26092901', item: '含量测定', status: '检验中', progress: 2, total: 5, next: '完成含量测定',
} : null)

const scheduleItems = computed(() => isMock ? [
  { day: '29', when: '今天', title: '稳定性 · 6 月取样', description: '美罗培南 · 14:00 前' },
  { day: '30', when: '明天', title: '留样 · 外观观察', description: '注射用粉针 · 3 份留样' },
] : [])

const quickLinks = computed(() => [
  { key: 'samples', label: '登记样品', description: '建立样品与批次上下文', path: '/hbos/lims/samples/new', icon: DatabaseOutlined, tone: 'green' },
  { key: 'results', label: '检验结果', description: '录入、复核并追踪结果', path: '/hbos/lims/results', icon: FileProtectOutlined, tone: 'blue' },
  { key: 'specifications', label: '查阅质量标准', description: '查看当前受控版本与限度', path: '/hbos/lims/specifications', icon: SafetyCertificateOutlined, tone: 'purple' },
  { key: 'retains', label: '留样工作台', description: '查看留样与观察任务', path: '/hbos/lims/retains', icon: InboxOutlined, tone: 'amber' },
  { key: 'stability', label: '稳定性考察', description: '安排时间点与趋势观察', path: '/hbos/lims/stability', icon: LineChartOutlined, tone: 'teal' },
].filter((link) => limsCapabilities.value.has(link.key as LimsShellCapability)))

async function loadDashboard() {
  errorMessage.value = ''
  loaded.value = false
  try {
    if (!portal.user) await portal.bootstrap()
    await Promise.all([portal.refreshSummaries(), portal.refreshTasks()])
  } catch {
    errorMessage.value = 'LIMS 工作台暂时无法加载，请稍后重试。'
  } finally {
    loaded.value = true
  }
}

onMounted(loadDashboard)
</script>
