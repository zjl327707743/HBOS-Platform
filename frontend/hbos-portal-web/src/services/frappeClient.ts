import axios from 'axios'

interface FrappeMethodResponse<T> {
  message: T
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
    csrfToken = null
    return new FrappeRequestError('CSRF_MISMATCH', '安全会话已更新，请刷新页面后重试。', status)
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

let cachedCsrf: string | null = null
let csrfToken: string | null = null

export function clearCachedCsrfToken() {
  cachedCsrf = null
}

export function clearFrappeCsrfToken() { csrfToken = null }

function readCookie(name: string): string | null {
  if (typeof document === 'undefined') return null
  const match = document.cookie.match(new RegExp('(^|;\\s*)' + name + '=([^;]*)'))
  return match?.[2] ? decodeURIComponent(match[2]) : null
}

function bootstrapCsrfToken(): string | null {
  const runtime = window as Window & {
    csrf_token?: string
    frappe?: { csrf_token?: string }
  }
  const meta = document.querySelector<HTMLMetaElement>('meta[name="csrf-token"]')?.content
  return runtime.frappe?.csrf_token || runtime.csrf_token || meta || null
}

/**
 * 独立 Portal 不一定由 Frappe Desk 注入 csrf_token，写操作前主动取一次。
 * 使用原始 axios 请求，避免获取 token 的 GET 再次进入本拦截器。
 */
async function ensureCsrfToken(): Promise<string | null> {
  const fromCookie = readCookie('csrftoken')
  if (fromCookie) return fromCookie
  if (cachedCsrf) return cachedCsrf
  try {
    const response = await axios.get(
      '/api/method/hb_lims_app.hbos_lims.lims_service.get_csrf_token',
      { baseURL: import.meta.env.VITE_FRAPPE_BASE_URL || '', withCredentials: true, timeout: 15000 },
    )
    cachedCsrf = response.data?.message || null
    return cachedCsrf
  } catch {
    return null
  }
}

async function getCsrfToken(): Promise<string> {
  csrfToken ||= bootstrapCsrfToken()
  if (csrfToken) return csrfToken

  try {
    const response = await http.get<FrappeMethodResponse<{
      ok: boolean
      data?: { csrf_token: string }
    }>>('/api/method/hbos_portal.api.csrf.get_token')
    const payload = response.data.message
    if (!payload.ok || !payload.data?.csrf_token) {
      throw new FrappeRequestError('UNAUTHENTICATED', '当前会话无法建立安全请求，请重新登录。')
    }
    csrfToken = payload.data.csrf_token
    return csrfToken
  } catch (error) {
    throw normalizeFrappeError(error, 'hbos_portal.api.csrf.get_token')
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
  const csrf = await ensureCsrfToken()
  if (csrf) {
    config.headers['X-Frappe-CSRF-Token'] = csrf
  }
  return config
})

http.interceptors.response.use(
  (response) => response,
  (error) => {
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
): Promise<T> {
  try {
    const response = await http.get<FrappeMethodResponse<T>>(
      `/api/method/${method}`,
      { params },
    )
    return response.data.message
  } catch (error) {
    throw normalizeFrappeError(error, method)
  }
}

/** 调用 LIMS 领域写操作；CSRF 与会话由同一 Portal 客户端统一处理。 */
export async function callFrappeAction<T>(
  method: string,
  params?: Record<string, unknown>,
): Promise<T> {
  const response = await http.post<FrappeMethodResponse<T>>(
    `/api/method/${method}`,
    params,
  )
  return response.data.message
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
    csrfToken = null
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
    csrfToken = null
  } catch (error) {
    throw normalizeFrappeError(error, 'logout')
  }
}
