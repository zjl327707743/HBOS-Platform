import { iamCommand, iamQuery } from './iamAccess'
const base='hb_attendance_app.hbos_attendance.portal.calculations.'
export interface CalculationEmployee {name:string;employee_name:string;employee_number:string;department:string}
export interface CalculationPreview {scope:string;employees:{name:string;employee_name:string}[];date_from:string;date_to:string;expected_inputs:string;warning:string}
export interface AttendancePolicy {name:string;employee:string;modified:string;policy_type:string;effective_from:string;effective_to:string|null;enabled:number;anchor_shift:string;group_name:string;remarks:string}
export const calculationEmployees=(action:string,search:string)=>iamQuery<{scope:string;items:CalculationEmployee[]}>(base+'calculation_employees',{action,search})
export const previewCalculation=(params:Record<string,unknown>)=>iamQuery<CalculationPreview>(base+'preview_calculation',params)
export const executeCalculation=(params:Record<string,unknown>)=>iamCommand<Record<string,unknown>>(base+'execute_calculation',params)
export const getEmployeePolicies=(employee:string)=>iamQuery<{items:AttendancePolicy[];policy_types:string[]}>(base+'get_employee_policies',{employee})
export const saveEmployeePolicy=(params:Record<string,unknown>)=>iamCommand<{name:string}>(base+'save_employee_policy',params)
