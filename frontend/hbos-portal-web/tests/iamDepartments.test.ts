import {expect,it,vi,beforeEach} from 'vitest'
vi.mock('@/services/frappeClient',()=>({callFrappeMethod:vi.fn(),callFrappePostMethod:vi.fn()}))
import {callFrappeMethod} from '@/services/frappeClient'
import {listDepartments} from '@/services/iamDepartments'
beforeEach(()=>vi.resetAllMocks())
it('preserves native keys and an unconfirmed department as unconfirmed',async()=>{const data={items:[{id:'Quality - C',name:'Quality',confirmed:false}],companies:[]};vi.mocked(callFrappeMethod).mockResolvedValue({ok:true,data});expect((await listDepartments()).items[0]).toEqual(data.items[0]);expect(callFrappeMethod).toHaveBeenCalledWith('hbos_portal.api.iam_departments.list_departments',{view_group:'daily'})})
it('rejects an unrecognised department response instead of presenting an empty success',async()=>{vi.mocked(callFrappeMethod).mockResolvedValue({ok:true,data:{departments:[]}});await expect(listDepartments()).rejects.toThrow()})
