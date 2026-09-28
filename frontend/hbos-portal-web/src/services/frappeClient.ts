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
  if (!axios.isAxiosError(error)) return false
  const status = error.response?.status
  return status === 401 || status === 403
}

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

/**
 * 经当前 origin 登录 Frappe（开发环境由 Vite 代理到 Frappe）。
 * 必须使用表单编码；Frappe 的 /api/method/login 不接受 JSON body。
 */
export async function login(usr: string, pwd: string): Promise<void> {
  const body = new URLSearchParams({ usr, pwd })
  await http.post('/api/method/login', body)
}
