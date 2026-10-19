import { iamQuery, IamError } from './iamAccess'
import type { DepartmentSummary } from '@/types/iam'
export async function listDepartments(view_group='daily', target_department?:string, company?:string) {
  const data = await iamQuery<{groups_available?:boolean;selected_company?:string;items: DepartmentSummary[]; companies: Array<{id: string; name: string}>}>('hbos_portal.api.iam_departments.list_departments', {view_group,...(target_department ? {target_department} : {}),...(company ? {company} : {})})
  if (!Array.isArray(data.items)) throw new IamError('部门列表格式无法确认。')
  return data
}
