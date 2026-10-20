import axios, { type AxiosRequestConfig } from 'axios'


interface FrappeMethodResponse<T> {
  message: T
}


interface SessionGuardedRequestConfig extends AxiosRequestConfig {
  hbosCsrfGeneration?: number
  hbosRequestEpoch?: number
}


/* ------------------------------------------------------------------ *
 * Portal provider method envelope (LIMS / Portal read APIs)
 * ------------------------------------------------------------------ */

export interface PortalMethodErrorPayload {
  code?: string
  message?: string
  retryable?: boolean
  trace_id?: string | null
}


export interface PortalMethodEnvelope<T> {
  ok: boolean
  data?: T
  error?: PortalMethodErrorPayload
}


export class PortalMethodError extends Error {
  code: string
  retryable: boolean
  traceId?: string | null

  constructor(error: PortalMethodErrorPayload | undefined, fallback = 'LIMS 数据暂时无法加载。') {
    super(error?.message || fallback)
    this.name = 'PortalMethodError'
    this.code = error?.code || 'PROVIDER_ERROR'
    this.retryable = Boolean(error?.retryable)
    this.traceId = error?.trace_id
  }
}


export function unwrapPortalMethod<T>(envelope: PortalMethodEnvelope<T>): T {
  if (!envelope?.ok) throw new PortalMethodError(envelope?.error)
  if (envelope.data === undefined) throw new PortalMethodError({ code: 'INVALID_RESPONSE', message: 'LIMS 服务返回了无效响应。' })
  return envelope.data
}


/* ------------------------------------------------------------------ *
 * Frappe request error contract (统一账号 / 知识 / 孪生 / P1 APIs)
 * ------------------------------------------------------------------ */
/**
 * Frappe 对「未登录访客」与「已登录但无权」都返回 403，同码不同因。
 * 保留状态码，让上层能分辨后再决定去登录还是去 403 页。
 *
 * 两条前端线各自定义了错误类型：库存线判 `instanceof FrappeHttpError`、
 * 账号/孪生线判 `instanceof FrappeRequestError`。`FrappeRequestError` 继承本类，
 * 故 `callFrappeMethod` 抛出子类时两种判据都能命中，合并后无需改任何调用方。
 */
export class FrappeHttpError extends Error {
  readonly status: number

  constructor(status: number, message: string) {
    super(message)
    this.name = 'FrappeHttpError'
    this.status = status
  }
}


/** 独立 fetch 请求的失败清理只作用于发起请求时的会话。 */
export function createFrappeCsrfInvalidator(): () => void {
  const generation = csrfGeneration
  return () => {
    if (generation === csrfGeneration) clearFrappeCsrfToken()
  }
}


export type FrappeRequestErrorCode =
  | 'UNAUTHENTICATED'
  | 'INVALID_CREDENTIALS'
  | 'INVALID_ORIGIN'
  | 'CSRF_MISMATCH'
  | 'FORBIDDEN'
  | 'NETWORK_ERROR'
  | 'SERVICE_ERROR'
  | 'VALIDATION_ERROR'
  | 'RATE_LIMITED' | 'PROOF_REQUIRED' | 'SESSION_UNCONFIRMED' | 'STALE_RESPONSE' | 'READ_CONFLICT'


export class FrappeRequestError extends FrappeHttpError {
  readonly code: FrappeRequestErrorCode

  constructor(code: FrappeRequestErrorCode, message: string, status?: number, public diagnosticId?: string) {
    super(status ?? 0, message)
    this.name = 'FrappeRequestError'
    this.code = code
  }
}


function responseText(data: unknown): string {
  if (!data || typeof data !== 'object') return String(data || '')
  const payload = data as Record<string, unknown>
  return [
    payload.exc_type,
    payload.exception,
    payload.message,
    payload._error_message,
    payload._server_messages,
  ].filter(Boolean).join(' ')
}


// `frappe.CSRFTokenError` 是一个笼统的异常类型：来源被拒、请求方式异常、令牌轮换都走它。
// 只按异常类型统一提示「安全会话已更新」会把「来源被拒」误导成刷新即可恢复，故按后端消息细分。
const CSRF_REASON_MESSAGES: Record<string, string> = {
  '请求来源无效。': '当前访问来源不是受信任的登录入口，请从正式入口重新登录。',
  '请使用同源 JSON 请求。': '登录请求方式异常，请从正式入口重新登录。',
  '安全会话已更新，请刷新后重试。': '安全会话已更新，请刷新页面后重试。',
  '待绑定请求安全校验失败。': '操作安全校验失败，请重新发起。',
}

const CSRF_DEFAULT_MESSAGE = '安全会话已更新，请刷新页面后重试。'


