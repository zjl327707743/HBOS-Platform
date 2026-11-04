import { callFrappeMethod, callFrappePostMethod } from './frappeClient'
const base='hb_attendance_app.hbos_attendance.page.hbos_shift_management.shift_management_data.'
export interface ShiftRule {name:string;rule_code:string;rule_name:string;department:string;shift_type:string;start_time:string;end_time:string;late_after:string;min_hours:number;effective_from:string;status:string;supersedes?:string;is_latest:number}
export interface ShiftEmployee {name:string;employee_name:string;employee_number:string;system_shift:string}
export interface ShiftOverview {departments:string[];shift_types:string[];rules:ShiftRule[];bindable_rules:ShiftRule[]}
export const shiftOverview=()=>callFrappeMethod<ShiftOverview>(base+'get_shift_overview')
export const shiftEmployees=(department:string)=>callFrappeMethod<ShiftEmployee[]>(base+'get_department_employees',{department})
export const boundShifts=(employee:string)=>callFrappeMethod<string[]>(base+'get_employee_bound_shifts',{employee})
export const shiftCommand=(method:string,params:Record<string,unknown>)=>callFrappePostMethod<Record<string,unknown>>(base+method,params)
