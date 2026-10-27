<template>
  <div class="kb-pdf-preview" data-pdf-preview :aria-busy="loading || painting">
    <p v-if="loading" role="status">正在读取并呈现预览版…</p>
    <a-alert v-if="error" type="warning" show-icon :message="error" description="下方正文仍可阅读；可点击上方“重新准备预览”重试。"/>
    <div v-if="pages" class="kb-pdf-pager" role="group" aria-label="PDF 原版页导航">
      <a-button :disabled="page<=1 || painting" @click="page--">上一原件页</a-button>
      <span>PDF 第 {{page}} / {{pages}} 页</span>
      <a-button :disabled="page>=pages || painting" @click="page++">下一原件页</a-button>
    </div>
    <div ref="surface" class="kb-pdf-surface"><canvas ref="canvas" v-show="!error && pages" role="img" :aria-label="'PDF 原版式第 '+page+' 页'"/></div>
    <p v-if="pages && !loading && !painting && !error" data-pdf-rendered role="status">已呈现 PDF 第 {{page}} 页。此页码属于预览文件，与上方索引正文页序分别显示。</p>
  </div>
</template>
<script setup lang="ts">
import { nextTick, onBeforeUnmount, ref, watch } from 'vue'
import type { PDFDocumentLoadingTask, PDFDocumentProxy, RenderTask } from 'pdfjs-dist'
import workerUrl from 'pdfjs-dist/build/pdf.worker.mjs?url'
const props=defineProps<{url:string}>()
const emit=defineEmits<{'access-lost':[]}>()
const surface=ref<HTMLDivElement|null>(null),canvas=ref<HTMLCanvasElement|null>(null)
const loading=ref(false),painting=ref(false),error=ref(''),pages=ref(0),page=ref(1)
let generation=0,drawGeneration=0,abort:AbortController|null=null
let task:PDFDocumentLoadingTask|null=null,pdf:PDFDocumentProxy|null=null,render:RenderTask|null=null
let observer:ResizeObserver|null=null,lastWidth=0
function clear(){
  generation++;drawGeneration++;abort?.abort();abort=null;render?.cancel();render=null
  const old=task;task=null;pdf=null;if(old)void old.destroy().catch(()=>{})
  pages.value=0;page.value=1;painting.value=false
  if(canvas.value){canvas.value.width=0;canvas.value.height=0}
}
async function draw(){
  if(!pdf||!canvas.value)return
  const current=pdf,epoch=generation,seq=++drawGeneration
  render?.cancel()
  if(render)await render.promise.catch(()=>{})
  if(epoch!==generation||seq!==drawGeneration)return
  painting.value=true
  try{
    const leaf=await current.getPage(page.value)
    if(epoch!==generation||seq!==drawGeneration||!canvas.value)return
    const base=leaf.getViewport({scale:1}),width=Math.max(240,Math.min(surface.value?.clientWidth||800,1100))
    lastWidth=width
    const scale=Math.min(width/base.width,Math.sqrt(2_000_000/(base.width*base.height)),2)
    const viewport=leaf.getViewport({scale})
    canvas.value.width=Math.ceil(viewport.width);canvas.value.height=Math.ceil(viewport.height)
    render=leaf.render({canvas:canvas.value,viewport})
    await render.promise
  }catch(e){if(epoch===generation&&seq===drawGeneration && (e as Error)?.name!=='RenderingCancelledException')error.value='本页预览未能呈现，请重新准备或继续阅读正文。'}
  finally{if(epoch===generation&&seq===drawGeneration)painting.value=false}
}
async function load(){
  clear();error.value='';loading.value=true
  const epoch=generation,controller=new AbortController();abort=controller
  try{
    const response=await fetch(props.url,{credentials:'same-origin',cache:'no-store',redirect:'error',signal:controller.signal})
    if(!response.ok){
      if(response.status===401||response.status===403)emit('access-lost')
      throw new Error('DELIVERY_UNAVAILABLE')
    }
    if(response.headers.get('Content-Type')?.split(';')[0]!=='application/pdf')throw new Error('INVALID_TYPE')
    const bytes=new Uint8Array(await response.arrayBuffer())
    if(bytes.byteLength>32*1024*1024||new TextDecoder('ascii').decode(bytes.subarray(0,5))!=='%PDF-')throw new Error('INVALID_PDF')
    const lib=await import('pdfjs-dist')
    if(epoch!==generation)return
    lib.GlobalWorkerOptions.workerSrc=workerUrl
    const local=import.meta.env.BASE_URL+'pdfjs/'
    // Render canvas only: no annotation links, scripting, XFA or embedded HTML.
    task=lib.getDocument({data:bytes,enableXfa:false,useSystemFonts:false,useWorkerFetch:true,
      cMapUrl:local+'cmaps/',cMapPacked:true,standardFontDataUrl:local+'standard_fonts/',wasmUrl:local+'wasm/',
      maxImageSize:16_000_000,canvasMaxAreaInBytes:16_000_000,verbosity:0})
    const value=await task.promise
    if(epoch!==generation)return
    if(value.numPages<1||value.numPages>2000)throw new Error('PAGE_LIMIT')
    pdf=value;pages.value=value.numPages;await nextTick();await draw()
    if(typeof ResizeObserver!=='undefined'&&surface.value){
      observer?.disconnect();observer=new ResizeObserver(entries=>{
        const width=Math.max(240,Math.min(entries[0]?.contentRect.width||800,1100))
        if(Math.abs(width-lastWidth)>8)void draw()
      });observer.observe(surface.value)
    }
  }catch(e){if(epoch===generation&&(e as Error)?.name!=='AbortError')error.value='预览未能读取，票据可能已过期或授权已变化。请重新准备。'}
  finally{if(epoch===generation)loading.value=false}
}
watch(()=>props.url,()=>void load(),{immediate:true})
watch(page,()=>void draw())
onBeforeUnmount(()=>{observer?.disconnect();clear()})
</script>
<style scoped>
.kb-pdf-preview{display:grid;gap:12px;min-width:0}.kb-pdf-pager{display:flex;flex-wrap:wrap;gap:10px;align-items:center;justify-content:center}.kb-pdf-surface{width:100%;overflow:auto;min-width:0;background:#eef1f4}.kb-pdf-surface canvas{display:block;margin:auto;max-width:100%;height:auto;background:white}.kb-pdf-preview p{font-size:12px;line-height:1.7;color:var(--hbos-text-secondary)}
</style>
