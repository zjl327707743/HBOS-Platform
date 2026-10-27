import { mount,flushPromises } from '@vue/test-utils'
import { afterEach,describe,expect,it,vi } from 'vitest'
import PdfPreview from '@/components/knowledge/PdfPreview.vue'
const pdf=vi.hoisted(()=>({get:vi.fn()}))
vi.mock('pdfjs-dist',()=>({GlobalWorkerOptions:{workerSrc:''},getDocument:pdf.get}))
afterEach(()=>{vi.unstubAllGlobals();vi.restoreAllMocks()})
describe('controlled PDF canvas boundary',()=>{
 it('reports expired content while leaving the caller in control of body reading',async()=>{
  vi.stubGlobal('fetch',vi.fn().mockResolvedValue({ok:false,status:404}))
  const wrapper=mount(PdfPreview,{props:{url:'/SYNTHETIC'},global:{stubs:{'a-alert':{props:['message','description'],template:'<p>{{message}} {{description}}</p>'}}}})
  await flushPromises();expect(wrapper.text()).toContain('票据可能已过期');expect(pdf.get).not.toHaveBeenCalled();wrapper.unmount()
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
})
