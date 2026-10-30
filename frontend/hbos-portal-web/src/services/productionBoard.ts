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

/**
 * 看板取数结果 —— **四态**，不是「有/没有」。
 *
 * 早先对非 2xx、网络错误、未配置一律返回 `null`，页面统一显示「未接入」。
 * 那会把「服务没配」「服务挂了」「上游飞书失败」「会话失效」混成一件事，
 * 运维方向完全错（用户被引导去联系管理员，而实际只需要重试）。
 */
export type BoardResult =
  | { state: 'ready'; data: ProductionBoardData }
  /** 服务未配置 / 未部署 —— 真的还没接入 */
  | { state: 'not_configured' }
  /** 连不上服务（网络层）或服务 5xx —— 该重试 */
  | { state: 'unreachable'; message: string }
  /** 服务活着但上游取数失败（502/503）—— 等待或稍后重试，不是接线问题 */
  | { state: 'upstream_error'; message: string }
  /** 会话/权限问题（401/403）—— 该重新登录或找管理员 */
  | { state: 'unauthorized'; message: string }

/**
 * 取当月看板数据。
 *
 * 取不到时**必须区分原因** —— 调用方据此给出「重试 / 等接入 / 重新登录」
 * 三种完全不同的下一步动作。见 `BoardResult`。
 *
 * 注意它**可能很慢**：冷缓存时服务端要并发拉 13 张表（实测约 19 秒，
 * 首次更久）。调用方应先把状态置为 loading，不要在这一步之前就把界面钉成
 * 「未接入」。
 *
 * @param refresh 点「刷新」时为 true —— 服务端绕过缓存同步重取，
 *   而不是先给旧值再后台更新（否则点了刷新看到的还是同一份数据）。
 */
export async function fetchProductionBoard(
  opts: { refresh?: boolean } = {},
): Promise<BoardResult> {
  if (!productionServiceConfigured) return { state: 'not_configured' }
  let res: Response
  try {
    const url = `${SERVICE_ORIGIN}/production/monthly${opts.refresh ? '?refresh=1' : ''}`
    res = await fetch(url, { headers: { Accept: 'application/json' } })
  } catch {
    return { state: 'unreachable', message: '无法连接生产数据服务，请检查网络或服务是否在运行。' }
  }

  if (res.ok) {
    // 200 但响应体不是 JSON（网关错误页 / 代理截断 / 空响应）不该冒泡成组件错误。
    let body: unknown
    try {
      body = await res.json()
    } catch {
      return { state: 'upstream_error', message: '取数服务返回了无法解析的响应。' }
    }
    // 结构校验：形状不对就当上游异常，别把残缺对象喂给页面算术
    const data = body as Partial<ProductionBoardData> | null
    if (!data || typeof data !== 'object' || !Array.isArray(data.rows) || typeof data.month !== 'string') {
      return { state: 'upstream_error', message: '取数服务返回的数据结构异常。' }
    }
    return { state: 'ready', data: data as ProductionBoardData }
  }
  if (res.status === 401 || res.status === 403) {
    return { state: 'unauthorized', message: '当前身份无权读取生产数据，请重新登录后再试。' }
  }
  if (res.status === 503) {
    return { state: 'upstream_error', message: '取数服务尚未就绪（凭据未配置或上游未连上）。' }
  }
  if (res.status >= 500) {
    return { state: 'upstream_error', message: `取数失败（HTTP ${res.status}），多为上游飞书限流或故障。` }
  }
  return { state: 'unreachable', message: `读取生产数据失败（HTTP ${res.status}）。` }
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
  /** 窗口跨度（月）。当前口径 = 1，即**只看当月**（Owner 2026-10-20）。 */
  windowMonths: number
  /** 窗口起点（含），`YYYY-MM-01`。 */
  windowStart: string
  /** 窗口终点（**不含**），`YYYY-MM-01`；不设上限时为 null。 */
  windowEnd: string | null
  total: number
  closed: number
  rate: number | null
  /** 解析不出日期、未纳入窗口的条数合计（源表有洞时 > 0，脚注要如实说）。 */
  undated: number
  /** 全部已配置的车间（含窗口内无异常的）。 */
  workshops: string[]
  /** 窗口内有记录、真正参与计算的车间。 */
  activeWorkshops: string[]
  byWorkshop: AnomalyWorkshop[]
  /** 取数失败的车间（该车间本轮没有数据，合计数偏低）。 */
  failedWorkshops: string[]
  /** 配置的车间总数 —— 前端据此判断「部分失败」还是「全部失败」。 */
  sourceCount?: number
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
  /** 配置的 QC 数据源总数 —— 前端据此判断「部分失败」还是「全部失败」。 */
  sourceCount?: number
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
  /**
   * 质量数据**自己的**取回时刻，与 `dataAsOf` 可能不同。
   *
   * 质量缓存比 board 活得久（一天 vs 12 小时），所以两者经常不是同一时刻 ——
   * 用一个时间戳标两者，会让上一天的质量结论看起来像刚取的。
   * 旧版服务不返回这个字段，此时前端不单独标注。
   */
  qualityDataAsOf?: string | null
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
  /** 完整报告（Markdown）。**只在 `full=true` 的请求里出现**。 */
  report?: string
}