function firstServerMessage(data: unknown): string {
  try {
    const messages = JSON.parse(String((data as Record<string, unknown> | undefined)?._server_messages || '[]'))
    const first = JSON.parse(messages[0] || '{}')
    if (typeof first.message === 'string') return first.message.replace(/<[^>]*>/g, '').trim()
  } catch { /* 后端未带可读消息时回退到默认提示。 */ }
  return ''
}
export function normalizeFrappeError(error: unknown, method?: string, fact?: Pick<SessionFact, 'authenticated'>): FrappeRequestError {
  if (error instanceof FrappeRequestError) return error
  if (!axios.isAxiosError(error)) return diagnostic()
  if (!error.response) return new FrappeRequestError('NETWORK_ERROR', '网络连接中断，操作结果尚未确认。请恢复连接后重试。')
  const status = error.response.status, detail = responseText(error.response.data)
  const credentialMethod = method === 'login' || method === 'login_mfa' || method?.endsWith('.password_login') || method?.endsWith('.reauthenticate') || method?.endsWith('.verify_feishu_code')
  const loginStep = method === 'login' || method === 'login_mfa' || method?.endsWith('.password_login')
  if (/account has been locked|账号.*锁定/i.test(detail)) return new FrappeRequestError('RATE_LIMITED', '验证尝试较多，当前暂不可用。请稍后重试。', status)
  if (status === 429 || /RateLimitExceededError/i.test(detail)) return new FrappeRequestError('RATE_LIMITED', '验证或请求较频繁，请稍后再试。', status)
  if (/CSRFTokenError|csrf token/i.test(detail)) { if (/请求来源无效/.test(detail)) return new FrappeRequestError('INVALID_ORIGIN', CSRF_REASON_MESSAGES['请求来源无效。']!, status); clearFrappeCsrfToken(); return new FrappeRequestError('CSRF_MISMATCH', CSRF_REASON_MESSAGES[firstServerMessage(error.response.data)] || '安全会话已更新，请重新核对后再提交。', status) }
  if (fact?.authenticated === false && !loginStep) return new FrappeRequestError('UNAUTHENTICATED', '登录状态已失效，请重新登录。', status)
  if (credentialMethod && /AuthenticationError|ExpiredLoginException|incorrect password|invalid login/i.test(detail)) return new FrappeRequestError('INVALID_CREDENTIALS', method === 'login_mfa' ? '二次认证未通过或已过期。请重新登录并输入当前验证码。' : (method === 'login' || method?.endsWith('.password_login') ? '账号或密码不正确。' : '密码或验证码不正确，请重新核对。'), status)
  // Account validation messages must never hide a confirmed Guest boundary.
  if (fact?.authenticated === false || (status === 401 && !credentialMethod && fact?.authenticated !== true)) return new FrappeRequestError('UNAUTHENTICATED', '登录状态已失效，请重新登录。', status)
  const wire = (error.response.data as {message?: {error?: {code?:string;message?:string}}})?.message?.error
  if (status === 409 && wire?.code === 'READ_CONFLICT') return new FrappeRequestError('READ_CONFLICT', '读取遇到暂时冲突，请重试查询。', status)
  if (wire?.code === 'PROOF_REQUIRED') return new FrappeRequestError('PROOF_REQUIRED', '本人身份验证已过期，请重新验证后再保存。', status)
  if (/not whitelisted|not permitted to access this method|Failed to get method/i.test(detail)) return fact?.authenticated ? diagnostic(status) : new FrappeRequestError('SESSION_UNCONFIRMED', '暂时无法确认登录状态，请重试核验或退出登录。', status)
  if (/AuthenticationError/.test(detail) && fact?.authenticated) return new FrappeRequestError('PROOF_REQUIRED', '本人身份验证已过期，请重新验证后再保存。', status)
  const accountMethod = method?.startsWith('hbos_portal.auth.') && !credentialMethod
  if (accountMethod && /ValidationError|AuthenticationError|PermissionError/.test(detail)) {
    const safe = safeAccountMessage(error.response.data)
    if (safe) return new FrappeRequestError('VALIDATION_ERROR', safe, status)
  }
  if (status === 403 || status === 417) return new FrappeRequestError('FORBIDDEN', safeAccountMessage(error.response.data) || '当前账号没有执行此操作的权限。', status)
  if (wire && ['INVALID_REQUEST','CONFLICT','VERSION_CONFLICT','STALE_PREVIEW','INVALID_RULE'].includes(wire.code || '') && typeof wire.message === 'string' && /[\u3400-\u9fff]/.test(wire.message) && !/Traceback|frappe\.|hbos_portal\.|<script/i.test(wire.message)) return new FrappeRequestError('VALIDATION_ERROR', wire.message.replace(/<[^>]*>/g, '').slice(0, 200), status)
  if (status === 400 && /ValidationError/.test(detail)) return new FrappeRequestError('VALIDATION_ERROR', '提交内容未通过核验，请检查填写内容。', status)
  return diagnostic(status)
}


