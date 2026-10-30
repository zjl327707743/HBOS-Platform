import { callFrappeMethod, csrfHeaders, frappeApiUrl } from '@/services/frappeClient'

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
  /**
   * 服务端返回的原始行数（过滤合计行**之前**）。
   *
   * 早先界面用 `columns.length && !rows.length` 判「只返回了合计行」——
   * 但那个分支写在 `if (!rows.length) return` **之后**，永远到不了。
   * 现在把原始行数带回来，界面能如实说明「N 行里有合计行，已略过」。
   */
  rawRowCount?: number
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
 *
 * `extraParams` 用于报表级开关——目前只有「库存余额」用它传
 * `ignore_prepared_report=1`（它是预处理报表，不传这个只会返回
 * `{prepared_report: true}` 而没有数据）。
 */
export async function runReport(
  reportName: string,
  filters: Record<string, unknown>,
  extraParams: Record<string, string> = {},
): Promise<ReportResult> {
  const payload = await callFrappeMethod<RawReportPayload>('frappe.desk.query_report.run', {
    report_name: reportName,
    filters: JSON.stringify(cleanFilters(filters)),
    are_default_filters: false,
    ...extraParams,
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
    rawRowCount: raw.length,
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
 * CSV 公式注入防护。
 *
 * 表格软件会把 `=`、`+`、`-`、`@`、Tab、CR 开头的单元格当公式执行。物料名、
 * 供应商、批号、备注都可能来自外部标签或人工录入 —— 一条 `=HYPERLINK(...)`
 * 就能把文件内容带出去，DDE 在旧版 Excel 上还能执行命令。
 *
 * 两条约束必须同时满足：
 *   1. **数值不加前缀** —— 否则 `-1` 会被写成 `'-1`，列就变成文本了；
 *   2. 文本命中公式前缀时前面加 `'`（Excel 的「按文本处理」标记）。
 */
export function neutralizeFormula(quoted: string, raw: unknown): string {
  if (typeof raw === 'number' || typeof raw === 'bigint') return quoted
  // 字符串形式的负数（报表里数量列常是字符串）：`-1` 不是公式，
  // 加前缀会把它变成文本，下游没法求和。只放行**完整**的数字串。
  if (/^-?\d+(\.\d+)?([eE][+-]?\d+)?$/.test(quoted)) return quoted
  // 已经是 `"..."` 形式时，前缀必须写在引号**里面**
  if (quoted.startsWith('"')) {
    return /^"[=+\-@\t\r]/.test(quoted) ? `"'${quoted.slice(1)}` : quoted
  }
  return /^[=+\-@\t\r]/.test(quoted) ? `'${quoted}` : quoted
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
 * ## 对「预处理报表」这条路是走不通的（实测结论）
 *
 * `export_query` 内部会 `run(report_name, form_params.filters, are_default_filters=False)`
 * —— 它 **不读** `ignore_prepared_report`（那个参数只被 `run()` 的 whitelisted 包装读）。
 * 所以对「库存余额」这类预处理报表，它会拿到 `{prepared_report: true}`、
 * `data.columns` 为空，然后渲染一个 HTML 错误页 **「没有要导出的数据」**。
 *
 * 实测：带上 `ignore_prepared_report=1` 也一样——响应仍是 `text/html`、9.2KB、
 * 首字节 `<!DO`。**透传参数解决不了**（我一度以为可以）。
 *
 * 所以此类报表走 `exportRowsAsCsv()`（客户端导出，见下）。
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
  extraParams: Record<string, string> = {},
): Promise<void> {
  const form = new URLSearchParams({
    report_name: reportName,
    file_format_type: 'Excel',
    filters: JSON.stringify(cleanFilters(filters)),
    include_filters: '1',
    ignore_visible_idx: '1',
    ...extraParams,
  })

  // 复用共享的 CSRF 机制（跨源时逐请求取 token）
  const headers: Record<string, string> = {
    'Content-Type': 'application/x-www-form-urlencoded',
    'X-Requested-With': 'XMLHttpRequest',
    ...(await csrfHeaders()),
  }

  // **必须走 Frappe 的绝对地址**：Portal 与 Frappe 跨源部署时，
  // 裸 `/api/...` 会打到 Portal 自己身上，导出稳定失败。
  const response = await fetch(
    frappeApiUrl('/api/method/frappe.desk.query_report.export_query'),
    { method: 'POST', credentials: 'include', headers, body: form },
  )

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
  const buffer = await response.arrayBuffer()

  // 200 也可能是 HTML 错误页（网关/登录跳转）。XLSX 是 zip，前两字节必须是 `PK`。
  // 不校验的话会把一个 HTML 存成 .xlsx，用户双击才发现打不开。
  assertXlsxBytes(new Uint8Array(buffer))
  const blob = new Blob([buffer], {
    type: response.headers.get('Content-Type') || 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
  })

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

/**
 * XLSX 是 zip 容器，前两字节必须是 `PK`。
 *
 * 服务端 200 也可能是 HTML 错误页（网关错误页 / 登录跳转 / 上面那段说的
 * 「没有要导出的数据」）。不校验就把 HTML 存成 `.xlsx`，用户双击才发现打不开 ——
 * 比直接报错更浪费人的时间。
 */
export function assertXlsxBytes(bytes: Uint8Array): void {
  // `PK` = zip 魔数。XLSX 本质是 zip。
  if (bytes.length >= 2 && bytes[0] === 0x50 && bytes[1] === 0x4b) return

  const head = new TextDecoder('utf-8', { fatal: false })
    .decode(bytes.slice(0, 200))
    .toLowerCase()
  if (head.includes('<!doctype') || head.includes('<html')) {
    throw new Error('服务端返回的是网页而不是 Excel（多半是没有可导出的数据）。')
  }
  throw new Error('导出内容不是有效的 Excel 文件，请稍后重试。')
}

/**
 * 客户端导出 CSV —— 给「服务端导不了」的报表用（目前只有库存余额）。
 *
 * 数据本来就在手里（`runReport` 已取回全部行，报表没有分页），所以不必再打一次服务端。
 * 带 UTF-8 BOM，Excel 打开中文不乱码。
 *
 * **导的是屏幕上看到的那些列**（调用方传 `visibleColumns`）—— 与界面一致，
 * 不会出现「文件里有列、页面上没有」的意外。
 */
export function exportRowsAsCsv(
  filename: string,
  columns: ReportColumn[],
  rows: Array<Record<string, unknown>>,
): void {
  const escape = (raw: unknown): string => {
    const text = raw === null || raw === undefined ? '' : String(raw)
    // 含分隔符 / 引号 / 换行时必须加引号，内部引号翻倍（RFC 4180）
    const quoted = /[",\n\r]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text
    return neutralizeFormula(quoted, raw)
  }

  const lines = [
    columns.map((c) => escape(c.label)).join(','),
    ...rows.map((row) => columns.map((c) => escape(row[c.fieldname])).join(',')),
  ]

  // BOM 在前，Excel 才会按 UTF-8 解析中文
  const blob = new Blob(['\ufeff' + lines.join('\r\n')], { type: 'text/csv;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  link.remove()
  setTimeout(() => URL.revokeObjectURL(url), 0)
}
