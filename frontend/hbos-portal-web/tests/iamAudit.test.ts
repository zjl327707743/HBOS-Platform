import {expect,it,vi} from 'vitest'
vi.mock('@/services/frappeClient',()=>({callFrappeMethod:vi.fn(),callFrappePostMethod:vi.fn()}))
import {callFrappeMethod} from '@/services/frappeClient'
import {listAuditEvents} from '@/services/iamAudit'
it('uses the separately authorised audit endpoint and bounded pagination',async()=>{vi.mocked(callFrappeMethod).mockResolvedValue({ok:true,data:{items:[],total:0,page:2,page_size:20}});expect((await listAuditEvents(2)).total).toBe(0);expect(callFrappeMethod).toHaveBeenCalledWith('hbos_portal.api.iam_audit.list_events',{page:2,page_size:20})})
it('surfaces denied audit access rather than deriving it from people access',async()=>{vi.mocked(callFrappeMethod).mockResolvedValue({ok:false,error:{code:'FORBIDDEN',message:'审计未授权'}});await expect(listAuditEvents()).rejects.toThrow('审计未授权')})

it('passes exact subject filters to the server rather than filtering only the current page', async()=>{vi.mocked(callFrappeMethod).mockResolvedValue({ok:true,data:{items:[],total:0,page:1,page_size:20}});await listAuditEvents(1,20,{subject_type:'Employee',subject_name:'EMP-1'});expect(callFrappeMethod).toHaveBeenLastCalledWith('hbos_portal.api.iam_audit.list_events',{page:1,page_size:20,subject_type:'Employee',subject_name:'EMP-1'})})
it('rejects incomplete subject filters before making a server request', async()=>{vi.mocked(callFrappeMethod).mockClear();await expect(listAuditEvents(1,20,{subject_type:'Employee'})).rejects.toThrow('同时');expect(callFrappeMethod).not.toHaveBeenCalled()})