export function isUnauthenticatedError(error: unknown): boolean {
  return error instanceof FrappeRequestError && error.code === 'UNAUTHENTICATED'
}


/* ------------------------------------------------------------------ *
 * HTTP client + CSRF + session guards
 * ------------------------------------------------------------------ */

const http = axios.create({
  baseURL: import.meta.env.VITE_FRAPPE_BASE_URL || '',
  withCredentials: true,
  timeout: 15000,
  headers: {
    'X-Requested-With': 'XMLHttpRequest',
  },
})


let csrfToken: string | null = null

let csrfRequest: Promise<string> | null = null

let csrfGeneration = 0

let allowInjectedCsrf = true


export function clearCachedCsrfToken() {
  csrfGeneration += 1
  csrfToken = null
  csrfRequest = null
  // The HTML belongs to the previous session after login, logout or rotation.
  allowInjectedCsrf = false
}


export const clearFrappeCsrfToken = clearCachedCsrfToken


function bootstrapCsrfToken(): string | null {
  if (typeof window === 'undefined') return null
  const runtime = window as Window & {
    csrf_token?: string
    frappe?: { csrf_token?: string }
  }
  const meta = document.querySelector<HTMLMetaElement>('meta[name="csrf-token"]')?.content
  return runtime.frappe?.csrf_token || runtime.csrf_token || meta || null
}


async function getCsrfToken(): Promise<string> {
  if (allowInjectedCsrf) {
    allowInjectedCsrf = false
    csrfToken ||= bootstrapCsrfToken()
  }
  if (csrfToken) return csrfToken
  if (csrfRequest) return csrfRequest

  const generation = csrfGeneration
  const request = (async () => {
    try {
      const response = await http.get<FrappeMethodResponse<{
        ok: boolean
        data?: { csrf_token: string }
      }>>('/api/method/hbos_portal.api.csrf.get_token', { hbosCsrfGeneration: generation } as SessionGuardedRequestConfig)
      const payload = response.data.message
      if (generation !== csrfGeneration) {
        // Reject the old write without invalidating a newer authenticated session.
        throw new FrappeRequestError('CSRF_MISMATCH', '安全会话已更新，请重试。')
      }
      if (!payload.ok || !payload.data?.csrf_token) {
        throw new FrappeRequestError('UNAUTHENTICATED', '当前会话无法建立安全请求，请重新登录。')
      }
      csrfToken = payload.data.csrf_token
      return csrfToken
    } catch (error) {
      assertCsrfGeneration(generation, error)
      throw normalizeFrappeError(error, 'hbos_portal.api.csrf.get_token')
    }
  })()
  csrfRequest = request
  try {
    return await request
  } finally {
    if (csrfRequest === request) csrfRequest = null
  }
}


let unauthorizedHandler: (() => void) | null = null

// Preserve the current auth failure after its own sign-out clears the token.
// A subsequent session change still makes that failure stale.
const sessionEndedErrors = new WeakMap<object, number>()


/**
 * 注册「会话失效」回调。由 main.ts 在 pinia / router 就绪后注入，
 * 避免 service 层直接 import store 与 router 造成循环依赖。
 */
export function setUnauthorizedHandler(handler: (() => void) | null) {
  unauthorizedHandler = handler
}


/** Frappe 对 Guest 访问受保护方法返回 403，会话过期可能返回 401。 */
export function isAuthError(error: unknown): boolean {
  if (error && typeof error === 'object' && 'code' in error && error.code === 'UNAUTHENTICATED') return true
  if (!axios.isAxiosError(error)) return false
  const status = error.response?.status
  if (status === 401) return true
  if (status !== 403) return false
  const payload = error.response?.data as { code?: string; error?: { code?: string }; exc_type?: string } | undefined
  return payload?.code === 'UNAUTHENTICATED'
    || payload?.error?.code === 'UNAUTHENTICATED'

}


http.interceptors.request.use(async (config) => {
  const guarded = config as typeof config & SessionGuardedRequestConfig
  guarded.hbosCsrfGeneration ??= csrfGeneration
  guarded.hbosRequestEpoch ??= requestEpoch
  if (config.method?.toLowerCase() !== 'get' && writesBlocked && !/\/(logout|login|hbos_portal.auth.accounts.password_login)$/.test(String(config.url))) throw new FrappeRequestError('SESSION_UNCONFIRMED', '正在核对当前登录状态，请稍后再提交。')
  if (config.method?.toLowerCase() === 'get') return config
  // A fresh login/security token must never be replaced by an older cache.
  if (config.headers.has('X-Frappe-CSRF-Token')) return config
  const url = String(config.url || '')
  if (url === '/api/method/login' || url === '/api/method/hbos_portal.auth.accounts.password_login') return config
  config.headers['X-Frappe-CSRF-Token'] = await getCsrfToken()
  assertCsrfGeneration(guarded.hbosCsrfGeneration)
  return config
})


