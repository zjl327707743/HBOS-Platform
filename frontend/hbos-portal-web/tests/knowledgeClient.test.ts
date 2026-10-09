import { beforeEach, describe, it, expect, vi } from 'vitest'
import { searchKnowledge, getKnowledgeSpaces, resolveKnowledgeEvidence, DomainApiError } from '@/services/p1Api'

const transport=vi.hoisted(() => ({post:vi.fn(),get:vi.fn()}))
vi.mock('@/services/frappeClient',() => ({callFrappePostMethod:transport.post,callFrappeMethod:transport.get}))
const card={document_id:'DOC_QA_DEMO',title:null,version:null,status_note:null,section:null,page_number:null,
  excerpt:'SYNTHETIC_EXCERPT_DEMO',evidence_id:'EV_QA_DEMO',space_id:'SPACE_QA_DEMO',source_type:'SYNTHETIC_TEST'}
beforeEach(() => {vi.clearAllMocks()})
describe('authorized space contract', () => {
  it('space selection narrows the search without exposing backend ids', async () => {
    transport.get.mockResolvedValue({ok:true,data:{spaces:[{space_id:'SPACE_QA_DEMO',title:'合成质检',document_count:1}]}})
    expect(await getKnowledgeSpaces()).toEqual([{space_id:'SPACE_QA_DEMO',title:'合成质检',document_count:1}])
    transport.post.mockResolvedValue({ok:true,data:{request_id:'REQ_DEMO',mode:'retrieval',results:[]}})
    await searchKnowledge('SYNTHETIC',{},['SPACE_QA_DEMO'])
    expect(transport.post).toHaveBeenCalledWith('hb_knowledge_app.hb_knowledge.api.search',{query:'SYNTHETIC',limit:5,space_ids:['SPACE_QA_DEMO']})
  })
  it('empty requested scope never falls back to all spaces', async () => {
    await expect(searchKnowledge('SYNTHETIC',{},[])).rejects.toBeInstanceOf(DomainApiError)
    expect(transport.post).not.toHaveBeenCalled()
  })
  it('rejects physical metadata channels in a space response', async () => {
    transport.get.mockResolvedValue({ok:true,data:{spaces:[{space_id:'SPACE_QA_DEMO',title:'合成质检',document_count:1,dataset_id:'PHYSICAL_DS'}]}})
    await expect(getKnowledgeSpaces()).rejects.toBeInstanceOf(DomainApiError)
  })
  it('rejects duplicate ids and unsafe titles', async () => {
    const space={space_id:'SPACE_QA_DEMO',title:'合成质检',document_count:1}
    transport.get.mockResolvedValueOnce({ok:true,data:{spaces:[space,space]}})
    await expect(getKnowledgeSpaces()).rejects.toBeInstanceOf(DomainApiError)
    transport.get.mockResolvedValueOnce({ok:true,data:{spaces:[{...space,title:'private /source/file.pdf'}]}})
    await expect(getKnowledgeSpaces()).rejects.toBeInstanceOf(DomainApiError)
  })
})
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

