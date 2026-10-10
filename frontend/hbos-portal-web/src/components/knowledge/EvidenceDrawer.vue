<template>
  <a-drawer :open="open" title="资料来源" width="min(560px, 100vw)" root-class-name="kb-drawer kb-scope evidence-drawer-root" @close="$emit('close')">
    <a-skeleton v-if="open && loading" active :paragraph="{rows:6}" />
    <div v-else-if="open && error" class="evidence-failure" role="status"><h2>{{failureTitle}}</h2><a-alert :type="permissionFailure?'warning':'error'" show-icon :message="error" :description="failureHelp"/><a-button @click="$emit('close')">返回查阅</a-button></div>
    <template v-else-if="open && evidence"><h2 class="kb-drawer-title">{{evidence.title || '来源依据'}}</h2><p class="kb-source-meta">{{evidence.document_number || '文号待核'}} · {{evidence.version || '版本待核'}}</p><div class="kb-source-status"><CheckCircleOutlined/>{{evidence.status_note==='INTERNAL_REFERENCE_REVIEWED'?'内部参考／有效性待核':evidence.status_note || '当前授权摘录'}}</div><div class="kb-source-excerpt"><strong>相关依据</strong><blockquote>{{evidence.excerpt}}</blockquote><p v-if="evidence.page_number || evidence.section" class="kb-muted">{{evidence.page_number ? '第 '+evidence.page_number+' 页' : ''}} {{evidence.section}}</p></div><div class="kb-drawer-actions"><a-button @click="$emit('bookmark',evidence)"><StarFilled v-if="bookmarked" class="kb-star"/><StarOutlined v-else/>{{bookmarked?'取消收藏':'收藏资料'}}</a-button><a-button disabled><DownloadOutlined/>下载</a-button></div><p class="kb-muted">待部门文档下载权限上线</p><a-button type="link" @click="$emit('feedback',evidence)"><MessageOutlined/>反馈来源问题</a-button></template>
  </a-drawer>
</template>
<script setup lang="ts">
import { computed } from 'vue'
import { StarOutlined, StarFilled, DownloadOutlined, MessageOutlined, CheckCircleOutlined } from '@ant-design/icons-vue'
import type { KnowledgeEvidence } from '@/contracts/p1'

const props = defineProps<{
  open: boolean
  loading: boolean
  evidence: KnowledgeEvidence | null
  error: string | null
  errorCode?: string | null
  bookmarked?: boolean
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

defineEmits<{ close: []; bookmark: [evidence:KnowledgeEvidence]; feedback: [evidence:KnowledgeEvidence] }>()
</script>

<style scoped>
blockquote{margin:16px 0 0;font-size:16px;line-height:28px;white-space:pre-wrap;overflow-wrap:anywhere;color:var(--hbos-text-primary)}.evidence-failure{display:grid;gap:16px}
</style>
