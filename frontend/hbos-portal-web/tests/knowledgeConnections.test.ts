import { mount, flushPromises } from '@vue/test-utils'
import { defineComponent } from 'vue'
import { beforeEach, afterEach, describe, expect, it, vi } from 'vitest'
import Connections from '@/components/knowledge/KnowledgeConnections.vue'
import { localInstaller, knowledgeUsageRules } from '@/services/knowledgeInstaller'
import { connectionGuidance, credentialFreePrompt, guidanceHasNoSecret } from '@/services/knowledgeHelp'

const api = vi.hoisted(() => ({ get: vi.fn(), create: vi.fn(), revoke: vi.fn() }))
vi.mock('@/services/p1Api', async original => ({
  ...await original<typeof import('@/services/p1Api')>(),
  getKnowledgeConnections: api.get,
  createKnowledgeConnection: api.create,
  revokeKnowledgeConnection: api.revoke,
}))

const Drawer = defineComponent({ props: ['open'], emits: ['close'], template: '<section v-if="open"><slot/><button data-close @click="$emit(\'close\')">close</button></section>' })
const Button = defineComponent({ props: ['disabled', 'htmlType'], template: '<button :disabled="disabled" :type="htmlType||\'button\'"><slot/></button>' })
const stubs = {
  'a-drawer': Drawer,
  'a-button': Button,
  'a-alert': { props: ['message', 'description'], template: '<p>{{message}} {{description}}</p>' },
  'a-skeleton': true,
  'a-spin': { template: '<span data-spin/>' },
  'a-popconfirm': { template: '<div><slot/></div>' },
  'a-tag': { props: ['color'], template: '<b><slot/></b>' },
}

const id = 'a'.repeat(32)
const token = 'hbos_mcp_' + id + '.' + 'x'.repeat(43)
const info = {
  items: [] as Record<string, unknown>[],
  tools: ['list_knowledge_spaces', 'search_knowledge', 'get_evidence', 'ask_knowledge'],
  endpoint: 'http://knowledge-r2.localhost:18350/mcp',
  deployment: 'LOCAL_UAT', query_blocked: false, ttl_days: 7,
  client_versions: { OpenClaw: 'SYNTHETIC', Hermes: 'SYNTHETIC' },
  client_verification: { OpenClaw: 'PENDING_REAL_CLIENT_TEST', Hermes: 'PENDING_REAL_CLIENT_TEST' },
}
const credential = { id, token, expires_at: '2026-10-12' }

async function opened() {
  const wrapper = mount(Connections, { props: { open: true, subject: 'A' }, global: { stubs } })
  await flushPromises()
  return wrapper
}
async function click(wrapper: ReturnType<typeof mount>, selector: string) {
  await wrapper.find(selector).trigger('click')
  await flushPromises()
}
async function toStepTwo(wrapper: ReturnType<typeof mount>) {
  await click(wrapper, '[data-step-continue]')
}

beforeEach(() => {
  vi.clearAllMocks()
  api.get.mockResolvedValue({ ...info, items: [] })
  api.create.mockResolvedValue(credential)
  api.revoke.mockResolvedValue({ revoked: true })
  URL.createObjectURL = vi.fn(() => 'blob:SYNTHETIC')
  URL.revokeObjectURL = vi.fn()
  vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {})
})
afterEach(() => vi.restoreAllMocks())

