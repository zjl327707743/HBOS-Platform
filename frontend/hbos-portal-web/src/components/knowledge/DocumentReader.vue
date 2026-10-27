<template>
  <div class="kb-document-reader" data-reader :aria-busy="loading ? 'true' : 'false'">
    <header class="kb-reader-header kb-panel hbos-glass-g1">
      <div class="kb-reader-crumb">
        <a-button type="link" size="small" data-reader-back @click="$emit('back')"><ArrowLeftOutlined />{{ backLabel }}</a-button>
        <span class="kb-reader-source">受控阅读 · {{ sourceLabel }}</span>
      </div>
      <template v-if="document">
        <h1 class="kb-reader-title">{{ document.title || '未标注标题' }}</h1>
        <p class="kb-reader-meta">
          {{ document.document_number || '文号待核' }} ·
          {{ document.business_version ? '业务版本 ' + document.business_version : '版本待核' }} ·
          {{ document.space_title || '业务目录待核' }}
        </p>
        <div class="kb-reader-badges">
          <a-tag :color="authorizationTone">{{ authorizationLabel }}</a-tag>
          <a-tag :color="referenceTone">{{ referenceLabel }}</a-tag>
          <a-tag v-if="versionResolved" color="default">按当前授权版本解析</a-tag>
          <a-tag v-if="body && body.derived" color="blue">派生阅读版</a-tag>
          <a-tag v-if="body && body.page_numbering !== 'AVAILABLE'" color="orange">页码未核验</a-tag>
          <a-tag v-if="document.source_type === 'COMPANY_CONTROLLED'" color="green">公司受控资料</a-tag>
        </div>
        <p v-if="document.status_note" class="kb-reader-status">{{ document.status_note }}</p>
        <a-alert v-if="disclosure" class="kb-reader-disclosure" type="info" show-icon :message="disclosure" />
        <p class="kb-reader-origin">
          正文为已授权索引文本的安全净化派生阅读版，<template v-if="body && body.page_numbering !== 'AVAILABLE'">页码尚未与原件核验，仅供定位参考，</template>引用请以原件为准。
          <template v-if="deliveryState.capabilities?.can_preview">原版式预览为{{ deliveryState.capabilities.preview_kind === 'DERIVED_PDF' ? '派生预览版（非原件）' : '原件 PDF' }}。</template>
          <template v-else-if="deliveryState.capabilities && deliveryState.capabilities.preview_reason">{{ deliveryReasonMessage(deliveryState.capabilities.preview_reason) }}</template>
          <template v-else>原版式预览与原件下载是否可用，以服务端核验结果为准。</template>
        </p>
        <div v-if="!loading && !failure && document" class="kb-reader-delivery" data-reader-delivery>
          <a-button v-if="deliveryState.capabilities?.can_preview" :loading="deliveryState.preview.busy" :disabled="deliveryState.preview.busy || deliveryState.download.busy" data-reader-preview @click="$emit('prepare-preview')">
            <FilePdfOutlined />{{ deliveryState.capabilities.preview_kind === 'DERIVED_PDF' ? '原版式预览（预览版）' : '原版式预览' }}
          </a-button>
          <a-button v-if="deliveryState.capabilities && !deliveryState.capabilities.can_preview" type="text" disabled data-reader-preview-unavailable>
            原版式预览不可用
          </a-button>
          <a-button v-if="deliveryState.capabilities?.can_download" :loading="deliveryState.download.busy" :disabled="deliveryState.download.busy || deliveryState.preview.busy" data-reader-download @click="$emit('prepare-download')">
            <DownloadOutlined />下载原件
          </a-button>
          <a-button v-else-if="deliveryState.capabilities" type="text" disabled data-reader-download-unavailable>
            <DownloadOutlined />下载未获授权
          </a-button>
          <a-button v-else type="text" :loading="deliveryState.loadingCapabilities" disabled data-reader-delivery-pending>
            正在核验预览与下载权限…
          </a-button>
        </div>
        <p v-if="deliveryState.capabilities && !deliveryState.capabilities.can_download" class="kb-muted">{{ deliveryReasonMessage(deliveryState.capabilities.download_reason) }}</p>
        <p v-if="deliveryState.notice" class="kb-reader-delivery-notice" role="status" data-delivery-notice>{{ deliveryState.notice }}</p>
        <a-alert
          v-if="deliveryState.error"
          type="warning"
          show-icon
          class="kb-reader-delivery-error"
          data-delivery-error
          :message="deliveryState.error"
        >
          <template #action>
            <a-button v-if="deliveryState.retryable" size="small" data-delivery-retry @click="$emit('prepare-retry')">重新准备</a-button>
          </template>
        </a-alert>
      </template>
    </header>

    <a-skeleton v-if="loading" active :paragraph="{ rows: 8 }" />

    <section v-else-if="failure" class="kb-reader-failure kb-panel hbos-glass-g1" data-reader-error :data-reader-failure="failure.kind" role="alert">
      <h2>{{ failureTitle }}</h2>
      <a-alert :type="failure.kind === 'unavailable' || failure.kind === 'invalid' ? 'warning' : 'error'" show-icon :message="failure.message" :description="failureHelp" />
      <div class="kb-reader-failure-actions">
        <a-button v-if="failure.retryable" type="primary" data-reader-retry @click="$emit('retry')"><ReloadOutlined />重试</a-button>
        <a-button data-reader-failure-back @click="$emit('back')">{{ backLabel }}</a-button>
      </div>
    </section>

    <template v-else-if="body">
      <section class="kb-reader-toolbar kb-panel hbos-glass-g1" aria-label="正文导航与查找">
        <div class="kb-reader-pager" role="group" aria-label="正文翻页">
          <a-button :disabled="page <= 1 || pageLoading" data-reader-prev @click="$emit('prev')"><LeftOutlined />上一页</a-button>
          <span class="kb-reader-page-count">第 {{ page }} 页<template v-if="pageCount !== null"> / 共 {{ pageCount }} 页</template><template v-else> · 页数待核</template></span>
          <a-button :disabled="pageCount === null || page >= pageCount || pageLoading" data-reader-next @click="$emit('next')">下一页<RightOutlined /></a-button>
          <form class="kb-reader-jump" @submit.prevent="submitJump">
            <label class="sr-only" for="reader-page-input">跳转页码</label>
            <input id="reader-page-input" v-model="pageInput" type="number" inputmode="numeric" min="1" :max="pageCount || undefined" :disabled="pageLoading">
            <a-button html-type="submit" :disabled="pageLoading" data-reader-jump>跳页</a-button>
          </form>
        </div>
        <form class="kb-reader-search" role="search" @submit.prevent="$emit('search')">
          <label class="sr-only" for="reader-search-input">在本文中查找</label>
          <input id="reader-search-input" :value="searchQuery" type="search" maxlength="120" placeholder="在本文中查找关键词…" :disabled="searching" @input="onSearchInput">
          <a-button html-type="submit" :loading="searching" :disabled="!searchQuery.trim()" data-reader-search-submit>查找</a-button>
          <a-button v-if="searchRan" :disabled="searching" data-reader-search-clear @click="$emit('clear-search')">清除</a-button>
        </form>
        <p v-if="searchMessage" class="kb-reader-search-status" role="status" data-reader-search-status>{{ searchMessage }}</p>
        <ul v-if="matches.length" class="kb-reader-matches" data-reader-search-results>
          <li v-for="(match, index) in matches" :key="match.block_id + '-' + index">
            <button type="button" data-reader-match @click="$emit('jump-match', match)">
              <span class="kb-reader-match-page">{{ match.page !== null ? '第 ' + match.page + ' 页' : '页码未核验' }}</span>
              <span class="kb-reader-match-snippet">{{ match.snippet }}</span>
            </button>
          </li>
        </ul>
      </section>

      <section v-if="pageFailure" class="kb-reader-page-failure" role="alert" data-reader-page-error>
        <a-alert type="error" show-icon :message="pageFailure.message" description="当前页面内容未更新；已保留上一次成功读取的正文。">
          <template #action><a-button v-if="pageFailure.retryable" size="small" data-reader-page-retry @click="$emit('retry-page')">重试本页</a-button></template>
        </a-alert>
      </section>

      <details v-if="navigation && navigation.toc.length" class="kb-reader-toc kb-panel hbos-glass-g1" data-reader-toc>
        <summary>目录（{{ navigation.toc.length }} 条<template v-if="navigation.toc_truncated">，目录仅覆盖前 {{ navigation.toc.length }} 部分</template>）</summary>
        <ol>
          <li v-for="entry in navigation.toc" :key="entry.ordinal">
            <button type="button" :disabled="entry.page_number === null" @click="entry.page_number !== null && $emit('go-page', entry.page_number)">
              {{ entry.title }}
              <small>{{ entry.page_number !== null ? '第 ' + entry.page_number + ' 页' : '页码未核验' }}</small>
            </button>
          </li>
        </ol>
      </details>

      <section class="kb-reader-body kb-panel hbos-glass-g1" :aria-busy="pageLoading ? 'true' : 'false'" data-reader-body>
        <div v-if="previewActive" class="kb-preview-frame" data-reader-preview-frame role="region" aria-label="原版式预览">
          <div class="kb-preview-head">
            <span>{{ previewKindLabel }} · {{ previewFilename }}</span>
            <span class="kb-preview-expiry" data-preview-expiry>预览票据 {{ previewExpiryLabel }} 到期，过期后需重新准备</span>
            <a-button size="small" data-preview-close @click="$emit('close-preview')"><CloseOutlined />关闭预览，回到正文</a-button>
            <a-button size="small" :disabled="deliveryState.preview.busy" @click="$emit('prepare-preview')">重新准备预览</a-button>
          </div>
          <iframe v-if="previewUrl" :src="previewUrl" :title="previewKindLabel" data-preview-iframe sandbox="allow-same-origin"></iframe>
          <p class="kb-muted">预览失败或空白时，可关闭预览继续阅读下方正文。</p>
        </div>
        <div v-if="body.blocks.length === 0 && !previewActive" class="kb-reader-empty" data-reader-empty>
          <a-empty v-if="body.block_total === 0" description="该资料暂无可读正文（索引正文不可用）。" />
          <a-empty v-else description="本页暂无可展示正文（本页索引文本未通过安全净化）；可翻页或使用文内查找。" />
        </div>
        <article
          v-for="(block, index) in body.blocks"
          :id="'reader-block-' + block.block_id"
          :key="block.block_id"
          class="kb-reader-block"
          :class="{ 'is-highlight': highlightBlockId === block.block_id }"
          :data-reader-block="block.block_id"
          :data-highlight="highlightBlockId === block.block_id ? 'true' : undefined"
        >
          <h3 v-if="showSection(index)" class="kb-reader-section">{{ block.section }}</h3>
          <p class="kb-reader-text" :data-reader-text="block.block_id">
            <template v-for="(segment, segmentIndex) in segments(block.block_id, block.text)" :key="segmentIndex">
              <mark v-if="segment.match">{{ segment.text }}</mark>
              <template v-else>{{ segment.text }}</template>
            </template>
          </p>
        </article>
        <p v-if="pageLoading" class="kb-reader-page-loading" role="status">正在读取该页正文…</p>
      </section>

      <footer class="kb-reader-footer">
        <span>共 {{ blockTotal }} 段正文</span>
        <span>阅读版由索引文本派生，页码以原件核验为准</span>
      </footer>
    </template>

    <section v-else class="kb-reader-failure kb-panel hbos-glass-g1" role="status">
      <h2>暂无可显示的正文</h2>
      <p>本次没有读取到可展示的正文内容，请返回后重新打开资料。</p>
      <a-button @click="$emit('back')">{{ backLabel }}</a-button>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'
