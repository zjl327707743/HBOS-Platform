import { afterEach, beforeEach, expect, it, vi } from 'vitest'

const http = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn() }))
vi.mock('axios', () => ({ default: {
  create: () => http,
  isAxiosError: (error: { isAxiosError?: boolean }) => Boolean(error?.isAxiosError),
} }))

let client: typeof import('@/services/frappeClient')
const csrfResponse = (token: string) => ({ data: { message: { ok: true, data: { csrf_token: token } } } })
const csrfError = () => ({ isAxiosError: true, response: { status: 400, data: { exc_type: 'CSRFTokenError' } } })
const tokenEndpoint = '/api/method/hbos_portal.api.csrf.get_token'
function deferred<T>() {
  let resolve!: (value: T) => void
  let reject!: (error: unknown) => void
  const promise = new Promise<T>((yes, no) => { resolve = yes; reject = no })
  return { promise, resolve, reject }
}

beforeEach(async () => {
  vi.resetModules()
  http.get.mockReset()
  http.post.mockReset().mockResolvedValue({ data: { message: {} } })
  delete (window as Window & { csrf_token?: string }).csrf_token
  document.cookie = 'csrftoken=; Max-Age=0; path=/'
  client = await import('@/services/frappeClient')
})
afterEach(() => {
  delete (window as Window & { csrf_token?: string }).csrf_token
  document.cookie = 'csrftoken=; Max-Age=0; path=/'
})

it('shares one current Portal token across inventory and account writes', async () => {
  document.cookie = 'csrftoken=OLD-LEGACY-COOKIE; path=/'
  http.get.mockResolvedValue(csrfResponse('CURRENT-TOKEN'))
  await client.postFrappeMethod('frappe.client.submit', { doc: 'synthetic' })
  await client.callFrappePostMethod('hbos_portal.auth.accounts.reauthenticate', { password: 'synthetic' })
  expect(http.get).toHaveBeenCalledTimes(1)
  expect(http.get).toHaveBeenCalledWith(tokenEndpoint)
  for (const call of http.post.mock.calls) {
    expect(call[2].headers['X-Frappe-CSRF-Token']).toBe('CURRENT-TOKEN')
  }
})

it('never restores the original page token after session clear', async () => {
  ;(window as Window & { csrf_token?: string }).csrf_token = 'OLD-PAGE-TOKEN'
  expect(await client.ensureCsrfToken()).toBe('OLD-PAGE-TOKEN')
  client.clearFrappeCsrfToken()
  http.get.mockResolvedValue(csrfResponse('NEW-SESSION-TOKEN'))
  expect(await client.ensureCsrfToken()).toBe('NEW-SESSION-TOKEN')
  expect(http.get).toHaveBeenCalledTimes(1)
})

it('invalidates the shared token on native login and logout', async () => {
  http.get.mockResolvedValueOnce(csrfResponse('PRE-LOGIN'))
  await client.ensureCsrfToken()
  http.get.mockResolvedValueOnce({ data: { message: { csrf_token: 'LOGIN-SECURITY' } } })
  await client.loginWithPassword('synthetic-user', 'synthetic-password')
  http.get.mockResolvedValueOnce(csrfResponse('POST-LOGIN'))
  expect(await client.ensureCsrfToken()).toBe('POST-LOGIN')
  await client.logoutFrappeSession()
  http.get.mockResolvedValueOnce(csrfResponse('AFTER-LOGOUT'))
  expect(await client.ensureCsrfToken()).toBe('AFTER-LOGOUT')
  expect(http.post.mock.calls.find(call => call[0] === '/api/method/logout')?.[2].headers['X-Frappe-CSRF-Token']).toBe('POST-LOGIN')
  expect(http.get.mock.calls.filter(call => call[0] === tokenEndpoint)).toHaveLength(3)
})

