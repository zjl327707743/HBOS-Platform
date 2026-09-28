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
      <button type="button" class="local-nav active" title="工作台"><DashboardOutlined /><span>工作台</span><b>5</b></button>
      <button type="button" class="local-nav" title="我的待检"><ExperimentOutlined /><span>我的待检</span><b>2</b></button>
      <button type="button" class="local-nav" title="我的复核"><CheckCircleOutlined /><span>我的复核</span><b>3</b></button>
      <button type="button" class="local-nav" title="我的审批"><SafetyCertificateOutlined /><span>我的审批</span></button>

      <div class="nav-section-label spaced">专业业务</div>
      <button type="button" class="local-nav" title="样品与检验"><DatabaseOutlined /><span>样品与检验</span></button>
      <button type="button" class="local-nav" title="质量与报告"><FileProtectOutlined /><span>质量与报告</span></button>
      <button type="button" class="local-nav" title="留样管理"><InboxOutlined /><span>留样管理</span></button>
      <button type="button" class="local-nav" title="稳定性管理"><LineChartOutlined /><span>稳定性管理</span></button>
      <button type="button" class="local-nav" title="合规审计"><AuditOutlined /><span>合规审计</span></button>
    </nav>

    <div class="sidebar-spacer"></div>
    <button type="button" class="local-nav management" title="管理后台"><SettingOutlined /><span>管理后台</span><ArrowRightOutlined /></button>
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
