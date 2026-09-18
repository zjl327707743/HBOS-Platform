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

// ---- M2-R8B 样品与时间点（R8H 接入用） ----

export interface SampleRow {
  name: string
  notice?: string
  protocol?: string
  stability_product: string
  product_name?: string
  sample_name?: string
  batch_no: string
  batch_size?: string
  storage_cond?: string
  condition_snapshot?: string
  room?: string
  storage_location?: string
  inverted_flag?: string
  init_qty?: number
  current_qty?: number
  qty_uom?: string
  in_date?: string
  start_date?: string
  need_evaluation?: number
  evaluation_conclusion?: string
  timepoint_gen_error?: string
  pack_desc?: string
  is_sterile_pack?: number
  package_count?: number
  label_no?: string
  status: string
}

export interface SampleLogRow {
  transaction_date: string
  transaction_type: string
  source_timepoint?: string
  sampling_reason?: string
  sample_no_out?: string
  return_sample_no?: string
  remaining_sample_no?: string
  qty_delta?: number
  qty_uom?: string
  remaining_qty?: number
  operator?: string
  reviewer?: string
  remarks?: string
}

export interface SampleDetail extends SampleRow {
  material_code?: string
  manufacture_date?: string
  finish_date?: string
  send_date?: string
  full_test_sample_date?: string
  package_spec?: string
  evaluated_by?: string
  evaluation_date?: string
  stored_by?: string
  reviewed_by?: string
  reviewed_date?: string
  pre_disposal_status?: string
  disposal_mark_reason?: string
  disposal_marked_by?: string
  disposal_marked_date?: string
  disposal_cancel_reason?: string
  disposal_cancelled_by?: string
  disposal_cancelled_date?: string
  logs: SampleLogRow[]
  timepoints: {
    name: string
    time_point_label: string
    condition_type: string
    status: string
    plan_sample_date?: string
    plan_test_date?: string
    actual_sample_date?: string
    actual_test_date?: string
  }[]
}

export interface ScheduleRow {
  name: string
  stability_sample: string
  condition_type: string
  storage_cond?: string
  time_point_label: string
  time_point_value: number
  time_point_unit: string
  plan_sample_date?: string
  actual_sample_date?: string
  plan_test_date?: string
  actual_test_date?: string
  delay_limit_days?: number
  is_full_test?: number
  is_zero_month?: number
  status: string
  batch_no?: string
  sample_name?: string
  room?: string
  product_name?: string
  sample_status?: string
  current_qty?: number
  policy_latest_sample_due?: string | null
  policy_latest_test_due?: string | null
  effective_sample_due?: string | null
  effective_test_due?: string | null
  delay_state?: string
  sample_overdue?: number
  test_overdue?: number
  exec_state?: string
}

export interface TimepointDetail {
  name: string
  stability_sample: string
  batch_no?: string
  sample_name?: string
  product_name?: string
  condition_type: string
  storage_cond?: string
  time_point_value: number
  time_point_unit: string
  time_point_label: string
  plan_sample_date?: string
  actual_sample_date?: string
  plan_test_date?: string
  actual_test_date?: string
  delay_limit_days?: number
  effective_sample_due?: string | null
  policy_latest_sample_due?: string | null
  effective_test_due?: string | null
  policy_latest_test_due?: string | null
  is_full_test?: number
  is_zero_month?: number
  is_extra?: number
  extra_reason?: string
  extra_approver_by?: string
  extra_approve_date?: string
  sample_by?: string
  test_by?: string
  status: string
  test_items: { stability_test_item: string; is_full_test?: number; is_required?: number }[]
  delays: DelayRow[]
}

export interface DelayRow {
  name?: string
  parent?: string
  delay_type: string
  planned_due_date?: string
  policy_latest_due_date?: string
  requested_due_date?: string
  reason?: string
  apply_by?: string
  apply_date?: string
  status: string
  approver_by?: string
  approve_at?: string
  approved_due_date?: string
  reject_reason?: string
  batch_no?: string
  sample_name?: string
  product_name?: string
  time_point_label?: string
  condition_type?: string
  timepoint_status?: string
}

