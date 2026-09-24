// ============================================================
// 留样板块 R7B/C 真实后端 API 适配层
// 对接 hb_lims_app.hbos_lims.retention_service whitelist
// （R7A register/adjust 沿用 src/api/lims.ts）
// ============================================================
import { callMethod } from './client'

// ---- 只读聚合投影（与后端 list_usage_applies / list_disposal_applies / get_observation_plan 对齐） ----

export interface UsageRow {
  name: string
  retention_name: string
  product: string
  sample_name: string
  batch: string
  qty: number
  uom: string
  scenario: string
  reason: string
  dept: string
  applicant: string
  applicant_date: string
  status: string
  stock_confirm_by?: string
  stock_qty?: number
  qc_approval?: string
  qa_approval?: string
  qm_approval?: string
  current_qty: number
  reserved_qty: number
  available_qty: number
}

export interface DisposalRow {
  name: string
  retention_name: string
  product: string
  sample_name: string
  batch: string
  category: string
  qty: number
  uom: string
  type: string
  reason: string
  method: string
  location: string
  qa_manager_required: number
  applicant: string
  applicant_date: string
  status: string
  current_qty: number
  reserved_qty: number
  deadline?: string
  new_retention_due_date?: string
  sample_prev_status?: string
  disposal_by?: string
  monitor_by?: string
  qm_approved_at?: string
  qc_supervisor_sign?: string
  qc_manager_sign?: string
  qa_review_sign?: string
  qa_manager_sign?: string
  qm_sign?: string
}

export interface ObsBoardRow {
  name: string
  product: string
  sampleName: string
  batch: string
  monthOffset?: number | null
  planDate?: string | null
  due: string
  result?: string | null
  selectedReason: string
  obsYear?: number | null
  obs_rule?: string
  status?: string
  reviewReady?: boolean
}

export interface ObsCompleteness {
  product: string
  rule: string
  year: number
  selected: number
  cap: number | null
}

export function usageList(status?: string): Promise<{ rows: UsageRow[]; total: number }> {
  return callMethod('hb_lims_app.hbos_lims.retention_service.list_usage_applies', { status })
}
export function disposalList(status?: string): Promise<{ rows: DisposalRow[]; total: number }> {
  return callMethod('hb_lims_app.hbos_lims.retention_service.list_disposal_applies', { status })
}
export function obsPlan(): Promise<{ rows: ObsBoardRow[]; completeness: ObsCompleteness[] }> {
  return callMethod('hb_lims_app.hbos_lims.retention_service.get_observation_plan')
}

// ---- 观察 ----
export function selectObsBatch(retentionName: string, obsYear: number, reason: string) {
  return callMethod('hb_lims_app.hbos_lims.retention_service.select_obs_batch', {
    retention_name: retentionName, obs_year: obsYear, obs_selected_reason: reason,
  })
}
export function cancelObsBatch(retentionName: string) {
  return callMethod('hb_lims_app.hbos_lims.retention_service.cancel_obs_batch', { retention_name: retentionName })
}
export function recordObservation(params: {
  retention_name: string; obs_month: number; obs_date?: string; appearance?: string
  result: string; abnormal_note?: string
}) {
  return callMethod('hb_lims_app.hbos_lims.retention_service.record_observation', params)
}
export function reviewObservation(retention_name: string, obs_month: number) {
  return callMethod('hb_lims_app.hbos_lims.retention_service.review_observation', { retention_name, obs_month })
}
export function reviewObservationByName(observation_name: string) {
  return callMethod('hb_lims_app.hbos_lims.retention_service.review_observation', { observation_name })
}

// ---- 使用申请 ----
export function createUsageApply(params: { retention_name: string; apply_qty: number; reason_type: string; reason_detail?: string; apply_dept?: string }) {
  return callMethod('hb_lims_app.hbos_lims.retention_service.create_usage_apply', params)
}
export function submitUsageApply(usage_name: string) {
  return callMethod('hb_lims_app.hbos_lims.retention_service.submit_usage_apply', { usage_name })
}
export function confirmUsageStock(usage_name: string) {
  return callMethod('hb_lims_app.hbos_lims.retention_service.confirm_stock', { usage_name })
}
export function approveUsage(usage_name: string) {
  return callMethod('hb_lims_app.hbos_lims.retention_service.approve_usage', { usage_name })
}
export function executeUsage(usage_name: string) {
  return callMethod('hb_lims_app.hbos_lims.retention_service.execute_usage', { usage_name })
}
export function rejectUsage(usage_name: string, reason: string) {
  return callMethod('hb_lims_app.hbos_lims.retention_service.reject_usage', { usage_name, reason })
}
export function cancelUsageApply(usage_name: string, reason: string) {
  return callMethod('hb_lims_app.hbos_lims.retention_service.cancel_usage_apply', { usage_name, reason })
}

