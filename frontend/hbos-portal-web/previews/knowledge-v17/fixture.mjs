import * as maintenance from './maintenance.mjs'
import * as batch from './batch.mjs'
import { createHash, randomBytes, randomUUID } from 'node:crypto'

const date = '2026-11-12T10:00:00+08:00'
const space = 'DEPT_QUALITY'
const categories = [
  { category_id: 'FOLDER_' + '1'.repeat(24), path: ['质量管理部'] },
  { category_id: 'FOLDER_' + '2'.repeat(24), path: ['质量管理部', '设备使用'] },
  { category_id: 'FOLDER_' + '3'.repeat(24), path: ['安全部门'] },
]
const titles = ['培养箱使用与日常检查指南', '岗位安全培训资料索引', '文件版本与引用核对指南']
const documents = Array.from({ length: 27 }, (_, index) => ({
  document_id: 'DOC_SYNTHETIC_' + index,
  version_id: 'V0' + (index % 4 + 1),
  title: titles[index] ?? '合成资料归档与版本核对记录 · ' + (index + 1),
  version: '0' + (index % 4 + 1),
  status_note: '已共享 · 合成资料',
  document_number: 'DEMO-' + String(index + 1).padStart(3, '0'),
  department: index === 1 ? '安全部门' : '质量管理部',
  space_id: index === 1 ? 'DEPT_SAFETY' : space,
  source_directories: [categories[index === 1 ? 2 : 1].path],
  download_state: 'available',
}))
const evidence = documents.map(doc => ({
  document_id: doc.document_id, evidence_id: 'EVIDENCE_' + doc.document_id, title: doc.title,
  version: doc.version, document_number: doc.document_number, page_number: 1, section: '查阅与核对',
  excerpt: '合成片段。使用资料前，请核对文件编号、适用范围和当前发布版本。',
  space_id: doc.space_id, source_type: 'SYNTHETIC_TEST',
}))
const activities = { Bookmark: [], History: [] }
const saved = new Map()
function record(kind, query, sources, data) {
  const id = randomUUID()
  const item = {
    id, query, created_at: date, available: true, titles: sources.map(doc => doc.title),
    document_ids: sources.map(doc => doc.document_id), version_ids: sources.map(doc => doc.version_id),
    ...(data.bookmark_type ? { bookmark_type: data.bookmark_type } : {}),
  }
  activities[kind].unshift(item)
  saved.set(id, { query, ...data })
  return id
}
for (const doc of documents.slice(0, 3).reverse()) record('Bookmark', doc.title, [doc], {
  space_ids: [doc.space_id], bookmark_type: 'Document', document: doc,
})
const question = '如何确认引用的是当前版本？'
record('History', question, [documents[0]], { space_ids: [], restored: {
  mode: 'search', search_mode: 'STANDARD', turns: [], results: [evidence[0]],
} })
const feedback = [
  { id: 'FB_SYN_1', category: '版本疑问', note: '请核对目录中显示的版本。', status: 'Pending', created_at: date, updated_at: date, reply: '' },
  { id: 'FB_SYN_2', category: '内容疑问', note: '希望补充培训资料的适用范围。', status: 'Resolved', created_at: date, updated_at: date, reply: '已补充适用范围，请查看当前版本。' },
]
const connections = []
const tickets = new Map()

