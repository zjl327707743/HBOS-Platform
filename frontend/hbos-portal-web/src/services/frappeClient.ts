import axios from 'axios'

interface FrappeMethodResponse<T> {
  message: T
}

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

const http = axios.create({
  baseURL: import.meta.env.VITE_FRAPPE_BASE_URL || '',
  withCredentials: true,
  timeout: 15000,
  headers: {
    'X-Requested-With': 'XMLHttpRequest',
  },
})

let cachedCsrf: string | null = null

function readCookie(name: string): string | null {
  if (typeof document === 'undefined') return null
  const match = document.cookie.match(new RegExp('(^|;\\s*)' + name + '=([^;]*)'))
  return match?.[2] ? decodeURIComponent(match[2]) : null
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

export function clearCachedCsrfToken() {
  cachedCsrf = null
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
  const response = await http.get<FrappeMethodResponse<T>>(
    `/api/method/${method}`,
    { params },
  )
  return response.data.message
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
