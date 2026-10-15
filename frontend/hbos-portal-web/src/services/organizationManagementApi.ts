import { callFrappeMethod, PortalMethodError, unwrapPortalMethod, type PortalMethodEnvelope } from '@/services/frappeClient'

export type ManagementReadOperation = 'hbos.organization.position.read' | 'hbos.organization.assignment.read' | 'hbos.organization.person.lookup'
export type ManagedFactStatus = 'active' | 'inactive' | 'revoked'
export interface ManagementReadFlags {
  read_only: true
  runtime_verified: false
  authorization_effect: 'none'
  position_authorization_connected: false
}
export interface ManagementPersonScope { source_type: 'Employee'; company_id: string; department_ids: string[] }
export interface ManagementReadScope {
  operation_id: ManagementReadOperation
  operation_schema_version: 1
  company_id: string
  target_department_ids: string[]
  include_children: false
  person_scope: ManagementPersonScope | null
}
export interface ManagementContext extends ManagementReadFlags { operation_ids: ManagementReadOperation[]; scopes: ManagementReadScope[] }
export interface ManagedPosition {
  record_id: string; title: string; company_id: string; department_id: string
  designation_id: string | null; status: ManagedFactStatus; revision: number
}
export interface ManagedPersonAssignment {
  record_id: string; position_id: string; person_source_id: string; status: ManagedFactStatus
  is_primary: boolean; valid_from_utc: string; valid_until_utc: string | null; revision: number
}
export interface ManagedPerson {
  source_id: string; display_name: string; company_id: string; department_id: string
  designation_id: string | null; link_status: 'linked' | 'unlinked'
  employee_status: 'Active' | 'Inactive' | 'Suspended' | 'Left'
}
export interface ManagementPage<T> extends ManagementReadFlags { items: T[]; total: number; page: number; page_size: number }
export interface ManagementListQuery { page?: number; page_size?: number; company_id?: string; department_id?: string; q?: string }
export interface ManagementAssignmentQuery { employee_id: string; page?: number; page_size?: number }

const operations: readonly ManagementReadOperation[] = ['hbos.organization.position.read', 'hbos.organization.assignment.read', 'hbos.organization.person.lookup']
const flagKeys = ['read_only', 'runtime_verified', 'authorization_effect', 'position_authorization_connected']
type Row = Record<string, unknown>

