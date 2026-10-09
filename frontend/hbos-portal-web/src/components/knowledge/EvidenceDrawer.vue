<template>
  <a-drawer
    :open="open"
    width="min(520px, 100vw)"
    placement="right"
    root-class-name="evidence-drawer-root"
    @close="$emit('close')"
  >
    <template #title>
      <div class="evidence-title">
        <small>依据卡 · EVIDENCE</small>
        <strong>{{ error ? failureTitle : loading ? '正在核验依据' : (open && evidence?.title) || '来源依据' }}</strong>
      </div>
    </template>

    <a-skeleton v-if="open && loading" active :paragraph="{ rows: 8 }" />
    <div v-else-if="open && error" class="evidence-failure" role="status">
      <a-alert :type="permissionFailure ? 'warning' : 'error'" show-icon :message="error" :description="failureHelp" />
      <a-button @click="$emit('close')">返回查阅</a-button>
    </div>
    <div v-else-if="open && evidence" class="evidence-content">
      <a-tag color="blue">授权摘录</a-tag>
      <a-tag v-if="evidence.source_type === 'SYNTHETIC_TEST'" color="orange">SYNTHETIC_ONLY</a-tag>
      <section class="evidence-card">
        <h3>来源信息</h3>
        <dl>
          <dt>文档编号</dt><dd>{{ evidence.document_number || '未标注' }}</dd>
          <dt>资料名称</dt><dd>{{ evidence.title || '未标注' }}</dd>
          <dt>资料版本</dt><dd>{{ evidence.version || '版本未核' }}</dd>
          <dt>核验状态</dt><dd>{{ evidence.status_note || '待核' }}</dd>
          <dt>定位页码</dt><dd>{{ evidence.page_number ?? '定位未核' }}</dd>
          <dt>定位章节</dt><dd>{{ evidence.section || '未标注' }}</dd>
          <dt>交付方式</dt><dd>每次查阅均核验资料状态</dd>
        </dl>
      </section>
      <section>
        <h3>必要摘录</h3>
        <blockquote>{{ evidence.excerpt }}</blockquote>
      </section>
      <div class="evidence-boundary">
        <SafetyCertificateOutlined />
        <span>资料仅供内部参考，请核对适用版本；不提供原件下载。</span>
      </div>
    </div>
  </a-drawer>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { SafetyCertificateOutlined } from '@ant-design/icons-vue'
import type { KnowledgeEvidence } from '@/contracts/p1'

const props = defineProps<{
  open: boolean
  loading: boolean
  evidence: KnowledgeEvidence | null
  error: string | null
  errorCode?: string | null
}>()

const permissionFailure = computed(() => ['AUTHENTICATION_REQUIRED', 'CLIENT_AUTH_FAILED', 'FORBIDDEN', 'SCOPE_REJECTED'].includes(props.errorCode || ''))
const failureTitle = computed(() => {
  if (['AUTHENTICATION_REQUIRED', 'CLIENT_AUTH_FAILED'].includes(props.errorCode || '')) return '登录状态已失效'
  if (['FORBIDDEN', 'SCOPE_REJECTED'].includes(props.errorCode || '')) return '当前来源不可访问'
  if (['UPSTREAM_UNAVAILABLE', 'SERVICE_ERROR', 'POLICY_UNAVAILABLE'].includes(props.errorCode || '')) return '来源核验暂不可用'
  return '来源暂不可用'
})
const failureHelp = computed(() => {
  if (['AUTHENTICATION_REQUIRED', 'CLIENT_AUTH_FAILED'].includes(props.errorCode || '')) return '请重新登录后再查阅，当前摘录已清除。'
  if (['EVIDENCE_UNAVAILABLE', 'EVIDENCE_REVOKED', 'EVIDENCE_INVALID'].includes(props.errorCode || '')) return '来源可能已过期、撤回或不再属于当前可读范围。请重新检索，系统不会保留失效摘录。'
  if (permissionFailure.value) return '请核对当前账号与资料范围，当前摘录已清除。'
  return '请稍后重新检索并核验来源；当前提示不代表没有相关资料。'
})

defineEmits<{ (event: 'close'): void }>()
</script>

<style scoped>
.evidence-title small { display: block; color: #72829d; font-size: var(--hbos-font-meta); letter-spacing: .14em; }
.evidence-title strong { display: block; margin-top: 4px; color: #1c365f; font-size: var(--hbos-font-card-title); overflow-wrap: anywhere; }
.evidence-failure { display: grid; justify-items: start; gap: 16px; }
.evidence-content { display: grid; gap: 22px; }
.evidence-card { padding: 18px; border: 1px solid rgba(65,91,138,.10); border-radius: 18px; background: #f7faff; }
h3 { margin: 0 0 12px; font-size: var(--hbos-font-card-title); line-height: var(--hbos-line-important); }
dl { display: grid; grid-template-columns: 88px minmax(0,1fr); gap: 10px 16px; margin: 0; font-size: var(--hbos-font-body); line-height: var(--hbos-line-body); }
dt { color: #72829d; }
dd { margin: 0; color: #314768; word-break: break-all; }
blockquote { margin: 0; padding: 18px; border-left: 3px solid #48bca6; border-radius: 0 16px 16px 0; background: #f3faf9; color: #314768; font-size: var(--hbos-font-card-title); line-height: var(--hbos-line-important); white-space: pre-wrap; overflow-wrap: anywhere; }
.evidence-boundary { display: flex; gap: 10px; padding: 13px; border-radius: 14px; background: rgba(38,183,141,.08); color: #3b6c62; font-size: var(--hbos-font-meta); line-height: 1.6; }
</style>
