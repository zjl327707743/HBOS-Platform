import { afterEach, beforeEach, expect, it, vi } from 'vitest'

const http = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn() }))
vi.mock('axios', async importOriginal => {
  const actual = await importOriginal<typeof import('axios')>()
  const { createTrackedAxios } = await import('./helpers/axiosAdapter')
  return { ...actual, default: { ...actual.default,
    create: (options?: import('axios').CreateAxiosDefaults) => createTrackedAxios(actual.default, http, options),
  } }
})

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
  expect(http.get).toHaveBeenCalledWith(tokenEndpoint, expect.objectContaining({ hbosCsrfGeneration: expect.any(Number) }))
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
  await vi.waitFor(() => expect(http.get).toHaveBeenCalledTimes(1))
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

it('does not let an old protected API 401 sign out a newer session', async () => {
  const unauthorized = vi.fn(() => client.clearFrappeCsrfToken())
  client.setUnauthorizedHandler(unauthorized)
  http.get.mockResolvedValueOnce(csrfResponse('OLD-TOKEN'))
  await client.ensureCsrfToken()
  const old = deferred<unknown>()
  http.get.mockReturnValueOnce(old.promise)
  const attempted = client.callFrappeMethod('hbos_portal.api.bootstrap.get_bootstrap').catch(error => error)
  await vi.waitFor(() => expect(http.get).toHaveBeenCalledTimes(2))
  client.clearFrappeCsrfToken()
  http.get.mockResolvedValueOnce(csrfResponse('NEW-TOKEN'))
  await client.ensureCsrfToken()
  old.reject({ isAxiosError: true, response: { status: 401, data: { exc_type: 'SessionExpired' } } })
  expect(await attempted).toMatchObject({ code: 'CSRF_MISMATCH' })
  expect(unauthorized).not.toHaveBeenCalled()
  expect(await client.ensureCsrfToken()).toBe('NEW-TOKEN')
  expect(http.get).toHaveBeenCalledTimes(3)
})

it.each([
  'hbos_portal.auth.accounts.reauthenticate',
  'hbos_portal.auth.accounts.verify_feishu_code',
  'hbos_portal.auth.accounts.set_password',
  'hbos_portal.auth.operations.verify_source',
  'hbos_portal.auth.operations.verify_custody_credentials',
])('ends the current session on a native account AuthenticationError from %s', async method => {
  const unauthorized = vi.fn(() => client.clearFrappeCsrfToken())
  client.setUnauthorizedHandler(unauthorized)
  http.get.mockResolvedValueOnce(csrfResponse('VALID-TOKEN'))
  http.post.mockRejectedValueOnce({ isAxiosError: true, response: { status: 401, data: {
    exc_type: 'AuthenticationError',
    _server_messages: JSON.stringify([JSON.stringify({ message: '本人验证未通过，请重新验证。' })]),
  } } })
  await expect(client.callFrappePostMethod(method, {})).rejects.toMatchObject({
    code: 'VALIDATION_ERROR', status: 401, message: '本人验证未通过，请重新验证。',
  })
  expect(unauthorized).toHaveBeenCalledTimes(1)
  http.get.mockResolvedValueOnce(csrfResponse('REISSUED-TOKEN'))
  expect(await client.ensureCsrfToken()).toBe('REISSUED-TOKEN')
  expect(http.get).toHaveBeenCalledTimes(2)
  expect(http.post).toHaveBeenCalledTimes(1)
})

it.each([
  '账号不可用，请重新登录。',
  '此账号正在完成受控交接，请稍后重新登录。',
  '账号正在交接，请重新登录。',
  '账号登录方式已更换，旧会话已失效。',
])('ends an unavailable current account session: %s', async message => {
  const unauthorized = vi.fn(() => client.clearFrappeCsrfToken())
  client.setUnauthorizedHandler(unauthorized)
  http.get.mockResolvedValueOnce(csrfResponse('UNAVAILABLE-TOKEN'))
  http.post.mockRejectedValueOnce({ isAxiosError: true, response: { status: 401, data: {
    exc_type: 'AuthenticationError',
    _server_messages: JSON.stringify([JSON.stringify({ message })]),
  } } })
  await expect(client.callFrappePostMethod('hbos_portal.auth.accounts.reauthenticate', {})).rejects.toMatchObject({
    code: 'VALIDATION_ERROR', status: 401, message,
  })
  expect(unauthorized).toHaveBeenCalledTimes(1)
  http.get.mockResolvedValueOnce(csrfResponse('REISSUED-TOKEN'))
  expect(await client.ensureCsrfToken()).toBe('REISSUED-TOKEN')
  expect(http.get).toHaveBeenCalledTimes(2)
  expect(http.post).toHaveBeenCalledTimes(1)
})

it.each([
  ['ValidationError', 417],
  ['PermissionError', 403],
])('keeps native non-auth %s rejection local to its account form', async (excType, status) => {
  const unauthorized = vi.fn(() => client.clearFrappeCsrfToken())
  client.setUnauthorizedHandler(unauthorized)
  http.get.mockResolvedValueOnce(csrfResponse('VALID-TOKEN'))
  http.post.mockRejectedValueOnce({ isAxiosError: true, response: { status, data: {
    exc_type: excType,
    _server_messages: JSON.stringify([JSON.stringify({ message: '请核对本次操作的确认信息。' })]),
  } } })
  await expect(client.callFrappePostMethod('hbos_portal.auth.accounts.set_password', {})).rejects.toMatchObject({
    code: 'VALIDATION_ERROR', status, message: '请核对本次操作的确认信息。',
  })
  expect(unauthorized).not.toHaveBeenCalled()
  expect(await client.ensureCsrfToken()).toBe('VALID-TOKEN')
  expect(http.get).toHaveBeenCalledTimes(1)
  expect(http.post).toHaveBeenCalledTimes(1)
})

it.each([
  ['hbos_portal.auth.accounts.reauthenticate', 'SessionExpired', undefined],
  ['hbos_portal.auth.accounts.reauthenticate', 'AuthenticationError', undefined],
  ['hbos_portal.auth.accounts.reauthenticate', 'AuthenticationError', '<b></b>'],
  ['hbos_portal.auth.accounts.get_security', 'AuthenticationError', '请重新登录。'],
  ['hbos_portal.api.bootstrap.get_bootstrap', 'SessionExpired', undefined],
])('invalidates the current session for %s 401 (%s, %s)', async (method, excType, message) => {
  const unauthorized = vi.fn(() => client.clearFrappeCsrfToken())
  client.setUnauthorizedHandler(unauthorized)
  http.get.mockResolvedValueOnce(csrfResponse('EXPIRED-TOKEN'))
  await client.ensureCsrfToken()
  http.get.mockRejectedValueOnce({ isAxiosError: true, response: { status: 401, data: {
    exc_type: excType,
    ...(message === undefined ? {} : { _server_messages: JSON.stringify([JSON.stringify({ message })]) }),
  } } })
  await expect(client.callFrappeMethod(method!)).rejects.toBeInstanceOf(client.FrappeHttpError)
  expect(unauthorized).toHaveBeenCalledTimes(1)
  http.get.mockResolvedValueOnce(csrfResponse('REISSUED-TOKEN'))
  expect(await client.ensureCsrfToken()).toBe('REISSUED-TOKEN')
  expect(http.get).toHaveBeenCalledTimes(3)
  expect(http.post).not.toHaveBeenCalled()
})
