import { callFrappeMethod } from '@/services/frappeClient'

/** 后端 `dashboard_data.get_data` 的返回结构（只声明本页真正消费的字段）。 */
export interface AttendanceDashboardData {
  total_late: number
  total_early: number
  total_absent: number
  anomaly_people: number
  total_employees: number
  attendance_rate: number
  daily_avg_late: number
  date_range: string
  top_late_names: string[]
  top_late_counts: number[]
  top_absent_names: string[]
  top_absent_counts: number[]
  dept_names: string[]
  dept_late: number[]
  dept_early: number[]
  dept_absent: number[]
  trend_labels: string[]
  trend_late: number[]
  trend_early: number[]
  trend_absent: number[]
  table_rows: AttendanceRow[]
}

export interface AttendanceRow {
  name: string
  num: string
  dept: string
  late_count: number
  early_count: number
  absent_count: number
  total_anomaly: number
}

/**
 * 取仪表盘数据。
 *
 * 日期区间不传则由后端按「本周一~周日」兜底——与 Desk 版页面同一口径，
 * 前端不重算窗口，避免两处漂移。
 */
export async function fetchAttendanceDashboard(
  start?: string,
  end?: string,
): Promise<AttendanceDashboardData> {
  return callFrappeMethod<AttendanceDashboardData>(
    'hb_attendance_app.hbos_attendance.page.hbos_attendance_dashboard.dashboard_data.get_data',
    {
      ...(start ? { start_str: start } : {}),
      ...(end ? { end_str: end } : {}),
    },
  )
}
