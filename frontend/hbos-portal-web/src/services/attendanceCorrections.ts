import { iamCommand, iamQuery } from './iamAccess'
export interface CorrectionEmployee {name:string;employee_name:string;employee_number:string;department:string;modified:string}
export interface Correction {name:string;employee:string;from_date:string;to_date:string;reason:string;explanation:string;docstatus:number;modified:string;half_day:number;half_day_date:string|null;include_holidays:number;shift:string|null;amended_from?:string|null}
export type CorrectionAction='create'|'submit'|'cancel'|'amend'
export interface CorrectionContext {employee:CorrectionEmployee;request:Correction|null}
const base='hb_attendance_app.hbos_attendance.portal.corrections.'
export const correctionEmployees=(action:CorrectionAction,search:string)=>iamQuery<{items:CorrectionEmployee[]}>(base+'list_correction_employees',{action,search})
export const correctionList=(employee:string,action:CorrectionAction)=>iamQuery<{items:Correction[]}>(base+'list_corrections',{employee,action})
export const correctionContext=(employee:string,action:CorrectionAction,request_name?:string)=>iamQuery<CorrectionContext>(base+'get_correction_context',{employee,action,...(request_name?{request_name}:{})})
export const createCorrection=(employee:string,expected_employee_version:string,settings:Record<string,unknown>,request_id:string)=>iamCommand<{name:string;docstatus:number}>(base+'create_correction',{employee,expected_employee_version,settings,request_id})
export const updateCorrection=(request_name:string,settings:Record<string,unknown>,expected_version:string,request_id:string)=>iamCommand<{name:string;docstatus:number}>(base+'update_correction',{request_name,settings,expected_version,request_id})
export const transitionCorrection=(request_name:string,action:CorrectionAction,expected_version:string,request_id:string)=>iamCommand<{name:string;docstatus:number}>(base+'transition_correction',{request_name,action,expected_version,request_id})
