/**
 * 四张库存报表的**前端侧元信息**。
 *
 * ## 为什么这里要再写一遍筛选定义
 *
 * 筛选是在报表的 `.js`（`frappe.query_reports["<报表名>"]`，Desk 专用）里声明的，
 * **服务端不提供读取接口**——`query_report.run` 的 `js_filters` 参数是「客户端把
 * 筛选传上来做权限校验」，方向相反。所以前端只能自己声明一份。
 *
 * 这是**有测试兜底的重复**，不是靠记性：`test_report_contract.py` 断言本文件里
 * 每张报表的 `fieldname` 集合与对应 `<报表>.js` 完全一致。报表加/改筛选项而忘了
 * 改这里，CI 会红。
 *
 * ## 列定义不在这里
 *
 * 表头与单元格**由服务端返回的 `columns` 驱动**（`query_report.run` 的响应里带着
 * 字段名/标签/类型/精度/宽度）。报表 `.py` 是 Authority，前端不硬编码列清单——
 * 将来报表加一列，前端不改代码就跟着出现。
 *
 * 这里只放**服务端给不出的东西**：路由、筛选 UI 形态、空态文案、值→语义映射。
 */

export type FilterKind = 'text' | 'number' | 'check' | 'select'

export interface ReportFilter {
  fieldname: string
  label: string
  kind: FilterKind
  /** 说明文字，取自报表 .js 的 description —— 不写清用户不知道能填什么 */
  description?: string
  placeholder?: string
  /** check 型的默认勾选状态 / number 型的默认值 */
  defaultChecked?: boolean
  defaultValue?: number
  options?: string[]
}

export interface ReportMeta {
  /** 路由段，也是 `query_report.run` 的 `report_name` */
  id: string
  /** 与 Report DocType 的 name 一致，用于调用接口 */
  reportName: string
  title: string
  sub: string
  /** 高频筛选（EA-5.4 §22：2–4 个直接铺开） */
  primaryFilters: ReportFilter[]
  /** 低频筛选，收进「更多筛选」 */
  extraFilters: ReportFilter[]
  /** 空态文案：因地制宜，不要千篇一律的「暂无数据」 */
  emptyTitle: string
  emptyBody: string
  /** 可选：报表特定的说明条 */
  notice?: { tone: 'warn' | 'info'; html: string }
}

/** 放行状态的可选值 —— 与 Batch 上 Select 的 options 一致 */
const RELEASE_OPTIONS = ['', '待检', '已放行', '不放行']

