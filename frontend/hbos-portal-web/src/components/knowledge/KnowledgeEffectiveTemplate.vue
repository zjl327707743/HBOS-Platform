<script setup lang="ts">
import KnowledgeDisclosureSummary from '@/components/knowledge/KnowledgeDisclosureSummary.vue'
import type {EffectiveParseTemplate,AutomaticQuality} from '@/services/knowledgeMaintenanceApi'
defineProps<{value?:EffectiveParseTemplate;quality?:AutomaticQuality}>()
</script>
<template>
  <details class="effective-template"><KnowledgeDisclosureSummary>本份资料的实际模板与核验记录</KnowledgeDisclosureSummary>
    <p v-if="!value?.effective_document_profile">{{value?.profile_sha256?'本份模板已固定，实际执行记录尚待就绪。':'历史解析模板尚待对账；没有用资料库默认值填充本份记录。'}}</p>
    <dl v-else><dt>输入件</dt><dd>{{value.input_kind==='DERIVED'?'受控派生件':'原件'}}<code>{{value.input_sha256}}</code></dd>
      <dt>解析器</dt><dd>{{value.parser}}<code>{{value.parser_version}}</code><code>{{value.parser_patch_sha256}}</code></dd>
      <dt>切块 / Overlap</dt><dd>{{value.chunk_tokens}} Token / {{value.overlap_percent}}%</dd>
      <dt>图表上下文</dt><dd>表格 {{value.table_context}} / 图像 {{value.image_context}}</dd>
      <dt>Embedding</dt><dd>{{value.embedding_model}} / {{value.embedding_dimensions}} 维</dd>
      <dt>模板身份</dt><dd><code>{{value.profile_sha256}}</code></dd>
      <dt>实际 OCR</dt><dd v-if="value.provenance">{{value.provenance.actual_ocr_engine?.join('、')||'未调用 OCR'}}<p>原件物理页：{{value.provenance.actual_ocr_pages?.join('、')||'无'}}</p></dd><dd v-else>历史执行记录待补齐</dd>
    </dl>
    <p v-if="quality">自动核验：{{quality.status==='AUTO_VERIFIED_PENDING_REVIEW'?'通过，待抽查发布':'待修复'}} · {{quality.queue==='COMPLEX'?'复杂资料支线':'普通资料'}}</p>
    <p v-if="quality?.text_check">正文行 {{quality.text_check.matched_lines}} / {{quality.text_check.source_lines}}；未匹配数字出现数 {{quality.text_check.missing_number_occurrences}}。</p>
  </details>
</template>
<style scoped>
.effective-template{margin:16px 0;padding:12px;border:1px solid var(--hbos-border-default);border-radius:8px}.effective-template summary{cursor:pointer;min-height:28px}.effective-template dl{display:grid;grid-template-columns:minmax(80px,120px) minmax(0,1fr);gap:10px;font-size:13px}.effective-template dd{margin:0;overflow-wrap:anywhere}.effective-template dt{color:var(--hbos-text-muted)}.effective-template code{display:block;overflow-wrap:anywhere;font-size:11px}.effective-template p{margin:6px 0}
</style>
