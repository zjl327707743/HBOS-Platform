import { callFrappeMethod } from '@/services/frappeClient'

const BASE = 'hb_attendance_app.hbos_attendance.page.hbos_employee_management.employee_management_data'

export interface EmployeeRow {
  name: string
  employee_name: string
  employee_number: string
  department: string
  cell_number?: string | null
  image?: string | null
  date_of_joining?: string | null
  hbos_fixed_shift?: string | null
  shift_type?: string | null
  start_time?: string | null
  end_time?: string | null
}

export interface DepartmentCount {
  department: string
  cnt: number
}

export interface ShiftOption {
  name: string
  rule_name: string
  shift_type: string
  start_time: string
  end_time: string
}

export async function fetchEmployees(filters: {
  department?: string
  search?: string
} = {}): Promise<EmployeeRow[]> {
  return callFrappeMethod<EmployeeRow[]>(`${BASE}.get_employees`, filters)
}

export async function fetchDepartments(): Promise<DepartmentCount[]> {
  return callFrappeMethod<DepartmentCount[]>(`${BASE}.get_departments`)
}

export async function fetchShiftOptions(): Promise<ShiftOption[]> {
  return callFrappeMethod<ShiftOption[]>(`${BASE}.get_shift_options`)
}
