import { callFrappeMethod } from '@/services/frappeClient'

/**
 * 考勤 DocType 列表 —— 门户原生渲染。
 *
 * 与报表同理：**列的取舍与取数都不重写**，后端 `list_data.py` 是权威，
 * 前端只负责渲染与交互（筛选、翻页）。
 */

export interface ListColumn {
  fieldname: string
  label: string
  width?: number
  /** 呈现方式：状态徽章 / 布尔 / 整数 / 小数 / 纯文本 */
  kind?: 'status' | 'bool' | 'int' | 'num'
}

export interface ListPayload {
  key: string
  doctype: string
  title: string
  hint: string
  columns: ListColumn[]
  /** 可筛选字段（后端白名单），前端照它渲染筛选条 */
  filter_fields: string[]
  rows: Record<string, unknown>[]
  total: number
  limit: number
  start: number
}

const BASE = 'hb_attendance_app.hbos_attendance.list_data'

/** 每页行数。这些表可能上万行（飞书请假实测 18633），必须服务端翻页。 */
export const LIST_PAGE_SIZE = 100

export async function fetchList(
  key: string,
  filters: Record<string, string>,
  start = 0,
  limit = LIST_PAGE_SIZE,
): Promise<ListPayload> {
  return callFrappeMethod<ListPayload>(`${BASE}.get_list`, {
    key,
    filters: JSON.stringify(filters),
    start,
    limit,
  })
}

export async function fetchFilterOptions(
  key: string,
  fieldname: string,
): Promise<{ value: string; label: string }[]> {
  return callFrappeMethod(`${BASE}.get_filter_options`, { key, fieldname })
}