describe('assistant connection journey — synthetic, zero model requests', () => {
  it('walks select → copy → try → help', async () => {
    const wrapper = await opened()
    expect(wrapper.text()).toContain('选择助手')
    expect(wrapper.text()).toContain('复制连接指引')
    expect(wrapper.text()).toContain('在助手里试问')
    expect(wrapper.text()).toContain('使用帮助')
    expect(wrapper.text()).toContain('支持版本：SYNTHETIC')
    await toStepTwo(wrapper)
    expect(wrapper.find('[data-copy-guidance]').exists()).toBe(true)
    expect(wrapper.find('[data-guidance-details]').exists()).toBe(true)
    wrapper.unmount()
  })

  it('copies one guidance block that names the endpoint and command but no credential', async () => {
    const written: string[] = []
    Object.assign(navigator, { clipboard: { writeText: vi.fn(async (value: string) => { written.push(value) }) } })
    const wrapper = await opened()
    await toStepTwo(wrapper)
    expect(wrapper.find('[data-guidance-details]').text()).not.toContain(token)
    await click(wrapper, '[data-copy-guidance]')
    expect(written).toHaveLength(1)
    const text = written[0]!
    expect(text).toContain(info.endpoint)
    expect(text).toContain('openclaw mcp add hbos')
    expect(text).toContain('搜索培养箱使用前检查的相关 SOP')
    expect(text).not.toContain(token)
    expect(guidanceHasNoSecret(text)).toBe(true)
    expect(wrapper.find('[data-copy-notice]').text()).toContain('不含凭据')
    wrapper.unmount()
  })

  it('generates the one personal connection and never renders the credential in the page', async () => {
    Object.assign(navigator, { clipboard: { writeText: vi.fn(async () => {}) } })
    const wrapper = await opened()
    await toStepTwo(wrapper)
    await click(wrapper, '[data-create-connection]')
    expect(api.create).toHaveBeenCalledTimes(1)
    expect(wrapper.text()).not.toContain(token)
    expect(wrapper.find('[data-copy-credential]').exists()).toBe(true)
    expect(URL.createObjectURL).not.toHaveBeenCalled()
    wrapper.unmount()
  })

  it('keeps the private installer behind the advanced option, and only as a copyable command', async () => {
    const written: string[] = []
    Object.assign(navigator, { clipboard: { writeText: vi.fn(async (value: string) => { written.push(value) }) } })
    const wrapper = await opened()
    await toStepTwo(wrapper)
    await click(wrapper, '[data-create-connection]')
    await click(wrapper, '[data-download-installer]')
    await flushPromises()
    expect(URL.createObjectURL).toHaveBeenCalledTimes(1)
    expect(wrapper.find('[data-install-command]').text()).toContain('python3')
    expect(wrapper.text()).not.toContain(token)
    expect(written.some(value => value.includes('python3'))).toBe(true)
    wrapper.unmount()
  })

  it('does not claim a connection from a generated credential or from tools alone', async () => {
    api.get.mockResolvedValue({
      ...info,
      items: [{ id, label: 'SYNTHETIC', client: 'OpenClaw', stage: 'Tools Discovered', expires_at: '2026-10-12', revoked: false, expired: false, verification_state: 'SERVER_READY' }],
    })
    const wrapper = await opened()
    await toStepTwo(wrapper)
    await click(wrapper, '[data-step-continue]')
    const state = wrapper.find('[data-connection-state]')
    expect(state.attributes('data-state')).toBe('waiting')
    expect(state.text()).toContain('等待首次成功查询')
    expect(state.text()).not.toContain('已连接')
    wrapper.unmount()
  })

  it('shows 已连接 only from the server’s own record of a search with an opened source', async () => {
    api.get.mockResolvedValue({
      ...info,
      items: [{ id, label: 'SYNTHETIC', client: 'OpenClaw', stage: 'Knowledge Used', expires_at: '2026-10-12', revoked: false, expired: false, verification_state: 'KNOWLEDGE_USED', knowledge_used_at: '2026-10-12T08:00' }],
    })
    const wrapper = await opened()
    await toStepTwo(wrapper)
    await click(wrapper, '[data-step-continue]')
    const state = wrapper.find('[data-connection-state]')
    expect(state.attributes('data-state')).toBe('connected')
    expect(state.text()).toContain('已连接')
    wrapper.unmount()
  })

  it('offers disconnect and the four tool help on the last step', async () => {
    api.get.mockResolvedValue({
      ...info,
      items: [{ id, label: 'SYNTHETIC', client: 'OpenClaw', stage: 'Knowledge Used', expires_at: '2026-10-12', revoked: false, expired: false, verification_state: 'KNOWLEDGE_USED', knowledge_used_at: '2026-10-12T08:00' }],
    })
    const wrapper = await opened()
    await toStepTwo(wrapper)
    await click(wrapper, '[data-step-continue]')
    await click(wrapper, '[data-step-continue]')
    expect(wrapper.text()).toContain('search_knowledge')
    expect(wrapper.text()).toContain('get_evidence')
    expect(wrapper.find('[data-revoke-connection]').exists()).toBe(true)
    expect(wrapper.find('[data-copy-example-2]').exists()).toBe(true)
    wrapper.unmount()
  })
})

describe('guidance and installer hygiene', () => {
  it('the copied guidance carries no credential and no long-lived bearer', () => {
    const text = connectionGuidance({
      client: 'OpenClaw', endpoint: info.endpoint,
      command: 'openclaw mcp add hbos --url ' + info.endpoint + ' --header "Authorization=Bearer {credential}"',
      rules: credentialFreePrompt(), example: '搜索培养箱使用前检查的相关 SOP。', version: 'SYNTHETIC',
    })
    expect(guidanceHasNoSecret(text)).toBe(true)
    expect(text).not.toContain(token)
    expect(text).toContain('你的本人凭据')
  })

  it('places credentials only in the private local file, never in rules', () => {
    const source = localInstaller('OpenClaw', info.endpoint, token, id)
    expect(source).toContain(token)
    expect(source).not.toContain('requests.')
    expect(source).toContain("entry='hbos-knowledge'")
    expect(knowledgeUsageRules).not.toContain(token)
    expect(knowledgeUsageRules).not.toContain('Bearer')
    expect(() => localInstaller('Hermes', info.endpoint, 'BAD', id)).toThrow()
    expect(() => localInstaller('OpenClaw', info.endpoint, token, id, 'rules with ' + token)).toThrow('提示词不得包含连接凭据')
  })
})
