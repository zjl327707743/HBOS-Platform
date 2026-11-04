import { iamQuery } from './iamAccess'
import type { MyAttendance } from '@/types/iam'
export interface AttendanceQuery { date_from?: string; date_to?: string; page?: number; page_size?: number }
export function attendanceParams(query: AttendanceQuery) {
  if (Object.keys(query).some(key => !['date_from','date_to','page','page_size'].includes(key))) throw new Error('本人考勤不接受人员、部门或任意筛选参数。')
  return { page: 1, page_size: 20, ...query }
}
export const getMyAttendance = (query: AttendanceQuery = {}) => iamQuery<MyAttendance>('hb_attendance_app.hbos_attendance.portal.personal.get_my_attendance', attendanceParams(query))
