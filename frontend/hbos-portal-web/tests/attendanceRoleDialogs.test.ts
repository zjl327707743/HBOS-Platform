import { describe, expect, it } from 'vitest'
import { defineComponent, h, ref } from 'vue'
import { flushPromises, mount } from '@vue/test-utils'
import { Modal } from 'ant-design-vue'
import SessionContent from '@/components/layout/SessionContent.vue'

describe('Attendance role dialogs share the protected session subtree',()=>{
  it('hides a draft during revalidation, restores it for the same scope and discards it for a changed scope',async()=>{
    const Draft=defineComponent({setup(){const text=ref('');return()=>h(Modal,{open:true,getContainer:false,footer:null},{default:()=>h('input',{'aria-label':'bounded draft',value:text.value,onInput:(event:Event)=>text.value=(event.target as HTMLInputElement).value})})}})
    const wrapper=mount(SessionContent,{attachTo:document.body,props:{pending:false,blocked:false,ready:true,generation:'same-user:company-A'},slots:{default:()=>h(Draft)},global:{stubs:{'a-alert':true,'a-button':true,RouterLink:true}}})
    await flushPromises()
    const input=wrapper.get('input[aria-label="bounded draft"]')
    await input.setValue('unsaved business explanation')
    await wrapper.setProps({blocked:true})
    expect(wrapper.get('input').element.closest('[inert]')).not.toBeNull()
    expect(wrapper.get('input').element.closest('[aria-hidden="true"]')).not.toBeNull()
    await wrapper.setProps({blocked:false})
    expect(wrapper.get('input').element.value).toBe('unsaved business explanation')
    await wrapper.setProps({generation:'same-user:company-B'})
    await flushPromises()
    expect(wrapper.get('input').element.value).toBe('')
    wrapper.unmount()
  })
})
