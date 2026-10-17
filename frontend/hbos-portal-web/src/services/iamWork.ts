import { iamCommand, iamQuery, IamError, canIam } from './iamAccess'
import { getPerson } from './iamPeople'
import type { WorkTarget, WorkSummary, WorkChange, WorkPreview, WorkApp, WorkScope, EmployeeSummary, PageResult, AppSettings } from '@/types/iam'
const prefix = 'hbos_portal.api.iam_access.'
export interface RegisteredApp { id: string; title: string; integrated: boolean; synthetic?: boolean; operations: Array<{ id: string; title: string; ordinary: boolean; scope_types: string[]; objects: Array<WorkScope & { label: string }> }> }
export interface EffectiveWork { subject_type: 'User' | 'Department'; subject_name: string; app_id: string; version: number; context_revision: string; permission_mode?: 'department' | 'personal'; operations: Array<{ operation_id: string; label: string; available: boolean; allowed: boolean; scopes: WorkScope[]; source: string; reason?: string; editable?: boolean }>; suspended: boolean; summary: string }
export async function getRegisteredApps() { const data=await iamQuery<{apps:RegisteredApp[]}>(prefix+'get_registered_apps'); if(!Array.isArray(data.apps)||data.apps.some(app=>typeof app.id!=='string'||typeof app.integrated!=='boolean'||!Array.isArray(app.operations)))throw new IamError('应用注册信息无法确认。');return data }
export async function listAppPeople(app_id: string, query: {search?:string;department?:string;page?:number;page_size?:number;view_group?:string} = {}) { const data=await iamQuery<PageResult<EmployeeSummary>>(prefix + 'list_app_people', {app_id,page:1,page_size:20,...query});if(!Array.isArray(data.items)||!Number.isInteger(data.total))throw new IamError('配置目标列表无法确认。');return data }
export async function getWorkSubject(employee_id: string, app_id: string) { const data=await iamQuery<{employee:EmployeeSummary;account:{status:string;user_id:string};association:{status:string};configuration_only:true}>(prefix + 'get_work_subject', {employee_id,app_id});if(data.configuration_only!==true||data.employee?.id!==employee_id)throw new IamError('配置目标与当前选择不符，请重新读取。');return data }
export function projectWork(raw: EffectiveWork, meta: RegisteredApp): WorkApp {
  if (!raw || raw.app_id !== meta.id || !Array.isArray(raw.operations) || typeof raw.version !== 'number' || typeof raw.context_revision !== 'string' || raw.operations.some(row=>typeof row.allowed!=='boolean'||typeof row.available!=='boolean'||!Array.isArray(row.scopes))) throw new IamError('应用安排格式无法确认，请重新读取。')
  return { app_id: meta.id, title: meta.title, integrated: meta.integrated, synthetic: meta.synthetic, status: raw.suspended ? '已暂停' : raw.operations.some(row => row.available && row.allowed) ? '可以使用' : '暂不可用', summary: raw.summary, source_text: '', suspended: raw.suspended, permission_mode: raw.permission_mode, version: raw.version, context_revision: raw.context_revision,
    objects: meta.operations.flatMap(row => row.objects),
    operations: raw.operations.map(row => { const definition = meta.operations.find(item => item.id === row.operation_id); return { operation_id: row.operation_id, label: row.label, enabled: row.allowed, scopes: row.scopes.map(scope => ({ ...scope, label: definition?.objects.find(obj => obj.scope_type === scope.scope_type && obj.scope_ref === scope.scope_ref)?.label })), source_text: row.source.replace(/部门安排/g,'来自所属部门').replace(/个人设置/g,'为此员工单独设置'), objects: definition?.objects || [], editable: meta.integrated && row.available && row.editable !== false && definition?.ordinary === true, important: definition?.ordinary === false, reason: !meta.integrated ? '尚未接入此管理功能' : !row.available ? '暂未开放' : row.editable === false && definition?.ordinary ? '存量特别安排仅供查看，请专门核对' : row.reason } }) }
}
export async function getEffectiveWork(target: WorkTarget, meta?: RegisteredApp) {
  const app = meta || (await getRegisteredApps()).apps.find(row => row.id === target.app_id)
  if (!app) throw new IamError('该应用尚未注册。')
  const raw = await iamQuery<EffectiveWork>(prefix + 'get_effective_access', { subject_type: target.subject_type, subject_name: target.subject_name, app_id: target.app_id })
  if(raw.subject_type!==target.subject_type||raw.subject_name!==target.subject_name)throw new IamError('服务端配置主体与当前目标不符。')
  return projectWork(raw, app)
}
async function summary(subject_type: 'User' | 'Department', subject_name: string, onlyApp?: string): Promise<WorkSummary> {
  const { apps } = await getRegisteredApps()
  const items = await Promise.all(apps.filter(app => app.id !== 'iam' && (!app.synthetic || app.integrated) && (!onlyApp || app.id===onlyApp)).map(app => getEffectiveWork({ subject_type, subject_name, app_id: app.id }, app)))
  return { subject_type, subject_name, apps: items }
}
export async function getWorkSummary(employee_id: string, appId?:string) { const person = canIam('iam.people.read') ? await getPerson(employee_id) : await getWorkSubject(employee_id,appId||'attendance'); return { ...await summary(person.employee.user_id ? 'User' : 'Department', person.employee.user_id || person.employee.department,appId), employee_id } }
export const getDepartmentWork = (department: string) => summary('Department', department)
export interface WorkDraft { target: WorkTarget; changes: WorkChange[]; expected_version: number; context_revision: string }
function payload(draft: WorkDraft) { return { subject_type: draft.target.subject_type, subject_name: draft.target.subject_name, app_id: draft.target.app_id, changes: draft.changes, expected_version: draft.expected_version, context_revision: draft.context_revision } }
interface RawPreview { before: EffectiveWork; after: EffectiveWork; changed: boolean; context_revision: string; impact?: WorkPreview['impact'] }
async function projectPreview(raw: RawPreview): Promise<WorkPreview> { const meta = (await getRegisteredApps()).apps.find(app => app.id === raw.after.app_id); if (!meta) throw new IamError('应用注册已变化，请重试。'); return { version: raw.before.version, context_revision: raw.context_revision, changed: raw.changed, summary: raw.after.summary, after: projectWork(raw.after, meta), impact: raw.impact } }
export const previewWork = async (draft: WorkDraft, kind?: 'restore' | 'suspend' | 'reenable') => projectPreview(await iamCommand<RawPreview>(prefix + 'preview_work', { ...payload(draft), ...(kind ? { kind } : {}) }))
export const saveWork = (draft: WorkDraft, preview: WorkPreview, request_id: string) => iamCommand<EffectiveWork>(prefix + 'save_work', { ...payload(draft), expected_version: preview.version, context_revision: preview.context_revision, request_id })
function settingsPayload(draft: WorkDraft, settings: AppSettings) { const {changes: _changes, ...rest} = payload(draft); return {...rest, settings} }
export const previewAppSettings = async (draft: WorkDraft, settings: AppSettings) => projectPreview(await iamCommand<RawPreview>(prefix + 'preview_app_settings', settingsPayload(draft, settings)))
export const saveAppSettings = (draft: WorkDraft, settings: AppSettings, preview: WorkPreview, request_id: string) => iamCommand<EffectiveWork>(prefix + 'save_app_settings', {...settingsPayload(draft, settings), expected_version:preview.version, context_revision:preview.context_revision, request_id})
export const workAction = (kind: 'restore_department_work' | 'suspend_app' | 'reenable_app', target: WorkTarget, version: number, context_revision: string, request_id: string) => iamCommand<EffectiveWork>(prefix + kind, { subject_type: target.subject_type, subject_name: target.subject_name, app_id: target.app_id, expected_version: version, context_revision, request_id })
export function savedWorkResult(raw:EffectiveWork, prior:WorkApp, target:WorkTarget) {
  if(raw.subject_type!==target.subject_type||raw.subject_name!==target.subject_name)throw new IamError('保存结果主体与当前目标不符，请读取实际状态。')
  return projectWork({...raw,operations:raw.operations.map(row=>({...row,editable:row.editable ?? prior.operations.find(old=>old.operation_id===row.operation_id)?.editable}))},{id:prior.app_id,title:prior.title,integrated:prior.integrated,synthetic:prior.synthetic,operations:prior.operations.map(row=>({id:row.operation_id,title:row.label,ordinary:!row.important,scope_types:[],objects:(row.objects||[]).map(scope=>({...scope,label:scope.label||scope.scope_ref||'本人'}))}))})
}
export function changedWork(original: WorkChange[], draft: WorkChange[]) {
  const comparable=(row:WorkChange|undefined)=>row?JSON.stringify([row.enabled,row.scopes.map(scope=>JSON.stringify([scope.scope_type,scope.scope_ref])).sort()]):''
  return draft.filter(row => comparable(original.find(item => item.operation_id === row.operation_id)) !== comparable(row))
}
