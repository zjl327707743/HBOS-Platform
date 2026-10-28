import {expect,it,vi,beforeEach} from 'vitest'
vi.mock('@/services/frappeClient',()=>({callFrappeMethod:vi.fn(),callFrappePostMethod:vi.fn()}))
import {callFrappeMethod,callFrappePostMethod} from '@/services/frappeClient'
import {changedWork,projectWork,saveWork,savedWorkResult,getWorkSubject,getWorkSummary,getDepartmentWork,type EffectiveWork,type RegisteredApp} from '@/services/iamWork'
const meta:RegisteredApp={id:'attendance',title:'考勤',integrated:true,operations:[{id:'read',title:'本人考勤',ordinary:true,scope_types:['SELF'],objects:[{scope_type:'SELF',scope_ref:'',label:'本人'}]},{id:'export',title:'导出',ordinary:true,scope_types:[],objects:[]}]}
const raw:EffectiveWork={subject_type:'User',subject_name:'user-a',app_id:'attendance',version:1,context_revision:'ctx',suspended:false,summary:'只能看本人',operations:[{operation_id:'read',label:'查看本人考勤',available:true,allowed:true,scopes:[{scope_type:'SELF',scope_ref:''}],source:'部门安排'},{operation_id:'export',label:'导出',available:false,allowed:false,scopes:[],source:'未接入'}]}
beforeEach(()=>vi.resetAllMocks())
it('never exposes unintegrated or unavailable operations as editable',()=>{expect(projectWork(raw,meta).operations[1]?.editable).toBe(false);expect(projectWork(raw,{...meta,integrated:false}).operations[0]?.editable).toBe(false)})
it('preserves exact scope pairs and source instead of expanding an action cross product',()=>{const app=projectWork(raw,meta);expect(app.operations[0]?.scopes).toEqual([{scope_type:'SELF',scope_ref:'',label:'本人'}]);expect(app.operations[0]?.source_text).toBe('来自所属部门')})
it('no-op produces no personal operation changes',()=>{const original=[{operation_id:'read',enabled:true,scopes:[{scope_type:'SELF',scope_ref:''}]}];expect(changedWork(original,structuredClone(original))).toEqual([])})
it('scope order alone is a no-op and complex saved rules remain read-only',()=>{const scopes=[{scope_type:'WAREHOUSE',scope_ref:'A'},{scope_type:'WAREHOUSE',scope_ref:'B'}];expect(changedWork([{operation_id:'view',enabled:true,scopes}],[{operation_id:'view',enabled:true,scopes:[...scopes].reverse()}])).toEqual([]);expect(projectWork({...raw,operations:[{...raw.operations[0]!,editable:false}]},meta).operations[0]?.editable).toBe(false)})
it('renders committed server results and versions instead of keeping a local success projection',()=>{const result=savedWorkResult({...raw,version:2,summary:'服务端已确认未安排',operations:[{...raw.operations[0]!,allowed:false,scopes:[]}]},projectWork(raw,meta),{subject_type:'User',subject_name:'user-a',app_id:'attendance'});expect(result.version).toBe(2);expect(result.summary).toBe('服务端已确认未安排');expect(result.operations[0]?.enabled).toBe(false);expect(()=>savedWorkResult({...raw,subject_name:'other'},projectWork(raw,meta),{subject_type:'User',subject_name:'user-a',app_id:'attendance'})).toThrow()})
it('uses minimal configuration subjects without a people detail or actor override',async()=>{const data={employee:{id:'EMP-1'},account:{status:'active',user_id:'user-a'},association:{status:'linked'},configuration_only:true};vi.mocked(callFrappeMethod).mockResolvedValue({ok:true,data});expect(await getWorkSubject('EMP-1','attendance')).toEqual(data);expect(callFrappeMethod).toHaveBeenCalledWith('hbos_portal.api.iam_access.get_work_subject',{employee_id:'EMP-1',app_id:'attendance'})})
it('submits only touched operations and the preview revision, and preserves a conflict failure',async()=>{vi.mocked(callFrappePostMethod).mockRejectedValue(Object.assign(new Error('conflict'),{status:409}));const draft={target:{subject_type:'User' as const,subject_name:'user-a',app_id:'attendance'},changes:[{operation_id:'read',enabled:false,scopes:[]}],expected_version:1,context_revision:'old'};await expect(saveWork(draft,{version:2,context_revision:'preview',changed:true,summary:'',after:projectWork(raw,meta)},'r1')).rejects.toThrow('conflict');expect(callFrappePostMethod).toHaveBeenCalledWith('hbos_portal.api.iam_access.save_work',{...draft.target,changes:draft.changes,expected_version:2,context_revision:'preview',request_id:'r1'})})
it('shows an enabled isolated synthetic app while default-off remains hidden and inventory stays unintegrated',async()=>{
  let enabled=false
  vi.mocked(callFrappeMethod).mockImplementation(async(method,params)=>{
    if(method.endsWith('get_work_subject'))return {ok:true,data:{employee:{id:'EMP-1',user_id:'user-a'},account:{user_id:'user-a',status:'active'},association:{status:'linked'},configuration_only:true}}
    if(method.endsWith('get_registered_apps'))return {ok:true,data:{apps:[meta,{id:'inventory',title:'库存管理',integrated:false,operations:[]},{id:'iam_demo',title:'合成扩展验证',integrated:enabled,synthetic:true,operations:[]}]}}
    if(method.endsWith('get_effective_access'))return {ok:true,data:{...raw,app_id:params?.app_id,operations:params?.app_id==='attendance'?raw.operations:[]}}
    throw new Error('unexpected request')
  })
  const defaultOff=await getWorkSummary('EMP-1')
  expect(defaultOff.apps.map(app=>app.app_id)).toEqual(['attendance','inventory'])
  expect(defaultOff.apps.find(app=>app.app_id==='inventory')?.integrated).toBe(false)
  enabled=true
  const isolatedOn=await getWorkSummary('EMP-1')
  expect(isolatedOn.apps.find(app=>app.app_id==='iam_demo')).toMatchObject({title:'合成扩展验证',integrated:true,synthetic:true})
  expect(isolatedOn.apps.find(app=>app.app_id==='inventory')?.integrated).toBe(false)
})
it('reads department app summaries one at a time so auth checks do not collide',async()=>{
  const apps=[meta,{...meta,id:'inventory',title:'库存',integrated:false}]
  let active=0,maxActive=0
  const track=async(data:unknown)=>{active++;maxActive=Math.max(maxActive,active);await new Promise(resolve=>setTimeout(resolve,0));active--;return {ok:true,data}}
  vi.mocked(callFrappeMethod).mockImplementation(async(method,params)=>{
    if(method.endsWith('get_registered_apps'))return track({apps})
    if(method.endsWith('get_effective_access')){
      return track({...raw,subject_type:'Department',subject_name:'D1',app_id:params?.app_id})
    }
    throw new Error(`unexpected request: ${method}`)
  })
  const results=await Promise.all([getDepartmentWork('D1'),getDepartmentWork('D1')])
  expect(results.map(result=>result.apps.map(app=>app.app_id))).toEqual([['attendance','inventory'],['attendance','inventory']])
  expect(maxActive).toBe(1)
})