function reject(response = true): never {
  throw new PortalMethodError({ code: response ? 'INVALID_RESPONSE' : 'INVALID_REQUEST', message: response ? '管理查询返回了无效资料，请稍后重试。' : '管理查询参数无效，请检查筛选条件。' })
}
function object(value: unknown, keys: readonly string[], response = true): Row {
  if (!value || typeof value !== 'object' || Array.isArray(value)) reject(response)
  const row = value as Row
  if (Object.keys(row).some(key => !keys.includes(key))) reject(response)
  return row
}
function complete(value: unknown, keys: readonly string[]): Row {
  const row = object(value, keys)
  if (keys.some(key => !Object.prototype.hasOwnProperty.call(row, key))) reject()
  return row
}
function text(value: unknown, maximum = 140, required = true, response = true): string {
  if (typeof value !== 'string' || Array.from(value).length > maximum || Array.from(value).some(char => char.charCodeAt(0) < 32 || char.charCodeAt(0) === 127) || (required && !value.trim())) reject(response)
  return response ? value : value.trim()
}
function integer(value: unknown, minimum: number, maximum: number, response = true): number {
  if (typeof value !== 'number' || !Number.isSafeInteger(value) || value < minimum || value > maximum) reject(response)
  return value
}
function ids(value: unknown): string[] {
  if (!Array.isArray(value) || !value.length) reject()
  const result = value.map(item => text(item))
  if (new Set(result).size !== result.length) reject()
  return result
}
function uuid(value: unknown): string {
  const result = text(value)
  if (!/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/u.test(result)) reject()
  return result
}
function nullableText(value: unknown): string | null { return value === null ? null : text(value) }
function status(value: unknown): ManagedFactStatus {
  if (value !== 'active' && value !== 'inactive' && value !== 'revoked') reject()
  return value
}
function utcTime(value: unknown): string {
  const result = text(value, 40)
  const instant = Date.parse(result)
  if (!/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|\+00:00)$/u.test(result) || !Number.isFinite(instant) || new Date(instant).toISOString().slice(0, 19) !== result.slice(0, 19)) reject()
  return result
}
function utcOrder(value: string): string {
  return `${value.slice(0, 19)}.${(value.match(/\.(\d{1,6})/u)?.[1] ?? '').padEnd(6, '0')}`
}
function flags(row: Row): ManagementReadFlags {
  if (row.read_only !== true || row.runtime_verified !== false || row.authorization_effect !== 'none' || row.position_authorization_connected !== false) reject()
  return { read_only: true, runtime_verified: false, authorization_effect: 'none', position_authorization_connected: false }
}
function optional(row: Row, key: string, fallback: unknown): unknown { return row[key] === undefined ? fallback : row[key] }
function listParams(query: ManagementListQuery): Record<string, unknown> {
  const row = object(query, ['page', 'page_size', 'company_id', 'department_id', 'q'], false)
  return {
    page: integer(optional(row, 'page', 1), 1, 10000, false), page_size: integer(optional(row, 'page_size', 10), 1, 50, false),
    company_id: text(optional(row, 'company_id', ''), 140, false, false), department_id: text(optional(row, 'department_id', ''), 140, false, false),
    q: text(optional(row, 'q', ''), 80, false, false),
  }
}
function assignmentParams(query: ManagementAssignmentQuery): Record<string, unknown> {
  const row = object(query, ['employee_id', 'page', 'page_size'], false)
  return { employee_id: text(row.employee_id, 140, true, false), page: integer(optional(row, 'page', 1), 1, 10000, false), page_size: integer(optional(row, 'page_size', 10), 1, 50, false) }
}
function position(value: unknown): ManagedPosition {
  const row = complete(value, ['record_id', 'title', 'company_id', 'department_id', 'designation_id', 'status', 'revision'])
  return { record_id: uuid(row.record_id), title: text(row.title), company_id: text(row.company_id), department_id: text(row.department_id), designation_id: nullableText(row.designation_id), status: status(row.status), revision: integer(row.revision, 1, Number.MAX_SAFE_INTEGER) }
}
function assignment(value: unknown): ManagedPersonAssignment {
  const row = complete(value, ['record_id', 'position_id', 'person_source_id', 'status', 'is_primary', 'valid_from_utc', 'valid_until_utc', 'revision'])
  if (typeof row.is_primary !== 'boolean') reject()
  const from = utcTime(row.valid_from_utc), until = row.valid_until_utc === null ? null : utcTime(row.valid_until_utc)
  if (until !== null && utcOrder(until) <= utcOrder(from)) reject()
  return { record_id: uuid(row.record_id), position_id: uuid(row.position_id), person_source_id: text(row.person_source_id), status: status(row.status), is_primary: row.is_primary, valid_from_utc: from, valid_until_utc: until, revision: integer(row.revision, 1, Number.MAX_SAFE_INTEGER) }
}
function person(value: unknown): ManagedPerson {
  const row = complete(value, ['source_id', 'display_name', 'company_id', 'department_id', 'designation_id', 'link_status', 'employee_status'])
  if (row.link_status !== 'linked' && row.link_status !== 'unlinked') reject()
  if (row.employee_status !== 'Active' && row.employee_status !== 'Inactive' && row.employee_status !== 'Suspended' && row.employee_status !== 'Left') reject()
  return { source_id: text(row.source_id), display_name: text(row.display_name), company_id: text(row.company_id), department_id: text(row.department_id), designation_id: nullableText(row.designation_id), link_status: row.link_status, employee_status: row.employee_status }
}
function page<T>(value: unknown, params: Record<string, unknown>, project: (item: unknown) => T, key: (item: T) => string): ManagementPage<T> {
  const row = complete(value, [...flagKeys, 'items', 'total', 'page', 'page_size'])
  const total = integer(row.total, 0, Number.MAX_SAFE_INTEGER), number = integer(row.page, 1, 10000), size = integer(row.page_size, 1, 50)
  if (number !== params.page || size !== params.page_size || !Array.isArray(row.items)) reject()
  const expectedLength = Math.min(size, Math.max(0, total - (number - 1) * size))
  if (row.items.length !== expectedLength) reject()
  const items = row.items.map(project)
  if (new Set(items.map(key)).size !== items.length) reject()
  return { ...flags(row), items, total, page: number, page_size: size }
}
function operation(value: unknown): ManagementReadOperation {
  if (!operations.includes(value as ManagementReadOperation)) reject()
  return value as ManagementReadOperation
}
function scope(value: unknown): ManagementReadScope {
  const row = complete(value, ['operation_id', 'operation_schema_version', 'company_id', 'target_department_ids', 'include_children', 'person_scope'])
  if (row.operation_schema_version !== 1 || row.include_children !== false) reject()
  const company = text(row.company_id), operationId = operation(row.operation_id)
  let personScope: ManagementPersonScope | null = null
  if (row.person_scope !== null) {
    const personRow = complete(row.person_scope, ['source_type', 'company_id', 'department_ids'])
    if (personRow.source_type !== 'Employee' || personRow.company_id !== company) reject()
    personScope = { source_type: 'Employee', company_id: text(personRow.company_id), department_ids: ids(personRow.department_ids) }
  }
  if (operationId !== 'hbos.organization.position.read' && personScope === null) reject()
  return { operation_id: operationId, operation_schema_version: 1, company_id: company, target_department_ids: ids(row.target_department_ids), include_children: false, person_scope: personScope }
}
async function read(method: string, params?: Record<string, unknown>): Promise<unknown> {
  const envelope = await callFrappeMethod<PortalMethodEnvelope<unknown>>(`hbos_portal.api.organization_relations.${method}`, params, { requireCsrf: true })
  if (envelope?.ok === true) complete(envelope, ['ok', 'data'])
  else if (envelope?.ok === false) {
    complete(envelope, ['ok', 'error'])
    const error = object(envelope.error, ['code', 'message', 'retryable', 'trace_id'])
    if (typeof error.code !== 'string' || typeof error.message !== 'string' || (error.retryable !== undefined && typeof error.retryable !== 'boolean') || (error.trace_id !== undefined && error.trace_id !== null && typeof error.trace_id !== 'string')) reject()
  } else reject()
  return unwrapPortalMethod(envelope)
}

