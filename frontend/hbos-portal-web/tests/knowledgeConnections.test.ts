import { mount, flushPromises } from '@vue/test-utils'
import { defineComponent } from 'vue'
import { beforeEach, afterEach, describe, expect, it, vi } from 'vitest'
import Connections from '@/components/knowledge/KnowledgeConnections.vue'
import { localInstaller, knowledgeUsageRules } from '@/services/knowledgeInstaller'
import { credentialFreePrompt } from '@/services/knowledgeHelp'
const api = vi.hoisted(() => ({ get: vi.fn(), create: vi.fn(), revoke: vi.fn() }))
vi.mock('@/services/p1Api', async original => ({ ...await original<typeof import('@/services/p1Api')>(), getKnowledgeConnections: api.get, createKnowledgeConnection: api.create, revokeKnowledgeConnection: api.revoke }))
const Drawer = defineComponent({ props: ['open'], emits: ['close'], template: '<section v-if="open"><slot/><button data-close @click="$emit(\'close\')">close</button></section>' })
const Button = defineComponent({ props: ['disabled', 'htmlType'], template: '<button :disabled="disabled" :type="htmlType||\'button\'"><slot/></button>' })
const stubs = { 'a-drawer': Drawer, 'a-button': Button, 'a-input': { props: ['value', 'disabled'], template: '<input :value="value" :disabled="disabled"/>' }, 'a-alert': { props: ['message', 'description'], template: '<p>{{message}} {{description}}</p>' }, 'a-skeleton': true, 'a-empty': true, 'a-collapse': { template: '<div><slot/></div>' }, 'a-collapse-panel': { template: '<div><slot/></div>' }, 'a-popconfirm': { template: '<div><slot/></div>' }, 'a-tag': { props: ['color'], template: '<b :data-color="color"><slot/></b>' } }
const info = { items: [], tools: ['list_knowledge_spaces', 'search_knowledge', 'get_evidence', 'ask_knowledge'], endpoint: 'http://localhost:18350/mcp', deployment: 'LOCAL_UAT', query_blocked: false, ttl_days: 7, client_versions: { OpenClaw: 'SYNTHETIC', Hermes: 'SYNTHETIC' }, client_verification: { OpenClaw: 'PENDING_REAL_CLIENT_TEST', Hermes: 'PENDING_REAL_CLIENT_TEST' } }
const id = 'a'.repeat(32), token = 'hbos_mcp_' + id + '.' + 'x'.repeat(43)
const credential = { id, token, challenge_id: 'b'.repeat(32), expires_at: '2026-10-12' }
function deferred() { let resolve!: (value: any) => void, reject!: (e: Error) => void; const promise = new Promise((a, b) => { resolve = a; reject = b }); return { promise, resolve, reject } }
async function opened() { const w = mount(Connections, { props: { open: true, subject: 'A' }, global: { stubs } }); await flushPromises(); return w }
async function clickButton(w: ReturnType<typeof mount>, selector: string) { await w.find(selector).trigger('click'); await flushPromises() }
async function legacyInstall(w: ReturnType<typeof mount>) { await w.find('[data-legacy-install]').trigger('click'); await flushPromises() }
beforeEach(() => { vi.clearAllMocks(); api.get.mockResolvedValue(info); api.create.mockResolvedValue(credential); api.revoke.mockResolvedValue({ revoked: true }); URL.createObjectURL = vi.fn(() => 'blob:SYNTHETIC'); URL.revokeObjectURL = vi.fn(); vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {}) })
afterEach(() => vi.restoreAllMocks())
describe('RC14 four-step connection wizard — synthetic, zero model requests', () => {
  it('walks the four steps in order and never shows the token in any copied text', async () => {
    const w = await opened()
    expect(w.text()).toContain('选择助手'); expect(w.text()).toContain('连接知识库'); expect(w.text()).toContain('实际试用'); expect(w.text()).toContain('使用帮助')
    // Step 1 keeps the model-neutral client version note.
    expect(w.text()).toContain('支持版本：SYNTHETIC')
    await clickButton(w, '[data-step-continue]')
    // Step 2: credential-free prompt copy plus a collapsed advanced Python path.
    expect(w.find('[data-copy-prompt]').exists()).toBe(true)
    expect(w.text()).toContain('高级选项：下载 Python 安装文件')
    expect(w.text()).not.toContain(token)
    const prompt = credentialFreePrompt()
    expect(prompt).not.toContain(token); expect(prompt).not.toContain('gpt-6-luna')
    expect(prompt).toContain('不指定默认模型')
    await w.unmount()
  })
  it('creates a native HTTP connection without downloading a script and keeps the prompt credential-free', async()=>{
    const w=await opened();await clickButton(w,'[data-step-continue]')
    await clickButton(w,'[data-create-connection]')
    expect(api.create).toHaveBeenCalledTimes(1);expect(URL.createObjectURL).not.toHaveBeenCalled()
    expect(w.find('input[aria-label="本人连接认证值"]').attributes('type')).toBe('password')
    expect(w.find('input[aria-label="本人连接认证值"]').element.value).toBe('Bearer '+token)
    expect(w.text()).not.toContain(token);expect(credentialFreePrompt()).not.toContain(token)
    await w.setProps({subject:'B'});await flushPromises()
    expect(w.find('input[aria-label="本人连接认证值"]').exists()).toBe(false);w.unmount()
  })
  it('keeps the legacy Python installer working behind the advanced option without leaking the token into the page', async () => {
    const w = await opened()
    await clickButton(w, '[data-step-continue]')
    await w.find('.kb-advanced summary').trigger('click')
    await legacyInstall(w)
    expect(URL.createObjectURL).toHaveBeenCalledTimes(1)
    expect(w.text()).toContain('python3')
    expect(w.text()).not.toContain(token)
    expect(w.text()).toContain('安装文件已下载')
    await w.unmount()
  })
  it('discards a credential returned after close without creating a download', async () => {
    const pending = deferred(); api.create.mockReturnValue(pending.promise); const w = await opened()
    await clickButton(w, '[data-step-continue]')
    await w.find('.kb-advanced summary').trigger('click')
    await legacyInstall(w)
    await w.get('[data-close]').trigger('click'); await w.setProps({ open: false }); pending.resolve(credential); await flushPromises()
    expect(URL.createObjectURL).not.toHaveBeenCalled(); expect(w.text()).not.toContain(token); w.unmount()
  })
  it('discards the former subject credential and allows a new installation', async () => {
    const pending = deferred(); api.create.mockReturnValueOnce(pending.promise); const w = await opened()
    await clickButton(w, '[data-step-continue]')
    await w.find('.kb-advanced summary').trigger('click')
    await legacyInstall(w)
    await w.setProps({ subject: 'B' }); await flushPromises(); pending.resolve(credential); await flushPromises()
    expect(URL.createObjectURL).not.toHaveBeenCalled()
    await clickButton(w, '[data-step-continue]')
    await w.find('.kb-advanced summary').trigger('click')
    await legacyInstall(w)
    expect(URL.createObjectURL).toHaveBeenCalledTimes(1); expect(w.text()).not.toContain(token); expect(w.text()).toContain('安装文件已下载'); w.unmount()
  })
  it('only shows a token-free command, clears it on client switch, and never trusts a legacy success stage', async () => {
    api.get.mockResolvedValue({ ...info, items: [{ id, label: 'SYNTHETIC', client: 'OpenClaw', stage: 'Evidence Opened', expires_at: '2026-10-12', revoked: false, expired: false }] })
    const w = await opened()
    await clickButton(w, '[data-step-continue]')
    await w.find('.kb-advanced summary').trigger('click')
    await legacyInstall(w)
    expect(w.text()).toContain('python3'); expect(w.text()).not.toContain(token)
    expect(w.text()).toContain('已准备连接（尚无实际使用记录）')
    await w.findAll('button').find(b => b.text().startsWith('Hermes'))!.trigger('click'); await flushPromises()
    expect(w.text()).not.toContain('python3'); w.unmount()
  })
  it('labels a server-recorded knowledge use as a completed query and keeps self-check separate', async () => {
    api.get.mockResolvedValue({ ...info, items: [{ id, label: 'SYNTHETIC', client: 'OpenClaw', stage: 'Evidence Opened', expires_at: '2026-10-12', revoked: false, expired: false, verification_state: 'KNOWLEDGE_USED', knowledge_used_at: '2026-10-12T08:00' }] })
    const w = await opened()
    await clickButton(w, '[data-step-continue]')
    await clickButton(w, '[data-step-continue]') // step 3
    expect(w.text()).toContain('已完成知识查询')
    expect(w.text()).toContain('服务自检')
    expect(w.text()).toContain('运行服务自检（不调用模型）')
    await w.unmount()
  })
})
describe('installer and prompt hygiene', () => {
  it('places credentials only in the private local file, never in rules or client challenge headers', () => {
    const source = localInstaller('OpenClaw', info.endpoint, token, id, 'b'.repeat(32))
    expect(source).toContain(token)
    expect(source).not.toContain('X-HBOS-Client-Challenge')
    expect(source).toContain("entry='hbos-knowledge'")
    expect(source).toContain('Continue? [y/N]')
    expect(source).not.toContain('requests.')
    expect(knowledgeUsageRules).not.toContain(token); expect(knowledgeUsageRules).not.toContain('Bearer')
    expect(knowledgeUsageRules).not.toContain('gpt-6-luna')
    expect(() => localInstaller('Hermes', info.endpoint, 'BAD', id, 'b'.repeat(32))).toThrow()
  })
  it('rejects a prompt that embeds the connection token', () => {
    expect(() => localInstaller('OpenClaw', info.endpoint, token, id, 'rules with ' + token)).toThrow('提示词不得包含连接凭据')
  })
})
