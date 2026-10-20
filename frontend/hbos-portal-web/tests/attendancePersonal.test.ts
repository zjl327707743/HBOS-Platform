import {expect,it,vi} from 'vitest'
vi.mock('@/services/frappeClient',()=>({callFrappeMethod:vi.fn(),callFrappePostMethod:vi.fn()}))
import {callFrappeMethod} from '@/services/frappeClient'
import {attendanceParams,getMyAttendance} from '@/services/attendancePersonal'
it.each(['employee','user','department','filters'])('rejects a %s override instead of changing the actor',(key)=>{expect(()=>attendanceParams({[key]:'another-person'} as never)).toThrow()})
it('requests only current-session attendance and keeps server totals',async()=>{const data={rows:[{id:'checkin-a',date:'2026-10-01'}],total:1,page:1,page_size:20,summary:{records:1,days:1}};vi.mocked(callFrappeMethod).mockResolvedValue({ok:true,data});expect(await getMyAttendance({date_from:'2026-10-01'})).toEqual(data);expect(callFrappeMethod).toHaveBeenCalledWith('hb_attendance_app.hbos_attendance.portal.personal.get_my_attendance',{date_from:'2026-10-01',page:1,page_size:20})})
