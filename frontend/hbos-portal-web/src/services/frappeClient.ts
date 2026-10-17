import axios from 'axios'

interface FrappeMethodResponse<T> { message: T }
const http = axios.create({ baseURL: import.meta.env.VITE_FRAPPE_BASE_URL || '', withCredentials: true, headers: { 'X-Requested-With': 'XMLHttpRequest' } })
let csrfToken: string | null = null
let csrfFlight: Promise<string> | null = null
let requestEpoch = 0
let writesBlocked = false
// DEV-only, non-authorizing lifecycle evidence. No URL, subject, SID, token,
// proof or payload is retained. These values never control a component key.
export const frappeDiagnostics = { document: import.meta.env.DEV ? crypto.randomUUID() : '', security: 0, capabilities: 0, bootstrap: 0 }
export const developmentObservation = import.meta.env.DEV && typeof window !== 'undefined' && new URLSearchParams(window.location.search).get('iam_uat') === '1'
function recordRead(method: string) {
  if (!import.meta.env.DEV) return
  if (method === 'hbos_portal.auth.accounts.get_security') frappeDiagnostics.security++
  if (method === 'hbos_portal.api.iam_access.get_capabilities') frappeDiagnostics.capabilities++
  if (method === 'hbos_portal.api.bootstrap.get_bootstrap') frappeDiagnostics.bootstrap++
}
export function clearFrappeCsrfToken() { csrfToken = null; csrfFlight = null }
export function invalidateFrappeRequests() { requestEpoch++; clearFrappeCsrfToken() }
export function blockFrappeWrites(blocked: boolean) { writesBlocked = blocked }
export type FrappeRequestErrorCode = 'UNAUTHENTICATED' | 'INVALID_CREDENTIALS' | 'PROOF_REQUIRED' | 'SESSION_UNCONFIRMED' | 'STALE_RESPONSE' | 'CSRF_MISMATCH' | 'FORBIDDEN' | 'NETWORK_ERROR' | 'SERVICE_ERROR' | 'VALIDATION_ERROR' | 'RATE_LIMITED'
export class FrappeRequestError extends Error {
  constructor(public code: FrappeRequestErrorCode, message: string, public status?: number, public diagnosticId?: string) { super(message); this.name = 'FrappeRequestError' }
}
interface SessionFact { authenticated: boolean; session_context: string | null; csrf_token?: string | null }
function responseText(data: unknown): string {
  if (!data || typeof data !== 'object') return String(data || '')
  const payload = data as Record<string, unknown>
  return [payload.exc_type, payload.exception, payload.message, payload._error_message, payload._server_messages].filter(Boolean).join(' ')
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
export function normalizeFrappeError(error: unknown, method?: string, fact?: Pick<SessionFact, 'authenticated'>): FrappeRequestError {
  if (error instanceof FrappeRequestError) return error
  if (!axios.isAxiosError(error)) return diagnostic()
  if (!error.response) return new FrappeRequestError('NETWORK_ERROR', '网络连接中断，操作结果尚未确认。请恢复连接后重试。')
  const status = error.response.status, detail = responseText(error.response.data)
  const credentialMethod = method === 'login' || method === 'login_mfa' || method?.endsWith('.password_login') || method?.endsWith('.reauthenticate') || method?.endsWith('.verify_feishu_code')
  const loginStep = method === 'login' || method === 'login_mfa' || method?.endsWith('.password_login')
  if (/account has been locked|账号.*锁定/i.test(detail)) return new FrappeRequestError('RATE_LIMITED', '验证尝试较多，当前暂不可用。请稍后重试。', status)
  if (status === 429 || /RateLimitExceededError/i.test(detail)) return new FrappeRequestError('RATE_LIMITED', '验证或请求较频繁，请稍后再试。', status)
  if (/CSRFTokenError|csrf token/i.test(detail)) { clearFrappeCsrfToken(); return new FrappeRequestError('CSRF_MISMATCH', '安全会话已更新，请重新核对后再提交。', status) }
  if (fact?.authenticated === false && !loginStep) return new FrappeRequestError('UNAUTHENTICATED', '登录状态已失效，请重新登录。', status)
  if (credentialMethod && /AuthenticationError|ExpiredLoginException|incorrect password|invalid login/i.test(detail)) return new FrappeRequestError('INVALID_CREDENTIALS', method === 'login_mfa' ? '二次认证未通过或已过期。请重新登录并输入当前验证码。' : (method === 'login' || method?.endsWith('.password_login') ? '账号或密码不正确。' : '密码或验证码不正确，请重新核对。'), status)
  // Account validation messages must never hide a confirmed Guest boundary.
  if (fact?.authenticated === false || (status === 401 && !credentialMethod)) return new FrappeRequestError('UNAUTHENTICATED', '登录状态已失效，请重新登录。', status)
  const wire = (error.response.data as {message?: {error?: {code?:string;message?:string}}})?.message?.error
  if (wire?.code === 'PROOF_REQUIRED') return new FrappeRequestError('PROOF_REQUIRED', '本人身份验证已过期，请重新验证后再保存。', status)
  if (/not whitelisted|not permitted to access this method|Failed to get method/i.test(detail)) return fact?.authenticated ? diagnostic(status) : new FrappeRequestError('SESSION_UNCONFIRMED', '暂时无法确认登录状态，请重试核验或退出登录。', status)
  if (/AuthenticationError/.test(detail) && fact?.authenticated) return new FrappeRequestError('PROOF_REQUIRED', '本人身份验证已过期，请重新验证后再保存。', status)
  const accountMethod = method?.startsWith('hbos_portal.auth.') && !credentialMethod
  if (accountMethod && /ValidationError|AuthenticationError|PermissionError/.test(detail)) {
    const safe = safeAccountMessage(error.response.data)
    if (safe) return new FrappeRequestError('VALIDATION_ERROR', safe, status)
  }
  if (status === 403 || status === 417) return new FrappeRequestError('FORBIDDEN', '当前账号没有执行此操作的权限。', status)
  if (wire && ['INVALID_REQUEST','CONFLICT','VERSION_CONFLICT','STALE_PREVIEW','INVALID_RULE'].includes(wire.code || '') && typeof wire.message === 'string' && /[\u3400-\u9fff]/.test(wire.message) && !/Traceback|frappe\.|hbos_portal\.|<script/i.test(wire.message)) return new FrappeRequestError('VALIDATION_ERROR', wire.message.replace(/<[^>]*>/g, '').slice(0, 200), status)
  if (status === 400 && /ValidationError/.test(detail)) return new FrappeRequestError('VALIDATION_ERROR', '提交内容未通过核验，请检查填写内容。', status)
  return diagnostic(status)
}
export const isUnauthenticatedError = (error: unknown) => error instanceof FrappeRequestError && error.code === 'UNAUTHENTICATED'
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
  if (axios.isAxiosError(error) && error.response && [401, 403, 417].includes(error.response.status) && !['login', 'login_mfa'].includes(method)) {
    try { fact = await probeFrappeSession() } catch { /* An inconclusive probe cannot establish Guest. */ }
  }
  const normalized = normalizeFrappeError(error, method, fact)
  assertEpoch(epoch)
  if (normalized.code === 'UNAUTHENTICATED' && typeof window !== 'undefined') window.dispatchEvent(new CustomEvent('hbos:session-expired'))
  return normalized
}
function assertEpoch(epoch: number) { if (epoch !== requestEpoch) throw new FrappeRequestError('STALE_RESPONSE', '会话已改变，已丢弃先前请求的结果。') }
async function getCsrfToken(): Promise<string> {
  if (csrfToken) return csrfToken
  if (csrfFlight) return csrfFlight
  const epoch = requestEpoch
  const flight = (async () => {
    const response = await http.get<FrappeMethodResponse<{ ok: boolean; data?: { csrf_token: string } }>>('/api/method/hbos_portal.api.csrf.get_token')
    assertEpoch(epoch)
    const payload = response.data.message
    if (!payload.ok || !payload.data?.csrf_token) throw new FrappeRequestError('UNAUTHENTICATED', '当前会话无法建立安全请求，请重新登录。')
    return csrfToken = payload.data.csrf_token
  })()
  csrfFlight = flight
  try { return await flight } catch (error) { throw await requestError(error, 'hbos_portal.api.csrf.get_token', epoch) } finally { if (csrfFlight === flight) csrfFlight = null }
}
export async function callFrappeMethod<T>(method: string, params?: Record<string, unknown>): Promise<T> {
  const epoch = requestEpoch
  recordRead(method)
  try { const response = await http.get<FrappeMethodResponse<T>>(`/api/method/${method}`, { params }); assertEpoch(epoch); return response.data.message }
  catch (error) { throw await requestError(error, method, epoch) }
}
export async function callFrappePostMethod<T>(method: string, data?: Record<string, unknown>, extraHeaders?: Record<string, string>): Promise<T> {
  const epoch = requestEpoch
  if (writesBlocked) throw new FrappeRequestError('SESSION_UNCONFIRMED', '正在核对当前登录状态，请稍后再提交。')
  try {
    const token = await getCsrfToken(); assertEpoch(epoch)
    if (writesBlocked) throw new FrappeRequestError('SESSION_UNCONFIRMED', '请先恢复当前登录状态，再保存草稿。')
    const response = await http.post<FrappeMethodResponse<T>>(`/api/method/${method}`, data || {}, { headers: { 'X-Frappe-CSRF-Token': token, 'Content-Type': 'application/json', ...extraHeaders } })
    assertEpoch(epoch); return response.data.message
  } catch (error) { throw await requestError(error, method, epoch) }
}
export interface PasswordLoginResult { tmp_id?: string; verification?: unknown; message?: string }
export async function loginWithPassword(username: string, password: string, otp = '', tmpId = ''): Promise<PasswordLoginResult> {
  try {
    const security = await probeFrappeSession()
    const result = await http.post<{message: PasswordLoginResult}>('/api/method/hbos_portal.auth.accounts.password_login', { username, password, otp, tmp_id: tmpId }, { headers: { 'Content-Type': 'application/json', ...(security.csrf_token ? { 'X-Frappe-CSRF-Token': security.csrf_token } : {}) } })
    invalidateFrappeRequests(); return result.data.message
  } catch (error) { throw normalizeFrappeError(error, tmpId ? 'login_mfa' : 'login') }
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
