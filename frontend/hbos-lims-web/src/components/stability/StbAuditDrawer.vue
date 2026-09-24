<template>
  <a-drawer v-model:open="open" title="合规审计日志" :width="560" placement="right">
    <p class="stb-gate-sub">
      {{ docName ? `对象 ${docName}` : '稳定性板块' }} · 数据来自 HBOS Audit Log（write-once）
    </p>
    <a-spin :spinning="loading">
      <div class="stb-drawer-section">
        <h3>最近事件（{{ total }} 条）</h3>
        <a-empty
          v-if="!loading && !events.length"
          description="暂无审计事件"
          :image="Empty.PRESENTED_IMAGE_SIMPLE"
        />
        <div v-for="e in events" :key="e.name" class="stb-audit-line">
          <span class="stb-audit-dot" :class="dotClass(e.log_type)"></span>
          <div>
            <strong>{{ e.log_type }} · {{ e.action_text || '—' }}</strong>
            <span>
              {{ e.doctype_target }} / {{ e.doc_name }} · {{ e.user }} · {{ e.created_at }}
            </span>
            <span v-if="e.reason">原因：{{ e.reason }}</span>
          </div>
        </div>
      </div>
    </a-spin>
    <div class="stb-notice">
      稳定性审计沿用既有 <span class="mono">HBOS Audit Log</span>，不另建专属审计页面；
      完整筛选与分页见合规审计日志页。
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
import { Empty } from 'ant-design-vue'
import { audit, type AuditEvent } from '@/api/stability'

const open = ref(false)
const loading = ref(false)
const events = ref<AuditEvent[]>([])
const total = ref(0)
const docName = ref<string | undefined>(undefined)

async function show(name?: string) {
  open.value = true
  docName.value = name
  loading.value = true
  try {
    const res = await audit(name, 20)
    events.value = res.events
    total.value = res.total
  } catch {
    // 具体错误已由 client 拦截层弹出
  } finally {
    loading.value = false
  }
}
defineExpose({ show })

function dotClass(logType: string): string {
  if (logType === 'SoD 拦截' || logType === '越权拦截' || logType === '删除拦截') return 'red'
  if (logType === '驳回' || logType === '方案作废' || logType === '通知单取消') return 'amber'
  if (logType === '通知单批准' || logType === '方案批准') return ''
  return 'gray'
}
</script>

<style scoped>
.stb-gate-sub { font-size: 12px; color: var(--muted); margin-bottom: 12px; }
.stb-audit-line span { display: block; }
</style>
