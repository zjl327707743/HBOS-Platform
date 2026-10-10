/**
 * 生产看板取数客户端。
 *
 * 数据来自**独立取数服务**（方案 B，见 `docs/frontend/P4_生产看板_取数架构方案对比.md`），
 * 不是 hbos_portal —— 生产看板与 Frappe 无关（Owner 2026-09-29 口径）。
 *
 * 服务端持有飞书凭据并按口径聚合；前端**不做任何计算**，
 * 只把服务返回的行原样渲染。这样「完成率怎么算、按哪个日期落月、怎么合并」
 * 只有服务端一处实现，不会前后端两套算法对不上。
 *
 * 服务未就绪时的行为（当前状态）：
 *   一律返回 null → 页面渲染「未接入」态，**不显示任何数字**。
 *   依据：EA-5.4 §16「没有真实 Provider 时必须隐藏，不展示假数字」。
 */

/** 取数服务的地址。留空表示服务未部署 —— 这是当前状态。 */
const SERVICE_ORIGIN = (import.meta.env.VITE_PRODUCTION_SERVICE_ORIGIN || '').replace(/\/+$/, '')

/** 服务是否已配置。未配置时所有请求短路为 null。 */
export const productionServiceConfigured = SERVICE_ORIGIN.length > 0

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

/** 取数结果 —— **区分「还没取到」和「取不到」**。
 *
 * 早先的实现用 `null` 同时表示两者，导致冷缓存（首次要拉 9 张飞书表，
 * 20~30 秒）期间页面显示「未接入」—— 用户以为坏了，其实在加载。
 */
export type BoardResult =
  | { state: 'loading' }
  | { state: 'unavailable' }
  | { state: 'ready'; data: ProductionBoardData }

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
  /** 本月已过天数 —— 用于「月初基准」提示。 */
  daysElapsed: number
  /** 数据截至时间（ISO 或展示串）。 */
  updatedAt: string
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

/**
 * 取当月看板数据。
 *
 * 取不到就返回 `unavailable` —— 调用方渲染未接入态，
 * **不得**用 0 或空行代替（见文件头说明）。
 *
 * 注意它**可能很慢**（冷缓存时服务端要拉 9 张表）。调用方应先把状态置为
 * `loading`，不要在这一步之前就把界面钉成「未接入」。
 */
export async function fetchProductionBoard(): Promise<ProductionBoardData | null> {
  if (!productionServiceConfigured) return null
  try {
    const res = await fetch(`${SERVICE_ORIGIN}/production/monthly`, {
      headers: { Accept: 'application/json' },
    })
    if (!res.ok) return null
    return (await res.json()) as ProductionBoardData
  } catch {
    return null
  }
}

/**
 * 取 AI 工艺分析结论（读「AI工艺分析结果」表）。
 *
 * 同样：取不到就返回空数组，页面显示「待分析」，
 * 而不是伪造一条结论 —— AI 结论直接影响生产判断，宁可不给。
 */
export async function fetchAiAnalysis(): Promise<AiAnalysisRow[]> {
  if (!productionServiceConfigured) return []
  try {
    const res = await fetch(`${SERVICE_ORIGIN}/production/ai-analysis`, {
      headers: { Accept: 'application/json' },
    })
    if (!res.ok) return []
    const data = (await res.json()) as { rows?: AiAnalysisRow[] }
    return data.rows || []
  } catch {
    return []
  }
}