export function samples(params: { keyword?: string; status?: string; stability_product?: string; limit?: number; offset?: number } = {}) {
  return callMethod<{ rows: SampleRow[] }>(
    'hb_lims_app.hbos_lims.stability_service.get_stability_samples', params)
}
export function sampleDetail(sampleName: string): Promise<SampleDetail> {
  return callMethod('hb_lims_app.hbos_lims.stability_service.get_stability_sample_detail', {
    sample_name: sampleName,
  })
}
export function schedule(params: { month?: string; condition?: string; exec_status?: string; keyword?: string; limit?: number } = {}) {
  return callMethod<{ rows: ScheduleRow[]; summary: Record<string, number> }>(
    'hb_lims_app.hbos_lims.stability_service.get_stability_schedule', params)
}
export function timepointDetail(timepointName: string): Promise<TimepointDetail> {
  return callMethod('hb_lims_app.hbos_lims.stability_service.get_stability_timepoint_detail', {
    timepoint_name: timepointName,
  })
}
export function delays(params: { delay_type?: string; status?: string; keyword?: string; limit?: number } = {}) {
  return callMethod<{ rows: DelayRow[]; summary: { pending: number; approved: number; rejected: number } }>(
    'hb_lims_app.hbos_lims.stability_service.get_stability_delays', params)
}

// ---- 样品写操作（方案 6.3.3） ----

export function registerSample(params: {
  notice: string
  stability_product: string
  batch_no: string
  in_date: string
  protocol?: string
  sample_name?: string
  material_code?: string
  batch_size?: string
  manufacture_date?: string
  finish_date?: string
  send_date?: string
  full_test_sample_date?: string
  storage_cond?: string
  room?: string
  storage_location?: string
  pack_desc?: string
  is_sterile_pack?: number
  package_count?: number
  package_spec?: string
  inverted_flag?: string
  init_qty?: number
  qty_uom?: string
  source_sample?: string
  label_no?: string
  evaluation_conclusion?: string
  evaluated_by?: string
  evaluation_date?: string
}) {
  return callMethod<{ name: string; status: string }>(
    'hb_lims_app.hbos_lims.stability_service.register_stability_sample', params)
}
export function reviewSampleStorage(sampleName: string) {
  return callMethod('hb_lims_app.hbos_lims.stability_service.review_sample_storage', { sample_name: sampleName })
}
export function recordSampling(sampleName: string, params: {
  timepoint?: string; qty: number; sampling_reason?: string; sample_date?: string
  sample_no_out?: string; remarks?: string
}) {
  return callMethod('hb_lims_app.hbos_lims.stability_service.record_sampling',
    { sample_name: sampleName, ...params })
}
export function returnSample(sampleName: string, params: {
  qty: number; timepoint?: string; return_sample_no?: string; remarks?: string; reviewer?: string
}) {
  return callMethod('hb_lims_app.hbos_lims.stability_service.return_sample',
    { sample_name: sampleName, ...params })
}
export function markForDisposal(sampleName: string, reason: string) {
  return callMethod('hb_lims_app.hbos_lims.stability_service.mark_for_disposal',
    { sample_name: sampleName, reason })
}
export function cancelDisposal(sampleName: string, reason: string) {
  return callMethod('hb_lims_app.hbos_lims.stability_service.cancel_disposal',
    { sample_name: sampleName, reason })
}
export function disposeSample(sampleName: string, params: { qty?: number; remarks?: string; reviewer?: string; location?: string } = {}) {
  return callMethod('hb_lims_app.hbos_lims.stability_service.dispose_sample',
    { sample_name: sampleName, ...params })
}
export function adjustStock(sampleName: string, qtyDelta: number, remarks: string) {
  return callMethod('hb_lims_app.hbos_lims.stability_service.adjust_stock',
    { sample_name: sampleName, qty_delta: qtyDelta, remarks })
}
export function transferOut(sampleName: string, remarks?: string) {
  return callMethod('hb_lims_app.hbos_lims.stability_service.transfer_out',
    { sample_name: sampleName, remarks })
}

// ---- 时间点写操作（方案 6.3.4） ----

