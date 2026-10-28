import { beforeEach, describe, expect, it, vi } from 'vitest'
import { defineComponent, h, ref } from 'vue'
import { flushPromises, mount } from '@vue/test-utils'
import Antd from 'ant-design-vue'
import SessionContent from '@/components/layout/SessionContent.vue'
import RoleSettings from '@/components/iam/RoleSettings.vue'

const api=vi.hoisted(()=>({query:vi.fn(),command:vi.fn()}))
vi.mock('@/services/iamRoles',()=>({roleQuery:api.query,roleCommand:api.command,assertRolePreview:(value:unknown)=>value}))
vi.mock('@/services/iamAccess',()=>({canIam:()=>true,iamMessage:(error:Error)=>error.message,iamSession:{rolesEnabled:true}}))
vi.mock('@/services/iamDepartments',()=>({listDepartments:async()=>({items:[],companies:[]})}))
vi.mock('@/composables/useAccountProof',async()=>{const {ref}=await import('vue');return {useAccountProof:()=>({valid:ref(false),method:ref('password'),sync:vi.fn(),invalidate:vi.fn()})}})
const Select=defineComponent({props:['value'],emits:['update:value','change'],template:'<select :value="value" @change="$emit(\'update:value\',$event.target.value);$emit(\'change\',$event.target.value)"><slot/></select>'})
const Option=defineComponent({props:['value','disabled'],template:'<option :value="value" :disabled="disabled"><slot/></option>'})
const Button=defineComponent({props:['disabled'],template:'<button type="button" :disabled="disabled"><slot/></button>'})
const stubs={'a-select':Select,'a-select-option':Option,'a-button':Button,'a-form':{template:'<form><slot/></form>'},'a-form-item':{template:'<div><slot/></div>'},'a-skeleton':true,'a-alert':true,OwnAccountVerification:true,RouterLink:true}

describe('Role source and authorization changes',()=>{
  beforeEach(()=>{vi.clearAllMocks()})

  it('preserves the same-subject draft through rechecks, then removes old scope content on a policy change',async()=>{
    const Draft=defineComponent({setup(){const value=ref('');return()=>h('input',{value:value.value,onInput:(event:Event)=>value.value=(event.target as HTMLInputElement).value})}})
    const wrapper=mount(SessionContent,{props:{pending:false,ready:true,blocked:false,generation:'1:scope-A'},slots:{default:()=>h(Draft)},global:{plugins:[Antd],stubs}})
    await wrapper.get('input').setValue('company A unsaved draft')
    await wrapper.setProps({blocked:true})
    await wrapper.setProps({blocked:false})
    expect(wrapper.get('input').element.value).toBe('company A unsaved draft')
    await wrapper.setProps({generation:'1:scope-B'})
    expect(wrapper.get('input').element.value).toBe('')
    wrapper.unmount()
  })

  it('distinguishes an unset department source from an explicit no-default choice',async()=>{
    api.query.mockResolvedValue({version:0,role_key:'',has_role_default:false})
    const wrapper=mount(RoleSettings,{props:{subjectKind:'department',subjectId:'D1'},global:{plugins:[Antd],stubs}})
    await flushPromises()
    expect(wrapper.text()).toContain('沿用已有安排')
    expect(wrapper.text()).toContain('当前状态：沿用已有考勤权限')
    expect(wrapper.text()).toContain('不会自动转换')
    expect(wrapper.find('input[type=radio][value="LEGACY"]').exists()).toBe(false)
    expect((wrapper.get('input[type=radio][value=""]').element as HTMLInputElement).checked).toBe(false)
    await wrapper.get('input[type=radio][value=""]').setValue(true)
    expect(wrapper.findAll('button').find(row=>row.text()==='预览影响')!.attributes('disabled')).toBeUndefined()
    await wrapper.findAll('button').find(row=>row.text()==='取消修改')!.trigger('click')
    expect(api.command).not.toHaveBeenCalled()
    wrapper.unmount()
  })

  it('keeps an explicit follow-department draft on focus without replacing a legacy personal source',async()=>{
    api.query.mockResolvedValue({version:0,mode:'LEGACY',role_key:'',responsibilities:[],effective_access:{allowed:true,reason:'沿用已有权限安排。',operations:[]}})
    const wrapper=mount(RoleSettings,{props:{subjectKind:'employee',subjectId:'E1'},global:{plugins:[Antd],stubs}})
    await flushPromises()
    expect(wrapper.text()).toContain('沿用已有独立安排')
    await wrapper.get('input[type=radio][value="FOLLOW_DEPARTMENT"]').setValue(true)
    window.dispatchEvent(new Event('focus'));await flushPromises()
    expect((wrapper.get('input[type=radio][value="FOLLOW_DEPARTMENT"]').element as HTMLInputElement).checked).toBe(true)
    expect(api.query).toHaveBeenCalledTimes(1)
    expect(api.command).not.toHaveBeenCalled()
    wrapper.unmount()
  })
})