import { ArrowLeftOutlined, LeftOutlined, RightOutlined, ReloadOutlined, FilePdfOutlined, DownloadOutlined, CloseOutlined } from '@ant-design/icons-vue'
import type {
  ReaderBody,
  ReaderDocument,
  ReaderFailure,
  ReaderNavigation,
  ReaderSearchMatch,
  ReaderSource,
} from '@/contracts/documentReader'
import type { DocumentCapabilities } from '@/services/knowledgeDelivery'
import { deliveryReasonMessage } from '@/services/knowledgeDelivery'

const props = defineProps<{
  from: ReaderSource
  /** True when the entry carried no logical version and the server resolved it. */
  versionResolved?: boolean
  document: ReaderDocument | null
  body: ReaderBody | null
  navigation: ReaderNavigation | null
  disclosure: string
  page: number
  pageCount: number | null
  blockTotal: number
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
  /** Frozen delivery contract state, owned by the view. */
  deliveryState: {
    capabilities: DocumentCapabilities | null
    loadingCapabilities: boolean
    preview: { busy: boolean; url: string | null; filename: string; expiresAt: number | null; kind: string }
    download: { busy: boolean; url: string | null; filename: string }
    error: string
    retryable: boolean
    notice: string
  }
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
  'prepare-preview': []
  'prepare-download': []
  'prepare-retry': []
  'close-preview': []
}>()