// ---- 处理申请 ----
export function createDisposalApply(params: {
  retention_name: string; disposal_type: string; qty: number; reason?: string
  disposal_method?: string; disposal_location?: string; qa_manager_required?: number
  new_retention_due_date?: string
}) {
  return callMethod('hb_lims_app.hbos_lims.retention_service.create_disposal_apply', params)
}
export function submitDisposalApply(dsp_name: string) {
  return callMethod('hb_lims_app.hbos_lims.retention_service.submit_disposal_apply', { dsp_name })
}
export function approveDisposal(dsp_name: string) {
  return callMethod('hb_lims_app.hbos_lims.retention_service.approve_disposal', { dsp_name })
}
export function rejectDisposal(dsp_name: string, reason: string) {
  return callMethod('hb_lims_app.hbos_lims.retention_service.reject_disposal', { dsp_name, reason })
}
export function cancelDisposalApply(dsp_name: string, reason: string) {
  return callMethod('hb_lims_app.hbos_lims.retention_service.cancel_disposal_apply', { dsp_name, reason })
}
export function disposalHandle(dsp_name: string) {
  return callMethod('hb_lims_app.hbos_lims.retention_service.dispose_handle', { dsp_name })
}
export function disposalMonitor(dsp_name: string) {
  return callMethod('hb_lims_app.hbos_lims.retention_service.dispose_monitor', { dsp_name })
}
export function continueRetention(dsp_name: string) {
  return callMethod('hb_lims_app.hbos_lims.retention_service.continue_retention', { dsp_name })
}

// ---- 可用留样候选（发起申请） ----
export interface RetentionCandidate {
  name: string
  sample_name: string
  batch_no: string
  current_qty: number
  reserved_qty: number
  available_qty: number
  qty_uom: string
  product_name: string
  status: string
}

export async function retentionCandidates(activeStatuses: string[] = ['在库', '部分使用']): Promise<RetentionCandidate[]> {
  // 前端只读投影：取留样与产品 join（数量展示派生 available_qty，不落库）
  const { listDoctype, getDoc } = await import('./lims')
  const samples = await listDoctype<Record<string, unknown>>('HBOS Retention Sample', ['*'], { status: ['in', activeStatuses] }, 0, 'retention_date desc')
  const out: RetentionCandidate[] = []
  for (const s of samples) {
    const product = await getDoc<{ product_name: string }>('HBOS Retention Product', String(s.retention_product))
    const cur = Number(s.current_qty || 0)
    const res = Number(s.reserved_qty || 0)
    out.push({
      name: String(s.name),
      sample_name: String(s.sample_name || ''),
      batch_no: String(s.batch_no || ''),
      current_qty: cur,
      reserved_qty: res,
      available_qty: cur - res,
      qty_uom: String(s.qty_uom || ''),
      product_name: product.product_name || '',
      status: String(s.status || ''),
    })
  }
  return out
}

// ---- 角色动作（与后端 workflow ACTION_ROLES 对齐；System Manager 全放行） ----
const ROLE = {
  analyst: 'LIMS Analyst',
  reviewer: 'LIMS Reviewer',
  qa: 'LIMS QA',
  manager: 'LIMS Manager',
  system: 'System Manager',
} as const

const ACTION_ROLES: Record<string, readonly string[]> = {
  register_retention: [ROLE.analyst, ROLE.manager, ROLE.system],
  select_obs_batch: [ROLE.reviewer, ROLE.manager, ROLE.system],
  cancel_obs_batch: [ROLE.reviewer, ROLE.manager, ROLE.system],
  record_observation: [ROLE.analyst, ROLE.reviewer, ROLE.manager, ROLE.system],
  review_observation: [ROLE.reviewer, ROLE.qa, ROLE.manager, ROLE.system],
  create_usage_apply: [ROLE.analyst, ROLE.manager, ROLE.system],
  usage_confirm: [ROLE.reviewer, ROLE.manager, ROLE.system],
  usage_qc: [ROLE.reviewer, ROLE.manager, ROLE.system],
  usage_qa: [ROLE.qa, ROLE.manager, ROLE.system],
  usage_qm: [ROLE.manager, ROLE.system],
  usage_execute: [ROLE.analyst, ROLE.manager, ROLE.system],
  usage_reject: [ROLE.reviewer, ROLE.qa, ROLE.manager, ROLE.system],
  usage_cancel: [ROLE.manager, ROLE.system],
  create_disposal_apply: [ROLE.analyst, ROLE.manager, ROLE.system],
  disposal_qc: [ROLE.reviewer, ROLE.manager, ROLE.system],
  disposal_qa: [ROLE.qa, ROLE.manager, ROLE.system],
  disposal_qm: [ROLE.manager, ROLE.system],
  disposal_handler: [ROLE.analyst, ROLE.manager, ROLE.system],
  disposal_monitor: [ROLE.qa, ROLE.manager, ROLE.system],
  disposal_cancel: [ROLE.manager, ROLE.system],
  transfer_out: [ROLE.manager, ROLE.system],
}

/** 当前会话角色下是否可执行指定动作（含 System Manager 放行）。 */
export function canAction(userRoles: string[] | undefined, action: string): boolean {
  if (!userRoles || !userRoles.length) return false
  if (userRoles.includes('System Manager')) return true
  const allowed = ACTION_ROLES[action]
  return !!allowed && userRoles.some((r) => (allowed as string[]).includes(r))
}

export const SOD_NOTE = '职责分离（SoD）：同一用户不得连续两级签署，申请人不得担任审批人；前端提示，后端硬校验。'
