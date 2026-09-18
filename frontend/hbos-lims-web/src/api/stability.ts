// ============================================================
// 稳定性板块真实后端 API 适配层
// 对接 hb_lims_app.hbos_lims.stability_service whitelist（M2-R8A 后端）
//
// 覆盖范围：R8A 已交付的「稳定性工作台」与「考察申请与方案」两视图所需接口
//（主数据 4 + 通知单 + 方案）。样品/时间点/结果/报告/变更等属 R8B~R8D，
// 对应视图在本轮仍为演示数据，不在此模块内。
// ============================================================
import { callMethod } from './client'

// ---- 只读投影（字段用后端 snake_case 原名，与 stability_service 返回对齐） ----

export interface StabilityKpi {
  notice_pending: number
  notice_approved: number
  protocol_pending: number
  protocol_approved: number
  product_count: number
  master: { condition: number; room: number; test_item: number }
  scope: string
}

export interface NoticeRow {
  name: string
  stability_product: string
  status: string
  version: number
  conditions_count: number
  qa_applicant?: string
  apply_date?: string
  approver_by?: string
  approve_date?: string
  reject_reason?: string
  creation: string
  product_name?: string
  category?: string
  dosage_form?: string
}

export interface ProtocolRow {
  name: string
  notice: string
  status: string
  version: number
  effective_date?: string
  drafted_by?: string
  draft_date?: string
  qa_review_by?: string
  qa_approve_by?: string
  approve_date?: string
  reject_reason?: string
  void_reason?: string
  creation: string
  stability_product?: string
  product_name?: string
}

export interface ProductRow {
  name: string
  product_code: string
  product_name: string
  category: string
  dosage_form?: string
  default_uom: string
  vd_months?: number
  qty_factor?: number
  pack_desc?: string
  is_outsource?: number
  need_inverted?: number
  is_active?: number
  storage_cond_long?: string
  storage_cond_acc?: string
  storage_cond_inter?: string
}

export interface MasterRow {
  name: string
  is_active?: number
  [key: string]: unknown
}

export interface NoticeStudyCondition {
  condition_type: string
  storage_cond: string
  exposure_days?: number
  is_required?: number
  remark?: string
}

export interface NoticeBatch {
  batch_no: string
  batch_size?: string
  manufacture_date?: string
  is_inverted?: number
  remark?: string
}

export interface NoticeDetail {
  name: string
  status: string
  version: number
  stability_product: string
  product_name?: string
  category?: string
  dosage_form?: string
  study_reason: string
  conditions_count: number
  extra_condition_reason?: string
  register_review_by?: string
  register_review_date?: string
  study_conditions: NoticeStudyCondition[]
  batches: NoticeBatch[]
  qty?: number
  qty_uom?: string
  pack_desc?: string
  test_cycle?: string
  test_method?: string
  snapshot: {
    spec_ref?: string
    spec_version?: string
    method_version?: string
    limits_snapshot?: string
    vd_months_snapshot?: number
    frozen: boolean
  }
  signoff: Record<string, string | undefined>
  protocols: ProtocolRow[]
}

export interface ProtocolDetail {
  name: string
  notice: string
  notice_status: string
  stability_product: string
  product_code: string
  product_name: string
  category?: string
  status: string
  version: number
  purpose?: string
  scope?: string
  batches: NoticeBatch[]
  study_conditions: NoticeStudyCondition[]
  items: {
    stability_test_item: string
    is_full_test?: number
    is_key_item?: number
    test_method?: string
    method_version?: string
  }[]
  qty?: number
  qty_uom?: string
  pack_desc?: string
  room_temp_recovery_days?: number
  snapshot: {
    spec_ref?: string
    spec_version?: string
    test_method_ref?: string
    method_version?: string
    vd_months_snapshot?: number
    frozen: boolean
  }
  signoff: Record<string, string | undefined>
}

export interface AuditEvent {
  name: string
  log_type: string
  doctype_target: string
  doc_name: string
  action_text?: string
  old_value?: string
  new_value?: string
  reason?: string
  user?: string
  created_at: string
}