const pageInput = ref(String(props.page))
watch(() => props.page, value => { pageInput.value = String(value) })

const EMPTY_DELIVERY = {
  capabilities: null,
  loadingCapabilities: false,
  preview: { busy: false, url: null as string | null, filename: '', expiresAt: null as number | null, kind: '' },
  download: { busy: false, url: null as string | null, filename: '' },
  error: '',
  retryable: false,
  notice: '',
}
const deliveryState = computed(() => props.deliveryState ?? EMPTY_DELIVERY)
const previewUrl = computed(() => deliveryState.value.preview.url)
const previewActive = computed(() => Boolean(deliveryState.value.preview.url))
const previewKindLabel = computed(() => (deliveryState.value.preview.kind === 'DERIVED_PDF' ? '派生预览版（非原件）' : '原件 PDF 预览'))
const previewExpiryLabel = computed(() => {
  const value = deliveryState.value.preview.expiresAt
  return typeof value === 'number' && Number.isFinite(value) ? new Date(value * 1000).toLocaleTimeString() : '稍后'
})
const previewFilename = computed(() => deliveryState.value.preview.filename || '资料')

const backLabel = computed(() => ({ ask: '返回回答', search: '返回搜索结果', catalog: '返回资料目录' }[props.from] || '返回'))
const sourceLabel = computed(() => ({ ask: '回答来源', search: '搜索结果', catalog: '资料目录' }[props.from] || '资料'))
const authorizationLabel = computed(() => {
  if (!props.document) return '授权状态待核'
  if (props.document.authorization === 'AUTHORIZED') return '已授权阅读'
  if (props.document.authorization === 'READ_ONLY') return '只读授权'
  return '授权状态待核'
})
const authorizationTone = computed(() => (props.document?.authorization === 'AUTHORIZED' ? 'green' : 'orange'))
const referenceLabel = computed(() => {
  const state = props.document?.reference_state
  if (state === 'CURRENT') return '当前现行版本'
  if (state === 'WITHDRAWN') return '已撤回'
  if (state === 'SUPERSEDED') return '历史版本'
  return '现行性待核'
})
const referenceTone = computed(() => (props.document?.reference_state === 'CURRENT' ? 'green' : 'orange'))
const failureTitle = computed(() => {
  if (!props.failure) return '资料暂不可读'
  if (props.failure.kind === 'unavailable') return '当前不可阅读'
  if (props.failure.kind === 'invalid') return '无法打开这份资料'
  if (props.failure.kind === 'upstream') return '正文服务暂时不可用'
  return '资料阅读暂不可用'
})
const failureHelp = computed(() => {
  if (!props.failure) return ''
  if (props.failure.kind === 'unavailable') return '如确认仍有阅读权限，请从资料目录重新打开当前版本；系统不会在未授权时保留正文。'
  if (props.failure.kind === 'invalid') return '请核对资料入口或从资料目录重新进入。'
  if (props.failure.kind === 'upstream') return '当前提示不代表该资料没有正文；请稍后重试。'
  return '请稍后重试；当前提示不代表该资料没有正文。'
})

