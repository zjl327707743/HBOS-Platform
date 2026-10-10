import { expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { defineComponent, ref, nextTick } from 'vue'
import { createRouter, createMemoryHistory } from 'vue-router'
import PortalLayout from '@/components/layout/PortalLayout.vue'
import KnowledgeTwinLayout from '@/components/layout/KnowledgeTwinLayout.vue'
import { usePortalStore } from '@/stores/portal'
vi.mock('@/composables/usePortalSession', () => ({usePortalSession: () => ({sessionPending:ref(false),sessionError:ref(null)})}))
const SubjectView = defineComponent({setup() { const mountedFor = usePortalStore().user?.id; return {mountedFor} },template:'<p data-test="subject-view">{{mountedFor}}</p>'})
it.each([['Portal',PortalLayout],['Knowledge/Twin',KnowledgeTwinLayout]])('A07: %s remounts route-local evidence when the authenticated user changes', async (_name,Layout) => {
 const pinia=createPinia();setActivePinia(pinia);const portal=usePortalStore()
 portal.user={id:'previous-subject'} as never
 const router=createRouter({history:createMemoryHistory(),routes:[{path:'/hbos/knowledge',component:SubjectView}]})
 await router.push('/hbos/knowledge');await router.isReady()
 const wrapper=mount(Layout,{global:{plugins:[pinia,router],stubs:{GlobalHeader:true,PointerAtmosphere:true,PortalSidebar:true,KnowledgeTwinSidebar:true,MobilePortalNav:true,CommandPalette:true}}})
 try {
  expect(wrapper.get('[data-test="subject-view"]').text()).toBe('previous-subject')
  portal.user={id:'next-subject'} as never;await nextTick()
  expect(wrapper.get('[data-test="subject-view"]').text()).toBe('next-subject')
 } finally { wrapper.unmount() }
})
