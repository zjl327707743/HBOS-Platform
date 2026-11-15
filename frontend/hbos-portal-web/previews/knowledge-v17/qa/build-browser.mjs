import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import { evaluate, navigate, resize, shot, close, send } from '../browser/cdp.mjs'
import { probe } from './structure.mjs'

// Run only on the same loopback listener serving the Frappe build.
const origin = 'http://127.0.0.1:18650'
const user = 'synthetic-layout'
const context = 'b'.repeat(64)
const message = data => ({ message: data })
const envelope = data => message({ ok: true, data })
const feedback = [
  { id: 'synthetic-one', category: '版本疑问', note: '请核对目录中显示的版本。', status: 'Pending' },
  { id: 'synthetic-two', category: '内容疑问', note: '希望补充培训资料的适用范围。', status: 'Resolved' },
]
const responses = {
  'hbos_portal.auth.accounts.get_security': message({
    user, session_context: context, first_password_required: false,
    identity: { display_name: '合成维护者', department: '合成', employee_number: '', login_name: user },
    temporary_password_state: { pending: false, temporary: false, generation: 0, can_claim: false, expires_at: null },
  }),
  'hbos_portal.api.iam_access.get_capabilities': envelope({
    schema_version: 1, subject_user: user, session_context: context, policy_revision: 'synthetic', capabilities: [],
  }),
  'hbos_portal.api.bootstrap.get_bootstrap': envelope({
    contract_version: 1, user: { id: user, display_name: '合成维护者' },
    branding: { product_name: 'HBOS', company_name: '海滨', workspace_name: '海滨智能工作平台' },
    apps: [{ manifest: { contract_version: 1, id: 'knowledge', title: '知识库', short_title: '知识库', description: '查阅共享资料', icon: 'ReadOutlined', accent: 'knowledge', order: 1, migration_mode: 'native', route: '/hbos/knowledge', capabilities: [] }, access: { can_enter: true } }],
    preferences: {},
  }),
  'hb_knowledge_app.hb_knowledge.api.get_status': envelope({ environment: 'production', can_enter: true, can_search: true, can_maintain: true, ask_enabled: true, gateway_configured: true, mode: 'retrieval' }),
  'hb_knowledge_app.hb_knowledge.api.get_maintenance': envelope({
    departments: [{ key: 'production', title: '合成部门' }], published_documents: [], batches: [], selected: null, feedback: { items: [] },
    import_availability: { can_parse: true, can_batch: true, configured: true, blocked: false },
  }),
  'hb_knowledge_app.hb_knowledge.api.get_feedback_queue': envelope({ items: feedback, page: 1, page_size: 6, has_more: false }),
}
const index = await readFile(process.env.HBOS_FRAPPE_INDEX, 'utf8')
assert.match(index, /\/assets\/[^"]+\.js/)
const { websocket } = await import('../browser/cdp.mjs')
const response = event => {
  const { method, params } = JSON.parse(event.data)
  if (method !== 'Fetch.requestPaused') return
  const url = new URL(params.request.url)
  if (url.origin !== origin) {
    void send('Fetch.failRequest', { requestId: params.requestId, errorReason: 'BlockedByClient' })
    return
  }
  const body = responses[url.pathname.slice('/api/method/'.length)]
  void send('Fetch.fulfillRequest', {
    requestId: params.requestId, responseCode: body ? 200 : 403,
    responseHeaders: [{ name: 'Content-Type', value: 'application/json' }],
    body: Buffer.from(JSON.stringify(body || message('Synthetic inspection only'))).toString('base64'),
  })
}
websocket.addEventListener('message', response)
await send('Fetch.enable', { patterns: [{ urlPattern: '*://*/api/*' }] })
try {
  await resize(1165, 757)
  await navigate(origin + '/hbos/knowledge/maintenance/feedback')
  for (let i = 0; i < 80 && !await evaluate("document.querySelector('.kb-staff-feedback-item')"); i++) {
    await new Promise(resolve => setTimeout(resolve, 80))
  }
  assert.equal(await evaluate("Boolean(document.querySelector('.kb-synthetic'))"), false)
  const result = await evaluate('(' + probe.toString() + ')()')
  assert.equal(result.feedback.length, feedback.length)
  await shot('outputs/结构返工/after/feedback-frappe-build.png')
  console.log('PASS Frappe build P09', JSON.stringify(result))
} finally {
  websocket.removeEventListener('message', response)
  await send('Fetch.disable')
  close()
}
