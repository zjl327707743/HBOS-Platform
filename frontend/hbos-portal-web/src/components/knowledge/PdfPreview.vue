<template>
  <div class="kb-pdf-preview" data-pdf-preview :aria-busy="loading || painting">
    <p v-if="loading" role="status">正在打开文件…</p>
    <a-alert v-if="error" type="warning" show-icon :message="error" :description="errorHelp"/>
    <div v-if="pages" class="kb-pdf-toolbar" role="group" aria-label="文件页与缩放">
      <a-button :disabled="page<=1 || painting" data-pdf-prev @click="page--">上一页</a-button>
      <label class="kb-pdf-jump"><span class="sr-only">跳到文件页码</span>
        <input v-model="pageInput" type="number" inputmode="numeric" min="1" :max="pages" :disabled="painting" @keydown.enter.prevent="jump">
        <span>/ {{pages}} 页</span>
      </label>
      <a-button :disabled="page>=pages || painting" data-pdf-next @click="page++">下一页</a-button>
      <span class="kb-pdf-zoom" role="group" aria-label="缩放">
        <a-button :disabled="scale<=0.5 || painting" data-pdf-zoom-out @click="setScale(scale-0.25)">缩小</a-button>
        <button type="button" class="kb-pdf-scale" data-pdf-fit @click="fitWidth" title="按栏宽显示">{{scale ? Math.round(scale*100) + '%' : '适宽'}}</button>
        <a-button :disabled="scale>=3 || painting" data-pdf-zoom-in @click="setScale(scale+0.25)">放大</a-button>
      </span>
    </div>
    <div ref="surface" class="kb-pdf-surface" data-pdf-surface><canvas ref="canvas" v-show="!error && pages" role="img" :aria-label="'文件第 '+page+' 页'"/></div>
    <p v-if="pages && !loading && !painting && !error" data-pdf-rendered role="status">当前为文件第 {{page}} 页，共 {{pages}} 页。</p>
  </div>
</template>
<script setup lang="ts">
import { nextTick, onBeforeUnmount, ref, watch } from 'vue'
import type { PDFDocumentLoadingTask, PDFDocumentProxy, RenderTask } from 'pdfjs-dist'
import workerUrl from 'pdfjs-dist/build/pdf.worker.mjs?url'

/**
 * One file view: canvas only, no iframe, no plugin, no script.
 *
 * The ticket that authorises the bytes lapses quickly on purpose. `renew` is
 * asked for a fresh one when a fetch is refused or fails, at most twice per
 * open, and the view never shows a ticket or an expiry to the employee.
 */
const props = defineProps<{ url: string; page?: number; zoom?: number; renew?: () => Promise<string | null> }>()
const emit = defineEmits<{ 'access-lost': []; 'update:page': [value: number]; 'update:zoom': [value: number] }>()

const surface = ref<HTMLDivElement | null>(null), canvas = ref<HTMLCanvasElement | null>(null)
const loading = ref(false), painting = ref(false), error = ref(''), pages = ref(0)
const page = ref(Math.max(1, Math.round(props.page || 1)))
const pageInput = ref(String(page.value))
const scale = ref(props.zoom && props.zoom > 0 ? props.zoom : 0)
const errorHelp = ref('文件仍可下载；也可以继续阅读下方检索正文。')

let generation = 0, drawGeneration = 0, abort: AbortController | null = null
let task: PDFDocumentLoadingTask | null = null, pdf: PDFDocumentProxy | null = null, render: RenderTask | null = null
let observer: ResizeObserver | null = null, lastWidth = 0, renewals = 0

watch(page, value => { pageInput.value = String(value); emit('update:page', value); void draw() })
watch(() => props.page, value => {
  const next = Math.max(1, Math.round(value || 1))
  if (next !== page.value) page.value = next
})
watch(scale, value => emit('update:zoom', value))

function clear() {
  generation++; drawGeneration++; abort?.abort(); abort = null; render?.cancel(); render = null
  const old = task; task = null; pdf = null; if (old) void old.destroy().catch(() => {})
  pages.value = 0; painting.value = false
  if (canvas.value) { canvas.value.width = 0; canvas.value.height = 0 }
}

function setScale(next: number) {
  const value = Math.min(3, Math.max(0.5, Math.round(next * 4) / 4))
  if (value === scale.value) return
  scale.value = value
  void draw()
}

function fitWidth() {
  // 0 means "fit the column" and is what a fresh open shows; pressing the
  // control returns to that fit without inventing a physical DPI.
  scale.value = 0
  emit('update:zoom', 0)
  void draw()
}

function jump() {
  const value = Number.parseInt(pageInput.value, 10)
  const next = Number.isSafeInteger(value) ? Math.min(Math.max(value, 1), pages.value || 1) : 1
  pageInput.value = String(next)
  if (next !== page.value) page.value = next
}

