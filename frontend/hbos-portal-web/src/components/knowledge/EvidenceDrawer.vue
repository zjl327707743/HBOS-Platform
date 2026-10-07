<template>
  <a-drawer
    :open="open"
    :width="520"
    placement="right"
    root-class-name="evidence-drawer-root"
    @close="$emit('close')"
  >
    <template #title>
      <div class="evidence-title">
        <small>依据卡 · EVIDENCE</small>
        <strong>{{ (open && evidence?.title) || (open && evidence?.document_id) || '正在核验依据' }}</strong>
      </div>
    </template>

    <a-skeleton v-if="open && loading" active :paragraph="{ rows: 8 }" />
    <a-alert v-else-if="open && error" type="error" show-icon :message="error" />
    <div v-else-if="open && evidence" class="evidence-content">
      <a-tag color="blue">授权摘录</a-tag>
      <a-tag v-if="evidence.source_type === 'SYNTHETIC_TEST'" color="orange">SYNTHETIC_ONLY</a-tag>
      <section class="evidence-card">
        <h3>来源信息</h3>
        <dl>
          <dt>资料编号</dt><dd>{{ evidence.document_id }}</dd>
          <dt>资料名称</dt><dd>{{ evidence.title || '未标注' }}</dd>
          <dt>资料版本</dt><dd>{{ evidence.version || '版本未核' }}</dd>
          <dt>核验状态</dt><dd>{{ evidence.status_note || '待核' }}</dd>
          <dt>定位页码</dt><dd>{{ evidence.page_number ?? '定位未核' }}</dd>
          <dt>定位章节</dt><dd>{{ evidence.section || '未标注' }}</dd>
          <dt>交付方式</dt><dd>短时证据 ID · 每次展开重新授权</dd>
        </dl>
      </section>
      <section>
        <h3>必要摘录</h3>
        <blockquote>{{ evidence.excerpt }}</blockquote>
      </section>
      <div class="evidence-boundary">
        <SafetyCertificateOutlined />
        <span>不提供原文件、全文、源路径或下载地址。屏幕上可见内容仍可能被人工保存。</span>
      </div>
    </div>
  </a-drawer>
</template>

<script setup lang="ts">
import { SafetyCertificateOutlined } from '@ant-design/icons-vue'
import type { KnowledgeEvidence } from '@/contracts/p1'

defineProps<{
  open: boolean
  loading: boolean
  evidence: KnowledgeEvidence | null
  error: string | null
}>()

defineEmits<{ (event: 'close'): void }>()
</script>

<style scoped>
.evidence-title small { display: block; color: #72829d; font-size: var(--hbos-font-meta); letter-spacing: .14em; }
.evidence-title strong { display: block; margin-top: 4px; color: #1c365f; font-size: var(--hbos-font-card-title); }
.evidence-content { display: grid; gap: 22px; }
.evidence-card { padding: 18px; border: 1px solid rgba(65,91,138,.10); border-radius: 18px; background: #f7faff; }
h3 { margin: 0 0 12px; font-size: var(--hbos-font-body); }
dl { display: grid; grid-template-columns: 100px 1fr; gap: 10px 16px; margin: 0; font-size: var(--hbos-font-meta); }
dt { color: #72829d; }
dd { margin: 0; color: #314768; word-break: break-all; }
blockquote { margin: 0; padding: 18px; border-left: 3px solid #6b65ff; border-radius: 0 16px 16px 0; background: #f7f8ff; color: #314768; font-size: var(--hbos-font-body); line-height: 1.85; white-space: pre-wrap; }
.evidence-boundary { display: flex; gap: 10px; padding: 13px; border-radius: 14px; background: rgba(38,183,141,.08); color: #3b6c62; font-size: var(--hbos-font-meta); line-height: 1.6; }
</style>
