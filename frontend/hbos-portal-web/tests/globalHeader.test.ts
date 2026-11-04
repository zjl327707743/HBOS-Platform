import { defineComponent } from 'vue'
import { flushPromises, mount } from '@vue/test-utils'
import { createMemoryHistory, createRouter } from 'vue-router'
import { createPinia } from 'pinia'
import Antd from 'ant-design-vue'
import { describe, expect, it, vi } from 'vitest'
import GlobalHeader from '@/components/layout/GlobalHeader.vue'

vi.mock('@/services/portalProvider', () => ({ portalDataSource: 'mock' }))

const Dropdown = defineComponent({ template: '<div><slot /><div class="dropdown-overlay"><slot name="overlay" /></div></div>' })
const Menu = defineComponent({ template: '<nav><slot /></nav>' })
const MenuItem = defineComponent({ emits: ['click'], template: '<button type="button" @click="$emit(\'click\')"><slot /></button>' })
const Modal = defineComponent({ template: '<div v-if="$attrs.open"><slot /></div>' })

describe('R6 mobile global navigation', () => {
  it('keeps global search reachable from the management mobile menu', async () => {
    const Placeholder = defineComponent({ template: '<div />' })
    const router = createRouter({ history: createMemoryHistory(), routes: [
      { path: '/hbos', component: Placeholder },
      { path: '/hbos/work', component: Placeholder },
      { path: '/hbos/apps', component: Placeholder },
    ] })
    await router.push('/hbos')
    await router.isReady()
    const wrapper = mount(GlobalHeader, {
      props: { avatarText: 'HB', apps: [], managementExperience: true },
      global: { plugins: [router, createPinia(), Antd], stubs: { AppSwitcher: true, NotificationCenter: true, 'a-dropdown': Dropdown, 'a-menu': Menu, 'a-menu-item': MenuItem, 'a-menu-divider': true, 'a-modal': Modal } },
    })
    const search = wrapper.findAll('button').find(button => button.text().trim() === '搜索')
    expect(search).toBeDefined()
    await search!.trigger('click')
    await flushPromises()
    expect(wrapper.emitted('open-command')).toHaveLength(1)
    wrapper.unmount()
  })
})
