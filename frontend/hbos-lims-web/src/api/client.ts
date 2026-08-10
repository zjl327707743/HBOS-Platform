import axios from 'axios'
import { ElMessage } from 'element-plus'

// ============================================================
// Frappe REST API 客户端
// 同域部署：复用 Frappe session Cookie（withCredentials）
// CSRF Token 从 Cookie 中的 csrftoken 读取
// ============================================================

function readCookie(name: string): string | null {
  const match = document.cookie.match(new RegExp('(^|;\\s*)' + name + '=([^;]*)'))
  return match ? decodeURIComponent(match[2]) : null
}

const api = axios.create({
  baseURL: '/api/method',
  timeout: 30000,
  withCredentials: true,
  headers: { 'Content-Type': 'application/json' },
})

api.interceptors.request.use((config) => {
  const csrf = readCookie('csrftoken')
  if (csrf) {
    config.headers['X-Frappe-CSRF-Token'] = csrf
  }
  return config
})

api.interceptors.response.use(
  (response) => {
    // 直接返回原始 axios response（包含 .data）
    return response
  },
  (error) => {
    const status = error.response?.status
    if (status === 401) {
      ElMessage.warning('登录已失效，请重新登录')
    } else {
      // 提取 Frappe 错误消息
      const serverMessages = error.response?.data?._server_messages
      if (serverMessages) {
        try {
          const messages = JSON.parse(serverMessages)
          for (const m of messages) {
            const parsed = JSON.parse(m)
            ElMessage.error(parsed.message || '请求失败')
          }
        } catch {
          ElMessage.error(error.message || '网络错误')
        }
      } else {
        ElMessage.error(error.message || '网络错误')
      }
    }
    return Promise.reject(error)
  },
)

// 统一调用 Frappe whitelist 方法（返回 message 字段）
export async function callMethod<T = any>(method: string, params: Record<string, unknown> = {}): Promise<T> {
  const res = await api.post(method, params)
  return res.data?.message as T
}

// 调用 Frappe whitelist 方法（GET 形式，用于查询）
export async function getMethod<T = any>(method: string, params: Record<string, unknown> = {}): Promise<T> {
  const res = await api.get(method, { params })
  return res.data?.message as T
}

export { api }
export default api