export function generateTimepoints(sampleName: string) {
  return callMethod<{ sample: string; created: number }>(
    'hb_lims_app.hbos_lims.stability_service.generate_timepoints', { sample_name: sampleName })
}
export function completeSampling(timepointName: string, actualSampleDate?: string) {
  return callMethod('hb_lims_app.hbos_lims.stability_service.complete_sampling',
    { timepoint_name: timepointName, actual_sample_date: actualSampleDate })
}
export function importZeroMonthResult(timepointName: string, source: string, baselineDoctype?: string, baselineName?: string) {
  return callMethod('hb_lims_app.hbos_lims.stability_service.import_zero_month_result',
    { timepoint_name: timepointName, source, baseline_doctype: baselineDoctype, baseline_name: baselineName })
}
export function startTesting(timepointName: string) {
  return callMethod('hb_lims_app.hbos_lims.stability_service.start_testing', { timepoint_name: timepointName })
}
export function cancelTimepoint(timepointName: string, reason: string) {
  return callMethod('hb_lims_app.hbos_lims.stability_service.cancel_timepoint',
    { timepoint_name: timepointName, reason })
}
export function approveExtraSampling(timepointName: string, reason?: string) {
  return callMethod('hb_lims_app.hbos_lims.stability_service.approve_extra_sampling',
    { timepoint_name: timepointName, reason })
}
export function applyDelay(timepointName: string, delayType: string, requestedDueDate: string, reason: string) {
  return callMethod('hb_lims_app.hbos_lims.stability_service.apply_delay',
    { timepoint_name: timepointName, delay_type: delayType, requested_due_date: requestedDueDate, reason })
}
export function approveDelay(timepointName: string, delayType: string, approvedDueDate: string) {
  return callMethod('hb_lims_app.hbos_lims.stability_service.approve_delay',
    { timepoint_name: timepointName, delay_type: delayType, approved_due_date: approvedDueDate })
}
export function rejectDelay(timepointName: string, delayType: string, reason: string) {
  return callMethod('hb_lims_app.hbos_lims.stability_service.reject_delay',
    { timepoint_name: timepointName, delay_type: delayType, reason })
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
  // 6.3.3 FLOW_STB_SAMPLE
  register_stability_sample: [ROLE.analyst, ROLE.reviewer, ROLE.manager, ROLE.system],
  review_sample_storage: [ROLE.reviewer, ROLE.qa, ROLE.manager, ROLE.system],
  record_sampling: [ROLE.analyst, ROLE.manager, ROLE.system],
  return_sample: [ROLE.analyst, ROLE.manager, ROLE.system],
  mark_for_disposal: [ROLE.reviewer, ROLE.qa, ROLE.qaManager, ROLE.manager, ROLE.system],
  cancel_disposal: [ROLE.reviewer, ROLE.qa, ROLE.qaManager, ROLE.manager, ROLE.system],
  dispose_sample: [ROLE.analyst, ROLE.manager, ROLE.system],
  adjust_stock: [ROLE.manager, ROLE.system],
  transfer_out: [ROLE.manager, ROLE.system],
  // 6.3.4 FLOW_STB_TIMEPOINT
  generate_timepoints: [ROLE.analyst, ROLE.reviewer, ROLE.manager, ROLE.system],
  complete_sampling: [ROLE.analyst, ROLE.manager, ROLE.system],
  import_zero_month_result: [ROLE.analyst, ROLE.manager, ROLE.system],
  start_testing: [ROLE.analyst, ROLE.manager, ROLE.system],
  cancel_timepoint: [ROLE.reviewer, ROLE.qa, ROLE.qaManager, ROLE.manager, ROLE.system],
  append_conditions: [ROLE.reviewer, ROLE.qaManager, ROLE.manager, ROLE.system],
  apply_delay: [ROLE.analyst, ROLE.manager, ROLE.system],
  approve_delay: [ROLE.reviewer, ROLE.qa, ROLE.qaManager, ROLE.manager, ROLE.system],
  reject_delay: [ROLE.reviewer, ROLE.qa, ROLE.qaManager, ROLE.manager, ROLE.system],
  approve_extra_sampling: [ROLE.manager, ROLE.system],
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
