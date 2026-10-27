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
      :delivery-state="deliveryState"
      @back="goBack"
      @retry="retry"
      @retry-page="retryPage"
      @prev="prev"
      @next="next"
      @go-page="goToPage"
      @search="runSearch"
      @clear-search="clearSearch"
      @jump-match="jumpToMatch"
      @prepare-preview="preparePreview"
      @prepare-download="prepareDownload"
      @prepare-retry="prepareRetry"
      @close-preview="closePreview"
      @delivery-denied="readerRetryFromFailure(new DomainApiError('FORBIDDEN','资料授权已变化，请返回后重新检索。'))"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import type { ReaderSource } from '@/contracts/documentReader'
import { useDocumentReader } from '@/composables/useDocumentReader'
import { useKnowledgeReturnStore } from '@/stores/knowledgeReturn'
import { usePortalStore } from '@/stores/portal'
import DocumentReader from '@/components/knowledge/DocumentReader.vue'
import {
  createDocumentDelivery,
  deliveryFailureMessage,
  fetchDocumentCapabilities,
  isRetryableDelivery,
} from '@/services/knowledgeDelivery'
import type { DocumentCapabilities } from '@/services/knowledgeDelivery'
import { DomainApiError } from '@/services/p1Api'

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

// ---- frozen delivery contract (capabilities / preview / download) -----------
// State lives here so the reader stays a pure presenter. Every ticket URL is
// short-lived and re-validated server-side on each request: even a prepared
// preview can later be refused, so failures always offer 重新准备, and the
// body text below the preview frame stays readable in every failure path.

interface DeliveryUiState {
  capabilities: DocumentCapabilities | null
  loadingCapabilities: boolean
  preview: { busy: boolean; url: string | null; filename: string; expiresAt: number | null; kind: string }
  download: { busy: boolean; url: string | null; filename: string }
  error: string
  retryable: boolean
  notice: string
}

const deliveryState = ref<DeliveryUiState>({
  capabilities: null,
  loadingCapabilities: false,
  preview: { busy: false, url: null, filename: '', expiresAt: null, kind: '' },
  download: { busy: false, url: null, filename: '' },
  error: '',
  retryable: false,
  notice: '',
})
let deliveryGeneration = 0
let lastDeliveryIntent: 'preview' | 'download' | null = null
let previewObjectUrl: string | null = null

function resetDelivery() {
  deliveryGeneration++
  lastDeliveryIntent = null
  if (previewObjectUrl) { URL.revokeObjectURL(previewObjectUrl); previewObjectUrl = null }
  deliveryState.value = {
    capabilities: null,
    loadingCapabilities: false,
    preview: { busy: false, url: null, filename: '', expiresAt: null, kind: '' },
    download: { busy: false, url: null, filename: '' },
    error: '',
    retryable: false,
    notice: '',
  }
}

function currentVersion(): string | null {
  return document.value?.version_id || versionId.value || null
}

async function loadCapabilities() {
  if (!documentId.value || !document.value) return
  const generation = ++deliveryGeneration
  const subject = subjectKey.value
  deliveryState.value.loadingCapabilities = true
  try {
    const capabilities = await fetchDocumentCapabilities(documentId.value, currentVersion())
    if (generation !== deliveryGeneration || subject !== subjectKey.value) return
    // The server is authoritative; never widen permissions in the UI.
    deliveryState.value.capabilities = capabilities
  } catch {
    if (generation === deliveryGeneration && subject === subjectKey.value) {
      // Capabilities are advisory; the body stays readable without them and the
      // reader shows a pending control instead of fake buttons.
      deliveryState.value.capabilities = null
    }
  } finally {
    if (generation === deliveryGeneration && subject === subjectKey.value) deliveryState.value.loadingCapabilities = false
  }
}

function failureMessage(error: unknown, intent: 'preview' | 'download'): string {
  const message = deliveryFailureMessage(error)
  return intent === 'preview' ? `预览未完成：${message} 正文仍可继续阅读。` : `下载未完成：${message}`
}

