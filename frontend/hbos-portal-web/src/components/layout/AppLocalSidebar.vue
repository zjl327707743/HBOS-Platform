<template>
  <aside class="app-local-sidebar glass-surface" aria-label="LIMS 应用导航">
    <div class="app-local-brand">
      <div class="app-icon lims"><ExperimentOutlined /></div>
      <div>
        <strong>LIMS</strong>
        <span>实验室质量管理</span>
      </div>
    </div>

    <button class="back-workspace" type="button" title="返回 HBOS 工作台" @click="$router.push('/hbos')">
      <ArrowLeftOutlined /><span>返回 HBOS 工作台</span>
    </button>

    <nav>
      <div class="nav-section-label">我的工作</div>
      <RouterLink v-if="limsCapabilities.has('dashboard')" class="local-nav" to="/hbos/lims" exact-active-class="active" title="工作台"><DashboardOutlined /><span>工作台</span></RouterLink>
      <template v-if="limsCapabilities.has('tasks')">
        <RouterLink class="local-nav" :class="{ active: isTaskView('my-testing') }" to="/hbos/lims/tasks?view=my-testing" title="我的待检"><ExperimentOutlined /><span>我的待检</span></RouterLink>
        <RouterLink class="local-nav" :class="{ active: isTaskView('my-review') }" to="/hbos/lims/tasks?view=my-review" title="我的复核"><CheckCircleOutlined /><span>我的复核</span></RouterLink>
        <RouterLink class="local-nav" :class="{ active: isTaskView('my-approval') }" to="/hbos/lims/tasks?view=my-approval" title="我的审批"><SafetyCertificateOutlined /><span>我的审批</span></RouterLink>
      </template>

      <div class="nav-section-label spaced">专业业务</div>
      <RouterLink v-if="limsCapabilities.has('samples')" class="local-nav" to="/hbos/lims/samples" exact-active-class="active" title="样品与检验"><DatabaseOutlined /><span>样品与检验</span></RouterLink>
      <RouterLink v-if="limsCapabilities.has('results')" class="local-nav" to="/hbos/lims/results" exact-active-class="active" title="质量与报告"><FileProtectOutlined /><span>质量与报告</span></RouterLink>
      <RouterLink v-if="limsCapabilities.has('ledger')" class="local-nav" to="/hbos/lims/ledger" exact-active-class="active" title="检验结果台账"><FileProtectOutlined /><span>检验结果台账</span></RouterLink>
      <RouterLink v-if="limsCapabilities.has('coa')" class="local-nav" to="/hbos/lims/coa" exact-active-class="active" title="检验报告"><FileTextOutlined /><span>检验报告</span></RouterLink>
      <RouterLink v-if="limsCapabilities.has('specifications')" class="local-nav" to="/hbos/lims/specifications" exact-active-class="active" title="质量标准"><BookOutlined /><span>质量标准</span></RouterLink>
      <template v-if="limsCapabilities.has('retains')">
        <RouterLink class="local-nav" to="/hbos/lims/retains" exact-active-class="active" title="留样工作台"><InboxOutlined /><span>留样工作台</span></RouterLink>
        <RouterLink class="local-nav local-nav-child" to="/hbos/lims/retains/samples" exact-active-class="active" title="留样登记与台账"><DatabaseOutlined /><span>登记与台账</span></RouterLink>
        <RouterLink class="local-nav local-nav-child" to="/hbos/lims/retains/observations" exact-active-class="active" title="观察任务"><ExperimentOutlined /><span>观察任务</span></RouterLink>
        <RouterLink class="local-nav local-nav-child" to="/hbos/lims/retains/usage" exact-active-class="active" title="使用申请"><FileProtectOutlined /><span>使用申请</span></RouterLink>
        <RouterLink class="local-nav local-nav-child" to="/hbos/lims/retains/disposal" exact-active-class="active" title="处理申请"><SafetyCertificateOutlined /><span>处理申请</span></RouterLink>
      </template>
      <template v-if="limsCapabilities.has('stability')">
        <RouterLink class="local-nav" to="/hbos/lims/stability" exact-active-class="active" title="稳定性工作台"><LineChartOutlined /><span>稳定性工作台</span></RouterLink>
        <RouterLink class="local-nav local-nav-child" to="/hbos/lims/stability/schedule" exact-active-class="active" title="取样与检测计划"><ClockCircleOutlined /><span>取样与检测计划</span></RouterLink>
        <RouterLink class="local-nav local-nav-child" to="/hbos/lims/stability/samples" exact-active-class="active" title="样品入箱台账"><DatabaseOutlined /><span>样品入箱台账</span></RouterLink>
        <RouterLink class="local-nav local-nav-child" to="/hbos/lims/stability/results" exact-active-class="active" title="稳定性结果"><FileProtectOutlined /><span>稳定性结果</span></RouterLink>
        <RouterLink class="local-nav local-nav-child" to="/hbos/lims/stability/trend" exact-active-class="active" title="趋势分析"><LineChartOutlined /><span>趋势分析</span></RouterLink>
      </template>
      <RouterLink v-if="limsCapabilities.has('audit')" class="local-nav" to="/hbos/lims/audit" exact-active-class="active" title="合规审计"><AuditOutlined /><span>合规审计</span></RouterLink>
    </nav>

    <div class="sidebar-spacer"></div>
  </aside>
</template>

<script setup lang="ts">
import {
  ArrowLeftOutlined,
  BookOutlined,
  AuditOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  DashboardOutlined,
  DatabaseOutlined,
  ExperimentOutlined,
  FileProtectOutlined,
  FileTextOutlined,
  InboxOutlined,
  LineChartOutlined,
  SafetyCertificateOutlined,
} from '@ant-design/icons-vue'
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { usePortalStore } from '@/stores/portal'
import { resolveLimsShellCapabilities } from '@/services/limsCapabilities'
import { portalDataSource } from '@/services/portalProvider'

const portal = usePortalStore()
const route = useRoute()
const limsCapabilities = computed(() =>
  resolveLimsShellCapabilities(
    portal.apps.find((app) => app.id === 'lims'),
    portalDataSource,
  ),
)

function isTaskView(view: string) {
  return route.path === '/hbos/lims/tasks' && route.query.view === view
}
</script>
