<template>
  <div class="kb-file-reader" data-reader :aria-busy="loading ? 'true' : 'false'">
    <!-- One toolbar for the whole file view: back, title, pages, zoom, fullscreen, download. -->
    <header class="kb-file-toolbar kb-panel hbos-glass-g1" data-reader-toolbar>
      <div class="kb-file-toolbar-main">
        <a-button type="text" data-reader-back @click="$emit('back')"><ArrowLeftOutlined />{{ backLabel }}</a-button>
        <div class="kb-file-title">
          <h1>{{ document?.title || '未标注标题' }}</h1>
          <p v-if="subtitle">{{ subtitle }}</p>
        </div>
        <div class="kb-file-actions">
          <a-button v-if="canDownload" type="primary" :loading="downloadBusy" data-reader-download @click="$emit('download')">
            <DownloadOutlined />下载原文件
          </a-button>
          <a-tooltip v-else-if="downloadReason" :title="downloadReason">
            <a-button disabled data-reader-download-unavailable><DownloadOutlined />原文件不可下载</a-button>
          </a-tooltip>
          <a-button v-if="previewUrl" data-reader-fullscreen @click="toggleFullscreen">
            <FullscreenOutlined />{{ fullscreen ? '退出全屏' : '全屏' }}
          </a-button>
        </div>
      </div>
    </header>

    <a-skeleton v-if="loading" active :paragraph="{ rows: 8 }" />

    <section v-else-if="failure && !previewUrl" class="kb-file-state kb-panel hbos-glass-g1" data-reader-error :data-reader-failure="failure.kind" role="alert">
      <h2>{{ failureTitle }}</h2>
      <a-alert :type="failure.kind === 'upstream' || failure.kind === 'error' ? 'error' : 'warning'" show-icon
               :message="failure.message" :description="failureHelp" />
      <div class="kb-file-state-actions">
        <a-button v-if="failure.retryable" type="primary" data-reader-retry @click="$emit('retry')"><ReloadOutlined />重试</a-button>
        <a-button v-if="canDownload" :loading="downloadBusy" @click="$emit('download')"><DownloadOutlined />下载原文件</a-button>
        <a-button data-reader-failure-back @click="$emit('back')">{{ backLabel }}</a-button>
      </div>
    </section>

    <template v-else>
      <section v-if="previewUrl" class="kb-file-surface kb-panel hbos-glass-g1" :class="{ 'is-fullscreen': fullscreen }" ref="surface">
        <div class="kb-file-kind" data-preview-kind>
          <FilePdfOutlined />
          <span>{{ previewKindText }}</span>
          <small v-if="previewFilename">{{ previewFilename }}</small>
        </div>
        <PdfPreview
          :url="previewUrl"
          :page="position.page"
          :zoom="position.zoom"
          :renew="renewPreview"
          @access-lost="$emit('access-lost')"
          @update:page="onPage"
          @update:zoom="onZoom"
        />
      </section>

      <section v-else-if="preparing" class="kb-file-state kb-panel hbos-glass-g1" data-reader-preparing role="status">
        <a-spin />
        <p>{{ preparingMessage }}</p>
        <a-button v-if="canDownload" :loading="downloadBusy" @click="$emit('download')"><DownloadOutlined />先下载原文件</a-button>
      </section>

      <section v-else-if="previewUnavailable" class="kb-file-state kb-panel hbos-glass-g1" data-reader-no-preview>
        <h2>这份资料暂无原版式预览</h2>
        <p>{{ previewUnavailable }}</p>
        <div class="kb-file-state-actions">
          <a-button v-if="canDownload" type="primary" :loading="downloadBusy" @click="$emit('download')"><DownloadOutlined />下载原文件</a-button>
          <a-button @click="showText = true">查看检索文本</a-button>
        </div>
      </section>

      <a-alert v-if="notice" type="info" show-icon :message="notice" class="kb-file-notice" data-reader-notice />
      <a-alert v-if="pageFailure" type="warning" show-icon :message="pageFailure.message" class="kb-file-notice" data-reader-page-error>
        <template #action><a-button v-if="pageFailure.retryable" size="small" @click="$emit('retry-page')">重试</a-button></template>
      </a-alert>

      <details v-if="body && body.block_total" class="kb-file-text kb-panel hbos-glass-g1" :open="showText" data-reader-text-panel @toggle="onToggleText">
        <summary>检索文本（{{ body.block_total }} 段，供定位与查找，不是原件版式）</summary>
        <form class="kb-reader-search" role="search" @submit.prevent="$emit('search')">
          <label class="sr-only" for="reader-search-input">在检索文本中查找</label>
          <input id="reader-search-input" :value="searchQuery" type="search" maxlength="120" placeholder="在检索文本中查找关键词…" :disabled="searching" @input="onSearchInput">
          <a-button html-type="submit" :loading="searching" :disabled="!searchQuery.trim()" data-reader-search-submit>查找</a-button>
          <a-button v-if="searchRan" :disabled="searching" data-reader-search-clear @click="$emit('clear-search')">清除</a-button>
        </form>
        <p v-if="searchMessage" class="kb-reader-search-status" role="status" data-reader-search-status>{{ searchMessage }}</p>
        <ul v-if="matches.length" class="kb-reader-matches" data-reader-search-results>
          <li v-for="(match, index) in matches" :key="match.block_id + '-' + index">
            <button type="button" data-reader-match @click="$emit('jump-match', match)">
              <span class="kb-reader-match-page">{{ match.page !== null ? '第 ' + match.page + ' 页' : '未核验页码' }}</span>
              <span class="kb-reader-match-snippet">{{ match.snippet }}</span>
            </button>
          </li>
        </ul>
        <div class="kb-reader-pager" role="group" aria-label="检索文本翻页">
          <a-button :disabled="page <= 1 || pageLoading" data-reader-prev @click="$emit('prev')">上一段</a-button>
          <span class="kb-reader-page-count">第 {{ page }} 段<template v-if="pageCount !== null"> / 共 {{ pageCount }} 段</template></span>
          <a-button :disabled="pageCount === null || page >= pageCount || pageLoading" data-reader-next @click="$emit('next')">下一段</a-button>
        </div>
        <article v-for="(block, index) in body.blocks" :id="'reader-block-' + block.block_id" :key="block.block_id"
                 class="kb-reader-block" :class="{ 'is-highlight': highlightBlockId === block.block_id }"
                 :data-reader-block="block.block_id">
          <h3 v-if="showSection(index)" class="kb-reader-section">{{ block.section }}</h3>
          <p class="kb-reader-text" :data-reader-text="block.block_id"><template v-for="(segment, segmentIndex) in segments(block.block_id, block.text)" :key="segmentIndex"><mark v-if="segment.match">{{ segment.text }}</mark><template v-else>{{ segment.text }}</template></template></p>
        </article>
        <p v-if="pageLoading" class="kb-reader-page-loading" role="status">正在读取…</p>
      </details>

      <footer class="kb-file-footer">
        <span>{{ document?.space_title || '已共享资料' }}<template v-if="document?.business_version"> · {{ document.business_version }}</template></span>
        <span>原文件由服务端按当前身份与版本核验后提供</span>
      </footer>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'
