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

/** 一个看板行的质量统计（当月）。 */
export interface QualityRow {
  label: string
  /** 已检批次 —— 会议口径下「登记即合格」。 */
  tested: number
  /** 判定不合格（夹在两个已检批次之间的空档）。 */
  failed: number
  /** 未检测（最后一个已检批次之后）—— **不进分母**。 */
  untested: number
  /** 合格率；没有已检批次时为 null（不是 100%）。 */
  rate: number | null
  failedBatches: string[]
}

/**
 * 质量合格率（会议 2026-10-19 定的取数规则）。
 *
 * **分母只是已检批次，不是当月全部批次。** 月初设备调试或刚开产时
 * 可能只检了 2 批就是 100% —— 页面必须把 `tested / (tested + failed)`
 * 和 `untested` 一并显示，否则「100%」会被读成「全批全检全合格」。
 */
export interface QualityInfo {
  month: string
  tested: number
  failed: number
  untested: number
  rate: number | null
  byLabel: QualityRow[]
  /** 有 QC 数据源的行。不在这个列表里的行**没有质量数据源**（如无菌两行）。 */
  coveredLabels: string[]
  /** 取数失败的 QC 表（该行本轮没有质量数据）。 */
  failedLabels: string[]
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
   * 服务端缓存命中时它会早于现在 —— 页面据此标「数据截至」，
   * 让看的人知道手里这份是几分钟前的还是刚拉的。
   */
  dataAsOf: string | null
  rows: ProductionRow[]
  anomaly?: AnomalyInfo
  quality?: QualityInfo | null
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
 * 注意它**可能很慢**：冷缓存时服务端要拉 9 张表（20~30 秒），
 * `refresh: true` 时服务端会**同步**重拉，同样是这个量级。
 * 调用方应先把状态置为 loading，不要在这一步之前就把界面钉成「未接入」。
 *
 * @param refresh 点「刷新」时为 true —— 服务端绕过缓存同步重取，
 *   而不是先给旧值再后台更新（否则点了刷新看到的还是同一份数据）。
 */
export async function fetchProductionBoard(
  opts: { refresh?: boolean } = {},
): Promise<ProductionBoardData | null> {
  if (!productionServiceConfigured) return null
  try {
    const url = `${SERVICE_ORIGIN}/production/monthly${opts.refresh ? '?refresh=1' : ''}`
    const res = await fetch(url, { headers: { Accept: 'application/json' } })
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
