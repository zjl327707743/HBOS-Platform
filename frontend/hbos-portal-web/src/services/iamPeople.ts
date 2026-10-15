import { iamCommand, iamQuery, IamError } from './iamAccess'
import type { EmployeeSummary, EmployeeDetail, EmployeeMetadata, PageResult, OwnershipEvidence, PersonResult } from '@/types/iam'
const prefix = 'hbos_portal.api.iam_people.'
export interface PeopleQuery { page?: number; page_size?: number; search?: string; department?: string; account_status?: string; category?: string }
export async function listPeople(query: PeopleQuery = {}) {
  const data = await iamQuery<PageResult<EmployeeSummary>>(prefix + 'list_people', { page: 1, page_size: 20, ...query })
  if (!Array.isArray(data.items) || !Number.isInteger(data.total) || data.total < 0) throw new IamError('人员列表格式无法确认。')
  return data
}
export const getPerson = (employee_id: string) => iamQuery<EmployeeDetail>(prefix + 'get_person', { employee_id })
export const getEmployeeMetadata = () => iamQuery<EmployeeMetadata>(prefix + 'get_employee_metadata')
export async function previewLink(employee_id: string, user_id: string, ownership_evidence: OwnershipEvidence) { const data=await iamCommand<{summary?:string;version:string}>(prefix+'preview_link',{employee_id,user_id,ownership_evidence});if(typeof data.version!=='string'||!data.version)throw new IamError('账号关联预览版本无法确认，请重新核验。');return data }
export const linkUser = (employee_id: string, user_id: string, ownership_evidence: OwnershipEvidence, expected_version: string, request_id: string) => iamCommand<PersonResult>(prefix + 'link_user', { employee_id, user_id, ownership_evidence, expected_version, request_id })
export const createUser = (employee_id: string, ownership_evidence: OwnershipEvidence, expected_version: string, request_id: string) => iamCommand<PersonResult>(prefix + 'create_user', { employee_id, ownership_evidence, expected_version, request_id })
export const createEmployee = (fields: Record<string, unknown>, expected_version: string, request_id: string) => iamCommand<PersonResult>(prefix + 'create_employee', { fields, expected_version, request_id })
export const transferEmployee = (employee_id: string, department: string, expected_version: string, request_id: string) => iamCommand<PersonResult>(prefix + 'transfer_employee', { employee_id, department, expected_version, request_id })
export const disableUser = (employee_id: string, expected_version: string, request_id: string) => iamCommand<PersonResult>(prefix + 'disable_user', { employee_id, expected_version, request_id })
export const resetTemporaryPassword = (employee_id: string, expected_version: string, request_id: string) => iamCommand<PersonResult>(prefix + 'reset_temporary_password', { employee_id, expected_version, request_id })