import { ArrowLeftOutlined, DownloadOutlined, FullscreenOutlined, FilePdfOutlined, ReloadOutlined } from '@ant-design/icons-vue'
import type {
  ReaderBody, ReaderDocument, ReaderFailure, ReaderSearchMatch, ReaderSource,
} from '@/contracts/documentReader'
import PdfPreview from './PdfPreview.vue'

const props = defineProps<{
  from: ReaderSource
  document: ReaderDocument | null
  body: ReaderBody | null
  page: number
  pageCount: number | null
  loading: boolean
  pageLoading: boolean
  failure: ReaderFailure | null
  pageFailure: ReaderFailure | null
  searchQuery: string
  searching: boolean
  searchRan: boolean
  searchMessage: string
  matches: ReaderSearchMatch[]
  highlightBlockId: string | null
  highlightQuery: string
  /* file view */
  previewUrl: string | null
  previewKind: 'ORIGINAL_PDF' | 'DERIVED_PDF' | null
  previewFilename: string
  previewUnavailable: string
  preparing: boolean
  preparingMessage: string
  canDownload: boolean
  downloadBusy: boolean
  downloadReason: string
  notice: string
  position: { page: number; zoom: number }
  renewPreview: () => Promise<string | null>
}>()

const emit = defineEmits<{
  back: []
  retry: []
  'retry-page': []
  prev: []
  next: []
  'go-page': [page: number]
  search: []
  'clear-search': []
  'jump-match': [match: ReaderSearchMatch]
  'update:searchQuery': [value: string]
  download: []
  'access-lost': []
  'page-change': [page: number]
  'zoom-change': [zoom: number]
}>()

