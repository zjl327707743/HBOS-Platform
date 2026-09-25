import { callFrappeMethod, csrfHeaders } from '@/services/frappeClient'

/**
 * 库存报表 —— 前端侧接口层。
 *
 * 后端 Authority：`frappe.desk.query_report`（ERPNext/Frappe 自带）与本 App 的
 * `hb_inventory_app/hbos_inventory/report/<报表>/`。
 *
 * 本文件**不计算任何业务数值**：剩余天数、紧急度、库位展开、权限过滤全在报表的
 * `.py` 里做。前端只负责「调接口、渲染、导出」。
 *
 * 尤其**不重算日期**——效期预警的 `days_left` 由报表用服务端日期算定；前端若拿
 * 客户端日期再算一遍，跨时区或跨零点就会与报表不一致。
 */

export interface ReportColumn {
  fieldname: string
  label: string
  fieldtype: string
  options?: string
  width?: number
  precision?: number
}

export interface ReportResult {
  columns: ReportColumn[]
  rows: Array<Record<string, unknown>>
  /** 服务端给的可选图表/汇总，本轮不渲染，留着免得将来再加一次调用 */
  executionTime?: number
}

interface RawReportPayload {
  result?: unknown
  columns?: ReportColumn[]
  execution_time?: number
}

/**
 * 跑一张报表。
 *
 * `query_report.run` 是 whitelisted 的 GET，**内部按会话校验报表权限**
 * （见 `validate_filters_permissions`）——所以前端不需要也不应该自己判权限：
 * 无权限会以错误形式返回，由调用方呈现为「无权限」状态。
 *
 * `are_default_filters=false`：我们传了 `filters` 就按它来，不要服务端再套一层默认值，
 * 否则界面上「清空筛选」会清不干净。
 */
export async function runReport(
  reportName: string,
  filters: Record<string, unknown>,
): Promise<ReportResult> {
  const payload = await callFrappeMethod<RawReportPayload>('frappe.desk.query_report.run', {
    report_name: reportName,
    filters: JSON.stringify(cleanFilters(filters)),
    are_default_filters: false,
  })

  const raw = Array.isArray(payload?.result) ? payload.result : []

  // 末行可能是服务端的合计行（`add_total_row` 的报表）——它没有真实记录的身份，
  // 强行当数据渲染会混进表格里。本 App 四张报表都没开合计行，但接口是通用的，
  // 这里按「对象里有非列字段」判一次，宁可少渲染也不要渲染出假的记录。
  const columnNames = new Set((payload?.columns || []).map((c) => c.fieldname))
  const rows = raw.filter((row): row is Record<string, unknown> => {
    if (!row || typeof row !== 'object' || Array.isArray(row)) return false
    return Object.keys(row).some((key) => columnNames.has(key))
  })

  return {
    columns: payload?.columns || [],
    rows,
    executionTime: payload?.execution_time,
  }
}

/** 空字符串与空数组不该当成筛选条件传过去——它们和「不限」是一回事 */
function cleanFilters(filters: Record<string, unknown>): Record<string, unknown> {
  const out: Record<string, unknown> = {}
  for (const [key, value] of Object.entries(filters || {})) {
    if (value === '' || value === null || value === undefined) continue
    out[key] = value
  }
  return out
}

/**
 * 导出 Excel。
 *
 * 走 `frappe.desk.query_report.export_query`（POST，需 CSRF）。它内部会
 * `can_export(ref_doctype, raise_exception=True)` —— 导出权限与查看权限分开，
 * 所以**导出失败不等于查询失败**，界面要能分别提示。
 *
 * 用 `fetch` 而不是 axios：响应体是二进制，需要 `blob()` 与 `createObjectURL`。
 *
 * **文件名自己拼，不读 `Content-Disposition`。** 服务端下发的是
 * `attachment; filename="货位明细表.xlsx"`（curl 验证过，中文正确），但
 * **浏览器读 header 时会把非 ASCII 按 ISO-8859-1 解码**，JS 拿到手的是
 * `è´§ä½æ...` 这样的乱码字节——再解码也回不来，直接塞进 `link.download`
 * 就会弹出乱码文件名。
 *
 * 好在文件名是可推导的：服务端固定用 `<报表名>.xlsx`
 * （`provide_binary_file` 里 `f"{_(filename)}.{extension}"`），
 * 而报表名就在我们手里。**拼出来比读回来可靠。**
 */
export async function exportReport(
  reportName: string,
  filters: Record<string, unknown>,
): Promise<void> {
  const form = new URLSearchParams({
    report_name: reportName,
    file_format_type: 'Excel',
    filters: JSON.stringify(cleanFilters(filters)),
    include_filters: '1',
    ignore_visible_idx: '1',
  })

  // 复用共享的 CSRF 机制（跨源时逐请求取 token）
  const headers: Record<string, string> = {
    'Content-Type': 'application/x-www-form-urlencoded',
    'X-Requested-With': 'XMLHttpRequest',
    ...(await csrfHeaders()),
  }

  const response = await fetch('/api/method/frappe.desk.query_report.export_query', {
    method: 'POST',
    credentials: 'include',
    headers,
    body: form,
  })

  if (!response.ok) {
    // 服务端会带中文业务提示；这里只兜一句可读的语义，不暴露状态码
    throw new Error(
      response.status === 403
        ? '你没有导出这张报表的权限。'
        : '导出失败，请重试；若反复失败请联系管理员。',
    )
  }

  // 不读 Content-Disposition —— 见函数头注释：浏览器读非 ASCII header 会乱码
  const filename = `${reportName}.xlsx`
  const blob = await response.blob()

  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  link.remove()
  // 立刻撤销会让部分浏览器来不及开始下载，给一帧
  setTimeout(() => URL.revokeObjectURL(url), 0)
}
