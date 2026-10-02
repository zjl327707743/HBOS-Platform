<template>
  <section class="product-page app-product-page">
    <div class="lims-app-hero glass-hero">
      <div>
        <span class="page-kicker">LIMS · MY LAB</span>
        <h1>我的实验室</h1>
        <p>进入业务应用后，视觉从 V3 Portal 收敛到 V2 Dashboard：仍属于 HBOS，但信息密度更高、操作更专业。</p>
      </div>
      <a-space>
        <a-button>查看全部样品</a-button>
        <a-button type="primary"><PlusOutlined /> 登记样品</a-button>
      </a-space>
    </div>

    <div class="lims-metrics">
      <article class="lims-stat glass-surface"><span>我的待检</span><strong>2</strong><small>1 项今天截止</small></article>
      <article class="lims-stat glass-surface"><span>待复核</span><strong>3</strong><small>1 项已超期</small></article>
      <article class="lims-stat glass-surface"><span>待 QA</span><strong>2</strong><small>COA / 结果</small></article>
      <article class="lims-stat glass-surface"><span>稳定性风险</span><strong>1</strong><small>本周时间点</small></article>
    </div>

    <div class="lims-dashboard-grid">
      <section class="section-panel glass-surface">
        <div class="section-head">
          <div><h2>我的工作队列</h2><p>根据当前 Session、角色、SoD 与业务状态实时投影</p></div>
          <a-button type="link">全部待办 <RightOutlined /></a-button>
        </div>

        <a-table :data-source="portal.limsQueue" :pagination="false" row-key="id" size="middle">
          <a-table-column title="样品" data-index="sample" key="sample">
            <template #default="{ record }">
              <strong>{{ record.sample }}</strong><div class="table-sub">{{ record.material }}</div>
            </template>
          </a-table-column>
          <a-table-column title="动作" data-index="action" key="action" />
          <a-table-column title="归属" data-index="owner" key="owner" />
          <a-table-column title="截止" data-index="due" key="due" />
          <a-table-column title="状态" data-index="status" key="status">
            <template #default="{ record }"><a-tag :color="tagColor(record.tone)">{{ record.status }}</a-tag></template>
          </a-table-column>
          <a-table-column title="" key="go">
            <template #default><a-button type="link">处理 <ArrowRightOutlined /></a-button></template>
          </a-table-column>
        </a-table>
      </section>

      <section class="section-panel glass-surface lab-pulse">
        <div class="section-head">
          <div><h2>实验室态势</h2><p>仅显示 LIMS 自己的业务指标</p></div>
        </div>
        <div class="lab-pulse-grid">
          <div><span>今日登记</span><strong>18</strong><small class="tone-success">↑ 4</small></div>
          <div><span>检验中</span><strong>24</strong><small>当前</small></div>
          <div><span>OOS 候选</span><strong class="tone-critical">1</strong><small>需关注</small></div>
          <div><span>今日发布 COA</span><strong>9</strong><small class="tone-success">正常</small></div>
        </div>
        <div class="mini-chart">
          <div class="chart-title">近 7 日任务完成</div>
          <svg viewBox="0 0 320 120" preserveAspectRatio="none">
            <defs><linearGradient id="area" x1="0" x2="0" y1="0" y2="1"><stop stop-color="#22b98c" stop-opacity=".28"/><stop offset="1" stop-color="#22b98c" stop-opacity=".02"/></linearGradient></defs>
            <path d="M0 90 C40 82,45 62,78 68 S120 42,156 50 S205 30,235 38 S278 20,320 25 L320 120 L0 120 Z" fill="url(#area)"/>
            <path d="M0 90 C40 82,45 62,78 68 S120 42,156 50 S205 30,235 38 S278 20,320 25" fill="none" stroke="#19b889" stroke-width="3"/>
          </svg>
        </div>
      </section>
    </div>

    <section class="section-panel glass-surface">
      <div class="section-head">
        <div><h2>专业工作区</h2><p>Local Navigation 组织业务域，Portal 不把这些菜单塞进企业一级导航</p></div>
      </div>
      <div class="professional-grid">
        <article><ExperimentOutlined /><strong>检验业务</strong><span>样品、任务与检验结果</span></article>
        <article><FileProtectOutlined /><strong>质量与报告</strong><span>OOS、COA、质量标准</span></article>
        <article><InboxOutlined /><strong>留样</strong><span>留样台账、观察、使用与处理</span></article>
        <article><LineChartOutlined /><strong>稳定性</strong><span>方案、时间点、结果与报告</span></article>
        <article><AuditOutlined /><strong>合规</strong><span>审计与追踪</span></article>
      </div>
    </section>
  </section>
</template>

<script setup lang="ts">
import {
  ArrowRightOutlined,
  AuditOutlined,
  ExperimentOutlined,
  FileProtectOutlined,
  InboxOutlined,
  LineChartOutlined,
  PlusOutlined,
  RightOutlined,
} from '@ant-design/icons-vue'
import { usePortalStore } from '@/stores/portal'
import type { Tone } from '@/contracts/portal'

const portal = usePortalStore()

function tagColor(tone: Tone) {
  return { critical: 'error', warning: 'warning', success: 'success', info: 'processing', neutral: 'default' }[tone]
}
</script>
