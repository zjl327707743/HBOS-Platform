// ============================================================
// 稳定性板块真实后端 API 适配层
// 对接 hb_lims_app.hbos_lims.stability_service whitelist
//
// 覆盖范围：R8A~R8D 后端全量（主数据 4 + 通知单 + 方案 + 样品/时间点 +
// 结果/报告 + 变更/稳定性室/设备），稳定性 7 视图全部接入本模块，无演示数据。
// ============================================================
import { callMethod } from './client'

// ---- 只读投影（字段用后端 snake_case 原名，与 stability_service 返回对齐） ----

export interface StabilityKpi {
  notice_pending: number
  notice_approved: number
  protocol_pending: number
  protocol_approved: number
  product_count: number
  sample_count: number
  timepoint_count: number
  result_count: number
  timepoint_by_status: {
    wait_sample: number; wait_test: number; testing: number; done: number; cancelled: number
  }
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
export function updateStabilityTestItemMapping(stabilityTestItem: string, baseTestItem?: string) {
  return callMethod<{ name: string; base_test_item?: string }>(
    'hb_lims_app.hbos_lims.stability_service.update_stability_test_item_mapping', {
      stability_test_item: stabilityTestItem,
      base_test_item: baseTestItem || undefined,
    })
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
  test_items?: { stability_test_item: string; is_full_test?: number; is_required?: number }[]
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

// ---- R8C：结果与报告（方案 6.3.5 / 6.3.6） ----

export interface ResultRow {
  name: string
  timepoint: string
  stability_sample: string
  stability_test_item: string
  item_snapshot?: string
  result_value?: number | string
  unit?: string
  status: string
  is_current?: number
  revision_no?: number
  supersedes?: string
  is_qualified?: number
  oos_flag?: number
  result_baseline?: string
  baseline_ref?: string
  is_significant_change?: number
  significant_change_basis?: string
  is_zero_month?: number
  source?: string
  source_test_result?: string
  analyst?: string
  test_date?: string
  reviewed_by?: string
  approved_by?: string
  creation: string
}

export interface ResultDetail extends ResultRow {
  spec_version?: string
  spec_limit?: string
  test_method?: string
  method_version?: string
  submitted_at?: string
  reviewed_at?: string
  approved_at?: string
  return_reason?: string
  void_reason?: string
  remark?: string
  revision_chain: { name: string; revision_no?: number; status: string; is_current?: number; supersedes?: string }[]
}

export interface TrendPoint {
  label: string
  timepoint: string
  plan_sample_date?: string
  result_value?: number | null
  status: string
  is_current?: number
  is_significant_change?: number
}

export interface TrendData {
  series: TrendPoint[]
  trend_line: { slope: number; intercept: number; r2: number; points: number } | null
  note: string
}

export interface ReportRow {
  name: string
  report_type: string
  stability_product: string
  product_name?: string
  year?: number
  status: string
  source_doctype?: string
  source_name?: string
  customer?: string
  client_code?: string
  seq?: number
  period_from?: string
  period_to?: string
  proposed_validity_months?: number
  proposed_validity_type?: string
  final_validity_months?: number
  final_validity_date?: string
  final_validity_type?: string
  drafted_by?: string
  draft_date?: string
  qa_approve_by?: string
  approve_date?: string
  creation: string
}

export interface ReportDetail extends ReportRow {
  study_scope?: string
  storage_conds?: string
  spec_ref?: string
  trend_analysis?: string
  impurity_profile?: string
  conclusion?: string
  trend_chart_ref?: string
  proposed_validity_basis?: string
  proposed_validity_date?: string
  client_requirement?: string
  qa_review_by?: string
  qa_review_date?: string
  reject_reason?: string
  void_reason?: string
}

export function results(params: { timepoint?: string; stability_sample?: string; stability_test_item?: string; status?: string; keyword?: string; limit?: number } = {}) {
  return callMethod<{ rows: ResultRow[] }>(
    'hb_lims_app.hbos_lims.stability_service.get_stability_results', params)
}
export function resultDetail(resultName: string): Promise<ResultDetail> {
  return callMethod('hb_lims_app.hbos_lims.stability_service.get_stability_result_detail', {
    result_name: resultName,
  })
}
export function trend(stabilityProduct: string, stabilityTestItem: string, conditionType?: string) {
  return callMethod<TrendData>('hb_lims_app.hbos_lims.stability_service.get_stability_trend', {
    stability_product: stabilityProduct, stability_test_item: stabilityTestItem,
    condition_type: conditionType,
  })
}
export function validityAdvice(stabilityProduct: string, sample?: string) {
  return callMethod<Record<string, unknown>>(
    'hb_lims_app.hbos_lims.stability_service.get_stability_validity_advice',
    { stability_product: stabilityProduct, sample })
}
export function reports(params: { report_type?: string; status?: string; keyword?: string; limit?: number } = {}) {
  return callMethod<{ rows: ReportRow[] }>(
    'hb_lims_app.hbos_lims.stability_service.get_stability_reports', params)
}
export function reportDetail(reportName: string): Promise<ReportDetail> {
  return callMethod('hb_lims_app.hbos_lims.stability_service.get_stability_report_detail', {
    report_name: reportName,
  })
}

export function recordResult(timepointName: string, stabilityTestItem: string, resultValue: number | string,
                             testDate?: string, unit?: string, source = '自检', remark?: string) {
  return callMethod<{ name: string; status: string; revision_no: number; is_significant_change?: number }>(
    'hb_lims_app.hbos_lims.stability_service.record_result',
    { timepoint_name: timepointName, stability_test_item: stabilityTestItem,
      result_value: resultValue, test_date: testDate, unit, source, remark })
}
export function submitResult(resultName: string, testDate?: string) {
  return callMethod('hb_lims_app.hbos_lims.stability_service.submit_result',
    { result_name: resultName, test_date: testDate })
}
export function reviewResult(resultName: string) {
  return callMethod('hb_lims_app.hbos_lims.stability_service.review_result', { result_name: resultName })
}
export function returnResult(resultName: string, reason: string) {
  return callMethod('hb_lims_app.hbos_lims.stability_service.return_result',
    { result_name: resultName, reason })
}
export function approveResult(resultName: string) {
  return callMethod('hb_lims_app.hbos_lims.stability_service.approve_result', { result_name: resultName })
}
export function reviseResult(resultName: string) {
  return callMethod('hb_lims_app.hbos_lims.stability_service.revise_result', { result_name: resultName })
}
export function voidResult(resultName: string, reason: string) {
  return callMethod('hb_lims_app.hbos_lims.stability_service.void_result',
    { result_name: resultName, reason })
}
export function evalTrend(timepointName: string, conclusion: string, remark?: string) {
  return callMethod('hb_lims_app.hbos_lims.stability_service.eval_trend',
    { timepoint_name: timepointName, conclusion, remark })
}
// 注：`complete_testing` 为系统动作、非公开入口（方案 6.3.4），由后端在
// 「全部必检项目均已批准」时自动调用，前端无对应接口与按钮。

export function createReport(params: {
  report_type: string; stability_product: string; year?: number
  source_doctype?: string; source_name?: string; customer?: string
  study_scope?: string; period_from?: string; period_to?: string
  storage_conds?: string; spec_ref?: string; client_requirement?: string
}) {
  return callMethod<{ name: string; status: string; seq?: number; advised_months?: number }>(
    'hb_lims_app.hbos_lims.stability_service.create_stability_report', params)
}
export function saveReportDraft(reportName: string, params: {
  conclusion?: string; trendAnalysis?: string; impurityProfile?: string; trendChartRef?: string
}) {
  return callMethod('hb_lims_app.hbos_lims.stability_service.save_report_draft',
    { report_name: reportName,
      conclusion: params.conclusion,
      trend_analysis: params.trendAnalysis,
      impurity_profile: params.impurityProfile,
      trend_chart_ref: params.trendChartRef })
}
export function submitReport(reportName: string) {
  return callMethod('hb_lims_app.hbos_lims.stability_service.submit_report', { report_name: reportName })
}
export function reviewReport(reportName: string) {
  return callMethod('hb_lims_app.hbos_lims.stability_service.review_report', { report_name: reportName })
}
export function approveReport(reportName: string, params: {
  finalValidityMonths: number; finalValidityDate: string; finalValidityType: string
}) {
  return callMethod('hb_lims_app.hbos_lims.stability_service.approve_report',
    { report_name: reportName,
      final_validity_months: params.finalValidityMonths,
      final_validity_date: params.finalValidityDate,
      final_validity_type: params.finalValidityType })
}
export function rejectReport(reportName: string, reason: string) {
  return callMethod('hb_lims_app.hbos_lims.stability_service.reject_report',
    { report_name: reportName, reason })
}
export function voidReport(reportName: string, reason: string) {
  return callMethod('hb_lims_app.hbos_lims.stability_service.void_report',
    { report_name: reportName, reason })
}

// ---- R8D：变更、稳定性室与设备（方案 6.3.7 / 6.3.8） ----

export interface ChangeRow {
  name: string
  change_scope: string
  change_level: string
  status: string
  notice?: string
  protocol?: string
  stability_sample?: string
  change_content?: string
  applicant?: string
  apply_date?: string
  approver_by?: string
  approve_date?: string
  supersedes?: string
  implement_by?: string
  implement_date?: string
  post_assessment_result?: string
  creation: string
}

export interface RoomLogRow {
  name: string
  room: string
  log_date: string
  period: string
  temperature: number
  temp_min?: number
  temp_max?: number
  humidity: number
  humidity_min?: number
  humidity_max?: number
  within_spec?: number
  exception_desc?: string
  action_taken?: string
  deviation_ref?: string
  capa_ref?: string
  checker?: string
  check_date?: string
}

export interface EquipmentRow {
  name: string
  equipment_name: string
  room?: string
  location?: string
  storage_cond?: string
  qualification_status?: string
  qualification_due?: string
  calibration_due?: string
  maintenance_due?: string
  is_monitored?: number
  has_ups?: number
  has_alarm?: number
  alarm_test_date?: string
  last_fault_date?: string
  status: string
}

export interface FaultSampleRow {
  stability_sample: string
  timepoint?: string
  impact_desc?: string
  is_transferred?: number
}

export interface FaultTicketRow {
  name: string
  equipment: string
  fault_start: string
  fault_end?: string
  status: string
  description: string
  emergency_action?: string
  transfer_path?: string
  risk_assessment?: string
  deviation_ref?: string
  capa_ref?: string
  handler?: string
  handle_date?: string
  affected_samples: FaultSampleRow[]
}

export function changes(params: { status?: string; change_scope?: string; keyword?: string; limit?: number } = {}) {
  return callMethod<{ rows: ChangeRow[] }>(
    'hb_lims_app.hbos_lims.stability_service.get_stability_changes', params)
}
export function changeDetail(changeName: string) {
  return callMethod<{ doc: ChangeRow & Record<string, unknown> }>(
    'hb_lims_app.hbos_lims.stability_service.get_stability_change_detail',
    { change_name: changeName })
}
export function roomLogs(params: { room?: string; from_date?: string; to_date?: string; only_abnormal?: number; limit?: number } = {}) {
  return callMethod<{ rows: RoomLogRow[] }>(
    'hb_lims_app.hbos_lims.stability_service.get_stability_room_logs', params)
}
export function equipments(params: { room?: string; status?: string } = {}) {
  return callMethod<{ rows: EquipmentRow[] }>(
    'hb_lims_app.hbos_lims.stability_service.get_stability_equipments', params)
}
export function faultTickets(params: { status?: string; equipment?: string; limit?: number } = {}) {
  return callMethod<{ rows: FaultTicketRow[] }>(
    'hb_lims_app.hbos_lims.stability_service.get_stability_fault_tickets', params)
}

export function createChange(params: {
  change_scope: string; change_level: string; change_content: string
  change_reason: string; impact_assessment: string
  notice?: string; protocol?: string; stability_sample?: string; supersedes?: string
  applicant_dept?: string; effective_date?: string
  extra_conditions?: { condition_type: string; storage_cond: string; exposure_days?: number; is_required?: number; remark?: string }[]
}) {
  return callMethod<{ name: string; status: string }>(
    'hb_lims_app.hbos_lims.stability_service.create_stability_change', params)
}
export function submitChange(changeName: string) {
  return callMethod('hb_lims_app.hbos_lims.stability_service.submit_change', { change_name: changeName })
}
export function reviewChange(changeName: string) {
  return callMethod<{ name: string; status: string }>(
    'hb_lims_app.hbos_lims.stability_service.review_change', { change_name: changeName })
}
export function approveChangeGeneral(changeName: string) {
  return callMethod('hb_lims_app.hbos_lims.stability_service.approve_change_general',
    { change_name: changeName })
}
export function approveChangeMajor(changeName: string) {
  return callMethod('hb_lims_app.hbos_lims.stability_service.approve_change_major',
    { change_name: changeName })
}
export function rejectChange(changeName: string, reason: string) {
  return callMethod('hb_lims_app.hbos_lims.stability_service.reject_change',
    { change_name: changeName, reason })
}
export function cancelChange(changeName: string) {
  return callMethod('hb_lims_app.hbos_lims.stability_service.cancel_change',
    { change_name: changeName })
}
export function implementChange(changeName: string, implementRecord: string) {
  return callMethod<{ name: string; status: string; result: Record<string, unknown> }>(
    'hb_lims_app.hbos_lims.stability_service.implement_change',
    { change_name: changeName, implement_record: implementRecord })
}
export function assessChange(changeName: string, postAssessment: string, postAssessmentResult: string) {
  return callMethod('hb_lims_app.hbos_lims.stability_service.assess_change',
    { change_name: changeName, post_assessment: postAssessment,
      post_assessment_result: postAssessmentResult })
}
export function logRoomEnv(params: {
  room: string; log_date: string; period: string; temperature: number; humidity: number
  checker?: string; check_date?: string; exception_desc?: string; action_taken?: string
  deviation_ref?: string; capa_ref?: string
}) {
  return callMethod<{ name: string; within_spec: number }>(
    'hb_lims_app.hbos_lims.stability_service.log_room_env', params)
}
export function manageEquipment(params: {
  equipment?: string; equipment_name?: string; room?: string; location?: string
  storage_cond?: string; qualification_status?: string; qualification_due?: string
  calibration_due?: string; maintenance_due?: string; is_monitored?: number
  has_ups?: number; has_alarm?: number; alarm_test_date?: string; status?: string
}) {
  return callMethod<{ name: string; status: string }>(
    'hb_lims_app.hbos_lims.stability_service.manage_equipment', params)
}
export function openFaultTicket(params: {
  equipment: string; description: string; fault_start: string; fault_end?: string
  affected_samples?: { stability_sample: string; timepoint?: string; impact_desc?: string }[]
  emergency_action?: string; transfer_path?: string
}) {
  return callMethod<{ name: string; status: string }>(
    'hb_lims_app.hbos_lims.stability_service.open_fault_ticket', params)
}
export function startFaultHandling(ticketName: string, emergencyAction: string) {
  return callMethod('hb_lims_app.hbos_lims.stability_service.start_fault_handling',
    { ticket_name: ticketName, emergency_action: emergencyAction })
}
export function submitFaultAssessment(ticketName: string, riskAssessment: string) {
  return callMethod('hb_lims_app.hbos_lims.stability_service.submit_fault_assessment',
    { ticket_name: ticketName, risk_assessment: riskAssessment })
}
export function returnFaultHandling(ticketName: string, reason?: string) {
  return callMethod('hb_lims_app.hbos_lims.stability_service.return_fault_handling',
    { ticket_name: ticketName, reason })
}
export function closeFaultTicket(ticketName: string, deviationRef?: string, capaRef?: string) {
  return callMethod('hb_lims_app.hbos_lims.stability_service.close_fault_ticket',
    { ticket_name: ticketName, deviation_ref: deviationRef, capa_ref: capaRef })
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
  manage_stability_master: [ROLE.manager, ROLE.system],
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
  // 6.3.5 FLOW_STB_RESULT（submit/review/approve/revise_result 与 R3 同名，稳定性口径见 SCOPED_ACTION_ROLES）
  record_result: [ROLE.analyst, ROLE.manager, ROLE.system],
  submit_result: [ROLE.analyst, ROLE.manager, ROLE.system],
  review_result: [ROLE.reviewer, ROLE.qa, ROLE.qaManager, ROLE.manager, ROLE.system],
  return_result: [ROLE.reviewer, ROLE.qa, ROLE.qaManager, ROLE.manager, ROLE.system],
  approve_result: [ROLE.qa, ROLE.qaManager, ROLE.manager, ROLE.system],
  revise_result: [ROLE.analyst, ROLE.manager, ROLE.system],
  void_result: [ROLE.qa, ROLE.qaManager, ROLE.manager, ROLE.system],
  eval_trend: [ROLE.analyst, ROLE.reviewer, ROLE.manager, ROLE.system],
  // complete_testing 为系统动作、无公开入口（方案 6.3.4），不在此登记
  // 6.3.6 FLOW_STB_REPORT
  create_stability_report: [ROLE.analyst, ROLE.reviewer, ROLE.manager, ROLE.system],
  save_report_draft: [ROLE.analyst, ROLE.reviewer, ROLE.manager, ROLE.system],
  submit_report: [ROLE.analyst, ROLE.reviewer, ROLE.manager, ROLE.system],
  review_report: [ROLE.reviewer, ROLE.qa, ROLE.qaManager, ROLE.manager, ROLE.system],
  approve_report: [ROLE.qa, ROLE.qaManager, ROLE.manager, ROLE.system],
  reject_report: [ROLE.qa, ROLE.qaManager, ROLE.manager, ROLE.system],
  void_report: [ROLE.qp, ROLE.manager, ROLE.system],
  // 6.3.7 FLOW_STB_CHANGE
  create_change: [ROLE.analyst, ROLE.reviewer, ROLE.qa, ROLE.qaManager, ROLE.manager, ROLE.system],
  submit_change: [ROLE.analyst, ROLE.reviewer, ROLE.manager, ROLE.system],
  review_change: [ROLE.qa, ROLE.qaManager, ROLE.manager, ROLE.system],
  approve_change_general: [ROLE.qaManager, ROLE.system],
  approve_change_major: [ROLE.qp, ROLE.system],
  reject_change: [ROLE.qaManager, ROLE.qp, ROLE.manager, ROLE.system],
  cancel_change: [ROLE.analyst, ROLE.reviewer, ROLE.qa, ROLE.qaManager, ROLE.manager, ROLE.system],
  implement_change: [ROLE.analyst, ROLE.reviewer, ROLE.manager, ROLE.system],
  assess_change: [ROLE.qa, ROLE.qaManager, ROLE.manager, ROLE.system],
  // 6.3.8 稳定性室与设备
  log_room_env: [ROLE.analyst, ROLE.reviewer, ROLE.manager, ROLE.system],
  manage_equipment: [ROLE.reviewer, ROLE.manager, ROLE.system],
  open_fault_ticket: [ROLE.analyst, ROLE.reviewer, ROLE.manager, ROLE.system],
  start_fault_handling: [ROLE.analyst, ROLE.reviewer, ROLE.manager, ROLE.system],
  submit_fault_assessment: [ROLE.analyst, ROLE.reviewer, ROLE.manager, ROLE.system],
  return_fault_handling: [ROLE.analyst, ROLE.reviewer, ROLE.manager, ROLE.system],
  close_fault_ticket: [ROLE.reviewer, ROLE.qa, ROLE.qaManager, ROLE.manager, ROLE.system],
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
