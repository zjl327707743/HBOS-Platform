<template>
  <aside class="app-local-sidebar glass-surface">
    <div class="app-local-brand">
      <div class="app-icon lims"><ExperimentOutlined /></div>
      <div>
        <strong>LIMS</strong>
        <span>实验室质量管理</span>
      </div>
    </div>

    <button class="back-workspace" type="button" @click="$router.push('/hbos')">
      <ArrowLeftOutlined /><span>返回 HBOS 工作台</span>
    </button>

    <nav>
      <div class="nav-section-label">我的工作</div>
      <a class="local-nav active"><DashboardOutlined /><span>工作台</span><b>5</b></a>
      <a class="local-nav"><ExperimentOutlined /><span>我的待检</span><b>2</b></a>
      <a class="local-nav"><CheckCircleOutlined /><span>我的复核</span><b>3</b></a>
      <a class="local-nav"><SafetyCertificateOutlined /><span>我的审批</span></a>

      <div class="nav-section-label spaced">专业业务</div>
      <a class="local-nav"><DatabaseOutlined /><span>样品与检验</span></a>
      <a class="local-nav"><FileProtectOutlined /><span>质量与报告</span></a>
      <a class="local-nav"><InboxOutlined /><span>留样管理</span></a>
      <a class="local-nav"><LineChartOutlined /><span>稳定性管理</span></a>
      <a class="local-nav"><AuditOutlined /><span>合规审计</span></a>
    </nav>

    <div class="sidebar-spacer"></div>
    <a class="local-nav management"><SettingOutlined /><span>管理后台</span><ArrowRightOutlined /></a>
  </aside>
</template>

<script setup lang="ts">
import {
  ArrowLeftOutlined,
  ArrowRightOutlined,
  AuditOutlined,
  CheckCircleOutlined,
  DashboardOutlined,
  DatabaseOutlined,
  ExperimentOutlined,
  FileProtectOutlined,
  InboxOutlined,
  LineChartOutlined,
  SafetyCertificateOutlined,
  SettingOutlined,
} from '@ant-design/icons-vue'
</script>