export async function getManagementContext(): Promise<ManagementContext> {
  const row = complete(await read('get_management_context'), [...flagKeys, 'operation_ids', 'scopes'])
  if (!Array.isArray(row.operation_ids) || !row.operation_ids.length || !Array.isArray(row.scopes)) reject()
  const operationIds = row.operation_ids.map(operation), scopes = row.scopes.map(scope)
  if (new Set(operationIds).size !== operationIds.length || scopes.some(item => !operationIds.includes(item.operation_id)) || operationIds.some(id => !scopes.some(item => item.operation_id === id))) reject()
  return { ...flags(row), operation_ids: operationIds, scopes }
}
export async function listManagedPositions(query: ManagementListQuery = {}): Promise<ManagementPage<ManagedPosition>> {
  const params = listParams(query)
  return page(await read('list_positions', params), params, position, item => item.record_id)
}
export async function getManagedPersonAssignments(query: ManagementAssignmentQuery): Promise<ManagementPage<ManagedPersonAssignment>> {
  const params = assignmentParams(query)
  const result = page(await read('get_person_assignments', params), params, assignment, item => item.record_id)
  if (result.items.some(item => item.person_source_id !== params.employee_id)) reject()
  return result
}
export async function lookupManagedPeople(query: ManagementListQuery = {}): Promise<ManagementPage<ManagedPerson>> {
  const params = listParams(query)
  return page(await read('lookup_people', params), params, person, item => item.source_id)
}
