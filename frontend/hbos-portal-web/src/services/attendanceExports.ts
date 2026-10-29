import { iamCommand } from './iamAccess'
export interface AttendanceExport {event_name:string;file_id:string;download_url:string;scope:string;date_from:string;date_to:string;coverage:{complete:boolean}}
export const createAttendanceExport=(kind:string,filters:Record<string,string>,request_id:string)=>iamCommand<AttendanceExport>('hb_attendance_app.hbos_attendance.portal.scoped_exports.create_export',{kind,filters,request_id})
