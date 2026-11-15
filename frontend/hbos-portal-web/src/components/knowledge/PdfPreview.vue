<template>
  <div class="kb-pdf-preview" data-pdf-preview :aria-busy="loading || painting">
    <p v-if="loading" role="status">正在打开文件…</p>
    <a-alert v-if="error" type="warning" show-icon :message="error" :description="errorHelp"/>
    <div class="kb-pdf-toolbar" :role="pages ? 'group' : undefined" :aria-label="pages ? '文件页与缩放' : undefined">
      <template v-if="pages">
        <a-button :disabled="page<=1 || painting" data-pdf-prev aria-label="上一页" @click="page--"><LeftOutlined /></a-button>
        <label class="kb-pdf-jump"><span class="sr-only">跳到文件页码</span>
          <input v-model="pageInput" type="number" inputmode="numeric" min="1" :max="pages" :disabled="painting" @keydown.enter.prevent="jump">
          <span class="kb-pdf-pages">/ {{pages}} 页</span>
        </label>
        <a-button :disabled="page>=pages || painting" data-pdf-next aria-label="下一页" @click="page++"><RightOutlined /></a-button>
        <span class="kb-pdf-zoom" role="group" aria-label="缩放">
          <a-button :disabled="(scale || 1) <= 0.5 || painting" data-pdf-zoom-out aria-label="缩小" @click="zoomBy(-0.25)"><MinusOutlined /></a-button>
          <button type="button" class="kb-pdf-scale" data-pdf-fit @click="fitWidth" title="按栏宽显示">{{Math.round((scale || 1) * 100)}}%</button>
          <a-button :disabled="scale >= 3 || painting" data-pdf-zoom-in aria-label="放大" @click="zoomBy(0.25)"><PlusOutlined /></a-button>
        </span>
      </template>
      <slot name="toolbar-extra" />
    </div>
    <div ref="surface" class="kb-pdf-surface" :class="{ 'kb-pdf-enlarged': scale > 1 }" data-pdf-surface><canvas ref="canvas" v-show="!error && pages" role="img" :aria-label="'文件第 '+page+' 页'"/></div>
    <p v-if="pages && !loading && !painting && !error" data-pdf-rendered role="status">当前为文件第 {{page}} 页，共 {{pages}} 页。</p>
  </div>
</template>
<script setup lang="ts">
import { nextTick, onBeforeUnmount, ref, watch } from 'vue'
import { LeftOutlined, MinusOutlined, PlusOutlined, RightOutlined } from '@ant-design/icons-vue'
import type { PDFDocumentLoadingTask, PDFDocumentProxy, RenderTask } from 'pdfjs-dist'
import workerUrl from 'pdfjs-dist/build/pdf.worker.mjs?url'
import { PdfRangeSource,PDF_RANGE_CHUNK_BYTES } from './pdfRange'

/**
 * One file view: canvas only, no iframe, no plugin, no script.
 *
 * The ticket that authorises the bytes lapses quickly on purpose. `renew` is
 * asked for a fresh one when a range is refused, at most twice per request.
 * A page change reauthorizes before drawing cached bytes. The view never
 * shows a ticket or an expiry to the employee.
 */
const props = defineProps<{ url: string; page?: number; zoom?: number; renew?: () => Promise<string | null> }>()
const emit = defineEmits<{ 'access-lost': []; 'update:page': [value: number]; 'update:zoom': [value: number] }>()

const surface = ref<HTMLDivElement | null>(null), canvas = ref<HTMLCanvasElement | null>(null)
const loading = ref(false), painting = ref(false), error = ref(''), pages = ref(0)
const page = ref(Math.max(1, Math.round(props.page || 1)))
const pageInput = ref(String(page.value))
const scale = ref(props.zoom && props.zoom > 0 ? props.zoom : 0)
const errorHelp = ref('文件仍可下载；也可以继续阅读下方检索正文。')

let generation = 0, drawGeneration = 0, byteSource: PdfRangeSource | null = null
let task: PDFDocumentLoadingTask | null = null, pdf: PDFDocumentProxy | null = null, render: RenderTask | null = null
let observer: ResizeObserver | null = null, lastWidth = 0

watch(page, value => { pageInput.value = String(value); emit('update:page', value); void draw(true) })
watch(() => props.page, value => {
  const next = Math.max(1, Math.round(value || 1))
  if (next !== page.value) page.value = next
})
watch(scale, value => emit('update:zoom', value))