it('drops an old token response instead of starting a write in the new session', async () => {
  const old = deferred<ReturnType<typeof csrfResponse>>()
  http.get.mockReturnValueOnce(old.promise)
  const attempted = client.postFrappeMethod('frappe.client.submit', { doc: 'OLD-DOC' }).catch(error => error)
  client.clearFrappeCsrfToken()
  http.get.mockResolvedValueOnce(csrfResponse('NEW-TOKEN'))
  await client.callFrappePostMethod('hbos_portal.auth.accounts.reauthenticate', { password: 'synthetic' })
  old.resolve(csrfResponse('OLD-TOKEN'))
  expect(await attempted).toMatchObject({ code: 'CSRF_MISMATCH' })
  expect(http.post).toHaveBeenCalledTimes(1)
  expect(http.post.mock.calls[0][0]).toContain('reauthenticate')
  expect(await client.ensureCsrfToken()).toBe('NEW-TOKEN')
})

it('does not let a late old CSRF failure erase the new session token', async () => {
  http.get.mockResolvedValueOnce(csrfResponse('OLD-TOKEN'))
  const old = deferred<unknown>()
  http.post.mockReturnValueOnce(old.promise)
  const attempted = client.postFrappeMethod('frappe.client.submit', { doc: 'OLD-DOC' }).catch(error => error)
  await vi.waitFor(() => expect(http.post).toHaveBeenCalledTimes(1))
  client.clearFrappeCsrfToken()
  http.get.mockResolvedValueOnce(csrfResponse('NEW-TOKEN'))
  await client.callFrappePostMethod('hbos_portal.auth.accounts.reauthenticate', { password: 'synthetic' })
  old.reject(csrfError())
  expect(await attempted).toMatchObject({ code: 'CSRF_MISMATCH' })
  expect(await client.ensureCsrfToken()).toBe('NEW-TOKEN')
  expect(http.get).toHaveBeenCalledTimes(2)
})

it.each(['document', 'upload', 'account'])('clears a rejected CSRF token without automatically repeating a %s write', async kind => {
  http.get.mockResolvedValueOnce(csrfResponse('REJECTED-TOKEN'))
  http.post.mockRejectedValueOnce(csrfError())
  const request = kind === 'upload'
    ? client.uploadFrappeFile('/api/method/upload_file', new File(['synthetic'], 'fixture.txt'))
    : kind === 'account'
      ? client.callFrappePostMethod('hbos_portal.auth.accounts.reauthenticate', { password: 'synthetic' })
      : client.postFrappeMethod('frappe.client.submit', { doc: 'synthetic' })
  const error = await request.catch(error => error)
  expect(error).toBeInstanceOf(client.FrappeHttpError)
  expect(error).toMatchObject({ code: 'CSRF_MISMATCH' })
  expect(http.post).toHaveBeenCalledTimes(1)
  expect(http.get).toHaveBeenCalledTimes(1)
  http.get.mockResolvedValueOnce(csrfResponse('REISSUED-TOKEN'))
  expect(await client.ensureCsrfToken()).toBe('REISSUED-TOKEN')
  expect(http.post).toHaveBeenCalledTimes(1)
})

it('stops a document write when the server refuses to issue a token', async () => {
  http.get.mockResolvedValue({ data: { message: { ok: false } } })
  await expect(client.postFrappeMethod('frappe.client.submit', { doc: 'synthetic' })).rejects.toMatchObject({ code: 'UNAUTHENTICATED' })
  expect(http.post).not.toHaveBeenCalled()
})

it('keeps the original Chinese inventory denial and FrappeHttpError compatibility', async () => {
  http.get.mockResolvedValue(csrfResponse('CURRENT-TOKEN'))
  http.post.mockRejectedValue({ isAxiosError: true, response: { status: 403, data: {
    exc_type: 'PermissionError',
    _server_messages: JSON.stringify([JSON.stringify({ message: '<strong>当前批次未放行</strong>，不能提交出库。' })]),
  } } })
  const error = await client.postFrappeMethod('frappe.client.submit', { doc: 'synthetic' }).catch(error => error)
  expect(error).toBeInstanceOf(client.FrappeHttpError)
  expect(error).toMatchObject({ status: 403, message: '当前批次未放行，不能提交出库。' })
  expect(http.post).toHaveBeenCalledTimes(1)
})
