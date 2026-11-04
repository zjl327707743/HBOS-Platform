import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createDocumentDelivery, fetchDocumentCapabilities, isRetryableDelivery } from '@/services/knowledgeDelivery'
const api=vi.hoisted(()=>({post:vi.fn()}))
vi.mock('@/services/frappeClient',()=>({callFrappePostMethod:api.post}))
const asset={content_url:'/api/method/hb_knowledge_app.hb_knowledge.api.document_content?ticket='+ 'a'.repeat(43),expires_at:1800000000,filename:'SYNTHETIC 安全规程 2026.pdf',content_type:'application/pdf',sha256:'a'.repeat(64),kind:'DERIVED_PDF'}
beforeEach(()=>vi.clearAllMocks())
describe('RC14 controlled file delivery boundary',()=>{
  it('accepts human readable filenames and posts an immutable version',async()=>{
    api.post.mockResolvedValue({ok:true,data:asset})
    const value=await createDocumentDelivery('DOC_SYNTHETIC','VER_SYNTHETIC','preview')
    expect(value.filename).toBe(asset.filename)
    expect(api.post).toHaveBeenCalledWith(expect.any(String),{document_id:'DOC_SYNTHETIC',version_id:'VER_SYNTHETIC',purpose:'preview'})
  })
  it.each(['https://untrusted.invalid/api/method/hb_knowledge_app.hb_knowledge.api.document_content?ticket='+ 'a'.repeat(43),asset.content_url+'&path=/private',asset.content_url+'&ticket=duplicate'])('rejects widened delivery URL %s',async content_url=>{
    api.post.mockResolvedValue({ok:true,data:{...asset,content_url}})
    await expect(createDocumentDelivery('DOC_SYNTHETIC','VER_SYNTHETIC','preview')).rejects.toThrow('无效响应')
  })
  it('maps an expired ticket using the backend state enum',async()=>{
    api.post.mockResolvedValue({ok:false,error:{code:'DOCUMENT_DELIVERY_UNAVAILABLE',state:'TICKET_EXPIRED',message:'/private/path'}})
    const error=await createDocumentDelivery('DOC_SYNTHETIC','VER_SYNTHETIC','preview').catch(e=>e)
    expect(isRetryableDelivery(error)).toBe(true)
    expect(error.message).toContain('已过期');expect(error.message).not.toContain('/private')
  })
  it('keeps read and download capabilities independent',async()=>{
    api.post.mockResolvedValue({ok:true,data:{document_id:'DOC_SYNTHETIC',version_id:'VER_SYNTHETIC',can_read:true,can_preview:true,can_download:false,preview_kind:'DERIVED_PDF',preview_reason:null,download_reason:'DOWNLOAD_NOT_AUTHORIZED'}})
    const value=await fetchDocumentCapabilities('DOC_SYNTHETIC','VER_SYNTHETIC')
    expect(value.can_read&&value.can_preview).toBe(true);expect(value.can_download).toBe(false)
  })
})