function clear() {
  generation++; drawGeneration++; byteSource?.close(); byteSource = null; render?.cancel(); render = null
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

/** Step from the fitted view (scale 0 = fit) into an explicit scale. */
function zoomBy(delta: number) {
  setScale((scale.value || 1) + delta)
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

async function draw(reauthorize = false) {
  if (!pdf || !canvas.value) return
  const current = pdf, epoch = generation, seq = ++drawGeneration
  render?.cancel()
  if (render) await render.promise.catch(() => {})
  if (epoch !== generation || seq !== drawGeneration) return
  painting.value = true
  try {
    // Already downloaded page data does not replace current authorization.
    if (reauthorize) await byteSource?.revalidate()
    if (epoch !== generation || seq !== drawGeneration) return
    const leaf = await current.getPage(Math.min(page.value, current.numPages))
    if (epoch !== generation || seq !== drawGeneration || !canvas.value) return
    const base = leaf.getViewport({ scale: 1 })
    const available = surface.value
      ? surface.value.clientWidth - parseFloat(getComputedStyle(surface.value).paddingInlineStart) - parseFloat(getComputedStyle(surface.value).paddingInlineEnd)
      : 800
    const column = Math.max(1, Math.min(available, 1100))
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

async function load() {
  clear(); error.value = ''; loading.value = true
  const epoch = generation
  try {
    const source = new PdfRangeSource(props.url,{ renew:props.renew,onAccessLost:()=>{
      if(epoch!==generation)return
      clear();loading.value=false;error.value='资料状态已变化，请重新打开资料。';errorHelp.value='';emit('access-lost')
    } })
    byteSource=source
    const first = await source.initialize()
    const lib = await import('pdfjs-dist')
    if (epoch !== generation) return
    lib.GlobalWorkerOptions.workerSrc = workerUrl
    const local = import.meta.env.BASE_URL + 'pdfjs/'
    class TicketRanges extends lib.PDFDataRangeTransport {
      requestDataRange(begin:number,end:number) {
        void source.read(begin,end).then(chunk=>{
          if(epoch===generation)this.onDataRange(begin,chunk)
        }).catch(e=>{
          if(epoch!==generation || (e as Error)?.name==='AbortError')return
          clear();loading.value=false;error.value='文件暂时没能打开，可以重试或下载原文件。'
        })
      }
      abort(){source.close()}
    }
    // Canvas only: no annotation links, scripting, XFA or embedded HTML.
    task = lib.getDocument({ range:new TicketRanges(first.length,first.initialData,true),rangeChunkSize:PDF_RANGE_CHUNK_BYTES,
      disableAutoFetch:true,disableStream:true,enableXfa: false, useSystemFonts: false, useWorkerFetch: true,
      cMapUrl: local + 'cmaps/', cMapPacked: true, standardFontDataUrl: local + 'standard_fonts/', wasmUrl: local + 'wasm/',
      maxImageSize: 16_000_000, canvasMaxAreaInBytes: 16_000_000, verbosity: 0 })
    const value = await task.promise
    if (epoch !== generation) return
    // The same ceiling the server uses for a preview: a published scanned book
    // in the corpus runs to 2032 pages, and this cap used to refuse it after
    // the bytes had already been fetched and parsed.
    if (value.numPages < 1 || value.numPages > 4000) throw new Error('PAGE_LIMIT')
    pdf = value; pages.value = value.numPages
    if (page.value > value.numPages) page.value = value.numPages
    await nextTick(); await draw()
    if (typeof ResizeObserver !== 'undefined' && surface.value) {
      observer?.disconnect()
      observer = new ResizeObserver(entries => {
        const width = Math.max(1, Math.min(entries[0]?.contentRect.width || 800, 1100))
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
.kb-pdf-preview{display:grid;grid-template-rows:auto minmax(0,1fr) auto;gap:10px;min-width:0;min-height:0}
.kb-pdf-toolbar{display:flex;flex-wrap:wrap;align-items:center;gap:8px}
.kb-pdf-jump{display:flex;align-items:center;gap:6px;font-size:13px;color:var(--hbos-text-secondary)}
.kb-pdf-jump input{width:68px;padding:5px 8px;border:1px solid var(--hbos-border-strong);border-radius:8px;font:inherit;color:var(--hbos-text-primary);background:var(--hbos-bg-surface)}
.kb-pdf-zoom{display:flex;align-items:center;gap:6px;margin-left:auto}
.kb-pdf-scale{min-width:62px;padding:5px 8px;border:1px solid var(--hbos-border-strong);border-radius:8px;background:var(--hbos-bg-surface);font:inherit;font-size:13px;color:var(--hbos-text-primary);cursor:pointer}
.kb-pdf-surface{width:100%;overflow:auto;min-width:0;background:#eef1f4;border-radius:10px;padding:8px;margin-top:33px}
@media(min-width:390px) and (max-width:1164px){.kb-pdf-surface{margin-top:39px}}
.kb-pdf-surface canvas{display:block;margin:auto;max-width:100%;height:auto;background:white;box-shadow:0 2px 10px rgba(32,59,102,.12)}
.kb-pdf-surface.kb-pdf-enlarged canvas{max-width:none;margin-inline:0}
.kb-pdf-preview p{font-size:12px;line-height:1.7;color:var(--hbos-text-secondary);margin:0}
@media (max-width:600px){
  .kb-pdf-preview{gap:6px}
  .kb-pdf-toolbar{gap:4px;row-gap:6px}
  .kb-pdf-toolbar .ant-btn{padding-inline:5px;min-width:28px}
  .kb-pdf-jump{gap:2px;font-size:11px}
  .kb-pdf-jump input{width:32px;padding:4px 2px;text-align:center}
  .kb-pdf-pages{font-size:11px;white-space:nowrap}
  .kb-pdf-zoom{gap:2px}
  .kb-pdf-scale{min-width:40px;padding:4px 2px;font-size:12px}
  .kb-pdf-surface{padding:4px}
}
</style>