// ---- 只读 ----

export function dashboard(): Promise<StabilityKpi> {
  return callMethod('hb_lims_app.hbos_lims.stability_service.get_stability_dashboard')
}
export function products(keyword?: string, includeInactive = false): Promise<{ rows: ProductRow[] }> {
  return callMethod('hb_lims_app.hbos_lims.stability_service.get_stability_products', {
    keyword, include_inactive: includeInactive ? 1 : 0,
  })
}
export function master(doctype: string, keyword?: string): Promise<{ rows: MasterRow[] }> {
  return callMethod('hb_lims_app.hbos_lims.stability_service.get_stability_master', { doctype, keyword })
}
export function notices(params: { keyword?: string; status?: string; limit?: number; offset?: number } = {}) {
  return callMethod<{ rows: NoticeRow[] }>(
    'hb_lims_app.hbos_lims.stability_service.get_stability_notices', params)
}
export function noticeDetail(noticeName: string): Promise<NoticeDetail> {
  return callMethod('hb_lims_app.hbos_lims.stability_service.get_stability_notice_detail', {
    notice_name: noticeName,
  })
}
export function protocols(params: { notice?: string; status?: string; keyword?: string; limit?: number; offset?: number } = {}) {
  return callMethod<{ rows: ProtocolRow[] }>(
    'hb_lims_app.hbos_lims.stability_service.get_stability_protocols', params)
}
export function protocolDetail(protocolName: string): Promise<ProtocolDetail> {
  return callMethod('hb_lims_app.hbos_lims.stability_service.get_stability_protocol_detail', {
    protocol_name: protocolName,
  })
}
export function audit(docName?: string, limit = 20): Promise<{ events: AuditEvent[]; total: number }> {
  return callMethod('hb_lims_app.hbos_lims.stability_service.get_stability_audit', {
    doc_name: docName, limit,
  })
}

// ---- 通知单写操作（方案 6.3.1） ----

export function createNotice(params: {
  stability_product: string
  study_reason: string
  study_conditions?: NoticeStudyCondition[]
  batches?: NoticeBatch[]
  extra_condition_reason?: string
  qty?: number
  qty_uom?: string
  pack_desc?: string
  test_cycle?: string
  test_method?: string
  spec_ref?: string
  spec_version?: string
  method_version?: string
  limits_snapshot?: string
}) {
  return callMethod<{ name: string; status: string }>(
    'hb_lims_app.hbos_lims.stability_service.create_stability_notice', params)
}
export function registerReview(noticeName: string, reviewDate?: string) {
  return callMethod('hb_lims_app.hbos_lims.stability_service.register_review', {
    notice_name: noticeName, review_date: reviewDate,
  })
}
export function submitNotice(noticeName: string) {
  return callMethod('hb_lims_app.hbos_lims.stability_service.submit_notice', { notice_name: noticeName })
}
export function confirmNoticeQc(noticeName: string) {
  return callMethod('hb_lims_app.hbos_lims.stability_service.confirm_notice_qc', { notice_name: noticeName })
}
export function approveNotice(noticeName: string) {
  return callMethod('hb_lims_app.hbos_lims.stability_service.approve_notice', { notice_name: noticeName })
}
export function rejectNotice(noticeName: string, reason: string) {
  return callMethod('hb_lims_app.hbos_lims.stability_service.reject_notice', {
    notice_name: noticeName, reason,
  })
}
export function cancelNotice(noticeName: string, reason?: string) {
  return callMethod('hb_lims_app.hbos_lims.stability_service.cancel_notice', {
    notice_name: noticeName, reason,
  })
}
export function closeNotice(noticeName: string) {
  return callMethod('hb_lims_app.hbos_lims.stability_service.close_notice', { notice_name: noticeName })
}

// ---- 方案写操作（方案 6.3.2） ----

