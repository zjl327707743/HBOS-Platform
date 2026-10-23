import {expect,it,vi} from 'vitest'
vi.mock('@/services/frappeClient',()=>({callFrappeMethod:vi.fn(),callFrappePostMethod:vi.fn()}))
import {callFrappeMethod} from '@/services/frappeClient'
import {listAuditEvents} from '@/services/iamAudit'
it('uses the separately authorised audit endpoint and bounded pagination',async()=>{vi.mocked(callFrappeMethod).mockResolvedValue({ok:true,data:{items:[],total:0,page:2,page_size:20}});expect((await listAuditEvents(2)).total).toBe(0);expect(callFrappeMethod).toHaveBeenCalledWith('hbos_portal.api.iam_audit.list_events',{page:2,page_size:20})})
it('surfaces denied audit access rather than deriving it from people access',async()=>{vi.mocked(callFrappeMethod).mockResolvedValue({ok:false,error:{code:'FORBIDDEN',message:'审计未授权'}});await expect(listAuditEvents()).rejects.toThrow('审计未授权')})
