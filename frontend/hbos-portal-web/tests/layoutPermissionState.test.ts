import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { defineComponent, ref } from 'vue'
import { createMemoryHistory, createRouter } from 'vue-router'
import KnowledgeTwinLayout from '@/components/layout/KnowledgeTwinLayout.vue'
import { usePortalStore } from '@/stores/portal'
import { DomainApiError } from '@/services/p1Api'

const api = vi.hoisted(() => ({ status: vi.fn() }))
vi.mock('@/composables/usePortalSession', () => ({
  usePortalSession: () => ({ sessionPending: ref(false), sessionError: ref(null), sessionRevision: ref(0) }),
}))
vi.mock('@/services/p1Api', async original => ({
  ...(await original<typeof import('@/services/p1Api')>()),
  getKnowledgeStatus: api.status,
}))

const Page = defineComponent({ template: '<p data-test="page">maintenance</p>' })

async function mountAt(path = '/hbos/knowledge/maintenance') {
  const pinia = createPinia(); setActivePinia(pinia)
  usePortalStore().user = { id: 'synthetic-maintainer' } as never
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/hbos/knowledge', component: Page },
      { path: '/hbos/knowledge/maintenance', component: Page },
      { path: '/hbos/knowledge/catalog', component: Page },
    ],
  })
  await router.push(path); await router.isReady()
  const wrapper = mount(KnowledgeTwinLayout, {
    global: {
      plugins: [pinia, router],
      stubs: {
        KnowledgeHeader: true, KnowledgeSidebar: true, GlobalHeader: true,
        PointerAtmosphere: true, KnowledgeTwinSidebar: true, CommandPalette: true,
        'a-skeleton': true, 'a-alert': true,
        'a-button': { template: '<button @click="$emit(\'click\')"><slot/></button>' },
        'a-result': { props: ['status', 'title'], template: '<div data-test="result">{{ status }} {{ title }}</div>' },
      },
    },
  })
  await flushPromises()
  return { wrapper, router }
}

beforeEach(() => { api.status.mockReset() })

describe('maintenance permission state is not conflated with a 403', () => {
  it('shows a service-unknown state instead of "no permission" when the status endpoint fails', async () => {
    api.status.mockRejectedValue(new DomainApiError('SERVICE_ERROR', '知识服务暂时不可用。'))
    const { wrapper } = await mountAt()
    try {
      expect(wrapper.find('[data-test="result"]').exists()).toBe(false)
      expect(wrapper.text()).toContain('维护权限状态暂时无法确认')
      expect(wrapper.text()).not.toContain('当前账号没有知识维护权限')
    } finally { wrapper.unmount() }
  })

  it('still shows the 403 only for an explicit permission denial', async () => {
    api.status.mockRejectedValue(new DomainApiError('FORBIDDEN', '当前账号没有知识维护权限。'))
    const { wrapper } = await mountAt()
    try {
      expect(wrapper.text()).toContain('当前账号没有知识维护权限')
    } finally { wrapper.unmount() }
  })

  it('shows the 403 when the status says can_maintain is false', async () => {
    api.status.mockResolvedValue({ can_maintain: false })
    const { wrapper } = await mountAt()
    try {
      expect(wrapper.text()).toContain('当前账号没有知识维护权限')
    } finally { wrapper.unmount() }
  })

  it('does not re-request the status on every knowledge route change', async () => {
    api.status.mockResolvedValue({ can_maintain: true })
    const { wrapper, router } = await mountAt('/hbos/knowledge')
    try {
      expect(api.status).toHaveBeenCalledTimes(1)
      await router.push('/hbos/knowledge/catalog'); await flushPromises()
      await router.push('/hbos/knowledge'); await flushPromises()
      // Same user, same permission scope: the entry must stay visible without a
      // second status request (and without a skeleton in between).
      expect(api.status).toHaveBeenCalledTimes(1)
    } finally { wrapper.unmount() }
  })

  it('recovers to granted after a retry once the service answers', async () => {
    api.status.mockRejectedValueOnce(new DomainApiError('SERVICE_ERROR', '知识服务暂时不可用。'))
    const { wrapper } = await mountAt()
    try {
      expect(wrapper.text()).toContain('维护权限状态暂时无法确认')
      api.status.mockResolvedValue({ can_maintain: true })
      const retry = wrapper.findAll('button').find(button => button.text().includes('重试'))
      expect(retry).toBeTruthy()
      await retry!.trigger('click'); await flushPromises()
      expect(wrapper.text()).not.toContain('维护权限状态暂时无法确认')
      expect(wrapper.find('[data-test="page"]').exists()).toBe(true)
    } finally { wrapper.unmount() }
  })
})
