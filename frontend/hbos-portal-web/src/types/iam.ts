export interface PageResult<T> { groups_available?: boolean; items: T[]; total: number; page: number; page_size: number }
export interface EmployeeSummary {
  verification_group?: 'daily'|'technical'
  id: string; name: string; employee_number: string; department: string; department_name: string
  company: string; position: string; user_id: string | null; account_status: 'active' | 'unopened' | 'disabled'
  attendance_status: 'confirmed' | 'pending'; version: string
}
export interface EmployeeDetail {
  configuration_only?: boolean
  employee: EmployeeSummary
  account: { user_id: string | null; username?: string; enabled?: boolean; feishu_bound?: boolean; initial_password_pending?: boolean; proposed_user_id?: string }
  association: { employee_id: string; user_id: string | null; attendance_identifier?: string | null }
  history: Array<{ operation?: string; occurred_at?: string; reason?: string }>
}
export interface SelectOption { value: string; label: string; company?: string }
export interface EmployeeMetadata {
  version: string
  required_fields: Array<{ fieldname: string; label: string; fieldtype: string; options?: string }>
  companies: SelectOption[]; departments: SelectOption[]; genders: SelectOption[]
}
export interface OwnershipEvidence { employee_number: string; company: string; account_user_id: string; reference: string }
export interface PersonResult { employee: EmployeeSummary; version: string; replayed?: boolean; temporary_password?: string }
export interface DepartmentSummary {
  id: string; name: string; parent_department?: string | null; company: string; confirmed: boolean; version?: string
  members?: EmployeeSummary[]
}
export interface AuditEvent { name?: string; actor: string; operation: string; subject_name: string; result: string; reason?: string; occurred_at: string }
export interface WorkScope { scope_type: string; scope_ref: string; label?: string }
export interface WorkOperation {
  available?: boolean
  operation_id: string; label: string; enabled: boolean; scopes: WorkScope[]; source_text: string
  editable: boolean; important?: boolean; reason?: string; objects?: WorkScope[]
}
export interface WorkApp {
  department_default?: { id: string; name: string; enabled: boolean; suspended: boolean; can_open: boolean }
  permission_mode?: 'department' | 'personal'
  synthetic?: boolean
  app_id: string; title: string; integrated: boolean; status: string; summary: string; source_text: string
  operations: WorkOperation[]; version: number; context_revision: string; suspended?: boolean; objects?: WorkScope[]
}
export interface AppSettings { access_state: 'normal' | 'paused'; permission_mode: 'department' | 'personal'; changes: WorkChange[] }
export interface WorkSummary { subject_type: 'User' | 'Department'; subject_name: string; employee_id?: string; apps: WorkApp[] }
export interface WorkChange { operation_id: string; enabled: boolean; scopes: WorkScope[] }
export interface WorkTarget { subject_type: 'User' | 'Department'; subject_name: string; app_id: string; employee_id?: string }
export interface WorkPreview { version: number; context_revision: string; changed: boolean; summary: string; after: WorkApp; impact?: { changed: number; personal_preserved: number; unavailable: number; employees: Array<{ name: string; result?:string; before?: string; after?: string; personal_preserved?: boolean }> }; warnings?: string[] }
export interface AttendanceRow { source?: 'Attendance' | 'Employee Checkin' | string; id: string; date: string; time?: string; log_type?: string; status?: string }
export interface MyAttendance { rows: AttendanceRow[]; total: number; page: number; page_size: number; date_from?: string; date_to?: string; site_today?: string; site_timezone?: string; summary: { records: number; days: number } }