async function prepareDelivery(intent: 'preview' | 'download') {
  if (!documentId.value || !document.value) return
  const generation = ++deliveryGeneration
  const subject = subjectKey.value
  lastDeliveryIntent = intent
  deliveryState.value.error = ''
  deliveryState.value.retryable = false
  deliveryState.value.notice = ''
  if (intent === 'preview') {
    if (previewObjectUrl) { URL.revokeObjectURL(previewObjectUrl); previewObjectUrl = null }
    deliveryState.value.preview = { ...deliveryState.value.preview, busy: true, url: null }
  } else deliveryState.value.download = { ...deliveryState.value.download, busy: true, url: null }
  try {
    const delivery = await createDocumentDelivery(documentId.value, currentVersion(), intent)
    if (generation !== deliveryGeneration || subject !== subjectKey.value) return
    if (intent === 'preview') {
      // Ticket URLs are same-origin and may be iframed directly; fall back to a
      // controlled blob fetch only if the browser blocks direct navigation.
      deliveryState.value.preview = {
        busy: false,
        url: delivery.content_url,
        filename: delivery.filename,
        expiresAt: delivery.expires_at,
        kind: delivery.kind === 'DERIVED_PDF' ? 'DERIVED_PDF' : 'ORIGINAL_PDF',
      }
      deliveryState.value.notice = delivery.kind === 'DERIVED_PDF'
        ? '已准备派生预览版（非原件）；票据会过期，过期后请重新准备。'
        : '已准备原件预览；票据会过期，过期后请重新准备。'
    } else {
      // Independent can_download gate: the link is created and revoked at once,
      // so the file saves through the short-lived ticket without a persistent URL.
      const link = document_anchor(delivery.content_url, delivery.filename)
      link.click()
      deliveryState.value.download = { busy: false, url: null, filename: delivery.filename }
      deliveryState.value.notice = '已开始下载。文件由服务端再次核验授权后提供。'
    }
  } catch (error) {
    if (generation !== deliveryGeneration || subject !== subjectKey.value) return
    deliveryState.value.error = failureMessage(error, intent)
    deliveryState.value.retryable = isRetryableDelivery(error)
    if (intent === 'preview') deliveryState.value.preview = { ...deliveryState.value.preview, busy: false, url: null }
    else deliveryState.value.download = { ...deliveryState.value.download, busy: false, url: null }
    // Access revocation must clear the whole reader, not only the delivery row.
    if (error instanceof DomainApiError && ['AUTHENTICATION_REQUIRED', 'CLIENT_AUTH_FAILED', 'FORBIDDEN', 'SCOPE_REJECTED', 'EMPTY_SCOPE'].includes(error.code)) {
      void readerRetryFromFailure(error)
    }
  }
}

function document_anchor(url: string, filename: string): HTMLAnchorElement {
  const link = window.document.createElement('a')
  link.href = url
  link.download = filename
  window.document.body.appendChild(link)
  setTimeout(() => link.remove(), 0)
  return link
}

function preparePreview() { void prepareDelivery('preview') }
function prepareDownload() { void prepareDelivery('download') }
function prepareRetry() {
  if (lastDeliveryIntent) { void prepareDelivery(lastDeliveryIntent); return }
  void loadCapabilities()
}
function closePreview() {
  deliveryGeneration++
  if (previewObjectUrl) { URL.revokeObjectURL(previewObjectUrl); previewObjectUrl = null }
  deliveryState.value.preview = { ...deliveryState.value.preview, url: null, busy: false }
  deliveryState.value.notice = '已关闭预览，可继续阅读正文。'
}

// Access failures raised by delivery are surfaced through the reader's own
// failure state so the whole view behaves like an unauthorized open.
function readerRetryFromFailure(error: DomainApiError) {
  reader.reset()
  resetDelivery()
  failure.value = { kind: 'unavailable', code: error.code, message: error.message, retryable: false }
}

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

watch([documentId, versionId], () => { resetDelivery(); openCurrent() }, { immediate: true })
// Capabilities load once the open succeeded and follow version changes; they
// never block or gate the body text.
watch(() => [document.value?.document_id, document.value?.version_id, loading.value], () => {
  if (!loading.value && document.value) void loadCapabilities()
})
onBeforeUnmount(() => { resetDelivery(); rememberPosition() })
</script>

<style scoped>
.knowledge-document-page { min-width: 0; }
</style>