export function createProtocol(params: {
  notice: string
  purpose?: string
  scope?: string
  batches?: NoticeBatch[]
  study_conditions?: NoticeStudyCondition[]
  items?: { stability_test_item: string; is_key_item?: number; test_method?: string; method_version?: string }[]
  qty?: number
  qty_uom?: string
  pack_desc?: string
  room_temp_recovery_days?: number
  spec_ref?: string
  spec_version?: string
  test_method_ref?: string
  method_version?: string
}) {
  return callMethod<{ name: string; status: string }>(
    'hb_lims_app.hbos_lims.stability_service.create_stability_protocol', params)
}
export function submitProtocol(protocolName: string) {
  return callMethod('hb_lims_app.hbos_lims.stability_service.submit_protocol', { protocol_name: protocolName })
}
export function reviewProtocol(protocolName: string) {
  return callMethod('hb_lims_app.hbos_lims.stability_service.review_protocol', { protocol_name: protocolName })
}
export function approveProtocol(protocolName: string, effectiveDate?: string) {
  return callMethod('hb_lims_app.hbos_lims.stability_service.approve_protocol', {
    protocol_name: protocolName, effective_date: effectiveDate,
  })
}
export function rejectProtocol(protocolName: string, reason: string) {
  return callMethod('hb_lims_app.hbos_lims.stability_service.reject_protocol', {
    protocol_name: protocolName, reason,
  })
}
export function voidProtocol(protocolName: string, reason: string) {
  return callMethod('hb_lims_app.hbos_lims.stability_service.void_protocol', {
    protocol_name: protocolName, reason,
  })
}

// ---- 角色动作矩阵（与后端 workflow_contract.ACTION_ROLES 对齐，逐行照方案 6.3.1 / 6.3.2） ----
// 仅用于前端按钮显隐；真正的准入判定在后端 `_check_action` + SoD，前端不可绕过。

const ROLE = {
  analyst: 'LIMS Analyst',
  reviewer: 'LIMS Reviewer',
  qa: 'LIMS QA',
  qaManager: 'LIMS QA Manager',
  qp: 'LIMS QP',
  manager: 'LIMS Manager',
  system: 'System Manager',
} as const

const ACTION_ROLES: Record<string, readonly string[]> = {
  // 6.3.1 FLOW_STB_NOTICE
  create_notice: [ROLE.qa, ROLE.qaManager, ROLE.manager, ROLE.system],
  register_review: [ROLE.qa, ROLE.qaManager, ROLE.manager, ROLE.system],
  submit_notice: [ROLE.qa, ROLE.qaManager, ROLE.manager, ROLE.system],
  confirm_notice_qc: [ROLE.reviewer, ROLE.manager, ROLE.system],
  approve_notice: [ROLE.qa, ROLE.qaManager, ROLE.manager, ROLE.system],
  reject_notice: [ROLE.reviewer, ROLE.qa, ROLE.qaManager, ROLE.manager, ROLE.system],
  cancel_notice: [ROLE.qa, ROLE.qaManager, ROLE.manager, ROLE.system],
  close_notice: [ROLE.qa, ROLE.qaManager, ROLE.manager, ROLE.system],
  // 6.3.2 FLOW_STB_PROTOCOL
  submit_protocol: [ROLE.analyst, ROLE.reviewer, ROLE.manager, ROLE.system],
  review_protocol: [ROLE.reviewer, ROLE.qa, ROLE.qaManager, ROLE.manager, ROLE.system],
  approve_protocol: [ROLE.qa, ROLE.qaManager, ROLE.manager, ROLE.system],
  reject_protocol: [ROLE.qa, ROLE.qaManager, ROLE.manager, ROLE.system],
  void_protocol: [ROLE.qp, ROLE.manager, ROLE.system],
}

/** 当前会话角色下是否可执行指定动作（含 System Manager 放行）。 */
export function canAction(userRoles: string[] | undefined, action: string): boolean {
  if (!userRoles || !userRoles.length) return false
  if (userRoles.includes('System Manager')) return true
  const allowed = ACTION_ROLES[action]
  return !!allowed && userRoles.some((r) => (allowed as string[]).includes(r))
}

export const SOD_NOTE =
  '职责分离（SoD）：申请人不得担任批准人，QA 审核人不得担任批准人；前端提示，后端硬校验。'
