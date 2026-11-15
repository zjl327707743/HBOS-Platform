import { portalSelectStub } from './portalSelectStub'
import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

// MC-6 (Main decision ERROR_CONTRACT_IS_SCOPE_REJECTED_POLICY_UNAVAILABLE_INVALID_REQUEST):
// knowledge-space create/copy failures must map the three terminal codes to the existing
// error surface and must not be retried automatically.
const api = vi.hoisted(() => ({
  spaces: vi.fn(), templates: vi.fn(), pipeline: vi.fn(),
  create: vi.fn(), copy: vi.fn(),
  approve: vi.fn(), inspect: vi.fn(), precheck: vi.fn(), resume: vi.fn(), upload: vi.fn(), verify: vi.fn(),
}))
vi.mock('@/services/knowledgeMaintenanceBatchApi', () => ({
  getManagedSpaces: api.spaces,
  getManagedTemplates: api.templates,
  getManagedPipeline: api.pipeline,
  createManagedSpace: api.create,
  copyManagedTemplate: api.copy,
  approveManagedRows: api.approve,
  inspectManagedSource: api.inspect,
  precheckManagedUpload: api.precheck,
  resumeManagedBatch: api.resume,
  uploadManagedGroup: api.upload,
  verifyManagedReader: api.verify,
}))

import KnowledgeBatchMaintenance from '@/components/knowledge/KnowledgeBatchMaintenance.vue'

function pipeline() {
  return {
    items: [], total: 0, normal_remaining: 0, exceptions: 0, awaiting_adoption: 0,
    available: 0, batch_count: 0, scan_truncated: false,
    controller_continues_without_browser: true, net_available_per_hour: null,
    human_interventions: 0,
  }
}
function codedError(code: string) {
  return Object.assign(new Error('backend raw detail'), { code })
}
let wrapper: ReturnType<typeof mount> | undefined
async function mountPanel() {
  wrapper = mount(KnowledgeBatchMaintenance, { global: { stubs: { PortalSelect: portalSelectStub } } })
  await flushPromises()
  return wrapper
}
function button(text: string) {
  return wrapper!.findAll('button').find(candidate => candidate.text() === text)!
}
function errorText() {
  return wrapper!.find('p[role="alert"]').text()
}
beforeEach(() => {
  vi.clearAllMocks()
  api.spaces.mockResolvedValue({
    can_manage_spaces: true,
    spaces: [{ space_id: 'SPACE_A', title: '合成空间A' }, { space_id: 'SPACE_B', title: '合成空间B' }],
  })
  api.templates.mockResolvedValue({ templates: [] })
  api.pipeline.mockResolvedValue(pipeline())
})
afterEach(() => { wrapper?.unmount(); wrapper = undefined; vi.useRealTimers() })

describe('MC-6: knowledge-space create/copy domain error mapping', () => {
  it.each([
    ['SCOPE_REJECTED', '当前账号无权执行该知识空间操作（SCOPE_REJECTED）；不会自动重试。'],
    ['POLICY_UNAVAILABLE', '该知识空间操作当前不可用（POLICY_UNAVAILABLE）；不会自动重试。'],
    ['INVALID_REQUEST', '知识空间操作请求无效（INVALID_REQUEST）；请核对后重试。'],
  ])('maps %s on create without auto retry', async (code, expected) => {
    api.create.mockRejectedValueOnce(codedError(code))
    await mountPanel()
    await wrapper!.find('input[maxlength="120"]').setValue('合成新空间')
    await button('创建标准空间并复制模板').trigger('click')
    await flushPromises()
    expect(api.create).toHaveBeenCalledTimes(1)
    expect(api.create).toHaveBeenCalledWith('合成新空间', 'SPACE_A')
    expect(errorText()).toContain(expected)
  })

  it('maps SCOPE_REJECTED on copy without auto retry', async () => {
    api.copy.mockRejectedValueOnce(codedError('SCOPE_REJECTED'))
    await mountPanel()
    // select a different target space so the copy action is enabled
    await wrapper!.findAll('select')[0].setValue('SPACE_B')
    await button('复制到当前空间的后续资料').trigger('click')
    await flushPromises()
    expect(api.copy).toHaveBeenCalledTimes(1)
    expect(api.copy).toHaveBeenCalledWith('SPACE_B', 'SPACE_A')
    expect(errorText()).toContain('当前账号无权执行该知识空间操作（SCOPE_REJECTED）；不会自动重试。')
  })

  it('keeps the original message for an unmapped terminal error', async () => {
    api.create.mockRejectedValueOnce(codedError('SERVICE_ERROR'))
    await mountPanel()
    await wrapper!.find('input[maxlength="120"]').setValue('合成新空间')
    await button('创建标准空间并复制模板').trigger('click')
    await flushPromises()
    expect(api.create).toHaveBeenCalledTimes(1)
    expect(errorText()).toContain('backend raw detail')
  })
})