// Deterministic visual scene (?state=visual). The frozen v1.7 prototype is the
// comparison baseline, so this preview-only scene reuses its document identities,
// counts, statuses and timestamps. Production components never read this data and
// the real API contract is unchanged; it only makes the same-condition screenshot
// comparison honest.
const visualSeeds = [
  ['培养箱使用与日常检查指南', '质量管理部', 'quality', 'DEMO-QC-018', '03', '无菌车间', '设备使用', '用于演示如何核对设备资料、适用版本和记录要求。'],
  ['岗位安全培训资料索引', '安全部门', 'safety', 'DEMO-EHS-002', '02', '安全部门', '岗位培训', '按岗位查找已共享培训资料，核对培训范围与当前版本。'],
  ['文件版本与引用核对指南', '质量管理部', 'quality', 'DEMO-QA-006', '04', '生产部门', '质量文件', '查阅前核对文件编号、版本、发布状态和适用范围。'],
  ['生产现场交接记录说明', '生产部门', 'production', 'DEMO-PRD-014', '02', '生产部门', '生产管理', '交接内容、记录字段与资料查阅方式的示例。'],
  ['新员工入职培训手册', '人事部门', 'hr', 'DEMO-HR-001', '05', '人事部门', '岗位培训', '用于展示员工培训资料的目录与阅读体验。'],
  ['设备图纸查阅与归档指引', '生产部门', 'production', 'DEMO-EQ-009', '01', '设备部建模图', '设备资料', '设备图纸归档和版本辨识的交互示例。'],
  ['无菌车间资料使用指引', '生产部门', 'production', 'DEMO-PRD-021', '02', '无菌车间', '生产管理', '示例资料不构成生产操作依据。请始终使用实际获准文件。'],
  ['药品监管规范条目（演示）', '公共法规', 'law', 'DEMO-LAW-001', '01', '法规文档', 'GMP与药品监管', '法规目录的呈现示例，不是正式法规文本或效力判断。'],
  ['环保合规资料目录（演示）', '公共法规', 'law', 'DEMO-LAW-002', '01', '法规文档', '安全环保', '展示法规分类、发布机构、效力状态和来源字段。'],
  ['培训记录归档说明', '人事部门', 'hr', 'DEMO-HR-009', '02', '人事部门', '岗位培训', '记录归档、查找和重新核对的示例资料。'],
  ['公共标准条目（演示）', '公共法规', 'law', 'DEMO-LAW-003', '01', '法规文档', '药典与技术标准', '分类和元数据仅用于交互设计，不代表现行标准。'],
  ['设备资料索引清单', '生产部门', 'production', 'DEMO-EQ-016', '01', '设备部建模图', '设备资料', '示例设备资料检索目录。'],
]
const visualSpaceByDept = { 质量管理部: 'DEPT_QUALITY', 安全部门: 'DEPT_SAFETY', 生产部门: 'DEPT_PRODUCTION', 人事部门: 'DEPT_HR', 公共法规: 'DEPT_LAW' }
const visualDocuments = visualSeeds.map((seed, index) => ({
  document_id: 'DOC_DEMO_' + String(index + 1).padStart(3, '0'),
  version_id: 'V0' + seed[4], title: seed[0], version: seed[4], status_note: index === 10 ? '待核 · 同步资料' : '已共享 · 同步资料',
  document_number: seed[3], department: seed[1], space_id: visualSpaceByDept[seed[1]],
  source_directories: [[seed[5], seed[6]]], download_state: 'available',
}))
for (let n = 13; n <= 27; n++) {
  const base = visualDocuments[(n - 13) % 7]
  visualDocuments.push({ ...base,
    document_id: 'DOC_DEMO_' + String(n).padStart(3, '0'),
    title: base.title.replace(/指南|说明|指引|索引|手册/, '相关记录') + ' · 示例 ' + (n - 12),
    document_number: 'DEMO-REF-' + String(n).padStart(3, '0') })
}
const visualEvidence = visualDocuments.map(doc => ({
  document_id: doc.document_id, evidence_id: 'EVIDENCE_' + doc.document_id, title: doc.title,
  version: doc.version, document_number: doc.document_number, page_number: 1, section: '查阅与核对',
  excerpt: '合成片段。使用资料前，请核对文件编号、适用范围和当前发布版本。',
  space_id: doc.space_id, source_type: 'SYNTHETIC_TEST',
}))
const visualActivities = { Bookmark: [], History: [] }
const visualSaved = new Map()
function visualRecord(kind, query, sourceDocs, data, createdAt) {
  const id = 'VISUAL_' + kind + '_' + visualSaved.size
  const item = { id, query, created_at: createdAt, available: true,
    titles: sourceDocs.map(doc => doc.title), document_ids: sourceDocs.map(doc => doc.document_id),
    version_ids: sourceDocs.map(doc => doc.version_id), ...(data.bookmark_type ? { bookmark_type: data.bookmark_type } : {}) }
  visualActivities[kind].unshift(item)
  visualSaved.set(id, { query, ...data })
  return id
}
for (const index of [0, 2, 4]) visualRecord('Bookmark', visualDocuments[index].title, [visualDocuments[index]],
  { space_ids: [visualDocuments[index].space_id], bookmark_type: 'Document', document: visualDocuments[index] }, '2026-11-12T10:00:00+08:00')
