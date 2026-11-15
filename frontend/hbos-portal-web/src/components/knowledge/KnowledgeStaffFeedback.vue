<script setup lang="ts">
import { MessageOutlined, ReloadOutlined } from '@ant-design/icons-vue'
import { ref, watch } from 'vue'
import PortalSelect from '@/components/portal/PortalSelect.vue'
import type { MaintenanceFeedback } from '@/services/knowledgeMaintenanceApi'

const props = defineProps<{
  items: MaintenanceFeedback[]; status: string; page: number; hasMore: boolean; loading: boolean; failed: boolean
  query: string; searchUnsupported: boolean
}>()
const emit = defineEmits<{
  'update:status': [status: string]
  'update:page': [page: number]
  'update:query': [query: string]
  search: []
  refresh: []
  open: [item: MaintenanceFeedback]
}>()
const draft = ref(props.query)
watch(() => props.query, value => { draft.value = value })
let lastSearchAt = 0
function submitSearch() {
  // Ant Input.Search emits `search` on Enter/icon click; the wrapper keydown below is a
  // deterministic fallback for headless/CDP input. Collapse the two paths into one request.
  const now = Date.now()
  if (now - lastSearchAt < 120) return
  lastSearchAt = now
  emit('update:query', draft.value.trim())
  emit('search')
}
function clearFilters() {
  draft.value = ''
  emit('update:query', '')
  emit('update:status', '')
  emit('search')
}
const statuses = [
  { value: '', label: '全部状态' },
  { value: 'Pending', label: '待处理' },
  { value: 'In Review', label: '处理中' },
  { value: 'Resolved', label: '已回复' },
]
function statusLabel(status: string) {
  return statuses.find(item => item.value === status)?.label ?? '状态待核对'
}
</script>

<template>
  <section class="v17-panel hbos-glass-g1 kb-staff-feedback" aria-labelledby="kb-staff-feedback-title" :aria-busy="loading">
    <header class="kb-staff-feedback-heading">
      <div class="kb-staff-feedback-title">
        <h2 id="kb-staff-feedback-title">反馈清单</h2>
        <span v-if="!loading && !failed" class="kb-staff-feedback-count">本页 {{ items.length }} 项</span>
      </div>
      <a-button class="kb-staff-refresh" aria-label="刷新反馈" :loading="loading" @click="emit('refresh')"><ReloadOutlined /><span>刷新反馈</span></a-button>
    </header>
    <div class="kb-staff-feedback-tools">
      <span class="kb-staff-search" @keydown.enter.prevent="submitSearch">
        <a-input-search :value="draft" aria-label="搜索员工反馈" placeholder="搜索反馈内容" :maxlength="120"
          allow-clear @update:value="draft = $event" @search="submitSearch" />
      </span>
      <PortalSelect :value="status" :options="statuses" aria-label="筛选反馈状态"
        @change="emit('update:status', $event)" />
      <a-button v-if="status || query" type="text" @click="clearFilters">清除筛选</a-button>
    </div>
    <p v-if="searchUnsupported" id="kb-staff-search-limit" class="kb-muted" data-v17-feedback-search-limitation>当前候选尚未提供内容搜索；已保留状态筛选与真实分页，请清除搜索后继续。</p>
    <p v-else class="kb-muted kb-staff-feedback-hint">内容搜索由服务端有界过滤，不会在浏览器扫描全量反馈。</p>
    <a-skeleton v-if="loading" active />
    <template v-else-if="!failed && items.length">
      <div class="kb-staff-feedback-columns" aria-hidden="true">
        <span class="kb-staff-copy">反馈内容</span>
        <span class="kb-staff-status">当前状态</span>
        <span class="kb-staff-action">操作</span>
      </div>
      <div class="kb-staff-feedback-list">
        <article v-for="item in items" :key="item.id" class="kb-staff-feedback-item">
          <span class="kb-staff-icon" aria-hidden="true"><MessageOutlined /></span>
          <div class="kb-staff-copy">
            <strong>{{ item.note || item.category }}</strong>
            <p>{{ item.category }}</p>
          </div>
          <div class="kb-staff-status">
            <a-tag :color="item.status === 'Resolved' ? 'green' : item.status === 'Pending' ? 'orange' : 'blue'">{{ statusLabel(item.status) }}</a-tag>
          </div>
          <div class="kb-staff-action">
            <a-button size="small" @click="emit('open', item)">{{ item.status === 'Resolved' ? '查看回复' : '处理反馈' }}</a-button>
          </div>
        </article>
      </div>
    </template>
    <a-empty v-else-if="!failed" :description="status || query ? '没有匹配的反馈' : '当前没有员工反馈'">
      <a-button v-if="status || query" @click="clearFilters">清除筛选</a-button>
    </a-empty>
    <div v-if="page > 1 || hasMore" class="v17-pagination">
      <span>第 {{ page }} 页</span>
      <div>
        <button type="button" :disabled="page <= 1 || loading" @click="emit('update:page', page - 1)">上一页</button>
        <button type="button" :disabled="!hasMore || loading" @click="emit('update:page', page + 1)">下一页</button>
      </div>
    </div>
  </section>