http.interceptors.response.use(
  (response) => { const epoch = (response.config as SessionGuardedRequestConfig).hbosRequestEpoch; if (epoch !== undefined) assertEpoch(epoch); return response },
  (error) => {
    const epoch = (error?.config as SessionGuardedRequestConfig | undefined)?.hbosRequestEpoch
    if (epoch !== undefined && epoch !== requestEpoch) return Promise.reject(new FrappeRequestError('STALE_RESPONSE', '会话已改变，已丢弃先前请求的结果。'))
    const generation = (error?.config as SessionGuardedRequestConfig | undefined)?.hbosCsrfGeneration
    if (generation !== undefined && generation !== csrfGeneration) {
      // A previous session's read must not clear the new token or sign it out.
      return Promise.reject(new FrappeRequestError('CSRF_MISMATCH', '安全会话已更新，请重试。'))
    }
    if (axios.isAxiosError(error) && /CSRFTokenError|csrf token/i.test(responseText(error.response?.data))) {
      clearCachedCsrfToken()
    }
    // AuthenticationError may mean expired proof; wrappers probe the current session
    // before dispatching a confirmed session boundary.
    return Promise.reject(error)
  },
)


function assertCsrfGeneration(generation: number, error?: unknown) {
  const endedAt = error && typeof error === 'object' ? sessionEndedErrors.get(error) : undefined
  if (generation !== csrfGeneration && endedAt !== csrfGeneration) {
    throw new FrappeRequestError('CSRF_MISMATCH', '安全会话已更新，请重新确认后重试。')
  }
}


export async function callFrappeMethod<T>(
  method: string,
  params?: Record<string, unknown>,
  options?: { requireCsrf?: boolean },
): Promise<T> {
  const epoch = requestEpoch
  recordRead(method)
  const generation = options?.requireCsrf === true ? csrfGeneration : undefined
  try {
    let headers: Record<string, string> | undefined
    if (generation !== undefined) {
      const token = await getCsrfToken()
      if (generation !== csrfGeneration) {
        throw new FrappeRequestError('CSRF_MISMATCH', '安全会话已更新，请重试。')
      }
      headers = { 'X-Frappe-CSRF-Token': token }
    }
    const config: SessionGuardedRequestConfig = { params, ...(headers ? { headers, hbosCsrfGeneration: generation } : {}) }
    const response = await http.get<FrappeMethodResponse<T>>(`/api/method/${method}`, config)
    if (generation !== undefined && generation !== csrfGeneration) {
      throw new FrappeRequestError('CSRF_MISMATCH', '安全会话已更新，请重试。')
    }
    assertEpoch(epoch); return response.data.message
  } catch (error) {
    // 走 normalizeFrappeError：既保留服务端中文业务提示、又带上 `code` 供
    // 账号 / 孪生线分流。它产出的 `FrappeRequestError` 是 `FrappeHttpError`
    // 的子类，库存线判 `instanceof FrappeHttpError` 同样命中。
    throw await requestError(error, method, epoch)
  }
}


/** 调用 LIMS 领域写操作；CSRF 与会话由同一 Portal 客户端统一处理。 */
export async function callFrappeAction<T>(
  method: string,
  params?: Record<string, unknown>,
): Promise<T> {
  return callFrappePostMethod<T>(method, params)
}


// ---------------------------------------------------------------------------
// CSRF（库存与账号共用 Portal 当前会话生命周期）
// ---------------------------------------------------------------------------

/**
 * 统一产品 Portal 只维护一份当前会话 token。登录、退出、账号变更或 CSRF 失败
 * 统一清理，库存写入与账号写入都不能继续使用旧缓存或旧页面注入值。
 * 取 token 失败即停止本次请求；用户重新确认后才能重新发起写入。
 */
export async function ensureCsrfToken(): Promise<string> {
  return getCsrfToken()
}


async function withCsrf(): Promise<Record<string, string>> {
  const generation = csrfGeneration
  const token = await ensureCsrfToken()
  assertCsrfGeneration(generation)
  return { 'X-Frappe-CSRF-Token': token }
}


/** 报表等现有调用方保留同一接口，凭据来源与其他 Portal 请求一致。 */
export async function csrfHeaders(): Promise<Record<string, string>> {
  return withCsrf()
}


// ---------------------------------------------------------------------------
// 单据读写（库存线）
// ---------------------------------------------------------------------------

/**
 * `getDocument` 对返回类型的最低要求：得能拿到单据号。
 *
 * **只要求 `name`**，不要求 `doctype` —— `frappe.client.get` 的返回里**没有**
 * `doctype` 字段（它的名字就是参数，不再回显）。要求它就等于逼调用方去补一个
 * 服务端根本没给的字段。
 */
