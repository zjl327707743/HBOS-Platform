import axios from 'axios'

interface FrappeMethodResponse<T> {
  message: T
}

/**
 * Frappe 对「未登录访客」与「已登录但无权」都返回 403，同码不同因。
 * 保留状态码，让上层能分辨后再决定去登录还是去 403 页。
 */
export class FrappeHttpError extends Error {
  readonly status: number

  constructor(status: number, message: string) {
    super(message)
    this.name = 'FrappeHttpError'
    this.status = status
  }
}

const http = axios.create({
  baseURL: import.meta.env.VITE_FRAPPE_BASE_URL || '',
  withCredentials: true,
  headers: {
    'X-Requested-With': 'XMLHttpRequest',
  },
})

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
    // 同样走 toFrappeError：服务端的中文业务提示必须优先于 axios 的
    // 「Request failed with status code 417」——那是实现细节，不是用户语义。
    throw toFrappeError(error)
  }
}

// ---------------------------------------------------------------------------
// CSRF
// ---------------------------------------------------------------------------

/**
 * Frappe 的 CSRF 校验一直在跑（`frappe.auth.validate_csrf_token`），任何非 GET 请求
 * 都必须带 `X-Frappe-CSRF-Token`，否则 400 `CSRFTokenError`。
 *
 * Desk 页面里能用，是框架注入了 `frappe.csrf_token`；Portal 是独立前端、跨源
 * （本地开发甚至跨端口），拿不到那个注入。所以走 `hb_inventory_app` 提供的受控接口。
 *
 * 该接口只返回**当前会话**的 token：有 cookie 才有 token，没 cookie 拿不到，
 * 拿不到就发不出合法 POST——因此并没有削弱 CSRF 防护。
 */
let cachedCsrf: string | null = null

function readCsrfCookie(): string | null {
  if (typeof document === 'undefined') return null
  const match = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]*)/)
  const value = match?.[1]
  return value ? decodeURIComponent(value) : null
}

export async function ensureCsrfToken(): Promise<string | null> {
  // 同源部署时 cookie 里就有，不必多打一次请求
  const fromCookie = readCsrfCookie()
  if (fromCookie) return fromCookie
  if (cachedCsrf) return cachedCsrf

  try {
    const response = await http.get<FrappeMethodResponse<string>>(
      '/api/method/hb_inventory_app.hbos_inventory.api.get_csrf_token',
    )
    cachedCsrf = response.data.message || null
    return cachedCsrf
  } catch {
    return null
  }
}

async function withCsrf(): Promise<Record<string, string>> {
  const token = await ensureCsrfToken()
  // 拿不到也照样发：让服务端给出权威的失败原因，而不是前端替它下结论
  return token ? { 'X-Frappe-CSRF-Token': token } : {}
}

export async function csrfHeaders(): Promise<Record<string, string>> {
  return withCsrf()
}

// ---------------------------------------------------------------------------
// 提交单据
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
  try {
    const response = await http.post<FrappeMethodResponse<T>>(
      `/api/method/${method}`,
      params,
      { headers: await withCsrf() },
    )
    return response.data.message
  } catch (error) {
    throw toFrappeError(error)
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
  const form = new FormData()
  form.append('file', file)
  for (const [key, value] of Object.entries(fields)) form.append(key, value)

  try {
    const response = await http.post<FrappeMethodResponse<Record<string, unknown>>>(
      endpoint,
      form,
      { headers: await withCsrf() },
    )
    return response.data.message || {}
  } catch (error) {
    throw toFrappeError(error)
  }
}

function toFrappeError(error: unknown): FrappeHttpError {
  if (axios.isAxiosError(error)) {
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