describe('N1 current-user feedback and paginated catalog projections', () => {
  const doc = { document_id: 'DOC_N1_DEMO', title: '合成标题', space_id: 'SPACE_N1_DEMO', department: '合成部门', document_number: null, version: null, status_note: 'SYNTHETIC_ONLY' }
  it('reads one server-scoped catalog page without a model POST', async () => {
    const { getKnowledgeDocumentsPage } = await import('@/services/p1Api')
    transport.get.mockResolvedValue({ ok: true, data: { documents: [doc], total: 25, page: 2, page_size: 12 } })
    expect(await getKnowledgeDocumentsPage(' 合成 ', 'SPACE_N1_DEMO', 2, 12)).toMatchObject({ total: 25, page: 2 })
    expect(transport.get).toHaveBeenCalledWith('hb_knowledge_app.hb_knowledge.api.get_documents_page', { query: '合成', space_id: 'SPACE_N1_DEMO', page: 2, page_size: 12 })
    expect(transport.post).not.toHaveBeenCalled()
  })
  it.each([
    { documents: [{ ...doc, dataset_id: 'PHYSICAL_ID' }], total: 1, page: 1, page_size: 12 },
    { documents: [doc], total: 1, page: 2, page_size: 12 },
    { documents: [doc, doc], total: 2, page: 1, page_size: 12 },
    { documents: [{ ...doc, space_id: 'OTHER_SPACE_DEMO' }], total: 1, page: 1, page_size: 12 },
    { documents: [doc], total: -1, page: 1, page_size: 12 },
  ])('rejects invalid catalog scope/metadata/page/count case %#', async data => {
    const { getKnowledgeDocumentsPage } = await import('@/services/p1Api')
    transport.get.mockResolvedValue({ ok: true, data })
    await expect(getKnowledgeDocumentsPage('', 'SPACE_N1_DEMO')).rejects.toBeInstanceOf(DomainApiError)
  })
  it('does not send invalid page sizes or noncanonical scope', async () => {
    const { getKnowledgeDocumentsPage } = await import('@/services/p1Api')
    await expect(getKnowledgeDocumentsPage('', '', 1, 51)).rejects.toBeInstanceOf(DomainApiError)
    await expect(getKnowledgeDocumentsPage('', ' SPACE_N1_DEMO')).rejects.toBeInstanceOf(DomainApiError)
    expect(transport.get).not.toHaveBeenCalled()
  })
  it('accepts current-user feedback statuses and refuses internal identifiers or unknown states', async () => {
    const { getKnowledgeFeedback } = await import('@/services/p1Api')
    const feedback = { id: 'FEEDBACK_N1_DEMO', category: '版本疑问', note: '合成维护问题', status: 'Pending', created_at: '2026-10-10', updated_at: '2026-10-10' }
    transport.get.mockResolvedValueOnce({ ok: true, data: { items: [feedback] } })
    expect(await getKnowledgeFeedback()).toEqual([feedback])
    transport.get.mockResolvedValueOnce({ ok: true, data: { items: [{ ...feedback, evidence_id: 'INTERNAL_EVIDENCE' }] } })
    await expect(getKnowledgeFeedback()).rejects.toBeInstanceOf(DomainApiError)
    transport.get.mockResolvedValueOnce({ ok: true, data: { items: [{ ...feedback, status: 'InventedStatus' }] } })
    await expect(getKnowledgeFeedback()).rejects.toBeInstanceOf(DomainApiError)
  })
  it('submits general feedback without an evidence token and preserves a server denial', async () => {
    const { sendKnowledgeFeedback } = await import('@/services/p1Api')
    transport.post.mockResolvedValueOnce({ ok: true, data: { id: 'GENERAL_FEEDBACK_DEMO' } })
    await sendKnowledgeFeedback(undefined, '其他', '合成一般使用问题')
    expect(transport.post).toHaveBeenCalledWith('hb_knowledge_app.hb_knowledge.api.submit_feedback', { evidence_id: undefined, category: '其他', note: '合成一般使用问题' })
    transport.post.mockResolvedValueOnce({ ok: false, error: { code: 'FORBIDDEN', message: 'SYNTHETIC_DENIED' } })
    await expect(sendKnowledgeFeedback(undefined, '其他', '合成一般使用问题')).rejects.toMatchObject({ code: 'FORBIDDEN' })
  })
  it('preserves a saved equipment/asset/component context while accepting legacy records without context', async () => {
    const { openKnowledgeSaved } = await import('@/services/p1Api')
    const saved = { query: '合成旧问题', space_ids: ['SPACE_N1_DEMO'], context: { equipment_id: 'EQ_N1_DEMO', asset_id: 'ASSET_N1_DEMO', component_id: 'COMPONENT_N1_DEMO' } }
    transport.post.mockResolvedValueOnce({ ok: true, data: saved }); expect(await openKnowledgeSaved('SAVED_N1_DEMO')).toEqual(saved)
    const { context, ...legacy } = saved
    transport.post.mockResolvedValueOnce({ ok: true, data: legacy }); expect(await openKnowledgeSaved('SAVED_LEGACY_DEMO')).toEqual(legacy)
    transport.post.mockResolvedValueOnce({ ok: true, data: { ...legacy, context: {} } }); expect(await openKnowledgeSaved('SAVED_EMPTY_CONTEXT_DEMO')).toEqual(legacy)
  })
  it.each([
    { equipment_id: 'EQ_N1_DEMO', dataset_id: 'PHYSICAL_ID' },
    { equipment_id: 42 },
    { asset_id: 'ASSET_WITHOUT_EQUIPMENT_DEMO' },
    null,
  ])('rejects an unsafe optional saved context case %#', async context => {
    const { openKnowledgeSaved } = await import('@/services/p1Api')
    transport.post.mockResolvedValue({ ok: true, data: { query: '合成旧问题', space_ids: ['SPACE_N1_DEMO'], context } })
    await expect(openKnowledgeSaved('SAVED_N1_DEMO')).rejects.toBeInstanceOf(DomainApiError)
  })
  it('rejects duplicate saved departments and unprojected response fields', async () => {
    const { openKnowledgeSaved } = await import('@/services/p1Api')
    transport.post.mockResolvedValueOnce({ ok: true, data: { query: '合成旧问题', space_ids: ['SPACE_N1_DEMO', 'SPACE_N1_DEMO'] } })
    await expect(openKnowledgeSaved('SAVED_N1_DEMO')).rejects.toBeInstanceOf(DomainApiError)
    transport.post.mockResolvedValueOnce({ ok: true, data: { query: '合成旧问题', space_ids: [], owner_user: 'PRIVATE_USER_DEMO' } })
    await expect(openKnowledgeSaved('SAVED_N1_DEMO')).rejects.toBeInstanceOf(DomainApiError)
  })
})