export interface FrappeDocPayload {
  name: string
}


/**
 * 读一份文档的**当前完整内容**，用于「改」与「提交」。
 *
 * ## 为什么必须读全文，而不是只传 `{doctype, name}`
 *
 * `frappe.client.submit(doc)` 内部是 `frappe.get_doc(dict)` —— 它**不是按名字去库里
 * 加载**，而是**拿传进来的 dict 当这份文档**。所以只传 `{doctype, name}` 会：
 *
 * 1. 文档没有 `modified` → `check_if_latest()` 判定「你打开后别人改过」→
 *    抛 `TimestampMismatchError`（实测）；
 * 2. 就算过了那关，文档也没有 `purpose` 等字段 → 校验会报「目的必须是一个…」（实测）。
 *
 * 实测：先 `get` 取全文、再提交那个 dict → `docstatus = 1` ✅。
 *
 * `frappe.client.save` 同理（走同一个 `get_doc(dict)`）——**改和提交都要走这里**。
 */
export async function getDocument<T extends FrappeDocPayload = FrappeDocPayload>(
  doctype: string,
  name: string,
): Promise<T> {
  const doc = await callFrappeMethod<T | null>('frappe.client.get', { doctype, name })
  if (!doc || !doc.name) throw new FrappeHttpError(404, '找不到这份单据。')
  return doc
}



/**
 * 提交一份单据。
 *
 * **先读全文再提交**——理由见 `getDocument`。不要退回成
 * `submit({doctype, name})`，那是实测会失败的写法。
 */
export async function submitDocument(doctype: string, name: string): Promise<void> {
  const doc = await getDocument(doctype, name)
  await postFrappeMethod('frappe.client.submit', { doc: JSON.stringify(doc) })
}


/**
 * 取消一份已提交的单据（`docstatus` 1 → 2）。账面会反向过账。
 *
 * **这里只传 `doctype + name`，不要照抄 `submitDocument` 的先读全文**：
 * `frappe.client.cancel` 内部是 `frappe.get_doc(doctype, name)`——它按名字去库里
 * 加载全文；而 `submit` 走 `frappe.get_doc(dict)`，把传进去的 dict **当文档用**，
 * 所以那边必须先读。两者语义相反，别互相抄。
 *
 * **权限不在前端判**：服务端按 `cancel` 权限拒（`Stock User` 在 `Stock Entry` /
 * `Pick List` 上有，`Stock Reconciliation` 只有 `Stock Manager`）。拒绝了就把它的
 * 中文提示原样呈现给用户。
 *
 * 取消后**删不掉**这张单（`frappe.client.delete` 会报 `LinkExistsError`，库存流水
 * 还引用着它）——已取消的单据是审计留痕，这是刻意的。
 */
export async function cancelDocument(doctype: string, name: string): Promise<void> {
  await postFrappeMethod('frappe.client.cancel', { doctype, name })
}


/**
 * 保存一份单据。
 *
 * 也要**先读全文再改**：`frappe.client.save` 走 `frappe.get_doc(dict)`，
 * 只传部分字段会把没传的字段清掉。调用方在这份全文上覆盖要改的字段即可。
 */
export async function saveDocument(
  doctype: string,
  name: string,
  changes: Record<string, unknown>,
): Promise<void> {
  const doc = await getDocument(doctype, name)
  await postFrappeMethod('frappe.client.save', {
    doc: JSON.stringify({ ...doc, ...changes }),
  })
}


/**
 * 调一个单据的**控制器方法**（ERPNext 里那些挂在表单上的按钮）。
 *
 * 走 `run_doc_method`——它要求方法带 `@frappe.whitelist()`，且**单据必须已存在**
 * （它按 `dt` + `dn` 去库里加载，与 `frappe.client.submit` 的语义相反）。
 *
 * 用途：拣货单的「定位货位」就是 ERPNext 自己的 `PickList.set_item_locations`。
 * 复用它能保证与本页无关的规则（预留、批次、优先货位）一条都不重写。
 *
 * 返回值是 `{docs: [...]}`——把服务端处理后的文档原样带回来，调用方据此刷新界面。
 */
export async function runDocMethod<T = unknown>(
  doctype: string,
  name: string,
  method: string,
  args: Record<string, unknown> = {},
): Promise<T> {
  return postFrappeMethod<T>('run_doc_method', {
    dt: doctype,
    dn: name,
    method,
    args: JSON.stringify(args),
  })
}


// ---------------------------------------------------------------------------
// 地址与主机名
// ---------------------------------------------------------------------------

const LOOPBACK_HOSTS = new Set(['localhost', '127.0.0.1', '[::1]'])