</template>

<style scoped>
.kb-staff-feedback {
  --feedback-icon: 36px;
  --feedback-state: 112px;
  --feedback-action: 110px;
  --feedback-gap: 15px;
}
.kb-staff-feedback-heading { display: flex; align-items: center; justify-content: space-between; gap: 10px; margin-bottom: 16px; }
/* P09: match the v1.7 fixed first-row anchor at each measured breakpoint; this only
   adjusts the gap after the heading (and one hint margin at desktop), not the catalog. */
@media (max-width: 389px) { .kb-staff-feedback-heading { margin-bottom: 2px; } }
@media (min-width: 390px) and (max-width: 1164px) { .kb-staff-feedback-heading { margin-bottom: 12px; } }
@media (min-width: 1165px) { .kb-staff-feedback-heading { margin-bottom: 0; } .kb-staff-feedback-tools + p { margin-bottom: 11px; } }
.kb-staff-feedback-title h2 { margin: 0; font-size: 18px; }
.kb-staff-feedback-title { display: flex; align-items: center; gap: 10px; white-space: nowrap; }
.kb-staff-feedback-count { color: #526984; background: #eef2f8; border-radius: 12px; padding: 2px 8px; font-size: 11px; }
.kb-staff-feedback-tools { display: flex; align-items: center; flex-wrap: wrap; gap: 12px; }
.kb-staff-feedback-tools > :first-child { flex: 1 1 230px; min-width: 0; }
.kb-staff-feedback-tools :deep(.v10-choice) { flex: 0 1 170px; }
.kb-staff-feedback-tools + p { margin: 8px 0 12px; font-size: 12px; }
.kb-staff-feedback-columns, .kb-staff-feedback-item {
  display: grid;
  grid-template-columns: var(--feedback-icon) minmax(0, 1fr) var(--feedback-state) var(--feedback-action);
  gap: var(--feedback-gap);
  align-items: center;
  border-bottom: 1px solid #e6ebf3;
}
.kb-staff-feedback-columns { padding: 12px 0; color: #596b84; font-size: 11px; }
.kb-staff-feedback-item { min-height: 94px; padding: 16px 0; }
.kb-staff-feedback-item:last-child { border-bottom: 0; }
.kb-staff-copy { grid-column: 2; min-width: 0; overflow-wrap: anywhere; }
.kb-staff-copy strong { color: #354d6c; font-size: 14px; line-height: 1.75; font-weight: 600; white-space: pre-wrap; }
.kb-staff-copy p { margin: 4px 0 0; color: #596b84; font-size: 12px; }
.kb-staff-icon { display: grid; place-items: center; width: var(--feedback-icon); height: 38px; border-radius: 11px; background: #ede9fb; color: #6550c3; }
.kb-staff-status { grid-column: 3; }
.kb-staff-action { grid-column: 4; justify-self: end; }
.kb-staff-action :deep(.ant-btn) { min-height: 34px; border-radius: 10px; }
@media (max-width: 1180px) {
  .kb-staff-feedback { --feedback-state: 88px; --feedback-action: 100px; --feedback-gap: 12px; }
}
@media (max-width: 767px) {
  .kb-staff-feedback-tools :deep(.v10-choice) { flex-basis: 100%; }
  .kb-staff-feedback-columns { display: none; }
  .kb-staff-feedback-item { grid-template-columns: var(--feedback-icon) minmax(0, 1fr) auto; align-items: start; row-gap: 8px; }
  .kb-staff-copy { grid-column: 2 / -1; }
  .kb-staff-status { grid-column: 2; align-self: center; }
  .kb-staff-action { grid-column: 3; }
}
@media (max-width: 360px) {
  .kb-staff-feedback { --feedback-icon: 28px; --feedback-gap: 9px; }
  .kb-staff-refresh { width: 42px; padding-inline: 0; }
  .kb-staff-refresh > span:not(.anticon) { display: none; }
}
</style>