function onSearchInput(event: Event) {
  emit('update:searchQuery', (event.target as HTMLInputElement).value)
}

function submitJump() {
  const parsed = Number.parseInt(pageInput.value, 10)
  const max = props.pageCount
  let next = Number.isSafeInteger(parsed) ? parsed : 1
  if (next < 1) next = 1
  if (max !== null && max > 0) next = Math.min(next, max)
  pageInput.value = String(next)
  emit('go-page', next)
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
  const haystack = text.toLocaleLowerCase()
  const needle = query.toLocaleLowerCase()
  if (!needle || !haystack.includes(needle)) return [{ text, match: false }]
  const result: TextSegment[] = []
  let cursor = 0
  let guard = 0
  while (cursor < text.length && guard < 100) {
    const found = haystack.indexOf(needle, cursor)
    if (found < 0) break
    if (found > cursor) result.push({ text: text.slice(cursor, found), match: false })
    result.push({ text: text.slice(found, found + needle.length), match: true })
    cursor = found + needle.length
    guard++
  }
  if (cursor < text.length) result.push({ text: text.slice(cursor), match: false })
  return result.length ? result : [{ text, match: false }]
}

// Bring the matched block into view after the target page has rendered.
watch([() => props.highlightBlockId, () => props.page], async () => {
  if (!props.highlightBlockId) return
  await nextTick()
  const element = document.getElementById(`reader-block-${props.highlightBlockId}`)
  if (element && typeof element.scrollIntoView === 'function') element.scrollIntoView({ block: 'center' })
})
</script>