visualRecord('History', '如何确认引用的是当前版本？', [visualDocuments[2]],
  { space_ids: [], restored: { mode: 'search', search_mode: 'STANDARD', turns: [], results: [visualEvidence[2]] } }, '2026-11-13T09:42:00+08:00')
visualRecord('History', '岗位安全培训资料', [visualDocuments[1], visualDocuments[4]],
  { space_ids: [], restored: { mode: 'search', search_mode: 'STANDARD', turns: [], results: [visualEvidence[1], visualEvidence[4]] } }, '2026-11-12T15:28:00+08:00')
const visualFeedback = [{
  id: 'FB_VISUAL_1', category: '版本疑问', note: '示例：希望更清楚地看到当前版本的生效信息。',
  status: 'Resolved', created_at: '2026-11-10T10:00:00+08:00', updated_at: '2026-11-10T10:00:00+08:00',
  reply: '已补充版本字段，请在资料详情中核对。此回复仅为演示。',
}]
const visualSpaces = [
  { space_id: 'DEPT_QUALITY', title: '质量管理部', document_count: 26 },
  { space_id: 'DEPT_SAFETY', title: '安全部门', document_count: 1 },
  { space_id: 'DEPT_PRODUCTION', title: '生产部门', document_count: 6 },
  { space_id: 'DEPT_HR', title: '人事部门', document_count: 2 },
  { space_id: 'DEPT_LAW', title: '公共法规', document_count: 3 },
]

