import { callFrappeMethod } from '@/services/frappeClient'

/**
 * 考勤报表的注册表 —— 门户原生渲染。
 *
 * 取数**不重写**：后端 `hbos_attendance/report_data.py` 直接调用报表自己的
 * `execute(filters)`，此处只负责发起调用与渲染。查询口径只有一份。
 *
 * 列的展示偏好（宽度、是否标色、是否隐藏）放在这里，因为那是**门户的呈现选择**，
 * 不属于报表的数据契约——后端只管把 columns / data 原样给出。
 */

export interface ReportColumn {
  label: string
  fieldname: string
  fieldtype?: string
  options?: string
  width?: number
}

export interface ReportPayload {
  report: string
  columns: ReportColumn[]
  data: Record<string, unknown>[]
  /** 过滤后的总行数（后端给），用于分页 */
  total: number
  limit: number
  start: number
}

export type FilterKind = 'month' | 'year' | 'date-range' | 'department'

export interface ReportSpec {
  slug: string
  title: string
  /** 后端端点（带模块路径，供 callFrappeMethod 使用） */
  method: string
  /** 一句话说明这页是什么，写给人看 */
  hint: string
  filters: FilterKind[]
  /** 明细列：内容是一串空格分隔的日期，逐日渲染成小标签 */
  detailFields: string[]
  /** 明细列的配色，与 Desk 侧报表的 formatter 保持一致 */
  detailTones: Record<string, string>
  /** 每页行数；报表本身不分页，由前端切分 */
  pageSize: number
  /**
   * 打开页面时的默认日期跨度（天）。留空表示「本月」。
   *
   * 为什么需要：这些报表**不加日期过滤会全量返回**——实测打卡流水 61815 行、
   * 考勤结果 32893 行，JSON 数 MB，首屏要等好几秒。默认给一个短窗口，
   * 用户要看更宽的历史自己改日期。
   */
  defaultRangeDays?: number
}

const BASE = 'hb_attendance_app.hbos_attendance.report_data'

export const attendanceReports: ReportSpec[] = [
  {
    slug: 'monthly',
    title: '月度考勤汇总',
    method: `${BASE}.get_monthly_summary`,
    hint: '按人汇总当月各班次天数、迟到、早退、缺勤与请假；明细列可逐日核对。',
    filters: ['month', 'year', 'department', 'date-range'],
    detailFields: ['late_detail', 'early_detail', 'absent_detail', 'leave_detail'],
    detailTones: {
      late_detail: 'critical',
      early_detail: 'warning',
      absent_detail: 'muted',
      leave_detail: 'success',
    },
    pageSize: 50,
  },
  {
    slug: 'checkins',
    title: '打卡流水',
    method: `${BASE}.get_checkin_flow`,
    hint: '原始打卡记录，含设备方向判定结果（上班卡 / 下班卡）。',
    filters: ['date-range', 'department'],
    detailFields: [],
    detailTones: {},
    pageSize: 100,
    defaultRangeDays: 7,
  },
  {
    slug: 'results',
    title: '考勤结果',
    method: `${BASE}.get_attendance_results`,
    hint: '判定引擎落库的每日考勤结论，是看板与汇总的口径来源。',
    filters: ['date-range', 'department'],
    detailFields: [],
    detailTones: {},
    pageSize: 100,
    defaultRangeDays: 30,
  },
  {
    slug: 'staging',
    title: '月度汇总 / 对账暂存',
    method: `${BASE}.get_monthly_staging`,
    hint: '月度汇总表导入后的暂存行，用于与后续判定结果对账。',
    filters: ['date-range', 'department'],
    detailFields: [],
    detailTones: {},
    pageSize: 100,
    defaultRangeDays: 30,
  },
]

export function findReport(slug: string): ReportSpec | undefined {
  return attendanceReports.find((report) => report.slug === slug)
}

/**
 * 取一页报表数据。
 *
 * 报表的 execute() 在后端是**全量算出**的（Frappe 脚本报表没有分页接口），
 * 故后端「算全量、只回一段」；这里传 start 让后端截不同的段。
 * 不传 limit：由后端按自己的上限（MAX_ROWS=500）封顶。
 */
export async function fetchReport(
  spec: ReportSpec,
  filters: Record<string, string>,
  start = 0,
): Promise<ReportPayload> {
  return callFrappeMethod<ReportPayload>(spec.method, {
    filters: JSON.stringify(filters),
    start,
  })
}
