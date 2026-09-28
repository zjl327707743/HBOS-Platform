<template>
  <section class="section-panel glass-surface">
    <div class="section-head">
      <div>
        <h2>业务脉搏</h2>
        <p>根据当前用户可见能力动态出现</p>
      </div>
      <a-segmented v-model:value="range" :options="['本周', '本月']" size="small" />
    </div>

    <div class="pulse-grid">
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
  </section>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import type { BusinessPulseDTO } from '@/contracts/portal'

defineProps<{ items: BusinessPulseDTO[] }>()
const range = ref('本周')

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
