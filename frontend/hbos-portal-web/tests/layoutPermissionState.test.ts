import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { defineComponent, ref } from 'vue'
import { createMemoryHistory, createRouter } from 'vue-router'
import KnowledgeTwinLayout from '@/components/layout/KnowledgeTwinLayout.vue'
import KnowledgeSidebar from '@/components/layout/KnowledgeSidebar.vue'
import { usePortalStore } from '@/stores/portal'
import { DomainApiError } from '@/services/p1Api'

const api = vi.hoisted(() => ({ status: vi.fn() }))
const ready = ref(true), blocked = ref(false)
vi.mock('@/composables/usePortalSession', () => ({
  usePortalSession: () => ({ sessionPending: ref(false), sessionError: ref(null), sessionRevision: ref(0), sessionReady: ready, sessionBlocked: blocked }),
}))
vi.mock('@/services/p1Api', async original => ({
  ...(await original<typeof import('@/services/p1Api')>()),
  getKnowledgeStatus: api.status,
}))

const Page = defineComponent({ template: '<p data-test="page">maintenance</p>' })

it('keeps Reader routes available and shows maintenance routes only when granted', async () => {
  const reader = ['/hbos/knowledge', '/hbos/knowledge/catalog', '/hbos/knowledge/favorites', '/hbos/knowledge/history']
  const maintenance = ['/hbos/knowledge/maintenance', '/hbos/knowledge/maintenance/upload',
    '/hbos/knowledge/maintenance/versions', '/hbos/knowledge/maintenance/feedback']
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [...reader, ...maintenance].map(path => ({ path, component: Page })),
  })
  await router.push(maintenance[0])
  const wrapper = mount(KnowledgeSidebar, {
    props: { canMaintain: false, maintenance: true },
    global: { plugins: [router] },
  })
  const readerNav = 'nav[aria-label="知识库导航"]'
  const maintenanceNav = 'nav[aria-labelledby="kb-maintenance-nav-label"]'
  const links = (selector: string) => wrapper.get(selector).findAll('a').map(link => link.attributes('href'))
  try {
    expect(links(readerNav)).toEqual(reader)
    expect(wrapper.find(maintenanceNav).exists()).toBe(false)
    await wrapper.setProps({ canMaintain: true })
    expect(wrapper.get('#kb-maintenance-nav-label').text()).toBe('资料维护')
    expect(links(readerNav)).toEqual(reader)
    expect(links(maintenanceNav)).toEqual(maintenance)
    for (const path of maintenance) {
      await router.push(path)
      expect(wrapper.findAll('nav [aria-current="page"]').map(link => link.attributes('href'))).toEqual([path])
    }
    await router.push(reader[0])
    await wrapper.setProps({ maintenance: false })
    expect(links(maintenanceNav)).toEqual(maintenance)
    expect(wrapper.get('nav [aria-current="page"]').attributes('href')).toBe(reader[0])
    await wrapper.setProps({ canMaintain: false })
    expect(wrapper.find(maintenanceNav).exists()).toBe(false)
    expect(links(readerNav)).toEqual(reader)
  } finally {
    wrapper.unmount()
  }
})

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

beforeEach(() => { api.status.mockReset(); ready.value = true; blocked.value = false })

describe('maintenance permission state is not conflated with a 403', () => {
  it('waits for confirmed initial access before mounting a document, then retains it during a background check', async () => {
    api.status.mockResolvedValue({ can_maintain: true })
    ready.value = false; blocked.value = true
    const { wrapper } = await mountAt('/hbos/knowledge')
    try {
      // Bootstrap already supplied the user, but POST reads are still blocked.
      expect(wrapper.find('[data-test="page"]').exists()).toBe(false)
      ready.value = true; blocked.value = false; await flushPromises()
      const page = wrapper.find('[data-test="page"]').element
      blocked.value = true; await flushPromises()
      expect(wrapper.find('[data-test="page"]').element).toBe(page)
      blocked.value = false; await flushPromises()
      expect(wrapper.find('[data-test="page"]').element).toBe(page)
    } finally { wrapper.unmount() }
  })
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
