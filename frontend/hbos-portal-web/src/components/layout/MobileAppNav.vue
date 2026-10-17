<template>
  <nav class="mobile-app-nav glass-surface" aria-label="LIMS 移动端导航">
    <button type="button" class="mobile-app-nav-item" @click="$router.push('/hbos')">
      <ArrowLeftOutlined /><span>HBOS</span>
    </button>
    <button type="button" class="mobile-app-nav-item active" @click="$router.push('/hbos/lims')">
      <DashboardOutlined /><span>工作台</span>
    </button>
    <button type="button" class="mobile-app-nav-item">
      <ExperimentOutlined /><span>待检</span>
    </button>
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
      <button type="button"><DashboardOutlined />工作台</button>
      <button type="button"><ExperimentOutlined />我的待检</button>
      <button type="button"><CheckCircleOutlined />我的复核</button>
      <button type="button"><SafetyCertificateOutlined />我的审批</button>

      <div class="nav-section-label spaced">专业业务</div>
      <button type="button">样品与检验</button>
      <button type="button">质量与报告</button>
      <button type="button">留样管理</button>
      <button type="button">稳定性管理</button>
      <button type="button">合规审计</button>
    </div>
  </a-drawer>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import {
  ArrowLeftOutlined,
  CheckCircleOutlined,
  DashboardOutlined,
  ExperimentOutlined,
  MenuOutlined,
  SafetyCertificateOutlined,
} from '@ant-design/icons-vue'

const drawerOpen = ref(false)
</script>
