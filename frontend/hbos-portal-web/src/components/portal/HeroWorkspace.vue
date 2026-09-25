<template>
  <section class="hero-workspace glass-hero">
    <div class="hero-main">
      <div class="eyebrow">HBOS · 企业运营工作空间</div>
      <div class="hello">晚上好，{{ userName }}</div>
      <h1>今天有 <span>{{ totalActions }} 项工作</span><br />需要你处理</h1>
      <p>
        清晰、明亮的信息层级为主体，叠加动态玻璃、沉浸式渐变和适度的空间感；
        第一眼先看到“我的事情”，而不是 ERP 对象。
      </p>

      <div class="hero-actions">
        <a-button type="primary" size="large" @click="$router.push('/hbos/work')">进入我的工作</a-button>
        <a-button size="large" @click="$router.push('/hbos/apps')">查看应用中心</a-button>
      </div>

      <div class="hero-metrics">
        <article v-for="metric in metrics" :key="metric.id" class="metric-glass">
          <strong :class="`tone-${metric.tone}`">{{ metric.value }}</strong>
          <span>{{ metric.label }}</span>
          <small>{{ metric.meta }}</small>
        </article>
      </div>
    </div>

    <aside class="hero-aside">
      <div class="status-glass">
        <div class="status-title">
          <span>工作台状态</span>
          <a-tag color="success">已连接</a-tag>
        </div>
        <div class="status-row"><i class="blue"></i><span>统一身份与会话</span><b>已连接</b></div>
        <div class="status-row"><i class="violet"></i><span>我的可用应用</span><b>{{ appCount }}</b></div>
        <div class="status-row"><i class="green"></i><span>需要我处理</span><b>{{ totalActions }}</b></div>
      </div>

      <div v-if="showTwinPreview" class="mini-twin-glass">
        <div class="status-title">
          <span>数字孪生概览</span>
          <a-tag color="processing">LIVE READY</a-tag>
        </div>
        <svg viewBox="0 0 420 160" fill="none" aria-label="数字孪生概览示意">
          <defs>
            <linearGradient id="hero-line" x1="0" x2="1">
              <stop stop-color="#6c63ff"/>
              <stop offset=".58" stop-color="#48a8ff"/>
              <stop offset="1" stop-color="#45d7bd"/>
            </linearGradient>
          </defs>
          <path d="M32 119 L137 61 L245 92 L341 46" stroke="url(#hero-line)" stroke-width="3" stroke-dasharray="8 8"/>
          <circle cx="137" cy="61" r="6" fill="#6c63ff"/>
          <circle cx="245" cy="92" r="6" fill="#48a8ff"/>
          <circle cx="341" cy="46" r="6" fill="#45d7bd"/>
          <rect x="111" y="70" width="48" height="55" rx="8" class="twin-box violet"/>
          <rect x="220" y="100" width="52" height="57" rx="8" class="twin-box blue"/>
          <rect x="317" y="56" width="48" height="52" rx="8" class="twin-box green"/>
        </svg>
      </div>
    </aside>
  </section>
</template>

<script setup lang="ts">
import type { SummaryMetricDTO } from '@/contracts/portal'

defineProps<{
  userName: string
  totalActions: number
  metrics: SummaryMetricDTO[]
  appCount: number
  showTwinPreview: boolean
}>()
</script>
