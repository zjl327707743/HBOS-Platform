import { callFrappeMethod, PortalMethodError, unwrapPortalMethod, type PortalMethodEnvelope } from '@/services/frappeClient'

export type PersonnelSource = 'User' | 'Employee'
export interface LivePerson {
  id: string; record_id: string; display_id: string; name: string; phone: string
  department: string; position: string; active: boolean; account_linked: boolean; role_profile: string
}
export interface LiveRole { id: string; name: string; created_at: string; description: string }
export interface LiveDepartment { id: string; name: string; parent_id: string | null }
export interface NativePersonnelFlags { read_only: true; authorization_domain: 'native_personnel'; management_policy_applied: false }
export interface LivePage<T> extends NativePersonnelFlags { items: T[]; total: number; position_authorization_connected: false }
export interface LiveOrganizations extends NativePersonnelFlags { items: LiveDepartment[]; truncated: boolean }
export interface PeopleQuery { source: PersonnelSource; page: number; page_size: number; name: string; department: string; position: string }

type Row = Record<string, unknown>
const nativeKeys = ['read_only', 'authorization_domain', 'management_policy_applied']
function reject(response = true): never {
  throw new PortalMethodError({ code: response ? 'INVALID_RESPONSE' : 'INVALID_REQUEST', message: response ? '人员目录返回了无效资料，请稍后重试。' : '人员目录筛选参数无效。' })
}
function object(value: unknown, keys: readonly string[], response = true, complete = true): Row {
  if (!value || typeof value !== 'object' || Array.isArray(value)) reject(response)
  const row = value as Row
  if (Object.keys(row).some(key => !keys.includes(key)) || (complete && keys.some(key => !Object.prototype.hasOwnProperty.call(row, key)))) reject(response)
  return row
}
function text(value: unknown, required = false, response = true): string {
  if (typeof value !== 'string' || Array.from(value).length > (response ? 500 : 100) || Array.from(value).some(char => char.charCodeAt(0) < 32 || char.charCodeAt(0) === 127) || (required && !value.trim())) reject(response)
  return response ? value : value.trim()
}
function integer(value: unknown, minimum: number, maximum: number, response = true): number {
  if (typeof value !== 'number' || !Number.isSafeInteger(value) || value < minimum || value > maximum) reject(response)
  return value
}
function nativeFlags(row: Row): NativePersonnelFlags {
  if (row.read_only !== true || row.authorization_domain !== 'native_personnel' || row.management_policy_applied !== false) reject()
  return { read_only: true, authorization_domain: 'native_personnel', management_policy_applied: false }
}
function person(value: unknown, source: PersonnelSource): LivePerson {
  const row = object(value, ['id', 'record_id', 'display_id', 'name', 'phone', 'department', 'position', 'active', 'account_linked', 'role_profile'])
  if (typeof row.active !== 'boolean' || typeof row.account_linked !== 'boolean') reject()
  const recordId = text(row.record_id, true), id = text(row.id, true), phone = text(row.phone)
  if (id !== `${source}:${recordId}` || (phone !== '' && phone !== '****' && !/^.{3}\*{4}.{4}$/u.test(phone))) reject()
  return { id, record_id: recordId, display_id: text(row.display_id, true), name: text(row.name, true), phone, department: text(row.department), position: text(row.position), active: row.active, account_linked: row.account_linked, role_profile: text(row.role_profile) }
}
function role(value: unknown): LiveRole {
  const row = object(value, ['id', 'name', 'created_at', 'description'])
  return { id: text(row.id, true), name: text(row.name, true), created_at: text(row.created_at), description: text(row.description) }
}
function nativePage<T>(value: unknown, number: number, size: number, project: (item: unknown) => T, extraKeys: string[] = []): LivePage<T> {
  const row = object(value, [...nativeKeys, 'items', 'total', 'position_authorization_connected', ...extraKeys])
  if (row.position_authorization_connected !== false || !Array.isArray(row.items)) reject()
  const total = integer(row.total, 0, Number.MAX_SAFE_INTEGER)
  if (row.items.length > Math.min(size, Math.max(0, total - (number - 1) * size))) reject()
  return { ...nativeFlags(row), position_authorization_connected: false, items: row.items.map(project), total }
}

async function read<T>(method: string, params?: Record<string, unknown>): Promise<T> {
  const envelope = await callFrappeMethod<PortalMethodEnvelope<T>>(`hbos_portal.api.people_access.${method}`, params)
  if (envelope?.ok === true) object(envelope, ['ok', 'data'])
  else if (envelope?.ok === false) {
    object(envelope, ['ok', 'error'])
    const error = object(envelope.error, ['code', 'message', 'retryable', 'trace_id'], true, false)
    if (typeof error.code !== 'string' || typeof error.message !== 'string' || (error.retryable !== undefined && typeof error.retryable !== 'boolean') || (error.trace_id !== undefined && error.trace_id !== null && typeof error.trace_id !== 'string')) reject()
  } else reject()
  return unwrapPortalMethod(envelope)
}
export async function getPeople(query: PeopleQuery): Promise<LivePage<LivePerson> & { source: PersonnelSource }> {
  const row = object(query, ['source', 'page', 'page_size', 'name', 'department', 'position'], false)
  if (row.source !== 'User' && row.source !== 'Employee') reject(false)
  const source = row.source, page = integer(row.page, 1, 10000, false), size = integer(row.page_size, 1, 50, false)
  const params = { source, page, page_size: size, name: text(row.name, false, false), department: text(row.department, false, false), position: text(row.position, false, false) }
  if (source === 'User' && (params.department || params.position)) reject(false)
  const value = await read<unknown>('get_people', params)
  const result = nativePage(value, page, size, item => person(item, source), ['source'])
  if ((value as Row).source !== source) reject()
  return { ...result, source }
}
export async function getPeopleRoles(page: number, pageSize: number, name: string): Promise<LivePage<LiveRole>> {
  const number = integer(page, 1, 10000, false), size = integer(pageSize, 1, 50, false)
  return nativePage(await read<unknown>('get_roles', { page: number, page_size: size, name: text(name, false, false) }), number, size, role)
}
export async function getPeopleOrganizations(): Promise<LiveOrganizations> {
  const row = object(await read<unknown>('get_organizations'), [...nativeKeys, 'items', 'truncated'])
  if (!Array.isArray(row.items) || row.items.length > 200 || typeof row.truncated !== 'boolean') reject()
  const items = row.items.map(value => {
    const item = object(value, ['id', 'name', 'parent_id'])
    return { id: text(item.id, true), name: text(item.name, true), parent_id: item.parent_id === null ? null : text(item.parent_id, true) }
  })
  return { ...nativeFlags(row), items, truncated: row.truncated }
}