const showText = ref(false)
const fullscreen = ref(false)
const surface = ref<HTMLElement | null>(null)

const backLabel = computed(() => ({ ask: '返回回答', search: '返回结果', catalog: '返回资料目录' }[props.from] || '返回'))
const subtitle = computed(() => {
  const document = props.document
  if (!document) return ''
  const parts = [document.document_number, document.business_version ? '版本 ' + document.business_version : '', document.space_title]
  return parts.filter(Boolean).join(' · ')
})
const previewKindText = computed(() => props.previewKind === 'DERIVED_PDF' ? '转换预览（由原文件生成，非原件）' : '原文件版式')
const failureTitle = computed(() => {
  if (!props.failure) return '资料暂不可读'
  if (props.failure.kind === 'unavailable') return '当前不可阅读'
  if (props.failure.kind === 'invalid') return '无法打开这份资料'
  return '资料服务暂时不可用'
})
const failureHelp = computed(() => {
  if (!props.failure) return ''
  if (props.failure.kind === 'unavailable') return '如确认仍可查阅，请从资料目录重新打开当前版本。'
  if (props.failure.kind === 'invalid') return '请从资料目录重新进入。'
  return '这不代表资料有问题，请稍后重试。'
})
const canDownload = computed(() => props.canDownload)

function onPage(value: number) { emit('page-change', value) }
function onZoom(value: number) { emit('zoom-change', value) }
function onSearchInput(event: Event) { emit('update:searchQuery', (event.target as HTMLInputElement).value) }
function onToggleText(event: Event) { showText.value = (event.target as HTMLDetailsElement).open }

async function toggleFullscreen() {
  const element = surface.value
  if (!element) return
  try {
    if (window.document.fullscreenElement) { await window.document.exitFullscreen(); fullscreen.value = false }
    else { await element.requestFullscreen(); fullscreen.value = true }
  } catch { fullscreen.value = false }
}

function showSection(index: number) {
  const blocks = props.body?.blocks || []
  const section = blocks[index]?.section
  if (!section) return false
  return index === 0 || blocks[index - 1]?.section !== section
}

interface TextSegment { text: string; match: boolean }
function segments(blockId: string, text: string): TextSegment[] {
  const query = props.highlightQuery.trim()
  if (!query || props.highlightBlockId !== blockId) return [{ text, match: false }]
  const haystack = text.toLocaleLowerCase(), needle = query.toLocaleLowerCase()
  if (!haystack.includes(needle)) return [{ text, match: false }]
  const result: TextSegment[] = []
  let cursor = 0, guard = 0
  while (cursor < text.length && guard < 100) {
    const found = haystack.indexOf(needle, cursor)
    if (found < 0) break
    if (found > cursor) result.push({ text: text.slice(cursor, found), match: false })
    result.push({ text: text.slice(found, found + needle.length), match: true })
    cursor = found + needle.length; guard++
  }
  if (cursor < text.length) result.push({ text: text.slice(cursor), match: false })
  return result.length ? result : [{ text, match: false }]
}

watch([() => props.highlightBlockId, () => props.page], async () => {
  if (!props.highlightBlockId || !showText.value) return
  await nextTick()
  window.document.getElementById(`reader-block-${props.highlightBlockId}`)?.scrollIntoView?.({ block: 'center' })
})
</script>