/**
 * Frappe 下发的 `sid` 是 host-only Cookie（没有 Domain 属性），所以
 * `localhost` 的登录态**不会**发给 `127.0.0.1`，反之亦然。两个名字指向同一台机器，
 * 但浏览器把它们当成两个不同的站点。
 *
 * 这里在**双方都是回环地址**时才把主机名对齐到当前页面——仅限本地开发的这个坑，
 * 真实域名之间不会发生替换。
 */
export function alignLoopbackHost(origin: string): string {
  if (typeof window === 'undefined') return origin

  try {
    const configured = new URL(origin)
    const current = window.location
    if (
      LOOPBACK_HOSTS.has(configured.hostname) &&
      LOOPBACK_HOSTS.has(current.hostname) &&
      configured.hostname !== current.hostname
    ) {
      configured.hostname = current.hostname
    }
    return configured.origin
  } catch {
    return origin
  }
}


/**
 * 把 Frappe 返回的相对地址（如 `/private/files/xxx.png`）拼成可用的绝对地址。
 *
 * **必须这样拼**：这些地址不属于 `/api`，不会被 Portal 的 dev proxy 转发。
 * 实测直接把 `/private/files/...` 塞进 `<img src>`，请求打到 Vite dev server、
 * 被 SPA fallback 兜成 `index.html`（**200 但 content-type 是 text/html**），
 * 图片自然显示不出来（`naturalWidth === 0`）。
 *
 * 用 `VITE_FRAPPE_APP_ORIGIN`（Frappe **在哪**），不是 `VITE_FRAPPE_BASE_URL`
 * （axios 的 baseURL，同源代理时为空）。两者语义不同，用错就拼不出地址。
 *
 * 同源部署时 `VITE_FRAPPE_APP_ORIGIN` 为空，返回原相对地址即可。
 */