async function draw() {
  if (!pdf || !canvas.value) return
  const current = pdf, epoch = generation, seq = ++drawGeneration
  render?.cancel()
  if (render) await render.promise.catch(() => {})
  if (epoch !== generation || seq !== drawGeneration) return
  painting.value = true
  try {
    const leaf = await current.getPage(Math.min(page.value, current.numPages))
    if (epoch !== generation || seq !== drawGeneration || !canvas.value) return
    const base = leaf.getViewport({ scale: 1 })
    const column = Math.max(240, Math.min(surface.value?.clientWidth || 800, 1100))
    lastWidth = column
    const fit = Math.min(column / base.width, Math.sqrt(2_000_000 / (base.width * base.height)), 2)
    const viewport = leaf.getViewport({ scale: fit * (scale.value || 1) })
    canvas.value.width = Math.ceil(viewport.width)
    canvas.value.height = Math.ceil(viewport.height)
    render = leaf.render({ canvas: canvas.value, viewport })
    await render.promise
  } catch (e) {
    if (epoch === generation && seq === drawGeneration && (e as Error)?.name !== 'RenderingCancelledException') {
      error.value = '这一页暂时没能显示，可以换一页或下载原文件。'
    }
  } finally {
    if (epoch === generation && seq === drawGeneration) painting.value = false
  }
}

async function fetchBytes(url: string, epoch: number): Promise<ArrayBuffer> {
  const controller = new AbortController(); abort = controller
  const response = await fetch(url, { credentials: 'same-origin', cache: 'no-store', redirect: 'error', signal: controller.signal })
  if (!response.ok) {
    const retryable = response.status === 401 || response.status === 403 || response.status === 416
    if (retryable && props.renew && renewals < 2 && epoch === generation) {
      renewals++
      const next = await props.renew()
      if (next && epoch === generation) return fetchBytes(next, epoch)
    }
    if (response.status === 401 || response.status === 403) emit('access-lost')
    throw new Error('FILE_UNAVAILABLE')
  }
  return response.arrayBuffer()
}

async function load() {
  clear(); error.value = ''; loading.value = true; renewals = 0
  const epoch = generation
  try {
    const buffer = await fetchBytes(props.url, epoch)
    if (epoch !== generation) return
    const bytes = new Uint8Array(buffer)
    if (bytes.byteLength > 768 * 1024 * 1024 || new TextDecoder('ascii').decode(bytes.subarray(0, 5)) !== '%PDF-') {
      throw new Error('NOT_A_PDF')
    }
    const lib = await import('pdfjs-dist')
    if (epoch !== generation) return
    lib.GlobalWorkerOptions.workerSrc = workerUrl
    const local = import.meta.env.BASE_URL + 'pdfjs/'
    // Canvas only: no annotation links, scripting, XFA or embedded HTML.
    task = lib.getDocument({ data: bytes, enableXfa: false, useSystemFonts: false, useWorkerFetch: true,
      cMapUrl: local + 'cmaps/', cMapPacked: true, standardFontDataUrl: local + 'standard_fonts/', wasmUrl: local + 'wasm/',
      maxImageSize: 16_000_000, canvasMaxAreaInBytes: 16_000_000, verbosity: 0 })
    const value = await task.promise
    if (epoch !== generation) return
    if (value.numPages < 1 || value.numPages > 2000) throw new Error('PAGE_LIMIT')
    pdf = value; pages.value = value.numPages
    if (page.value > value.numPages) page.value = value.numPages
    await nextTick(); await draw()
    if (typeof ResizeObserver !== 'undefined' && surface.value) {
      observer?.disconnect()
      observer = new ResizeObserver(entries => {
        const width = Math.max(240, Math.min(entries[0]?.contentRect.width || 800, 1100))
        if (Math.abs(width - lastWidth) > 8) void draw()
      })
      observer.observe(surface.value)
    }
  } catch (e) {
    if (epoch !== generation || (e as Error)?.name === 'AbortError') return
    error.value = (e as Error)?.message === 'NOT_A_PDF' ? '这份文件不是可预览的 PDF，请下载原文件查看。' : '文件暂时没能打开，可以重试或下载原文件。'
    errorHelp.value = '重开会自动获取新的访问凭据，无需手动处理。'
  } finally {
    if (epoch === generation) loading.value = false
  }
}

watch(() => props.url, () => void load(), { immediate: true })
onBeforeUnmount(() => { observer?.disconnect(); clear() })
defineExpose({ page, pages, scale, reload: load })
</script>
<style scoped>
.kb-pdf-preview{display:grid;gap:10px;min-width:0}
.kb-pdf-toolbar{display:flex;flex-wrap:wrap;align-items:center;gap:8px}
.kb-pdf-jump{display:flex;align-items:center;gap:6px;font-size:13px;color:var(--hbos-text-secondary)}
.kb-pdf-jump input{width:68px;padding:5px 8px;border:1px solid var(--hbos-border-strong);border-radius:8px;font:inherit;color:var(--hbos-text-primary);background:var(--hbos-bg-surface)}
.kb-pdf-zoom{display:flex;align-items:center;gap:6px;margin-left:auto}
.kb-pdf-scale{min-width:62px;padding:5px 8px;border:1px solid var(--hbos-border-strong);border-radius:8px;background:var(--hbos-bg-surface);font:inherit;font-size:13px;color:var(--hbos-text-primary);cursor:pointer}
.kb-pdf-surface{width:100%;overflow:auto;min-width:0;background:#eef1f4;border-radius:10px;padding:8px}
.kb-pdf-surface canvas{display:block;margin:auto;max-width:100%;height:auto;background:white;box-shadow:0 2px 10px rgba(32,59,102,.12)}
.kb-pdf-preview p{font-size:12px;line-height:1.7;color:var(--hbos-text-secondary);margin:0}
@media (max-width:600px){.kb-pdf-zoom{margin-left:0;width:100%;justify-content:space-between}.kb-pdf-surface{padding:4px}}
</style>
