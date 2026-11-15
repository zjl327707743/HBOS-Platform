import { beforeEach, describe, expect, it, vi } from 'vitest'
import { askKnowledgeReference, searchKnowledge } from '@/services/p1Api'

const transport = vi.hoisted(() => ({ post: vi.fn(), get: vi.fn() }))
vi.mock('@/services/frappeClient', () => ({ callFrappePostMethod: transport.post, callFrappeMethod: transport.get }))
const evidence = { document_id: 'DOC_SYNTHETIC', evidence_id: 'EVID_SYNTHETIC', title: '合成来源', excerpt: '条款正文。' }
const answer = { request_id: 'REQ_SYNTHETIC', turn_id: 'TURN_SYNTHETIC', conversation_id: 'TURN_SYNTHETIC',
  mode: 'internal_reference_generation', answer_status: 'GENERATED_WITH_SOURCES', answerable: true,
  answer: '按来源条款执行。[C1]', citations: [{ ...evidence, citation_label: 'C1' }], answer_origin: 'KNOWLEDGE', model_alias: 'deepseek-flash' }

beforeEach(() => { window.sessionStorage.clear(); vi.clearAllMocks() })

describe('source excerpts agree with the server source contract', () => {
  it('preserves literal web references in both search and answer citations', async () => {
    const excerpt = '正文条款。参考 FDA CGMP 法规 (/about-fda/about-center)。\nhttps:/\n原件物理第13页。'
    transport.post.mockResolvedValue({ ok: true, data: { request_id: 'REQ_SYNTHETIC', mode: 'retrieval', results: [{ ...evidence, excerpt }] } })
    expect((await searchKnowledge('合成问题')).results[0].excerpt).toBe(excerpt)
    transport.post.mockResolvedValue({ ok: true, data: { ...answer, citations: [{ ...evidence, excerpt, citation_label: 'C1' }] } })
    expect((await askKnowledgeReference('合成问题')).citations[0].excerpt).toBe(excerpt)
  })

  it.each(['<script>alert(1)</script>', 'javascript:alert(1)', 'password=credential', '../private/file', '%252e%252e%252fprivate', '\\u003cscript'])('still refuses unsafe source content: %s', async excerpt => {
    transport.post.mockResolvedValue({ ok: true, data: { ...answer, citations: [{ ...evidence, excerpt, citation_label: 'C1' }] } })
    await expect(askKnowledgeReference('合成问题')).rejects.toThrow('无效响应')
  })

  it('keeps generated answers on the stricter gate', async () => {
    transport.post.mockResolvedValue({ ok: true, data: { ...answer, answer: '访问 https://example.invalid/private' } })
    await expect(askKnowledgeReference('合成问题')).rejects.toThrow('无效响应')
  })
})
