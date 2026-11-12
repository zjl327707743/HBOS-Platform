import { callFrappeMethod } from '@/services/frappeClient'

/**
 * 门户侧的 Frappe 文件上传。
 *
 * 为什么要单独一层：Frappe 对 POST 做 CSRF 校验，而门户是独立 SPA，
 * 拿不到 Desk 页面里内联下发的 `frappe.csrf_token`。后端 `file_api.get_csrf_token`
 * 把当前会话的 token 交给已认证的同源前端（这正是 CSRF token 的本来用途）。
 *
 * 上传本身走 Frappe 内置的 `upload_file`——权限、大小、扩展名的校验由框架负责，
 * 这里不重复实现。
 */

const CSRF_ENDPOINT = 'hb_attendance_app.hbos_attendance.file_api.get_csrf_token'

let cachedToken: string | null = null

async function csrfToken(): Promise<string> {
  if (!cachedToken) {
    cachedToken = await callFrappeMethod<string>(CSRF_ENDPOINT)
  }
  return cachedToken
}

/** 会话失效或 token 轮换后清一次，下次重新取。 */
export function forgetCsrfToken() {
  cachedToken = null
}

export interface UploadResult {
  fileUrl: string
  fileName: string
}

export async function uploadToFrappe(
  file: File,
  options: { doctype?: string; isPrivate?: boolean; folder?: string } = {},
): Promise<UploadResult> {
  const form = new FormData()
  form.append('file', file)
  form.append('is_private', options.isPrivate === false ? '0' : '1')
  form.append('folder', options.folder || 'Home/Attachments')
  if (options.doctype) form.append('doctype', options.doctype)

  const send = async (token: string) =>
    fetch('/api/method/upload_file', {
      method: 'POST',
      headers: { 'X-Frappe-CSRF-Token': token, 'X-Requested-With': 'XMLHttpRequest' },
      body: form,
      credentials: 'same-origin',
    })

  let response = await send(await csrfToken())

  // 403 大多是 token 陈旧（会话重开/轮换）→ 作废重取一次。
  // 只重试一次：真的没权限时反复重试没有意义。
  if (response.status === 403) {
    forgetCsrfToken()
    response = await send(await csrfToken())
  }

  const payload = await response.json().catch(() => null)
  if (!response.ok || !payload || payload.exc) {
    const raw = payload?._server_messages || payload?.exc || `上传失败（HTTP ${response.status}）`
    throw new Error(plainMessage(raw))
  }

  return {
    fileUrl: payload.message?.file_url || '',
    fileName: payload.message?.file_name || file.name,
  }
}

/** Frappe 的错误信息是嵌套 JSON 字符串，剥一层再显示，别让用户看到转义符。 */
function plainMessage(raw: unknown): string {
  const text = String(raw)
  try {
    const parsed = JSON.parse(text)
    const first = Array.isArray(parsed) ? parsed[0] : parsed
    const inner = typeof first === 'string' ? JSON.parse(first) : first
    return String(inner?.message || inner?.exc || text).replace(/<[^>]+>/g, '').trim()
  } catch {
    return text.replace(/<[^>]+>/g, '').trim().slice(0, 300)
  }
}
