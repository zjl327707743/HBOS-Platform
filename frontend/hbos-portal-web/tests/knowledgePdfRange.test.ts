import { describe,expect,it,vi } from 'vitest'
import { PdfRangeSource,PDF_RANGE_CHUNK_BYTES } from '@/components/knowledge/pdfRange'

function server(total:number) {
  return vi.fn(async(_url:string,options:RequestInit)=>{
    const match=/bytes=(\d+)-(\d+)/.exec((options.headers as Record<string,string>).Range)!
    const start=Number(match[1]),end=Math.min(Number(match[2])+1,total)
    const bytes=new Uint8Array(end-start).fill(start ? 66 : 65)
    if(start===0)bytes.set(new TextEncoder().encode('%PDF-'))
    return new Response(bytes,{status:206,headers:{'Content-Range':`bytes ${start}-${end-1}/${total}`,'Content-Length':String(bytes.length)}})
  })
}

describe('bounded authenticated PDF source',()=>{
 it('calls native browser fetch with the Window receiver for initial and later ranges',async()=>{
  const good=server(3*PDF_RANGE_CHUNK_BYTES)
  const native=vi.fn(function(this:unknown,url:string,options:RequestInit){
    if(this!==globalThis)throw new TypeError("Failed to execute 'fetch' on 'Window': Illegal invocation")
    return good(url,options)
  })
  vi.stubGlobal('fetch',native)
  const source=new PdfRangeSource('/file')
  try {
    await source.initialize()
    await source.read(PDF_RANGE_CHUNK_BYTES,2*PDF_RANGE_CHUNK_BYTES)
    expect(native).toHaveBeenCalledTimes(2)
  } finally {source.close();vi.unstubAllGlobals()}
 })
 it('opens a500MiB file with one bounded range and reads only later requested pieces',async()=>{
  const fetcher=server(500*1024*1024),source=new PdfRangeSource('/file',{fetcher})
  const first=await source.initialize()
  expect(first.length).toBe(500*1024*1024);expect(first.initialData.byteLength).toBe(PDF_RANGE_CHUNK_BYTES)
  expect(fetcher).toHaveBeenCalledTimes(1)
  const piece=await source.read(3*PDF_RANGE_CHUNK_BYTES,5*PDF_RANGE_CHUNK_BYTES)
  expect(piece.byteLength).toBe(2*PDF_RANGE_CHUNK_BYTES)
  expect(fetcher).toHaveBeenCalledTimes(3)
  for(const [,options] of fetcher.mock.calls)expect(options.credentials).toBe('same-origin')
  source.close()
 })
 it('refuses an ignored range without buffering a full response',async()=>{
  const cancel=vi.fn(),read=vi.fn()
  const fetcher=vi.fn(async()=>({ok:true,status:200,body:{cancel,getReader:()=>({read})}} as unknown as Response))
  await expect(new PdfRangeSource('/file',{fetcher}).initialize()).rejects.toThrow()
  expect(read).not.toHaveBeenCalled();expect(cancel).toHaveBeenCalled()
 })
 it('rejects wrong boundaries, changed total length, or oversized coalesced requests',async()=>{
  const good=server(5*PDF_RANGE_CHUNK_BYTES),fetcher=vi.fn(good)
  const source=new PdfRangeSource('/file',{fetcher});await source.initialize()
  fetcher.mockImplementationOnce(async()=>new Response(new Uint8Array(10),{status:206,headers:{'Content-Range':'bytes 1-10/5242880'}}))
  await expect(source.read(PDF_RANGE_CHUNK_BYTES,PDF_RANGE_CHUNK_BYTES+10)).rejects.toThrow()
  fetcher.mockImplementationOnce(server(6*PDF_RANGE_CHUNK_BYTES))
  await expect(source.read(PDF_RANGE_CHUNK_BYTES,2*PDF_RANGE_CHUNK_BYTES)).rejects.toThrow()
  await expect(source.read(0,500*PDF_RANGE_CHUNK_BYTES)).rejects.toThrow()
  source.close()
 })
 it('coalesces expired-ticket renewal across concurrent requests and rejects foreign URLs',async()=>{
  const good=server(5*PDF_RANGE_CHUNK_BYTES),renew=vi.fn(async()=>'/fresh'),lost=vi.fn()
  const fetcher=vi.fn(async(url:string,options:RequestInit)=>url==='/old' && String((options.headers as Record<string,string>).Range)!==`bytes=0-${PDF_RANGE_CHUNK_BYTES-1}` ? new Response(null,{status:403}):good(url,options))
  const source=new PdfRangeSource('/old',{fetcher,renew,onAccessLost:lost});await source.initialize()
  await Promise.all([source.read(PDF_RANGE_CHUNK_BYTES,2*PDF_RANGE_CHUNK_BYTES),source.read(2*PDF_RANGE_CHUNK_BYTES,3*PDF_RANGE_CHUNK_BYTES)])
  expect(renew).toHaveBeenCalledTimes(1);expect(lost).not.toHaveBeenCalled()
  expect(()=>new PdfRangeSource('https://foreign.invalid/file',{fetcher})).toThrow()
  source.close()
 })
 it('reauthorizes a cached page and refuses it after revocation',async()=>{
  const renew=vi.fn(async()=>null),lost=vi.fn(),source=new PdfRangeSource('/file',{fetcher:server(1000),renew,onAccessLost:lost})
  await source.initialize();await expect(source.revalidate()).rejects.toThrow()
  expect(renew).toHaveBeenCalledTimes(1);expect(lost).toHaveBeenCalledTimes(1)
  source.close()
 })
 it('aborts every pending range and does not restart requests after close',async()=>{
  const signals:AbortSignal[]=[]
  const fetcher=vi.fn(async(_url:string,options:RequestInit)=>{
    signals.push(options.signal as AbortSignal)
    return new Promise<Response>((_resolve,reject)=>options.signal?.addEventListener('abort',()=>reject(new DOMException('Aborted','AbortError'))))
  })
  const source=new PdfRangeSource('/file',{fetcher}),pending=source.initialize();source.close()
  await expect(pending).rejects.toThrow();expect(signals.every(x=>x.aborted)).toBe(true)
  await expect(source.read(0,1)).rejects.toThrow();expect(fetcher).toHaveBeenCalledTimes(1)
 })
})
