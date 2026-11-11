<template>
  <section class="section-panel glass-surface">
    <div class="section-head">
      <div>
        <h2>业务概览</h2>
        <p>查看你有权使用的业务汇总</p>
      </div>
      <a-tag v-if="live" color="success">真实汇总</a-tag>
      <a-tag v-else>Mock · 演示汇总</a-tag>
    </div>

    <PortalState v-if="error" kind="error" title="部分业务汇总暂时不可用" :description="error" retry @retry="$emit('retry')" />
    <div v-if="loading" class="pulse-grid pulse-loading" aria-label="正在读取业务汇总">
      <article v-for="index in 4" :key="index" class="pulse-card"><a-skeleton active :paragraph="false" /></article>
    </div>
    <div v-else-if="items.length" class="pulse-grid">
      <article v-for="item in items" :key="item.id" class="pulse-card">
        <span>{{ item.label }}</span>
        <strong>{{ item.value }}</strong>
        <small :class="`tone-${item.tone || 'neutral'}`">{{ item.trend }}</small>
        <svg v-if="item.sparkline" class="spark" viewBox="0 0 110 58" preserveAspectRatio="none">
          <polyline :points="points(item.sparkline)" fill="none" stroke="url(#spark-gradient)" stroke-width="2.6" />
          <defs>
            <linearGradient id="spark-gradient" x1="0" x2="1">
              <stop stop-color="#6c63ff" />
              <stop offset="1" stop-color="#47cdbd" />
            </linearGradient>
          </defs>
        </svg>
      </article>
    </div>
    <div v-else-if="!error" class="home-panel-empty">
      <BarChartOutlined />
      <strong>当前没有可展示的业务汇总</strong>
      <span>有业务数据且当前账号获准查看时，会显示相应汇总。</span>
    </div>
  </section>
</template>

<script setup lang="ts">
import PortalState from './PortalState.vue'
import { BarChartOutlined } from '@ant-design/icons-vue'
import type { BusinessPulseDTO } from '@/contracts/portal'

withDefaults(defineProps<{
  items: BusinessPulseDTO[]
  loading?: boolean
  live?: boolean
  error?: string | null
}>(), {
  loading: false,
  live: false,
})
defineEmits<{ retry: [] }>()

function points(values: number[]) {
  const min = Math.min(...values)
  const max = Math.max(...values)
  const span = Math.max(max - min, 1)
  return values.map((value, index) => {
    const x = (index / Math.max(values.length - 1, 1)) * 108 + 1
    const y = 52 - ((value - min) / span) * 43
    return `${x},${y}`
  }).join(' ')
}
</script>
