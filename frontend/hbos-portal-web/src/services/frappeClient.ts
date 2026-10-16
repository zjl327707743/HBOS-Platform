import axios from 'axios'

interface FrappeMethodResponse<T> {
  message: T
}

const http = axios.create({
  baseURL: import.meta.env.VITE_FRAPPE_BASE_URL || '',
  withCredentials: true,
  headers: {
    'X-Requested-With': 'XMLHttpRequest',
  },
})

let csrfToken: string | null = null

export function clearFrappeCsrfToken() { csrfToken = null }

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

function bootstrapCsrfToken(): string | null {
  const runtime = window as Window & {
    csrf_token?: string
    frappe?: { csrf_token?: string }
  }
  const meta = document.querySelector<HTMLMetaElement>('meta[name="csrf-token"]')?.content
  return runtime.frappe?.csrf_token || runtime.csrf_token || meta || null
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
    const security = await http.get<{message: {csrf_token?: string}}>('/api/method/hbos_portal.auth.accounts.get_request_security')
    const result = await http.post<{message: PasswordLoginResult}>('/api/method/hbos_portal.auth.accounts.password_login', { username, password, otp, tmp_id: tmpId }, {
      headers: { 'Content-Type': 'application/json', 'X-Requested-With': 'XMLHttpRequest', ...(security.data.message.csrf_token ? {'X-Frappe-CSRF-Token': security.data.message.csrf_token} : {}) },
    })
    csrfToken = null
    return result.data.message
  } catch (error) {
    throw normalizeFrappeError(error, tmpId ? 'login_mfa' : 'login')
  }
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

export async function callFrappeUploadMethod<T>(method: string, form: FormData): Promise<T> {
  try {
    const token = await getCsrfToken()
    const response = await http.post<FrappeMethodResponse<T>>(`/api/method/${method}`, form, { headers: { 'X-Frappe-CSRF-Token': token } })
    return response.data.message
  } catch (error) { throw normalizeFrappeError(error, method) }
}
