import { expect,it,vi,beforeEach } from 'vitest'
vi.mock('@/services/frappeClient',()=>({callFrappeMethod:vi.fn(),callFrappePostMethod:vi.fn()}))
import {callFrappeMethod,callFrappePostMethod} from '@/services/frappeClient'
import {listPeople,linkUser,createEmployee} from '@/services/iamPeople'
beforeEach(()=>vi.resetAllMocks())
it('retains unopened Employee rows and server pagination instead of fabricating User records',async()=>{const result={items:[{id:'EMP-1',employee_number:'00101',user_id:null}],total:1,page:1,page_size:20};vi.mocked(callFrappeMethod).mockResolvedValue({ok:true,data:result});expect(await listPeople()).toEqual(result)})
it('links explicit native keys and ownership evidence with version and idempotency',async()=>{vi.mocked(callFrappePostMethod).mockResolvedValue({ok:true,data:{version:'v2'}});const evidence={employee_number:'00101',company:'Company A',account_user_id:'account-a',reference:'已核对受控归属证明编号ABCDEFG'};await linkUser('EMP-1','account-a',evidence,'v1','request-1');expect(callFrappePostMethod).toHaveBeenCalledWith('hbos_portal.api.iam_people.link_user',{employee_id:'EMP-1',user_id:'account-a',ownership_evidence:evidence,expected_version:'v1',request_id:'request-1'})})
it('does not fill missing birth or joining dates in new employee requests',async()=>{vi.mocked(callFrappePostMethod).mockRejectedValue(new Error('缺生日'));await expect(createEmployee({first_name:'Test'},'meta-v1','r1')).rejects.toThrow('缺生日');expect(callFrappePostMethod).toHaveBeenCalledWith(expect.any(String),{fields:{first_name:'Test'},expected_version:'meta-v1',request_id:'r1'})})