export const INVENTORY_REPORTS: ReportMeta[] = [
  {
    id: 'location-detail',
    reportName: '货位明细表',
    title: '货位明细表',
    sub: '按货位逐项列出当前库存',
    primaryFilters: [
      {
        fieldname: 'warehouse',
        label: '货位 / 库位',
        kind: 'text',
        placeholder: '如 16-03-206 - HB',
        // 照抄 .js 的 description：不写清用户不知道能填层级
        description: '可填具体货位，也可填库位或层，配合下方勾选展开',
      },
      { fieldname: 'include_children', label: '含下级货位', kind: 'check', defaultChecked: true },
    ],
    extraFilters: [
      { fieldname: 'item_code', label: '物料', kind: 'text', placeholder: '物料代码' },
      { fieldname: 'batch_no', label: '批号', kind: 'text', placeholder: '批号' },
    ],
    emptyTitle: '这个货位下没有库存',
    emptyBody: '该货位当前账面数量为零。可能尚未入库，或已全部发出。',
  },
  {
    id: 'expiry-warning',
    reportName: '效期预警',
    title: '效期预警',
    sub: '列出生效期临近或已过期的批次',
    primaryFilters: [
      {
        fieldname: 'within_days',
        label: '预警天数（剩余不足）',
        kind: 'number',
        defaultValue: 90,
        description: '列出生效期在 N 天内的批次',
      },
      { fieldname: 'include_expired', label: '含已过期', kind: 'check', defaultChecked: true },
      { fieldname: 'warehouse', label: '货位', kind: 'text', placeholder: '全部货位' },
    ],
    extraFilters: [
      { fieldname: 'item_code', label: '物料', kind: 'text', placeholder: '物料代码' },
      { fieldname: 'release_status', label: '放行状态', kind: 'select', options: RELEASE_OPTIONS },
    ],
    emptyTitle: '近期没有临近效期的批次',
    emptyBody: '在设定的预警天数内没有需要关注的批次。可以调大「预警天数」再看。',
  },
  {
    id: 'batch-location',
    reportName: '按批号查货位',
    title: '按批号查货位',
    sub: '输批号定位货位；外购料可输原厂批号后按结果核对',
    primaryFilters: [
      {
        fieldname: 'batch_no',
        label: '批号',
        kind: 'text',
        placeholder: '支持模糊匹配，如 BMT',
        // 不写「模糊匹配」，用户输 BMT 只查到一部分会以为数据不全
        description: '支持模糊匹配；外购物料可输入原厂批号后按结果核对',
      },
      { fieldname: 'warehouse', label: '货位', kind: 'text', placeholder: '全部货位' },
    ],
    extraFilters: [
      { fieldname: 'item_code', label: '物料', kind: 'text', placeholder: '物料代码' },
      { fieldname: 'release_status', label: '放行状态', kind: 'select', options: RELEASE_OPTIONS },
    ],
    emptyTitle: '没找到这个批号',
    emptyBody:
      '批号支持模糊匹配。确认输入无误后仍查不到，说明该系统里没有这个批次——可能还没入库。',
  },
  {
    id: 'stocktake',
    reportName: '库级盘点三对账',
    title: '库级盘点三对账',
    sub: 'ERP 账面数量导出后，与货位卡、实物三方核对',
    // 这张报表的 _columns() 声明了 11 列，但 card_qty / physical_qty /
    // variance_corrected 三列是 None——报表本身算不出，注释写明「由现场填写 /
    // 在导出的 Excel 中计算」。所以界面只显示 erp_qty，并由 hideEmptyColumns 隐藏那三列。
    notice: {
      tone: 'warn',
      html:
        '本页只显示 <b>ERP 账面数量</b>。「货位卡数量」「实物数量」需要现场清点，' +
        '报表给不出——<b>请导出后在 Excel 里填写，差异列随之算出</b>。' +
        '因此这里不显示那三列，免得空格被读成「数量为零」。',
    },
    primaryFilters: [
      {
        fieldname: 'warehouse',
        label: '库位',
        kind: 'text',
        placeholder: '如 3904',
        description: '选库位（如 3904）或货位；配合下方勾选展开下级',
      },
      { fieldname: 'include_children', label: '含下级', kind: 'check', defaultChecked: true },
    ],
    extraFilters: [
      { fieldname: 'item_code', label: '物料', kind: 'text', placeholder: '物料代码' },
    ],
    emptyTitle: '这个库位下没有库存',
    emptyBody: '该库位当前账面数量为零，没有需要盘点的记录。',
  },
]

/**
 * 整列全空时隐藏的字段。
 *
 * 只用于**报表明确算不出**的列（目前只有库级盘点那三列由现场填写）。
 * 通用规则「空列就藏」是错的——一列里偶尔为空是正常数据，藏了会让人以为报表缺列。
 */
export const ALWAYS_HIDDEN_WHEN_EMPTY: Record<string, string[]> = {
  stocktake: ['card_qty', 'physical_qty', 'variance_corrected'],
}

export function findReport(id: string): ReportMeta | undefined {
  return INVENTORY_REPORTS.find((r) => r.id === id)
}

export const REPORT_PATH_PREFIX = '/hbos/inventory/report'

export function reportPath(id: string): string {
  return `${REPORT_PATH_PREFIX}/${id}`
}
