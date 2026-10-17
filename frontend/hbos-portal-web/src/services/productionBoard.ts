/**
 * 生产看板取数客户端。
 *
 * ## 走的是 HBOS 受控后端，不是直连 FastAPI
 *
 * ```
 * 浏览器 → hbos_portal.api.production.get_board → 生产 FastAPI → 飞书多维表格
 * ```
 *
 * 早先这里是浏览器**直连** FastAPI（`VITE_PRODUCTION_SERVICE_ORIGIN`）。
 * 那种形态下服务地址暴露在浏览器里，任何人绕开 Portal 就能打它；权限与数据范围
 * 无从谈起（CORS 不是鉴权）。现在统一走 `callFrappeMethod` ——
 * 会话校验、应用权限（默认拒绝）、服务间令牌都在**服务端**完成。
 *
 * 前端**不做任何计算**，只把服务返回的行原样渲染 —— 口径只有服务端一处实现。
 *
 * 服务未就绪 / 无权访问时：抛 `PortalApiError` 或返回 null，页面渲染「未接入」态，
 * **不显示任何数字**（EA-5.4 §16：没有真实 Provider 时必须隐藏，不展示假数字）。
 */

import { callFrappeMethod } from '@/services/frappeClient'
import type { PortalApiError } from '@/services/portalApi'

/** 后端返回的信封（与 `portalApi.ts` 同一层协议）。 */
interface PortalEnvelope<T> {
  ok: boolean
  data?: T
  error?: { code: string; message: string; retryable: boolean; trace_id?: string | null }
}

export interface ProductionRow {
  /** 行名，与 `PRODUCTION_ROWS` 的 label 对应。 */
  label: string
  /** 本月已完成批数。 */
  done: number
  /** 本月目标批数（月度生产计划明细 1–31 日求和）。 */
  target: number
  /** 本月实际收率（按收料日期落月的平均），无数据为 null。 */
  yieldRate: number | null
  /** 目标收率（合并行按计划批数加权），无数据为 null。 */
  targetYieldRate: number | null
  /** 昨日入库量（kg），管理人员看板用；无数据为 null。 */
  yesterdayInbound: number | null
}

/** 一个车间的异常闭环统计。 */
export interface AnomalyWorkshop {
  name: string
  /** 该车间的「闭环」判据（全车间统一 = `事件原因` 非空，Owner 2026-10-08）。 */
  closureLabel: string
  total: number
  closed: number
  rate: number | null
  /** 解析不出日期、未纳入窗口的条数。 */
  undated: number
}

/** 异常闭环（各车间独立 Base 汇总）。 */
export interface AnomalyInfo {
  windowMonths: number
  windowStart: string
  total: number
  closed: number
  rate: number | null
  /** 全部已配置的车间（含窗口内无异常的）。 */
  workshops: string[]
  /** 窗口内有记录、真正参与计算的车间。 */
  activeWorkshops: string[]
  byWorkshop: AnomalyWorkshop[]
  failedWorkshops: string[]
}

export interface ProductionBoardData {
  /** 数据月份，如 "2026-10"。 */
  month: string
  /** 本月已过天数 —— 用于「月初基准」提示。**服务端每次请求现算**。 */
  daysElapsed: number
  /** 数据截至时间（ISO 或展示串）。 */
  updatedAt: string
  /**
   * 这批**行数据**是什么时候取回来的（带时区偏移的 ISO），没有则为 null。
   *
   * 与 `updatedAt` 的区别：`updatedAt` 是「今天」，这个是「数据的新鲜度」。
   * 服务端缓存命中时它会早于现在 —— 页面据此标「数据截至」。
   */
  dataAsOf: string | null
  rows: ProductionRow[]
  anomaly?: AnomalyInfo
}

export interface AiAnalysisRow {
  product: string
  process: string
  summary: string
  grade: string
  analyzedAt: string | null
}

function unwrap<T>(envelope: PortalEnvelope<T>): T {
  if (!envelope || !envelope.ok || envelope.data === undefined) {
    throw new Error(envelope?.error?.message || '生产数据暂时不可用。')
  }
  return envelope.data
}

/**
 * 取当月看板数据。
 *
 * 取不到就返回 `null` —— 调用方渲染未接入态，
 * **不得**用 0 或空行代替（见文件头说明）。
 *
 * 注意它**可能很慢**：冷取时服务端要并发拉 13 张飞书表（约 15 秒），
 * `refresh: true` 时服务端会同步重取，同样是这个量级。
 *
 * @param opts.refresh 点「刷新」时为 true —— 服务端绕过缓存同步重取。
 */
export async function fetchProductionBoard(
  opts: { refresh?: boolean } = {},
): Promise<ProductionBoardData | null> {
  try {
    const envelope = await callFrappeMethod<PortalEnvelope<ProductionBoardData>>(
      'hbos_portal.api.production.get_board',
      { refresh: opts.refresh ? 1 : 0 },
    )
    return unwrap(envelope)
  } catch (error) {
    // 无权限 / 未登录 / 服务未接入都会走到这里 —— 页面显示「未接入」，
    // **不显示任何数字**。具体原因由调用方按需提示。
    void (error as PortalApiError | Error)
    return null
  }
}

/**
 * 取 AI 工艺分析结论（读「AI工艺分析结果」表）。
 *
 * 取不到就返回空数组，页面显示「待分析」，而不是伪造一条结论 ——
 * AI 结论直接影响生产判断，宁可不给。
 */
export async function fetchAiAnalysis(): Promise<AiAnalysisRow[]> {
  try {
    const envelope = await callFrappeMethod<
      PortalEnvelope<{ rows?: AiAnalysisRow[] }>
    >('hbos_portal.api.production.get_ai_analysis')
    const data = unwrap(envelope)
    return data.rows || []
  } catch {
    return []
  }
}
