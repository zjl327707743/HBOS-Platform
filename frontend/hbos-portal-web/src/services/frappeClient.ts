import axios, { type AxiosRequestConfig } from 'axios'

interface FrappeMethodResponse<T> {
  message: T
}

interface SessionGuardedRequestConfig extends AxiosRequestConfig {
  hbosCsrfGeneration?: number
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

export type FrappeRequestErrorCode =
  | 'UNAUTHENTICATED'
  | 'INVALID_CREDENTIALS'
  | 'INVALID_ORIGIN'
  | 'CSRF_MISMATCH'
  | 'FORBIDDEN'
  | 'NETWORK_ERROR'
  | 'SERVICE_ERROR'
  | 'VALIDATION_ERROR'
  | 'RATE_LIMITED'

export class FrappeRequestError extends Error {
  code: FrappeRequestErrorCode
  status?: number

  constructor(code: FrappeRequestErrorCode, message: string, status?: number) {
    super(message)
    this.name = 'FrappeRequestError'
    this.code = code
    this.status = status
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

export function normalizeFrappeError(error: unknown, method?: string): FrappeRequestError {
  if (error instanceof FrappeRequestError) return error
  if (!axios.isAxiosError(error)) {
    return new FrappeRequestError('SERVICE_ERROR', 'HBOS 服务暂时不可用，请稍后重试。')
  }
  if (!error.response) {
    return new FrappeRequestError('NETWORK_ERROR', '无法连接 HBOS 服务，请检查本机服务状态。')
  }

  const status = error.response.status
  const detail = responseText(error.response.data)
  const isBootstrap = method === 'hbos_portal.api.bootstrap.get_bootstrap'
  const isGuestPermission = /\bGuest\b|not permitted to access this method|login to access/i.test(detail)
  if (status === 429 || /RateLimitExceededError/.test(detail)) return new FrappeRequestError('RATE_LIMITED', '请求较频繁，请稍后再试。', status)
  if (/SecurityException/.test(detail) && /account has been locked|账号.*锁定/i.test(detail)) {
    return new FrappeRequestError('RATE_LIMITED', '验证尝试较多，当前暂不可用。请稍后重试。', status)
  }
  if (method === 'login_mfa' && /AuthenticationError|ExpiredLoginException/.test(detail)) {
    return new FrappeRequestError('INVALID_CREDENTIALS', '二次认证未通过或已过期。请重新登录并输入当前验证码。', status)
  }
  const accountMethod = method?.startsWith('hbos_portal.auth.') && !method.endsWith('password_login')
  if (accountMethod && /ValidationError|AuthenticationError|PermissionError/.test(String((error.response.data as Record<string, unknown>)?.exc_type))) {
    try {
      const data = error.response.data as Record<string, unknown>
      const messages = JSON.parse(String(data._server_messages || '[]'))
      const first = JSON.parse(messages[0] || '{}')
      if (typeof first.message === 'string') return new FrappeRequestError('VALIDATION_ERROR', first.message.replace(/<[^>]*>/g, '').slice(0, 500), status)
    } catch { /* Never show framework exceptions or request metadata. */ }
  }
  if (/AuthenticationError|invalid login|incorrect password/i.test(detail)) {
    return new FrappeRequestError('INVALID_CREDENTIALS', '账号或密码不正确。', status)
  }
  if (status === 401 || ((status === 403 || status === 417) && (isBootstrap || isGuestPermission))) {
    return new FrappeRequestError('UNAUTHENTICATED', '登录状态已失效，请重新登录。', status)
  }
  if (/CSRFTokenError|csrf token/i.test(detail)) {
    const serverMessage = firstServerMessage(error.response.data)
    const message = CSRF_REASON_MESSAGES[serverMessage] || CSRF_DEFAULT_MESSAGE
    if (/请求来源无效/.test(detail)) {
      return new FrappeRequestError('INVALID_ORIGIN', CSRF_REASON_MESSAGES['请求来源无效。'] ?? CSRF_DEFAULT_MESSAGE, status)
    }
    clearCachedCsrfToken()
    return new FrappeRequestError('CSRF_MISMATCH', message, status)
  }
  if (status === 403 || status === 417) {
    return new FrappeRequestError('FORBIDDEN', '当前账号没有执行此操作的权限。', status)
  }
  return new FrappeRequestError('SERVICE_ERROR', 'HBOS 服务请求失败，请稍后重试。', status)
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
    || payload?.exc_type === 'AuthenticationError'
}

http.interceptors.request.use(async (config) => {
  if (config.method?.toLowerCase() === 'get') return config
  // A fresh login/security token must never be replaced by an older cache.
  if (config.headers.has('X-Frappe-CSRF-Token')) return config
  const url = String(config.url || '')
  if (url === '/api/method/login' || url === '/api/method/hbos_portal.auth.accounts.password_login') return config
  config.headers['X-Frappe-CSRF-Token'] = await getCsrfToken()
  return config
})

http.interceptors.response.use(
  (response) => response,
  (error) => {
    const generation = (error?.config as SessionGuardedRequestConfig | undefined)?.hbosCsrfGeneration
    if (generation !== undefined && generation !== csrfGeneration) {
      // A previous session's read must not clear the new token or sign it out.
      return Promise.reject(new FrappeRequestError('CSRF_MISMATCH', '安全会话已更新，请重试。'))
    }
    if (axios.isAxiosError(error) && /CSRFTokenError|csrf token/i.test(responseText(error.response?.data))) {
      clearCachedCsrfToken()
    }
    const url = String(error?.config?.url || '')
    // 登录请求自身的 401 由登录页就近提示，不触发跳转。
    if (isAuthError(error) && !url.includes('/api/method/login')) {
      unauthorizedHandler?.()
    }
    return Promise.reject(error)
  },
)

export async function callFrappeMethod<T>(
  method: string,
  params?: Record<string, unknown>,
  options?: { requireCsrf?: boolean },
): Promise<T> {
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
    return response.data.message
  } catch (error) {
    // These fixed read methods use the Portal error envelope even on non-2xx
    // responses. Preserve only reviewed codes; never render native error data.
    const queries = ['get_management_context', 'list_positions', 'get_person_assignments', 'lookup_people']
    const query = method.startsWith('hbos_portal.api.organization_relations.')
      && queries.includes(method.slice('hbos_portal.api.organization_relations.'.length))
    if (query && axios.isAxiosError(error)) {
      const payload = error.response?.data as { message?: unknown } | undefined
      const raw = payload?.message ?? error.response?.data
      if (raw && typeof raw === 'object') {
        const envelope = raw as PortalMethodEnvelope<unknown>
        const code = envelope.ok === false ? envelope.error?.code : undefined
        const messages: Record<string, string> = {
          NOT_SUPPORTED: '岗位与任职查询尚未启用。',
          FORBIDDEN: '当前账号没有查看岗位或任职资料的权限。',
          UNAUTHENTICATED: '登录状态已失效，请重新登录。',
          SOURCE_UNAVAILABLE: '岗位与任职资料暂时无法读取，请稍后重试。',
          CONFLICT: '查询条件或权限已更新，请重新查询。',
          CONFLICT_RETRY_REQUIRED: '查询条件或权限已更新，请重新查询。',
          INVALID_REQUEST: '查询条件无效，请检查后重试。',
        }
        if (typeof code === 'string' && Object.prototype.hasOwnProperty.call(messages, code)) {
          throw new PortalMethodError({ code, message: messages[code], retryable: envelope.error?.retryable === true })
        }
      }
    }
    throw normalizeFrappeError(error, method)
  }
}

/** 调用 LIMS 领域写操作；CSRF 与会话由同一 Portal 客户端统一处理。 */
export async function callFrappeAction<T>(
  method: string,
  params?: Record<string, unknown>,
): Promise<T> {
  return callFrappePostMethod<T>(method, params)
}

export async function callFrappePostMethod<T>(
  method: string,
  data?: Record<string, unknown>,
  extraHeaders?: Record<string, string>,
): Promise<T> {
  try {
    const token = await getCsrfToken()
    const response = await http.post<FrappeMethodResponse<T>>(
      `/api/method/${method}`,
      data || {},
      {
        headers: {
          'X-Frappe-CSRF-Token': token,
          'Content-Type': 'application/json',
          ...extraHeaders,
        },
      },
    )
    return response.data.message
  } catch (error) {
    throw normalizeFrappeError(error, method)
  }
}

export interface PasswordLoginResult { tmp_id?: string; verification?: unknown; message?: string }
export async function loginWithPassword(username: string, password: string, otp = '', tmpId = ''): Promise<PasswordLoginResult> {
  try {
    const security = await http.get<{ message: { csrf_token?: string } }>('/api/method/hbos_portal.auth.accounts.get_request_security')
    const result = await http.post<{ message: PasswordLoginResult }>('/api/method/hbos_portal.auth.accounts.password_login', { username, password, otp, tmp_id: tmpId }, {
      headers: { 'Content-Type': 'application/json', 'X-Requested-With': 'XMLHttpRequest', ...(security.data.message.csrf_token ? { 'X-Frappe-CSRF-Token': security.data.message.csrf_token } : {}) },
    })
    clearCachedCsrfToken()
    return result.data.message
  } catch (error) {
    throw normalizeFrappeError(error, tmpId ? 'login_mfa' : 'login')
  }
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
  try {
    const token = await getCsrfToken()
    await http.post('/api/method/logout', {}, {
      headers: {
        'X-Frappe-CSRF-Token': token,
        'Content-Type': 'application/json',
      },
    })
    clearCachedCsrfToken()
  } catch (error) {
    throw normalizeFrappeError(error, 'logout')
  }
}