const failure = (code, message = '合成场景：当前服务不可用。') => ({ ok: false, error: { code, message } })
const success = data => ({ ok: true, data })
function paginate(items, args) {
  const page = Number(args.page || 1), page_size = Number(args.page_size || 6)
  const start = (page - 1) * page_size
  return { items: items.slice(start, start + page_size), page, page_size, has_more: start + page_size < items.length }
}
function pdfFor(doc, pageCount = 1) {
  const streams = Array.from({ length: pageCount }, (_, index) =>
    `BT /F1 18 Tf 52 735 Td (HBOS synthetic fixture: ${doc.document_number}) Tj 0 -36 Td (Document version ${doc.version} / page ${index + 1}) Tj ET`)
  const pageObjects = [], contents = []
  let objectNumber = 4
  for (let index = 0; index < pageCount; index++) {
    pageObjects.push(objectNumber++)
    contents.push(objectNumber++)
  }
  const objects = [
    '<< /Type /Catalog /Pages 2 0 R >>',
    `<< /Type /Pages /Kids [${pageObjects.map(id => id + ' 0 R').join(' ')}] /Count ${pageCount} >>`,
    '<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>',
  ]
  pageObjects.forEach((id, index) => {
    objects.push(`<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 3 0 R >> >> /Contents ${contents[index]} 0 R >>`)
    objects.push(`<< /Length ${streams[index].length} >>\nstream\n${streams[index]}\nendstream`)
  })
  let content = '%PDF-1.4\n'
  const offsets = objects.map((value, index) => {
    const offset = content.length
    content += `${index + 1} 0 obj\n${value}\nendobj\n`
    return String(offset).padStart(10, '0')
  })
  const xref = content.length
  return Buffer.from(content + `xref\n0 ${objects.length + 1}\n0000000000 65535 f \n${offsets.map(offset => offset + ' 00000 n \n').join('')}trailer\n<< /Size ${objects.length + 1} /Root 1 0 R >>\nstartxref\n${xref}\n%%EOF\n`)
}
function readDocument(doc, pages = 1) {
  return {
    document: {
      document_id: doc.document_id, version_id: doc.version_id, title: doc.title,
      document_number: doc.document_number, space_id: doc.space_id, space_title: doc.department,
      business_version: doc.version, status_note: doc.status_note, reference_state: 'CURRENT',
      authorization: 'AUTHORIZED', source_type: 'SYNTHETIC_TEST',
    },
    body: {
      origin: 'INDEXED_CHUNKS', page_numbering: 'UNAVAILABLE', derived: true, page: 1, page_count: pages, block_total: 3,
      blocks: ['资料说明', '查阅与核对', '版本与记录'].map((section, index) => ({
        block_id: 'block-' + index, ordinal: index + 1, page_number: null, section,
        text: `${section}。本段用于演示 ${doc.title} 的正文检索、定位和版本核验。合成内容仅用于界面验收。`,
      })),
    },
    navigation: { toc: [{ title: '资料说明', ordinal: 1, page_number: null }], toc_source: 'ORIGINAL_HEADING_LINES', toc_truncated: false },
  }
}
const maintenanceOnly = /^(get_maintenance|get_feedback_queue|review_feedback|upload_knowledge|plan_import|submit_import|batch_progress|pause_import|resume_import|reclaim_import|queue_import|review_import|approve_import|publish_import|preview_import|withdraw_import)/
async function method(name, args, state) {
  if (state === 'timeout' || state === 'error') return failure('SERVICE_ERROR')
  if (state === 'forbidden' && name !== 'get_status') return failure('FORBIDDEN')
  if (state === 'reader' && maintenanceOnly.test(name)) return failure('FORBIDDEN')
  const empty = state === 'empty'
  const visual = state === 'visual'
  const activeDocuments = visual ? visualDocuments : documents
  const activeEvidence = visual ? visualEvidence : evidence
  const activeFeedback = visual ? visualFeedback : feedback
  const activityRows = kind => (visual ? visualActivities : activities)[kind] || []
  const savedRows = visual ? visualSaved : saved
  const readerPages = visual ? 3 : 1
  const doc = activeDocuments.find(row => row.document_id === args.document_id)
  const open = () => doc && state !== 'stale' && (!args.version_id || doc.version_id === args.version_id)
  const page = Number(args.page || 1)
  switch (name) {
    case 'get_status':
      return success({ environment: 'production', can_enter: state !== 'forbidden', can_search: state !== 'forbidden',
        can_maintain: state !== 'reader' && state !== 'forbidden', ask_enabled: true, gateway_configured: true, mode: 'retrieval' })
    case 'get_spaces':
      return success({ spaces: empty ? [] : visual ? visualSpaces : [
        { space_id: space, title: '质量管理部', document_count: 26 },
        { space_id: 'DEPT_SAFETY', title: '安全部门', document_count: 1 },
      ] })
    case 'get_documents_page': {
      const query = String(args.query || '')
      const category_ids = JSON.parse(args.category_ids || '[]')
      const format = args.format || null, sort = args.sort || 'relevance'
      const filtered = empty ? [] : activeDocuments.filter(row =>
        `${row.title} ${row.document_number} ${row.department}`.includes(query) &&
        (!category_ids.length || categories.some(c => category_ids.includes(c.category_id) && c.path.every((part, i) => row.source_directories[0][i] === part))))
      if (sort !== 'relevance') filtered.sort((a, b) => a.title.localeCompare(b.title, 'zh') * (sort === 'title_desc' ? -1 : 1))
      const page_size = Number(args.page_size || 20)
      if (args.contract_version === undefined) {
        const scoped = filtered.filter(doc => !args.space_id || args.space_id === doc.space_id)
        return success({ page, page_size, total: scoped.length, documents: scoped.slice((page - 1) * page_size, page * page_size) })
      }
      return success({
        page, page_size, total_documents: filtered.length,
        documents: filtered.slice((page - 1) * page_size, page * page_size).map(row => ({ ...row, file_formats: ['pdf'] })),
        category_options: categories, format_options: ['pdf'], corpus_revision: 'a'.repeat(64), directory_revision: 'b'.repeat(64),
        applied_filters: { query, category_ids, format, sort },
      })
    }
    case 'search': {
      const terms = String(args.query).trim()
      const results = empty ? [] : activeEvidence.filter(row => row.title.includes(terms) || row.document_number.includes(terms))
        .filter(row => !args.space_ids || args.space_ids.includes(row.space_id)).slice(0, 5)
      if (!visual) record('History', terms, documents.filter(row => results.some(hit => hit.document_id === row.document_id)),
        { space_ids: args.space_ids || [], restored: { mode: 'search', search_mode: args.search_mode, turns: [], results } })
      return success({ request_id: randomUUID(), mode: 'retrieval', search_mode: args.search_mode, results })
    }
    case 'ask': {
      const request_id = randomUUID(), turn_id = args.conversation_id || randomUUID()
      const base = { request_id, turn_id, conversation_id: turn_id }
      const general = state === 'general' && !args.knowledge_only
      const citations = activeEvidence.filter(row => !args.space_ids || args.space_ids.includes(row.space_id)).slice(0, 3)
        .map((row, index) => ({ ...row, citation_label: 'C' + (index + 1) }))
      const answer = general
        ? { ...base, mode: 'general_generation', answer_status: 'GENERAL_ANSWERED', answerable: true, answer: '这是一段合成通用回答。', citations: [], answer_origin: 'GENERAL', model_alias: 'deepseek-flash' }
        : empty || !citations.length
          ? { ...base, mode: 'authorized_generation', answer_status: 'INSUFFICIENT_EVIDENCE', answerable: false, answer: '当前范围内未找到足够依据。', citations: [], answer_origin: 'KNOWLEDGE', model_alias: null }
          : { ...base, mode: 'internal_reference_generation', answer_status: 'GENERATED_WITH_SOURCES', answerable: true, answer: '先核对资料的文号和当前发布版本 [C1]。\n\n再核对共享范围与实际适用场景。以下内容仅用于合成验收。', citations, answer_origin: 'KNOWLEDGE', model_alias: 'deepseek-flash' }
      if (!visual) record('History', args.question, documents.filter(row => answer.citations.some(hit => hit.document_id === row.document_id)),
        { space_ids: args.space_ids || [], restored: { mode: 'ask', search_mode: args.search_mode, results: [], turns: [{ ...answer, question: args.question }] } })
      return success(answer)
    }
    case 'resolve_evidence': {
      const result = activeEvidence.find(row => row.evidence_id === args.evidence_id)
      return result && state !== 'stale' ? success(result) : failure('EVIDENCE_UNAVAILABLE')
    }
    case 'get_activity': return success(paginate(empty ? [] : activityRows(args.kind), args))
    case 'open_saved': return savedRows.has(args.activity_id) && state !== 'stale' ? success(savedRows.get(args.activity_id)) : failure('EVIDENCE_UNAVAILABLE')
    case 'save_document_bookmark':
      return open() ? success({ id: record('Bookmark', doc.title, [doc], { space_ids: [doc.space_id], bookmark_type: 'Document', document: doc }) }) : failure('DOCUMENT_VERSION_STALE')
    case 'save_bookmark': {
      const source = activeEvidence.find(row => row.evidence_id === args.evidence_id)
      const bound = activeDocuments.find(row => row.document_id === source?.document_id)
      return bound ? success({ id: record('Bookmark', bound.title, [bound], { space_ids: [bound.space_id], bookmark_type: 'Document', document: bound }) }) : failure('EVIDENCE_UNAVAILABLE')
    }
    case 'remove_saved':
      for (const kind of Object.keys(activities)) activities[kind] = activities[kind].filter(item => item.id !== args.activity_id)
      return success({ removed: saved.delete(args.activity_id) })
    case 'get_feedback': return success(paginate(empty ? [] : activeFeedback, args))
    case 'get_feedback_queue': {
      // Main 10h minimal interface: bounded read-only substring filter (query, 1-120 chars).
      // ?state=feedback-no-search keeps the pre-interface candidate to exercise the honest
      // UI fallback; it is a synthetic old-candidate state, not a capability claim.
      if (state === 'feedback-no-search' && args.query) {
        return failure('INVALID_REQUEST', '合成旧候选未提供反馈内容搜索。')
      }
      const queue = visual ? visualFeedback : feedback
      const needle = typeof args.query === 'string' ? args.query.trim() : ''
      if (needle.length > 120) return failure('INVALID_REQUEST', '反馈搜索最多 120 个字符。')
      const matchedQueue = empty ? [] : queue
        .filter(item => !args.status || item.status === args.status)
        .filter(item => !needle || `${item.category || ''} ${item.note || ''}`.includes(needle))
        .map(item => ({ ...item, maintenance_reply: item.reply }))
      if (visual) return success(paginate(matchedQueue, args))
      const visible = empty ? [] : state === 'feedback-one' ? feedback.slice(0, 1)
        : state === 'feedback-long' ? [
          { ...feedback[0], note: '合成反馈用于验证移动端长文完整换行和状态操作列位置。'.repeat(15) },
          ...feedback.slice(1),
        ] : feedback
      return success(paginate(visible.filter(item => !args.status || item.status === args.status)
        .map(item => ({ ...item, maintenance_reply: item.reply })), args))
    }
    case 'submit_feedback': {
      const id = randomUUID()
      activeFeedback.unshift({ id, category: args.category, note: args.note, status: 'Pending', created_at: date, updated_at: date, reply: '' })
      return success({ id })
    }
    case 'review_feedback': {
      const item = activeFeedback.find(row => row.id === args.activity_id)
      if (!item) return failure('INVALID_REQUEST')
      Object.assign(item, { status: args.status, reply: args.reply })
      return success({ id: item.id })
    }
    case 'open_document':
    case 'read_document_page':
      return open() ? success(readDocument(doc, readerPages)) : failure(doc ? 'DOCUMENT_VERSION_STALE' : 'DOCUMENT_READ_UNAVAILABLE')
    case 'search_document': {
      if (!open()) return failure('DOCUMENT_VERSION_STALE')
      const blocks = readDocument(doc, readerPages).body.blocks
      return success({ searched_blocks: blocks.length, capped: false, matches: blocks.filter(block => block.text.includes(args.query))
        .map(block => ({ ordinal: block.ordinal, page: null, block_id: block.block_id, snippet: block.text })) })
    }
    case 'document_capabilities':
      return open() ? success({ document_id: doc.document_id, version_id: doc.version_id, can_read: true, can_preview: true, can_download: true, preview_kind: 'ORIGINAL_PDF', preview_reason: null, download_reason: null }) : failure('DOCUMENT_VERSION_STALE')
    case 'create_document_delivery': {
      if (!open()) return failure('DOCUMENT_VERSION_STALE')
      const ticket = randomBytes(32).toString('base64url')
      const content = pdfFor(doc, readerPages), filename = doc.document_number + '.pdf'
      const expires_at = Math.floor(Date.now() / 1000) + 120
      tickets.set(ticket, { content, filename, expires_at })
      for (const [id, entry] of tickets) if (entry.expires_at < Date.now() / 1000) tickets.delete(id)
      return success({ content_url: '/api/method/hb_knowledge_app.hb_knowledge.api.document_content?ticket=' + ticket,
        expires_at, filename, content_type: 'application/pdf', sha256: createHash('sha256').update(content).digest('hex'), kind: 'ORIGINAL_PDF' })
    }
    case 'get_connections':
      return success({ items: connections, endpoint: 'http://127.0.0.1:18650/mcp', auth_type: 'Bearer', ttl_days: 7,
        tools: ['list_knowledge_spaces', 'search_knowledge', 'get_evidence', 'ask_knowledge'],
        deployment: 'LOCAL_UAT', query_blocked: false, client_versions: { OpenClaw: '合成', Hermes: '合成' }, client_verification: {} })
    case 'create_connection': {
      const id = randomBytes(16).toString('hex')
      const expires_at = new Date(Date.now() + 604800000).toISOString()
      connections.unshift({ id, label: args.label, client: args.client_name, stage: '等待核验', expires_at, revoked: false, expired: false, last_used_at: null })
      return success({ id, token: 'hbos_mcp_' + id + '.' + randomBytes(32).toString('base64url'), expires_at })
    }
    case 'revoke_connection': {
      const item = connections.find(row => row.id === args.connection_id)
      if (!item) return failure('INVALID_REQUEST')
      item.revoked = true
      return success({ revoked: true })
    }
    case 'get_maintenance':
      return success(await maintenance.getMaintenance(args.batch_id, page, args.locate, args, state))
    case 'get_version_lineage':
      // The real lineage endpoint is not part of this synthetic preview. Only the
      // deterministic ?state=visual comparison scene supplies a chain, clearly synthetic.
      return visual ? success(await maintenance.getVersionLineage(args.document_id, state))
        : failure('SERVICE_ERROR', '合成预览：版本沿革未接入本夹具；页面应显示诚实不可用态。')
    case 'preview_import': return success(await maintenance.previewImport())
    case 'upload_knowledge': return success(await maintenance.uploadKnowledge(args.file, args))
    case 'get_maintenance_spaces': return success(await batch.getManagedSpaces())
    case 'get_maintenance_templates': return success(await batch.getManagedTemplates())
    case 'get_maintenance_pipeline': return success(await batch.getManagedPipeline())
    case 'plan_import': return success(await maintenance.planImport(args.manifest))
    case 'submit_import': return success(await maintenance.submitImport(args.plan_sha256, args.approval_ref, args.label))
    case 'batch_progress': return success(await maintenance.getBatchProgress())
    case 'pause_import': return success(await maintenance.pauseImport())
    case 'resume_import': return success(await maintenance.resumeImport())
    case 'reclaim_import': return success(await maintenance.reclaimImport())
    case 'queue_import':
    case 'review_import':
    case 'review_import_batch':
    case 'approve_import_sharing':
    case 'publish_import':
    case 'withdraw_import': return success(await maintenance.maintenanceAction(name, args))
    default: return failure('SERVICE_ERROR', '合成预览未配置此方法。')
  }
}