/**
 * AI 结论的读取结果 —— **三态**，不是「有/没有」。
 *
 * 早先非 2xx、网络异常、无结果全返回 `[]`，页面统一显示「暂无结果」。
 * 服务宕机、权限错误、503 被读成「AI 还没跑」—— 故障被藏起来了。
 */
export type AiAnalysisResult =
  | { state: 'ready'; rows: AiAnalysisRow[] }
  | { state: 'empty' }
  | { state: 'unavailable'; message: string }

/**
 * 取 AI 工艺分析结论（读「AI工艺分析结果」表）。
 *
 * **`full=true` 才带完整报告**，默认只取摘要：
 * 62 道工序 × 每份 800~2000 字 = 十几万字符。看板列表一屏只用得上摘要，
 * 全文留给「查看详情」按需取（见 `fetchAiReport`）。
 */
export async function fetchAiAnalysis(
  opts: { full?: boolean } = {},
): Promise<AiAnalysisResult> {
  if (!productionServiceConfigured) {
    return { state: 'unavailable', message: '生产数据服务尚未接入。' }
  }
  try {
    const url = `${SERVICE_ORIGIN}/production/ai-analysis${opts.full ? '?full=1' : ''}`
    const res = await fetch(url, { headers: { Accept: 'application/json' } })
    if (!res.ok) {
      const hint =
        res.status === 503
          ? 'AI 结果服务尚未就绪。'
          : res.status === 502
            ? 'AI 结果读取失败（上游取数失败）。'
            : `AI 结果读取失败（HTTP ${res.status}）。`
      return { state: 'unavailable', message: hint }
    }
    const data = (await res.json()) as { rows?: AiAnalysisRow[] }
    const rows = Array.isArray(data.rows) ? data.rows : []
    return rows.length ? { state: 'ready', rows } : { state: 'empty' }
  } catch {
    return { state: 'unavailable', message: '无法连接生产数据服务，请稍后重试。' }
  }
}

/**
 * 完整报告缓存 —— 带 **TTL**，并支持手动失效。
 *
 * 早先是模块级永久缓存：16:30 AI 更新后页面会一直读到旧报告，
 * 点看板的「刷新」按钮也不会重取（那个按钮只刷 board 数据）。
 */
const REPORT_CACHE_TTL_MS = 5 * 60 * 1000
let reportCache: { rows: AiAnalysisRow[]; fetchedAt: number } | null = null

/** 让报告缓存失效 —— 看板「刷新」时调用，避免 16:30 之后还读旧报告。 */
export function invalidateAiReportCache(): void {
  reportCache = null
}

export async function fetchAiReport(product: string, process: string): Promise<string | null> {
  if (!productionServiceConfigured) return null
  const fresh = reportCache && Date.now() - reportCache.fetchedAt < REPORT_CACHE_TTL_MS
  if (!fresh) {
    const result = await fetchAiAnalysis({ full: true })
    if (result.state !== 'ready') {
      reportCache = null
      return null
    }
    reportCache = { rows: result.rows, fetchedAt: Date.now() }
  }
  const hit = reportCache?.rows.find((r) => r.product === product && r.process === process)
  return hit?.report ?? null
}