<style scoped>
.kb-document-reader { display: grid; gap: 18px; min-width: 0; }
.kb-document-reader .kb-panel { margin: 0; }
.kb-reader-header { padding: 24px; border-radius: 23px; display: grid; gap: 12px; min-width: 0; }
.kb-reader-crumb { display: flex; flex-wrap: wrap; align-items: center; gap: 8px; }
.kb-reader-source { font-size: 12px; color: var(--hbos-text-muted); }
.kb-reader-title { margin: 0; font-size: 26px; line-height: 34px; color: #203b66; overflow-wrap: anywhere; }
.kb-reader-meta { margin: 0; font-size: 14px; line-height: 22px; color: var(--hbos-text-secondary); overflow-wrap: anywhere; }
.kb-reader-badges { display: flex; flex-wrap: wrap; gap: 8px; }
.kb-reader-status { margin: 0; font-size: 13px; line-height: 20px; color: var(--hbos-text-secondary); }
.kb-reader-disclosure { margin: 4px 0 0; }
.kb-reader-origin { margin: 0; font-size: 12px; line-height: 20px; color: var(--hbos-text-muted); }
.kb-reader-delivery { display: flex; flex-wrap: wrap; gap: 10px; align-items: center; }
.kb-reader-delivery-notice { margin: 0; font-size: 12px; line-height: 20px; color: #147e70; overflow-wrap: anywhere; }
.kb-reader-delivery-error { margin: 0; }
.kb-preview-frame { grid-column: 1 / -1; display: grid; gap: 8px; border: 1px solid var(--hbos-border-strong); border-radius: 12px; padding: 12px; background: rgba(255,255,255,.6); }
.kb-preview-head { display: flex; flex-wrap: wrap; align-items: center; gap: 10px; font-size: 13px; color: var(--hbos-text-secondary); }
.kb-preview-expiry { font-size: 12px; color: var(--hbos-text-muted); margin-left: auto; }
.kb-preview-frame iframe { width: 100%; height: 70vh; min-height: 320px; border: 1px solid var(--hbos-border-strong); border-radius: 8px; background: #fff; }
.kb-reader-toolbar { padding: 16px 20px; border-radius: 20px; display: grid; gap: 12px; min-width: 0; }
.kb-reader-pager { display: flex; flex-wrap: wrap; align-items: center; gap: 10px; }
.kb-reader-page-count { font-size: 14px; color: var(--hbos-text-secondary); white-space: nowrap; }
.kb-reader-jump { display: flex; align-items: center; gap: 6px; margin-left: auto; }
.kb-reader-jump input { width: 76px; padding: 6px 8px; border: 1px solid var(--hbos-border-strong); border-radius: 8px; font: inherit; color: var(--hbos-text-primary); background: var(--hbos-bg-surface); }
.kb-reader-search { display: flex; flex-wrap: wrap; align-items: center; gap: 8px; }
.kb-reader-search input { flex: 1 1 220px; min-width: 0; padding: 9px 12px; border: 1px solid var(--hbos-border-strong); border-radius: 10px; font: inherit; color: var(--hbos-text-primary); background: var(--hbos-bg-surface); }
.kb-reader-search-status { margin: 0; font-size: 13px; line-height: 20px; color: var(--hbos-text-secondary); overflow-wrap: anywhere; }
.kb-reader-matches { list-style: none; margin: 0; padding: 0; display: grid; gap: 6px; max-height: 240px; overflow-y: auto; }
.kb-reader-matches button { display: flex; gap: 10px; width: 100%; text-align: left; border: 1px solid var(--hbos-border-strong); border-radius: 10px; background: rgba(255, 255, 255, .72); padding: 8px 10px; font: inherit; cursor: pointer; overflow-wrap: anywhere; }
.kb-reader-match-page { flex: none; font-size: 12px; color: #127a67; white-space: nowrap; }
.kb-reader-match-snippet { font-size: 13px; line-height: 20px; color: var(--hbos-text-primary); }
.kb-reader-page-failure { min-width: 0; }
.kb-reader-toc { padding: 14px 20px; border-radius: 18px; min-width: 0; }
.kb-reader-toc summary { cursor: pointer; font-size: 14px; color: #203b66; }
.kb-reader-toc ol { margin: 12px 0 0; padding-left: 20px; display: grid; gap: 6px; max-height: 280px; overflow-y: auto; }
.kb-reader-toc button { border: 0; background: transparent; padding: 4px 0; text-align: left; font: inherit; color: #247a70; cursor: pointer; overflow-wrap: anywhere; }
.kb-reader-toc button:disabled { color: var(--hbos-text-muted); cursor: default; }
.kb-reader-toc small { margin-left: 8px; color: var(--hbos-text-muted); }
.kb-reader-body { padding: 24px 28px; border-radius: 23px; display: grid; gap: 16px; min-width: 0; }
.kb-reader-block { min-width: 0; padding-bottom: 4px; border-bottom: 1px dashed rgba(65, 91, 138, .12); }
.kb-reader-block:last-of-type { border-bottom: 0; }
.kb-reader-block.is-highlight { background: rgba(21, 155, 137, .07); border-radius: 10px; padding: 8px 10px; }
.kb-reader-section { margin: 4px 0 8px; font-size: 17px; line-height: 26px; color: #203b66; overflow-wrap: anywhere; }
.kb-reader-text { margin: 0; font-size: 16px; line-height: 28px; color: var(--hbos-text-primary); white-space: pre-wrap; overflow-wrap: anywhere; }
.kb-reader-text mark { background: #ffe9a8; color: inherit; padding: 0 1px; border-radius: 2px; }
.kb-reader-empty { padding: 12px 0; }
.kb-reader-page-loading { margin: 0; font-size: 13px; color: var(--hbos-text-muted); }
.kb-reader-failure { padding: 24px; border-radius: 23px; display: grid; gap: 16px; min-width: 0; }
.kb-reader-failure h2 { margin: 0; font-size: 20px; line-height: 28px; color: #203b66; }
.kb-reader-failure-actions { display: flex; flex-wrap: wrap; gap: 10px; }
.kb-reader-footer { display: flex; flex-wrap: wrap; justify-content: space-between; gap: 8px; font-size: 12px; line-height: 20px; color: var(--hbos-text-muted); padding: 0 4px; }
@media (max-width: 390px) {
  .kb-reader-delivery { flex-direction: column; align-items: stretch; }
  .kb-reader-delivery .ant-btn { width: 100%; }
}
@media (max-width: 900px) {
  .kb-reader-header, .kb-reader-body { padding: 20px; }
  .kb-reader-jump { margin-left: 0; }
}
@media (max-width: 600px) {
  .kb-document-reader { gap: 14px; }
  .kb-reader-header { padding: 16px; border-radius: 18px; }
  .kb-reader-title { font-size: 21px; line-height: 29px; }
  .kb-reader-toolbar { padding: 14px; border-radius: 16px; }
  .kb-reader-pager { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .kb-reader-delivery { flex-direction: column; align-items: stretch; }
  .kb-reader-delivery .ant-btn { width: 100%; }
  .kb-reader-page-count { grid-column: 1 / -1; grid-row: 1; text-align: center; }
  .kb-reader-jump { grid-column: 1 / -1; margin-left: 0; }
  .kb-reader-search input { flex-basis: 100%; }
  .kb-preview-frame iframe { height: 56vh; }
  .kb-preview-expiry { margin-left: 0; }
  .kb-reader-body { padding: 16px; border-radius: 18px; gap: 14px; }
  .kb-reader-text { font-size: 16px; line-height: 27px; }
  .kb-reader-footer { flex-direction: column; }
}
</style>