<style scoped>
.kb-file-reader{display:grid;gap:14px;min-width:0}
.kb-file-reader .kb-panel{margin:0}
.kb-file-toolbar{padding:14px 18px;border-radius:20px}
.kb-file-toolbar-main{display:flex;flex-wrap:wrap;align-items:center;gap:12px;min-width:0}
.kb-file-title{min-width:0;flex:1 1 260px}
.kb-file-title h1{margin:0;font-size:20px;line-height:28px;color:#203b66;overflow-wrap:anywhere}
.kb-file-title p{margin:2px 0 0;font-size:13px;color:var(--hbos-text-muted);overflow-wrap:anywhere}
.kb-file-actions{display:flex;gap:8px;flex-wrap:wrap;margin-left:auto}
.kb-file-surface{padding:12px;border-radius:20px;display:grid;gap:8px;min-width:0}
.kb-file-surface.is-fullscreen{padding:16px;overflow:auto;background:#fff;border-radius:0;height:100%}
.kb-file-kind{display:flex;flex-wrap:wrap;align-items:center;gap:8px;font-size:13px;color:var(--hbos-text-secondary)}
.kb-file-kind small{color:var(--hbos-text-muted);overflow-wrap:anywhere}
.kb-file-state{padding:26px;border-radius:20px;display:grid;gap:14px;justify-items:start}
.kb-file-state h2{margin:0;font-size:19px;color:#203b66}
.kb-file-state p{margin:0;color:var(--hbos-text-secondary);line-height:22px}
.kb-file-state-actions{display:flex;flex-wrap:wrap;gap:10px}
.kb-file-notice{margin:0}
.kb-file-text{padding:16px 20px;border-radius:18px;min-width:0}
.kb-file-text summary{cursor:pointer;font-size:14px;color:#203b66}
.kb-reader-search{display:flex;flex-wrap:wrap;align-items:center;gap:8px;margin:12px 0}
.kb-reader-search input{flex:1 1 220px;min-width:0;padding:9px 12px;border:1px solid var(--hbos-border-strong);border-radius:10px;font:inherit;color:var(--hbos-text-primary);background:var(--hbos-bg-surface)}
.kb-reader-search-status{margin:0 0 8px;font-size:13px;color:var(--hbos-text-secondary);overflow-wrap:anywhere}
.kb-reader-matches{list-style:none;margin:0 0 12px;padding:0;display:grid;gap:6px;max-height:240px;overflow-y:auto}
.kb-reader-matches button{display:flex;gap:10px;width:100%;text-align:left;border:1px solid var(--hbos-border-strong);border-radius:10px;background:rgba(255,255,255,.72);padding:8px 10px;font:inherit;cursor:pointer;overflow-wrap:anywhere}
.kb-reader-match-page{flex:none;font-size:12px;color:#127a67;white-space:nowrap}
.kb-reader-match-snippet{font-size:13px;line-height:20px;color:var(--hbos-text-primary)}
.kb-reader-pager{display:flex;flex-wrap:wrap;align-items:center;gap:10px;margin-bottom:12px}
.kb-reader-page-count{font-size:13px;color:var(--hbos-text-secondary);white-space:nowrap}
.kb-reader-block{min-width:0;padding:8px 0;border-bottom:1px dashed rgba(65,91,138,.12)}
.kb-reader-block.is-highlight{background:rgba(21,155,137,.07);border-radius:10px;padding:8px 10px}
.kb-reader-section{margin:4px 0 8px;font-size:16px;line-height:24px;color:#203b66;overflow-wrap:anywhere}
.kb-reader-text{margin:0;font-size:15px;line-height:26px;color:var(--hbos-text-primary);white-space:pre-wrap;overflow-wrap:anywhere}
.kb-reader-text mark{background:#ffe9a8;color:inherit;padding:0 1px;border-radius:2px}
.kb-reader-page-loading{margin:0;font-size:13px;color:var(--hbos-text-muted)}
.kb-file-footer{display:flex;flex-wrap:wrap;justify-content:space-between;gap:8px;font-size:12px;line-height:20px;color:var(--hbos-text-muted);padding:0 4px}
@media (max-width:600px){
  .kb-file-toolbar{padding:12px}
  .kb-file-title h1{font-size:18px;line-height:26px}
  .kb-file-actions{width:100%;margin-left:0}
  .kb-file-actions .ant-btn{flex:1 1 auto}
  .kb-file-surface,.kb-file-text{padding:12px;border-radius:16px}
}
</style>
