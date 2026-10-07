import { beforeEach, describe, it, expect, vi } from 'vitest'
import { searchKnowledge, resolveKnowledgeEvidence, DomainApiError } from '@/services/p1Api'

const transport=vi.hoisted(() => ({post:vi.fn(),get:vi.fn()}))
vi.mock('@/services/frappeClient',() => ({callFrappePostMethod:transport.post,callFrappeMethod:transport.get}))
const card={document_id:'DOC_QA_DEMO',title:null,version:null,status_note:null,section:null,page_number:null,
  excerpt:'SYNTHETIC_EXCERPT_DEMO',evidence_id:'EV_QA_DEMO',space_id:'SPACE_QA_DEMO',source_type:'SYNTHETIC_TEST'}
beforeEach(() => {vi.clearAllMocks()})
describe('C01/C04 actual knowledge client; Frappe transport stub is not Session/CSRF proof',() => {
  it('preserves search/resolve methods and legacy flat device context',async () => {
    transport.post.mockResolvedValueOnce({ok:true,data:{request_id:'REQ_DEMO',mode:'retrieval',results:[card],context:{equipment_id:'EQ_DEMO'}}})
    await searchKnowledge('SYNTHETIC',{equipment_id:'EQ_DEMO'})
    expect(transport.post).toHaveBeenCalledWith('hb_knowledge_app.hb_knowledge.api.search',{query:'SYNTHETIC',limit:5,equipment_id:'EQ_DEMO'})
    transport.post.mockResolvedValueOnce({ok:true,data:card})
    expect(await resolveKnowledgeEvidence('EV_QA_DEMO')).toEqual(card)
    expect(transport.post).toHaveBeenLastCalledWith('hb_knowledge_app.hb_knowledge.api.resolve_evidence',{evidence_id:'EV_QA_DEMO'})
  })
  it('omits legacy empty response context in canonical client data',async () => {
    transport.post.mockResolvedValue({ok:true,data:{request_id:'REQ_DEMO',mode:'retrieval',results:[],context:{}}})
    expect(await searchKnowledge('SYNTHETIC')).not.toHaveProperty('context')
  })
  it('does not spread spoofed context fields into a request',async () => {
    await expect(searchKnowledge('SYNTHETIC',{equipment_id:'EQ_DEMO',subject:'USER_OTHER_DEMO'} as never)).rejects.toBeInstanceOf(DomainApiError)
    expect(transport.post).not.toHaveBeenCalled()
  })
  it.each([
    {...card,file_path:'/SYNTHETIC/original.pdf'},
    {...card,metadata:{nested:{download_url:'https://SYNTHETIC.invalid'}}},
    {...card,excerpt:'SYNTHETIC /SYNTHETIC/original.pdf'},
    {...card,excerpt:'https%3A%2F%2FSYNTHETIC.invalid%2Foriginal'},
    {...card,excerpt:'<b>SYNTHETIC</b>'},
    {...card,page_number:-1},
  ])('rejects unsafe card fields/strings/locator case %#',async value => {
    transport.post.mockResolvedValue({ok:true,data:value})
    await expect(resolveKnowledgeEvidence('EV_QA_DEMO')).rejects.toBeInstanceOf(DomainApiError)
  })
  it('does not display a raw backend error message',async () => {
    transport.post.mockResolvedValue({ok:false,error:{code:'EVIDENCE_UNAVAILABLE',message:'/SYNTHETIC/private/file.pdf'}})
    await expect(resolveKnowledgeEvidence('EV_QA_DEMO')).rejects.toMatchObject({code:'EVIDENCE_UNAVAILABLE',message:'该证据不可用或已失效。'})
  })
  it('accepts an old bounded P1 evidence DTO without new optional Space fields',async () => {
    const {space_id,source_type,...legacy}=card
    transport.post.mockResolvedValue({ok:true,data:legacy})
    expect(await resolveKnowledgeEvidence('EV_QA_DEMO')).toEqual(legacy)
  })
  it('cancellation abandons await; late transport success is not consumed',async () => {
    let complete!:(value:unknown)=>void
    transport.post.mockReturnValue(new Promise(resolve => {complete=resolve}))
    const controller=new AbortController()
    const pending=resolveKnowledgeEvidence('EV_QA_DEMO',controller.signal)
    controller.abort()
    await expect(pending).rejects.toMatchObject({name:'AbortError'})
    complete({ok:true,data:card})
  })
  it('already canceled request never sends to Frappe',async () => {
    const controller=new AbortController(); controller.abort()
    await expect(resolveKnowledgeEvidence('EV_QA_DEMO',controller.signal)).rejects.toMatchObject({name:'AbortError'})
    expect(transport.post).not.toHaveBeenCalled()
  })
})