export function installFixture(server) {
  server.middlewares.use(async (req, res, next) => {
    const url = new URL(req.url, 'http://127.0.0.1')
    if (url.pathname === '/') { res.writeHead(302, { Location: '/hbos/knowledge' }).end(); return }
    if (!url.pathname.startsWith('/api/') && url.pathname !== '/mcp') return next()
    const json = (status, message) => res.writeHead(status, { 'Content-Type': 'application/json', 'Cache-Control': 'no-store' }).end(JSON.stringify({ message }))
    if (url.pathname === '/api/method/hbos_portal.api.csrf.get_token') return json(200, success({ csrf_token: 'synthetic-local-preview' }))
    const match = /^\/api\/method\/hb_knowledge_app\.hb_knowledge\.(?:api|maintenance_batch)\.([a-z_]+)$/.exec(url.pathname)
    if (!match) return json(403, '合成预览没有真实 API 转发。')
    const name = match[1]
    if (name === 'document_content') {
      const ticket = tickets.get(url.searchParams.get('ticket'))
      if (!ticket || ticket.expires_at < Date.now() / 1000) return json(404, '合成预览凭条失效。')
      const range = /^bytes=(\d+)-(\d+)$/.exec(req.headers.range || '')
      const headers = { 'Content-Type': 'application/pdf', 'Accept-Ranges': 'bytes', 'Content-Disposition': `inline; filename="${ticket.filename}"` }
      if (!range) return res.writeHead(200, { ...headers, 'Content-Length': ticket.content.length }).end(ticket.content)
      const start = Number(range[1]), end = Math.min(Number(range[2]), ticket.content.length - 1)
      if (start > end) return res.writeHead(416, { 'Content-Range': `bytes */${ticket.content.length}` }).end()
      return res.writeHead(206, { ...headers, 'Content-Range': `bytes ${start}-${end}/${ticket.content.length}`, 'Content-Length': end - start + 1 }).end(ticket.content.subarray(start, end + 1))
    }
    try {
      const referer = new URL(req.headers.referer || '/', url)
      const state = referer.searchParams.get('state') || 'success'
      const args = Object.fromEntries(url.searchParams)
      if (req.method === 'POST') {
        const chunks = []
        let size = 0
        for await (const chunk of req) {
          size += chunk.length
          if (size > 21 * 1024 * 1024) return json(413, failure('INVALID_REQUEST'))
          chunks.push(chunk)
        }
        const contentType = req.headers['content-type'] || ''
        const body = Buffer.concat(chunks)
        Object.assign(args, contentType.startsWith('multipart/form-data')
          ? Object.fromEntries(await new Response(body, { headers: { 'Content-Type': contentType } }).formData())
          : JSON.parse(body.toString() || '{}'))
      }
      if (state === 'loading') {
        const timer = setTimeout(() => json(200, failure('SERVICE_ERROR')), 25000)
        res.on('close', () => clearTimeout(timer))
        return
      }
      return json(200, await method(name, args, state))
    } catch (error) {
      console.error('Knowledge preview fixture:', error.message)
      return json(200, failure('SERVICE_ERROR'))
    }
  })
}
