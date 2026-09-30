<template>
  <section class="product-page lims-dashboard-v2">
    <div class="lims-dashboard-heading">
      <div>
        <span class="page-kicker">LIMS · 实验室工作台</span>
        <h1>今天，先把下一项检验做好</h1>
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
      <section v-if="metrics.length" class="lims-metrics" aria-label="LIMS 工作指标">
        <component
          v-for="metric in metrics"
          :key="metric.id"
          :is="canOpenTasks ? RouterLink : 'article'"
          class="lims-stat glass-surface"
          :class="[`metric-${metric.tone}`, { 'is-pending': !canOpenTasks }]"
          :to="canOpenTasks ? (metric.deepLink || '/hbos/lims') : undefined"
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
          <li class="active"><b>1</b><span>任务分配</span></li>
          <li><b>2</b><span>开展检验</span></li>
          <li><b>3</b><span>提交结果</span></li>
          <li><b>4</b><span>复核</span></li>
          <li><b>5</b><span>批准</span></li>
        </ol>
      </section>

      <div class="lims-dashboard-columns">
        <section class="section-panel glass-surface">
          <div class="section-head">
            <div><h2>接下来要做</h2><p>任务、样品、状态和下一步动作来自 LIMS Provider</p></div>
            <RouterLink v-if="canOpenTasks" class="lims-text-link" to="/hbos/lims/tasks?view=my-testing">查看任务</RouterLink>
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
            <div><h2>实验室态势</h2><p>后端字段接入后显示受控风险与分布</p></div>
          </div>
          <div class="lims-context-grid">
            <article><span>超期 / OOS 风险</span><strong>数据待接入</strong><small>不使用猜测数字</small></article>
            <article><span>近期样品</span><strong>数据待接入</strong><small>等待样品只读字段</small></article>
            <article><span>检验组分布</span><strong>数据待接入</strong><small>等待聚合字段</small></article>
            <article><span>数据同步</span><strong>{{ lastSyncLabel }}</strong><small>由 Provider 返回</small></article>
          </div>
        </section>
      </div>
    </template>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import {
  ArrowRightOutlined,
  ExperimentOutlined,
  InboxOutlined,
  ReloadOutlined,
} from '@ant-design/icons-vue'
import { RouterLink } from 'vue-router'
import { usePortalStore } from '@/stores/portal'
import { resolveLimsShellCapabilities } from '@/services/limsCapabilities'
import { portalDataSource } from '@/services/portalProvider'

const portal = usePortalStore()
const errorMessage = ref('')
const loaded = ref(false)

const metrics = computed(() => portal.summaryMetrics.filter((metric) => metric.appId === 'lims'))
const tasks = computed(() => portal.tasks.filter((task) => task.appId === 'lims' && task.status !== 'done'))
const canOpenTasks = computed(() => resolveLimsShellCapabilities(
  portal.apps.find((app) => app.id === 'lims'),
  portalDataSource,
).has('tasks'))
const loading = computed(() => portal.loading || portal.summariesLoading || portal.tasksLoading || !loaded.value)
const scopeLabel = computed(() => metrics.value[0]?.scopeLabel || '由 LIMS 服务控制')
const lastSyncLabel = computed(() => {
  const value = metrics.value[0]?.generatedAt
  if (!value) return '等待同步'
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString('zh-CN', { hour12: false })
})

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
