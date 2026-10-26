<template>
  <div class="knowledge-document-page">
    <DocumentReader
      :from="from"
      :version-resolved="!versionId"
      :document="document"
      :body="body"
      :navigation="navigation"
      :disclosure="disclosure"
      :page="page"
      :page-count="pageCount"
      :block-total="blockTotal"
      :loading="loading"
      :page-loading="pageLoading"
      :failure="failure"
      :page-failure="pageFailure"
      v-model:search-query="searchQuery"
      :searching="searching"
      :search-ran="searchRan"
      :search-message="searchMessage"
      :matches="matches"
      :highlight-block-id="highlightBlockId"
      :highlight-query="highlightQuery"
      @back="goBack"
      @retry="retry"
      @retry-page="retryPage"
      @prev="prev"
      @next="next"
      @go-page="goToPage"
      @search="runSearch"
      @clear-search="clearSearch"
      @jump-match="jumpToMatch"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import type { ReaderSource } from '@/contracts/documentReader'
import { useDocumentReader } from '@/composables/useDocumentReader'
import { useKnowledgeReturnStore } from '@/stores/knowledgeReturn'
import { usePortalStore } from '@/stores/portal'
import DocumentReader from '@/components/knowledge/DocumentReader.vue'

const route = useRoute()
const router = useRouter()
const portal = usePortalStore()
const returnStore = useKnowledgeReturnStore()

const subjectKey = computed(() => portal.user?.id || null)
const documentId = computed(() => String(route.params.documentId || ''))
const versionId = computed(() => {
  const value = route.query.version_id
  return typeof value === 'string' && value.trim() ? value.trim() : null
})
const from = computed<ReaderSource>(() => {
  const value = String(route.query.from || '')
  return value === 'ask' || value === 'search' || value === 'catalog' ? value : 'search'
})

const reader = useDocumentReader(() => subjectKey.value)
const {
  document, body, navigation, disclosure, loading, pageLoading, page, pageCount, blockTotal,
  failure, pageFailure, searchQuery, searching, searchRan, searchFailure, matches,
  searchedBlocks, searchCapped, highlightBlockId, highlightQuery,
  open, goToPage, runSearch, clearSearch, jumpToMatch,
} = reader

const searchMessage = computed(() => {
  if (searching.value) return '正在查找正文…'
  if (searchFailure.value) return searchFailure.value.message
  if (!searchRan.value) return ''
  const term = searchQuery.value.trim()
  if (!matches.value.length) return `未在可检索正文中找到“${term}”。`
  return `找到 ${matches.value.length} 处匹配 · 已检索 ${searchedBlocks.value} 段正文${searchCapped.value ? '（仅检索部分正文）' : ''}`
})

function storedPage(): number {
  const raw = Number(route.query.page)
  if (Number.isSafeInteger(raw) && raw >= 1 && raw <= 100000) return raw
  const subject = subjectKey.value
  const position = returnStore.positionFor(subject, documentId.value, versionId.value)
    || returnStore.positionFor(subject, documentId.value, null)
  return position && Number.isSafeInteger(position.page) && position.page >= 1 ? position.page : 1
}

function openCurrent() {
  void open({
    documentId: documentId.value,
    versionId: versionId.value,
    page: storedPage(),
  })
}

function rememberPosition() {
  if (!documentId.value || !body.value) return
  const position = { page: page.value, searchQuery: searchQuery.value.trim() }
  const resolved = document.value?.version_id || versionId.value || null
  returnStore.rememberPosition(subjectKey.value, documentId.value, resolved, position)
  // An entry that only knows the document id (citation/search) reopens without
  // VER_ id; remember the same position under that key too, never inventing one.
  if (resolved && resolved !== versionId.value) returnStore.rememberPosition(subjectKey.value, documentId.value, null, position)
}

function goBack() {
  rememberPosition()
  const fallback = from.value === 'catalog' ? '/hbos/knowledge/catalog' : '/hbos/knowledge'
  const historyState = window.history.state as { back?: unknown } | null
  const back = historyState && typeof historyState.back === 'string' ? historyState.back : ''
  if (back.startsWith('/hbos/knowledge')) router.back()
  else void router.push(fallback)
}

function retry() { void reader.retry() }
function retryPage() { void reader.retry() }
function prev() { void goToPage(page.value - 1) }
function next() { void goToPage(page.value + 1) }

watch([documentId, versionId], () => openCurrent(), { immediate: true })
onBeforeUnmount(rememberPosition)
</script>

<style scoped>
.knowledge-document-page { min-width: 0; }
</style>
