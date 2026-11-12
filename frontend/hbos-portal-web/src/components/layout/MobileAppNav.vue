<template>
  <nav class="mobile-app-nav glass-surface" aria-label="LIMS 移动端导航">
    <RouterLink class="mobile-app-nav-item" to="/hbos" exact-active-class="active">
      <ArrowLeftOutlined /><span>HBOS</span>
    </RouterLink>
    <RouterLink class="mobile-app-nav-item" to="/hbos/lims" exact-active-class="active">
      <DashboardOutlined /><span>工作台</span>
    </RouterLink>
    <RouterLink v-if="limsCapabilities.has('tasks')" class="mobile-app-nav-item" :class="{ active: isTaskView('my-testing') }" to="/hbos/lims/tasks?view=my-testing">
      <ExperimentOutlined /><span>待检</span>
    </RouterLink>
    <button type="button" class="mobile-app-nav-item" @click="drawerOpen = true">
      <MenuOutlined /><span>菜单</span>
    </button>
  </nav>

  <a-drawer
    v-model:open="drawerOpen"
    title="LIMS 导航"
    placement="bottom"
    height="70vh"
    root-class-name="mobile-lims-drawer"
  >
    <div class="mobile-local-menu">
      <div class="nav-section-label">我的工作</div>
      <RouterLink v-if="limsCapabilities.has('dashboard')" to="/hbos/lims" exact-active-class="active" @click="closeDrawer"><DashboardOutlined />工作台</RouterLink>
      <template v-if="limsCapabilities.has('tasks')">
        <RouterLink :class="{ active: isTaskView('my-testing') }" to="/hbos/lims/tasks?view=my-testing" @click="closeDrawer"><ExperimentOutlined />我的待检</RouterLink>
        <RouterLink :class="{ active: isTaskView('my-review') }" to="/hbos/lims/tasks?view=my-review" @click="closeDrawer"><CheckCircleOutlined />我的复核</RouterLink>
        <RouterLink :class="{ active: isTaskView('my-approval') }" to="/hbos/lims/tasks?view=my-approval" @click="closeDrawer"><SafetyCertificateOutlined />我的审批</RouterLink>
      </template>

      <div class="nav-section-label spaced">专业业务</div>
      <RouterLink v-if="limsCapabilities.has('samples')" to="/hbos/lims/samples" exact-active-class="active" @click="closeDrawer"><DatabaseOutlined />样品与检验</RouterLink>
      <RouterLink v-if="limsCapabilities.has('results')" to="/hbos/lims/results" exact-active-class="active" @click="closeDrawer"><FileProtectOutlined />质量与报告</RouterLink>
      <RouterLink v-if="limsCapabilities.has('ledger')" to="/hbos/lims/ledger" exact-active-class="active" @click="closeDrawer"><FileProtectOutlined />检验结果台账</RouterLink>
      <RouterLink v-if="limsCapabilities.has('coa')" to="/hbos/lims/coa" exact-active-class="active" @click="closeDrawer"><FileTextOutlined />检验报告</RouterLink>
      <RouterLink v-if="limsCapabilities.has('specifications')" to="/hbos/lims/specifications" exact-active-class="active" @click="closeDrawer"><BookOutlined />质量标准</RouterLink>
      <template v-if="limsCapabilities.has('retains')">
        <RouterLink to="/hbos/lims/retains" exact-active-class="active" @click="closeDrawer"><InboxOutlined />留样工作台</RouterLink>
        <RouterLink to="/hbos/lims/retains/samples" exact-active-class="active" @click="closeDrawer"><DatabaseOutlined />登记与台账</RouterLink>
        <RouterLink to="/hbos/lims/retains/observations" exact-active-class="active" @click="closeDrawer"><ExperimentOutlined />观察任务</RouterLink>
        <RouterLink to="/hbos/lims/retains/usage" exact-active-class="active" @click="closeDrawer"><FileProtectOutlined />使用申请</RouterLink>
        <RouterLink to="/hbos/lims/retains/disposal" exact-active-class="active" @click="closeDrawer"><SafetyCertificateOutlined />处理申请</RouterLink>
      </template>
      <template v-if="limsCapabilities.has('stability')">
        <RouterLink to="/hbos/lims/stability" exact-active-class="active" @click="closeDrawer"><LineChartOutlined />稳定性工作台</RouterLink>
        <RouterLink to="/hbos/lims/stability/schedule" exact-active-class="active" @click="closeDrawer"><ClockCircleOutlined />取样与检测计划</RouterLink>
        <RouterLink to="/hbos/lims/stability/samples" exact-active-class="active" @click="closeDrawer"><DatabaseOutlined />样品入箱台账</RouterLink>
        <RouterLink to="/hbos/lims/stability/results" exact-active-class="active" @click="closeDrawer"><FileProtectOutlined />稳定性结果</RouterLink>
        <RouterLink to="/hbos/lims/stability/trend" exact-active-class="active" @click="closeDrawer"><LineChartOutlined />趋势分析</RouterLink>
      </template>
      <RouterLink v-if="limsCapabilities.has('audit')" to="/hbos/lims/audit" exact-active-class="active" @click="closeDrawer"><AuditOutlined />合规审计</RouterLink>
    </div>
  </a-drawer>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRoute } from 'vue-router'
import {
  ArrowLeftOutlined,
  BookOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  DashboardOutlined,
  DatabaseOutlined,
  ExperimentOutlined,
  FileProtectOutlined,
  FileTextOutlined,
  InboxOutlined,
  LineChartOutlined,
  MenuOutlined,
  SafetyCertificateOutlined,
  AuditOutlined,
} from '@ant-design/icons-vue'
import { usePortalStore } from '@/stores/portal'
import { resolveLimsShellCapabilities } from '@/services/limsCapabilities'
import { portalDataSource } from '@/services/portalProvider'

const drawerOpen = ref(false)
const portal = usePortalStore()
const route = useRoute()
const limsCapabilities = computed(() =>
  resolveLimsShellCapabilities(
    portal.apps.find((app) => app.id === 'lims'),
    portalDataSource,
  ),
)

function closeDrawer() {
  drawerOpen.value = false
}

function isTaskView(view: string) {
  return route.path === '/hbos/lims/tasks' && route.query.view === view
}
</script>
