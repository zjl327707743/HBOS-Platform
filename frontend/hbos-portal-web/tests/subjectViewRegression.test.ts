import { expect, it, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { defineComponent, ref, nextTick } from 'vue'
import { createRouter, createMemoryHistory } from 'vue-router'
import PortalLayout from '@/components/layout/PortalLayout.vue'
import KnowledgeTwinLayout from '@/components/layout/KnowledgeTwinLayout.vue'
import { usePortalStore } from '@/stores/portal'
const sessionChecking=ref(false)
vi.mock('@/composables/usePortalSession', () => ({usePortalSession: () => ({sessionPending:sessionChecking,sessionError:ref(null)})}))
vi.mock('@/services/p1Api',async original=>({...await original<typeof import('@/services/p1Api')>(),getKnowledgeStatus:async()=>({can_enter:true,can_maintain:false})}))
const SubjectView = defineComponent({setup() { const mountedFor = usePortalStore().user?.id; return {mountedFor} },template:'<p data-test="subject-view">{{mountedFor}}</p>'})
it.each([['Portal',PortalLayout],['Knowledge/Twin',KnowledgeTwinLayout]])('A07: %s remounts route-local evidence when the authenticated user changes', async (_name,Layout) => {
 const pinia=createPinia();setActivePinia(pinia);const portal=usePortalStore()
 portal.user={id:'previous-subject'} as never
 const router=createRouter({history:createMemoryHistory(),routes:[{path:'/hbos/knowledge',component:SubjectView}]})
 await router.push('/hbos/knowledge');await router.isReady()
 const wrapper=mount(Layout,{global:{plugins:[pinia,router],stubs:{GlobalHeader:true,PointerAtmosphere:true,PortalSidebar:true,KnowledgeTwinSidebar:true,KnowledgeHeader:true,KnowledgeSidebar:true,MobilePortalNav:true,CommandPalette:true}}})
 try {
  expect(wrapper.get('[data-test="subject-view"]').text()).toBe('previous-subject')
  portal.user={id:'next-subject'} as never;await nextTick()
  expect(wrapper.get('[data-test="subject-view"]').text()).toBe('next-subject')
 } finally { wrapper.unmount() }
})

it('UAT2 keeps a knowledge draft through session revalidation and clears it on identity change',async()=>{
 const pinia=createPinia();setActivePinia(pinia);const portal=usePortalStore();portal.user={id:'A'} as never
 const Draft=defineComponent({setup(){return {draft:ref('')}},template:'<input v-model="draft" data-draft/>'})
 const router=createRouter({history:createMemoryHistory(),routes:[{path:'/hbos/knowledge',component:Draft}]});await router.push('/hbos/knowledge');await router.isReady()
 const w=mount(KnowledgeTwinLayout,{global:{plugins:[pinia,router],stubs:{KnowledgeHeader:true,KnowledgeSidebar:true,'a-config-provider':{template:'<div><slot/></div>'},'a-skeleton':true}}})
 try{await flushPromises();await w.get('[data-draft]').setValue('中文草稿');sessionChecking.value=true;await nextTick();expect(w.get('[data-draft]').element).toHaveProperty('value','中文草稿');expect(w.get('main').attributes('aria-busy')).toBe('true');sessionChecking.value=false;await flushPromises();expect(w.get('[data-draft]').element).toHaveProperty('value','中文草稿');portal.user={id:'B'} as never;await flushPromises();expect(w.get('[data-draft]').element).toHaveProperty('value','')}finally{sessionChecking.value=false;w.unmount()}
})
