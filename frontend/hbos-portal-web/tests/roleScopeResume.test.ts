import { beforeEach, describe, expect, it, vi } from 'vitest'
import { defineComponent, h, ref } from 'vue'
import { flushPromises, mount } from '@vue/test-utils'
import SessionContent from '@/components/layout/SessionContent.vue'
import RoleSettings from '@/components/iam/RoleSettings.vue'

const api=vi.hoisted(()=>({query:vi.fn(),command:vi.fn()}))
vi.mock('@/services/iamRoles',()=>({roleQuery:api.query,roleCommand:api.command,assertRolePreview:(value:unknown)=>value}))
vi.mock('@/services/iamAccess',()=>({canIam:()=>true,iamMessage:(error:Error)=>error.message}))
vi.mock('@/services/iamDepartments',()=>({listDepartments:async()=>({items:[],companies:[]})}))
vi.mock('@/composables/useAccountProof',()=>({useAccountProof:()=>({valid:ref(false),sync:vi.fn(),invalidate:vi.fn()})}))
const Select=defineComponent({props:['value'],emits:['update:value','change'],template:'<select :value="value" @change="$emit(\'update:value\',$event.target.value);$emit(\'change\',$event.target.value)"><slot/></select>'})
const Option=defineComponent({props:['value','disabled'],template:'<option :value="value" :disabled="disabled"><slot/></option>'})
const Button=defineComponent({props:['disabled'],template:'<button type="button" :disabled="disabled"><slot/></button>'})
const stubs={'a-select':Select,'a-select-option':Option,'a-button':Button,'a-form':{template:'<form><slot/></form>'},'a-form-item':{template:'<div><slot/></div>'},'a-skeleton':true,'a-alert':true,OwnAccountVerification:true,RouterLink:true}

describe('Role source and authorization changes',()=>{
  beforeEach(()=>{vi.clearAllMocks()})

  it('preserves the same-subject draft through rechecks, then removes old scope content on a policy change',async()=>{
    const Draft=defineComponent({setup(){const value=ref('');return()=>h('input',{value:value.value,onInput:(event:Event)=>value.value=(event.target as HTMLInputElement).value})}})
    const wrapper=mount(SessionContent,{props:{pending:false,ready:true,blocked:false,generation:'1:scope-A'},slots:{default:()=>h(Draft)},global:{stubs}})
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
    const wrapper=mount(RoleSettings,{props:{subjectKind:'department',subjectId:'D1'},global:{stubs}})
    await flushPromises()
    expect(wrapper.text()).toContain('沿用已有安排')
    await wrapper.findAll('button').find(row=>row.text()==='调整默认角色')!.trigger('click')
    expect(wrapper.get('select').element.value).toBe('LEGACY')
    await wrapper.get('select').setValue('')
    expect(wrapper.findAll('button').find(row=>row.text()==='核对实际结果')!.attributes('disabled')).toBeUndefined()
    await wrapper.findAll('button').find(row=>row.text()==='取消修改')!.trigger('click')
    expect(api.command).not.toHaveBeenCalled()
    wrapper.unmount()
  })

  it('keeps an explicit follow-department draft on focus without replacing a legacy personal source',async()=>{
    api.query.mockResolvedValue({version:0,mode:'LEGACY',role_key:'',responsibilities:[],effective_access:{allowed:true,reason:'沿用已有权限安排。',operations:[]}})
    const wrapper=mount(RoleSettings,{props:{subjectKind:'employee',subjectId:'E1'},global:{stubs}})
    await flushPromises()
    expect(wrapper.text()).toContain('沿用已有独立安排')
    await wrapper.findAll('button').find(row=>row.text()==='设置角色与范围')!.trigger('click')
    await wrapper.get('select').setValue('FOLLOW_DEPARTMENT')
    window.dispatchEvent(new Event('focus'));await flushPromises()
    expect(wrapper.get('select').element.value).toBe('FOLLOW_DEPARTMENT')
    expect(api.query).toHaveBeenCalledTimes(1)
    expect(api.command).not.toHaveBeenCalled()
    wrapper.unmount()
  })
})
