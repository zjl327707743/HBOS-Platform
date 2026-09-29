import { callFrappeMethod } from '@/services/frappeClient'

const BASE = 'hb_attendance_app.hbos_attendance.page.hbos_department_board.department_board_data'

/** `summarize_rows` 的返回（board_stats._EMPTY 的全部键）。 */
export interface BoardStats {
  total: number
  expected: number
  present: number
  late: number
  noCard: number
  outOnly: number
  unknownTime: number
  notStarted: number
  absent: number
  leave: number
  rest: number
  exempt: number
  attendance_rate: number | null
}

/** 每个部门一行，字段与 `dept_summary` 一致。 */
export interface DeptStats {
  dept: string
  total: number
  expected: number
  present: number
  noCard: number
  outOnly: number
  unknownTime: number
  notStarted: number
  late: number
  absent: number
  leave: number
}

/**
 * 明细行。
 *
 * `state` 是后端状态机的输出（`department_board.live_state` / `day_review`，
 * 共 14 种取值）；`label` 是它自带的中文文案，前端**不再自造**——两处各写一套
 * 中文必然漂移。
 */
export interface BoardRow {
  dept: string
  num: string
  name: string
  expected_label: string
  kind: string
  fact_only: boolean
  state: string
  label: string
  first_hm: string | null
  out_hm?: string | null
  card_count: number
  tags: string[]
  note: string
  anomaly_hidden: boolean
}

export interface BoardMeta {
  date: string
  mode: 'live' | 'review'
  now_hm: string
  scope: string
}

export interface BoardPayload {
  departments: { name: string; count: number }[]
  meta: BoardMeta
  stats: BoardStats
  dept_stats: DeptStats[]
  rows: BoardRow[]
}

export async function fetchBoard(department?: string, dateStr?: string): Promise<BoardPayload> {
  return callFrappeMethod<BoardPayload>(`${BASE}.get_data`, {
    ...(department ? { department } : {}),
    ...(dateStr ? { date_str: dateStr } : {}),
  })
}

/** 手动触发打卡同步（后端自身有 ≥120s 节流，前端不再叠一层）。 */
export async function triggerLiveSync(): Promise<{ throttled: boolean; seconds_left?: number; result?: unknown; error?: string }> {
  return callFrappeMethod(`${BASE}.live_sync`)
}
