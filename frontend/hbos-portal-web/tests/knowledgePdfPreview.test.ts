import { mount,flushPromises } from '@vue/test-utils'
import { afterEach,describe,expect,it,vi } from 'vitest'
import PdfPreview from '@/components/knowledge/PdfPreview.vue'
const pdf=vi.hoisted(()=>({get:vi.fn()}))
vi.mock('pdfjs-dist',()=>({GlobalWorkerOptions:{workerSrc:''},getDocument:pdf.get,
 PDFDataRangeTransport:class { constructor(public length:number,public initialData:Uint8Array,public progressiveDone:boolean){} onDataRange=vi.fn() }
}))
afterEach(()=>{pdf.get.mockReset();vi.unstubAllGlobals();vi.restoreAllMocks()})
describe('controlled PDF canvas boundary',()=>{
 it('reports an unopened file without ticket language and leaves body reading to the caller',async()=>{
  vi.stubGlobal('fetch',vi.fn().mockResolvedValue({ok:false,status:404}))
  const wrapper=mount(PdfPreview,{props:{url:'/SYNTHETIC'},global:{stubs:{'a-alert':{props:['message','description'],template:'<p>{{message}} {{description}}</p>'}}}})
  await flushPromises()
  // The employee never sees ticket language; the file surface says it could not
  // open and the caller keeps the body/download paths.
  expect(wrapper.text()).not.toContain('票据')
  expect(wrapper.text()).toContain('文件暂时没能打开')
  expect(pdf.get).not.toHaveBeenCalled();wrapper.unmount()
 })
 it('signals access loss and never hands denied bytes to the PDF engine',async()=>{
  vi.stubGlobal('fetch',vi.fn().mockResolvedValue({ok:false,status:403}))
  const wrapper=mount(PdfPreview,{props:{url:'/SYNTHETIC'},global:{stubs:{'a-alert':true}}})
  await flushPromises();expect(wrapper.emitted('access-lost')).toHaveLength(1);expect(pdf.get).not.toHaveBeenCalled();wrapper.unmount()
 })
 it('aborts pending bytes when the reader closes',async()=>{
  let signal:AbortSignal|undefined
  vi.stubGlobal('fetch',vi.fn((_u,options)=>{signal=options.signal;return new Promise(()=>{})}))
  const wrapper=mount(PdfPreview,{props:{url:'/SYNTHETIC'},global:{stubs:{'a-alert':true}}})
  wrapper.unmount();expect(signal?.aborted).toBe(true)
 })
 it('passes only the initial bounded chunk to the PDF engine for a200MiB file',async()=>{
  const size=200*1024*1024,chunk=new Uint8Array(1024*1024);chunk.set(new TextEncoder().encode('%PDF-'))
  const fetcher=vi.fn(async()=>new Response(chunk,{status:206,headers:{'Content-Range':`bytes 0-${chunk.length-1}/${size}`,'Content-Length':String(chunk.length)}}))
  vi.stubGlobal('fetch',fetcher)
  const destroy=vi.fn().mockResolvedValue(undefined)
  pdf.get.mockReturnValue({promise:new Promise(()=>{}),destroy})
  const wrapper=mount(PdfPreview,{props:{url:'/SYNTHETIC'},global:{stubs:{'a-alert':true,'a-button':true}}})
  await vi.waitFor(()=>expect(pdf.get).toHaveBeenCalledTimes(1))
  const config=pdf.get.mock.calls[0]?.[0]
  expect(config.data).toBeUndefined();expect(config.range.length).toBe(size)
  expect(config.range.initialData.byteLength).toBe(1024*1024)
  expect(config.disableAutoFetch).toBe(true);expect(config.disableStream).toBe(true)
  expect(fetcher).toHaveBeenCalledTimes(1)
  wrapper.unmount();expect(destroy).toHaveBeenCalledTimes(1)
 })
})
