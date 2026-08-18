import { callMethod, getMethod } from './client'

// ============================================================
// HBOS LIMS API 契约层
// 对接 hb_lims_app.hbos_lims.lims_service 现有 whitelist 方法
// 与 docs/frontend/M2_LIMS_Vue前端开发流程.md 第 7 节一致
// ============================================================

// ---- 样品登记与任务 ----
export function registerSample(params: {
  sample_type?: string
  material_code?: string
  material_name?: string
  batch_no?: string
  sample_source?: string
  specification?: string
  priority?: string
  test_due_date?: string
  remarks?: string
}) {
  return callMethod<string>('hb_lims_app.hbos_lims.lims_service.register_sample', params)
}

export function generateTasks(sample_name: string, lab_department?: string) {
  return callMethod<string[]>('hb_lims_app.hbos_lims.lims_service.generate_tasks', { sample_name, lab_department })
}

export function assignTask(task_name: string, assignee?: string) {
  return callMethod<string>('hb_lims_app.hbos_lims.lims_service.assign_task', { task_name, assignee })
}

export function startTask(task_name: string) {
  return callMethod<{ task: string; result: string }>('hb_lims_app.hbos_lims.lims_service.start_task', { task_name })
}

// ---- 检验结果 ----
export function submitResult(params: {
  result_name: string
  raw_value?: string
  result_value?: string
  result_text?: string
  calc_input_json?: string
  calculation_used?: string
  instrument_used?: string
}) {
  return callMethod('hb_lims_app.hbos_lims.lims_service.submit_result', params)
}

export function reviewResult(result_name: string) {
  return callMethod('hb_lims_app.hbos_lims.lims_service.review_result', { result_name })
}

export function approveResult(result_name: string) {
  return callMethod('hb_lims_app.hbos_lims.lims_service.approve_result', { result_name })
}

export function reviseResult(result_name: string, new_value: string, reason: string, field = 'result_value') {
  return callMethod('hb_lims_app.hbos_lims.lims_service.revise_result', { result_name, new_value, reason, field })
}

// ---- COA ----
export function createCoa(sample_name: string) {
  return callMethod<string>('hb_lims_app.hbos_lims.lims_service.create_coa', { sample_name })
}

export function reviewCoa(coa_name: string) {
  return callMethod('hb_lims_app.hbos_lims.lims_service.review_coa', { coa_name })
}

export function publishCoa(coa_name: string) {
  return callMethod('hb_lims_app.hbos_lims.lims_service.publish_coa', { coa_name })
}

// ---- 样品终态 ----
export function releaseSample(sample_name: string) {
  return callMethod('hb_lims_app.hbos_lims.lims_service.release_sample', { sample_name })
}

// ---- 质量标准管理 ----
export interface SpecItemInput {
  item?: string
  item_name?: string
  method_sop?: string
  limits_type?: string
  lower_limit?: number | null
  upper_limit?: number | null
  unit?: string
  significant_digits?: number
  remark?: string
}

export function createSpecification(params: {
  spec_code: string
  spec_name: string
  material_code?: string
  material_name?: string
  standard_source?: string
  effective_date?: string
  version?: string
  items?: SpecItemInput[]
  remarks?: string
}) {
  return callMethod<string>('hb_lims_app.hbos_lims.lims_service.create_specification', params)
}

export function updateSpecification(params: {
  spec_name: string
  spec_code?: string
  spec_name_label?: string
  material_code?: string
  material_name?: string
  standard_source?: string
  effective_date?: string
  items?: SpecItemInput[]
  remarks?: string
}) {
  return callMethod<string>('hb_lims_app.hbos_lims.lims_service.update_specification', params)
}

export function activateSpecification(spec_name: string) {
  return callMethod<string>('hb_lims_app.hbos_lims.lims_service.activate_specification', { spec_name })
}

export function obsoleteSpecification(spec_name: string) {
  return callMethod<string>('hb_lims_app.hbos_lims.lims_service.obsolete_specification', { spec_name })
}

export function deleteSpecification(spec_name: string) {
  return callMethod<string>('hb_lims_app.hbos_lims.lims_service.delete_specification', { spec_name })
}

// ---- 报表查询（Frappe Script Report）----
export interface ReportColumn {
  label: string
  fieldname: string
  fieldtype: string
  width?: number
  options?: string
}

export interface ReportResult {
  columns: ReportColumn[]
  result: Record<string, unknown>[]
}

/**
 * 运行 Frappe Script Report。
 * report_name 需为 scrub 后的目录名，例如：待检任务看板 / 样品台账 / 检验结果清单 / coa_发布记录 / 审计追踪查询
 */
export function runReport(report_name: string, filters: Record<string, unknown> = {}): Promise<ReportResult> {
  return getMethod('frappe.desk.query_report.run', { report_name, filters })
}

// ---- 标准 Frappe 读取 ----
export async function listDoctype<T = any>(
  doctype: string,
  fields: string[] = ['*'],
  filters: Record<string, unknown> = {},
  limit = 50,
  orderBy = 'modified desc',
): Promise<T[]> {
  return getMethod('frappe.client.get_list', {
    doctype,
    fields: JSON.stringify(fields),
    filters: JSON.stringify(filters),
    limit_page_length: limit,
    order_by: orderBy,
  })
}

export function getDoc<T = any>(doctype: string, name: string): Promise<T> {
  return getMethod('frappe.client.get', { doctype, name })
}

export function getDocField<T = any>(doctype: string, fieldname: string, filters: Record<string, unknown>): Promise<T> {
  return getMethod('frappe.client.get_value', { doctype, fieldname, filters })
}

export function getMeta<T = any>(doctype: string): Promise<T> {
  return getMethod('frappe.client.get_list', { doctype })
}

// ---- 文件 / PDF 下载 ----
export function getFileUrl(path: string): string {
  if (!path) return ''
  return `/api/method/frappe.utils.file_manager.download_file?file_url=${encodeURIComponent(path)}`
}