describe('N1 bounded follow-up responses', () => {
  const refusal = '无法可靠定位前一回答中的具体条目。请指出步骤名称或关键词后再问；当前资料不足以直接回答这个追问。'
  const unanswered = { request_id: 'REQ_FOLLOWUP_DEMO', turn_id: 'TURN_FOLLOWUP_DEMO', conversation_id: 'TURN_FOLLOWUP_DEMO', mode: 'authorized_generation', answer_status: 'INSUFFICIENT_EVIDENCE', answerable: false, answer: refusal, citations: [] }
  it('shows the exact server clarification for an ambiguous reference without invented citations', async () => {
    const { askKnowledgeReference } = await import('@/services/p1Api')
    transport.post.mockResolvedValue({ ok: true, data: unanswered })
    expect(await askKnowledgeReference('上面第二条是什么意思？', 'SPACE_QA_DEMO', 'PREVIOUS_TURN_DEMO')).toEqual(unanswered)
    expect(transport.post).toHaveBeenCalledWith('hb_knowledge_app.hb_knowledge.api.ask', { question: '上面第二条是什么意思？', space_ids: ['SPACE_QA_DEMO'], conversation_id: 'PREVIOUS_TURN_DEMO' })
  })
  it.each([
    { ...unanswered, answer: '未被契约批准的拒答文本' },
    { ...unanswered, conversation_id: 'MISMATCHED_TURN_DEMO' },
    { ...unanswered, citations: [{ ...card, citation_label: 'C1' }] },
    { request_id: 'REQ_DUPLICATE_DEMO', turn_id: 'TURN_DUPLICATE_DEMO', mode: 'internal_reference_generation', answer_status: 'REFERENCE_ANSWERED', answerable: true, answer: 'SYNTHETIC [C1]', citations: [{ ...card, citation_label: 'C1' }, { ...card, citation_label: 'C1' }] },
    { request_id: 'REQ_SCOPE_DEMO', turn_id: 'TURN_SCOPE_DEMO', mode: 'internal_reference_generation', answer_status: 'REFERENCE_ANSWERED', answerable: true, answer: 'SYNTHETIC [C1]', citations: [{ ...card, space_id: 'OTHER_SPACE_DEMO', citation_label: 'C1' }] },
  ])('rejects fabricated clarification, mismatched context, or ambiguous/wrong-scope citation case %#', async data => {
    const { askKnowledgeReference } = await import('@/services/p1Api')
    transport.post.mockResolvedValue({ ok: true, data })
    await expect(askKnowledgeReference('合成问题', 'SPACE_QA_DEMO')).rejects.toBeInstanceOf(DomainApiError)
  })
})
