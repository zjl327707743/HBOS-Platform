<template>
  <a-drawer v-model:open="open" title="合规审计日志" :width="520" placement="right">
    <p class="stb-gate-sub">沿用现有 LIMS 审计入口 · 原型摘要</p>
    <div class="stb-drawer-section">
      <h3>最近事件</h3>
      <div v-for="(e, i) in AUDIT_SUMMARY" :key="i" class="stb-audit-line">
        <span class="stb-audit-dot" :class="dotClass(e.tone)"></span>
        <div>
          <strong>{{ e.title }}</strong>
          <span>{{ e.desc }}</span>
        </div>
      </div>
    </div>
    <div class="stb-notice">
      原型只展示摘要；正式页面复用既有 <span class="mono">HBOS Audit Log</span> 查询能力，不另建稳定性专属审计页面。
    </div>
    <template #footer>
      <a-button @click="open = false">关闭</a-button>
      <router-link to="/audit-log">
        <a-button type="primary">查看完整审计</a-button>
      </router-link>
    </template>
  </a-drawer>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { AUDIT_SUMMARY, type Tone } from '@/demo/stabilityDemo'

const open = ref(false)

function show() {
  open.value = true
}
defineExpose({ show })

function dotClass(tone: Tone): string {
  if (tone === 'warn') return 'amber'
  if (tone === 'danger') return 'red'
  return ''
}
</script>

<style scoped>
.stb-gate-sub { font-size: 12px; color: var(--muted); margin-bottom: 12px; }
</style>