export function frappeAssetUrl(path: string): string {
  const value = String(path || '')
  if (!value) return ''
  if (/^https?:\/\//i.test(value)) return value

  const origin = String(import.meta.env.VITE_FRAPPE_APP_ORIGIN || '')
    .trim()
    .replace(/\/+$/, '')
  if (!origin) return value

  return `${alignLoopbackHost(origin)}${value.startsWith('/') ? value : `/${value}`}`
}


export async function postFrappeMethod<T>(
  method: string,
  params?: Record<string, unknown>,
): Promise<T> {
  if (writesBlocked) throw new FrappeRequestError('SESSION_UNCONFIRMED', '正在核对当前登录状态，请稍后再提交。')
  const epoch = requestEpoch
  const generation = csrfGeneration
  try {
    const headers = await withCsrf()
    assertCsrfGeneration(generation)
    const response = await http.post<FrappeMethodResponse<T>>(
      `/api/method/${method}`,
      params,
      { headers, hbosCsrfGeneration: generation } as SessionGuardedRequestConfig,
    )
    assertEpoch(epoch); return response.data.message
  } catch (error) {
    assertCsrfGeneration(generation, error)
    throw await requestError(error, method, epoch)
  }
}


/**
 * 上传文件（multipart）。`upload_file` 同样是 POST，需要 CSRF。
 *
 * 不走 axios 的 `baseURL`——调用方给的是 Frappe 侧的绝对地址（跨源时带 origin），
 * 因为 Portal 与 Frappe 可能不同源。
 */
export async function uploadFrappeFile(
  endpoint: string,
  file: File,
  fields: Record<string, string> = {},
): Promise<Record<string, unknown>> {
  if (writesBlocked) throw new FrappeRequestError('SESSION_UNCONFIRMED', '正在核对当前登录状态，请稍后再提交。')
  const epoch = requestEpoch
  const generation = csrfGeneration
  const form = new FormData()
  form.append('file', file)
  for (const [key, value] of Object.entries(fields)) form.append(key, value)

  try {
    const headers = await withCsrf()
    assertCsrfGeneration(generation)
    const response = await http.post<FrappeMethodResponse<Record<string, unknown>>>(
      endpoint,
      form,
      { headers, hbosCsrfGeneration: generation } as SessionGuardedRequestConfig,
    )
    assertEpoch(epoch); return response.data.message || {}
  } catch (error) {
    assertCsrfGeneration(generation, error)
    throw await requestError(error, 'upload_file', epoch)
  }
}


function toFrappeError(error: unknown): FrappeHttpError {
  if (error instanceof FrappeRequestError) return error
  if (axios.isAxiosError(error)) {
    const normalized = normalizeFrappeError(error)
    if (normalized.code === 'CSRF_MISMATCH' || normalized.code === 'UNAUTHENTICATED') return normalized
    const status = error.response?.status ?? 0
    // 服务端的中文业务提示优先于 axios 的英文 message——EA-5.4 §28 要求
    // 用户看到的是业务语义，不是「Request failed with status code 400」
    const serverMessage = extractServerMessage(error.response?.data)
    return new FrappeHttpError(status, serverMessage || 'HBOS 服务暂时不可用')
  }
  return new FrappeHttpError(0, 'HBOS 服务不可达')
}


/** Frappe 把业务错误塞在 `_server_messages` 里，结构是「JSON 数组的 JSON 字符串」 */
function extractServerMessage(data: unknown): string | null {
  if (!data || typeof data !== 'object') return null
  const raw = (data as { _server_messages?: unknown })._server_messages
  if (typeof raw !== 'string') return null
  try {
    const outer = JSON.parse(raw) as unknown
    if (!Array.isArray(outer)) return null
    const messages: string[] = []
    for (const item of outer) {
      try {
        const parsed = typeof item === 'string' ? JSON.parse(item) : item
        const message = (parsed as { message?: unknown })?.message
        if (typeof message === 'string' && message) {
          // 去掉 Frappe 自动套上的 <strong> / <br>，只留可读文字
          messages.push(message.replace(/<[^>]+>/g, '').trim())
        }
      } catch {
        /* 单条解析失败就跳过，不影响其余 */
      }
    }
    return messages.length ? messages.join('　') : null
  } catch {
    return null
  }
}


/**
 * 会话是否仍然有效。
 *
 * 判定 403 的真正成因时必须先问这一句：`frappe.auth.get_logged_user` 对访客
 * 同样返回 403，所以「收到 403」本身并不等于「没有权限」。
 */
export async function hasFrappeSession(): Promise<boolean> {
  try {
    const response = await http.get<FrappeMethodResponse<string>>(
      '/api/method/frappe.auth.get_logged_user',
    )
    const user = String(response.data.message || '')
    return Boolean(user) && user !== 'Guest'
  } catch {
    return false
  }
}


// ---------------------------------------------------------------------------
// 账号 / 会话（账号线：统一账号发布带入）
// ---------------------------------------------------------------------------

export async function callFrappePostMethod<T>(
  method: string,
  data?: Record<string, unknown>,
  extraHeaders?: Record<string, string>,
): Promise<T> {
  if (writesBlocked) throw new FrappeRequestError('SESSION_UNCONFIRMED', '正在核对当前登录状态，请稍后再提交。')
  const epoch = requestEpoch
  const generation = csrfGeneration
  try {
    const token = await getCsrfToken()
    assertCsrfGeneration(generation)
    const response = await http.post<FrappeMethodResponse<T>>(
      `/api/method/${method}`,
      data || {},
      {
        hbosCsrfGeneration: generation,
        headers: {
          'X-Frappe-CSRF-Token': token,
          'Content-Type': 'application/json',
          ...extraHeaders,
        },
      } as SessionGuardedRequestConfig,
    )
    assertEpoch(epoch); return response.data.message
  } catch (error) {
    assertCsrfGeneration(generation, error)
    throw await requestError(error, method, epoch)
  }
}


export interface PasswordLoginResult { tmp_id?: string; verification?: unknown; message?: string }
export async function loginWithPassword(username: string, password: string, otp = '', tmpId = ''): Promise<PasswordLoginResult> {
  try {
    const security = await probeFrappeSession()
    const result = await http.post<{message: PasswordLoginResult}>('/api/method/hbos_portal.auth.accounts.password_login', { username, password, otp, tmp_id: tmpId }, { headers: { 'Content-Type': 'application/json', ...(security.csrf_token ? { 'X-Frappe-CSRF-Token': security.csrf_token } : {}) } })
    invalidateFrappeRequests(); return result.data.message
  } catch (error) { throw normalizeFrappeError(error, tmpId ? 'login_mfa' : 'login') }
}


/**
 * 经当前 origin 登录 Frappe（开发环境由 Vite 代理到 Frappe）。
 * 必须使用表单编码；Frappe 的 /api/method/login 不接受 JSON body。
 */
export async function login(usr: string, pwd: string): Promise<void> {
  const body = new URLSearchParams({ usr, pwd })
  await http.post('/api/method/login', body)
  clearCachedCsrfToken()
}


/** Frappe 标准登出：服务端结束会话成功后才清除本地会话。 */
export async function logout(): Promise<void> {
  await http.post('/api/method/logout')
  clearCachedCsrfToken()
}
export async function logoutFrappeSession(): Promise<void> {
  // Only logout may retry once after a native CSRF rotation. Business writes
  // are never replayed, even if their outcome is uncertain.
  const epoch = requestEpoch
  let fact = await probeFrappeSession(); assertEpoch(epoch)
  const originalContext = fact.session_context
  if (!fact.authenticated) { clearFrappeCsrfToken(); return }
  for (let attempt = 0; attempt < 2; attempt++) {
    try {
      await http.post('/api/method/logout', {}, { headers: { 'X-Frappe-CSRF-Token': fact.csrf_token || '', 'Content-Type': 'application/json' } })
      assertEpoch(epoch)
      const after = await probeFrappeSession(); assertEpoch(epoch)
      if (after.authenticated) throw new FrappeRequestError('SESSION_UNCONFIRMED', '服务端尚未确认退出，请重试退出。')
      clearFrappeCsrfToken(); return
    } catch (error) {
      const normalized = normalizeFrappeError(error, 'logout')
      assertEpoch(epoch)
      if (attempt === 0 && normalized.code === 'CSRF_MISMATCH') {
        fact = await probeFrappeSession(); assertEpoch(epoch)
        if (!fact.authenticated) return
        if (fact.session_context !== originalContext) throw new FrappeRequestError('SESSION_UNCONFIRMED', '当前登录会话已变化，请核对身份后重新退出。')
        continue
      }
      throw normalized
    }
  }
}
let requestEpoch = 0
let writesBlocked = false
function recordRead(method: string) {
  if (!import.meta.env.DEV) return
  if (method === 'hbos_portal.auth.accounts.get_security') frappeDiagnostics.security++
  if (method === 'hbos_portal.api.iam_access.get_capabilities') frappeDiagnostics.capabilities++
  if (method === 'hbos_portal.api.bootstrap.get_bootstrap') frappeDiagnostics.bootstrap++
}
function diagnostic(status?: number) {
  const id = globalThis.crypto?.randomUUID?.().slice(0, 8) || Math.random().toString(16).slice(2, 10)
  // Log metadata only: never framework payloads, URLs, identities or credentials.
  console.warn('[HBOS 服务诊断]', { id, status })
  return new FrappeRequestError('SERVICE_ERROR', `服务暂时无法完成请求，请重试或联系管理员。诊断编号：${id}`, status, id)
}
function safeAccountMessage(data: unknown): string | null {
  try {
    const messages = JSON.parse(String((data as Record<string, unknown>)._server_messages || '[]'))
    const message = JSON.parse(messages[0] || '{}').message
    if (typeof message === 'string' && /[\u3400-\u9fff]/.test(message) && !/Traceback|File \\"|hbos_portal\.|frappe\.|<script|exception/i.test(message)) return message.replace(/<[^>]*>/g, '').slice(0, 200)
  } catch { /* Only a bounded, user-facing Chinese message may leave this boundary. */ }
  return null
}
interface SessionFact { authenticated: boolean; session_context: string | null; csrf_token?: string | null }
export async function probeFrappeSession(): Promise<SessionFact> {
  try {
    const response = await http.get<FrappeMethodResponse<SessionFact>>('/api/method/hbos_portal.auth.accounts.get_request_security', { headers: { 'Cache-Control': 'no-cache' } })
    const value = response.data.message
    if (typeof value?.authenticated !== 'boolean' || (value.authenticated && (typeof value.session_context !== 'string' || value.session_context.length !== 64))) throw new FrappeRequestError('SESSION_UNCONFIRMED', '暂时无法确认登录状态，请重试核验。')
    return value
  } catch (error) { throw normalizeFrappeError(error, 'session_probe') }
}
async function requestError(error: unknown, method: string, epoch: number): Promise<FrappeRequestError> {
  assertEpoch(epoch)
  let fact: SessionFact | undefined
  if (axios.isAxiosError(error) && error.response && (error.response.status === 401 || [403, 417].includes(error.response.status) && /AuthenticationError|not whitelisted|not permitted to access this method|login to access|Failed to get method/i.test(responseText(error.response.data))) && !['login', 'login_mfa'].includes(method)) {
    try { fact = await probeFrappeSession() } catch { /* An inconclusive probe cannot establish Guest. */ }
  }
  const normalized = normalizeFrappeError(error, method, fact)
  assertEpoch(epoch)
  if (normalized.code === 'UNAUTHENTICATED') { unauthorizedHandler?.(); if (typeof window !== 'undefined') window.dispatchEvent(new CustomEvent('hbos:session-expired')); if (typeof normalized === 'object') sessionEndedErrors.set(normalized, csrfGeneration) }
  return normalized
}
function assertEpoch(epoch: number) { if (epoch !== requestEpoch) throw new FrappeRequestError('STALE_RESPONSE', '会话已改变，已丢弃先前请求的结果。') }
export function blockFrappeWrites(blocked: boolean) { writesBlocked = blocked }
export function invalidateFrappeRequests() { requestEpoch++; clearFrappeCsrfToken() }
export const frappeDiagnostics = { document: import.meta.env.DEV ? crypto.randomUUID() : '', security: 0, capabilities: 0, bootstrap: 0 }
export const developmentObservation = import.meta.env.DEV && typeof window !== 'undefined' && new URLSearchParams(window.location.search).get('iam_uat') === '1'
