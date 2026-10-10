import axios, { type AxiosAdapter } from 'axios'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'

const originalAdapter = axios.defaults.adapter
let token: string
let writes: string[]
let tokenReads: number

beforeEach(() => {
  vi.resetModules()
  token = 'synthetic-session-A'
  writes = []
  tokenReads = 0
  axios.defaults.adapter = (async config => {
    const url = String(config.url)
    let message: unknown = { ok: true }
    if (url.endsWith('lims_service.get_csrf_token')) message = token
    else if (url.endsWith('hbos_portal.api.csrf.get_token')) {
      tokenReads += 1
      message = { ok: true, data: { csrf_token: token } }
    } else if (url.endsWith('accounts.get_request_security')) message = { csrf_token: token }
    else if (config.method === 'post') {
      const supplied = String(config.headers.get('X-Frappe-CSRF-Token'))
      writes.push(supplied)
      if (supplied !== token) {
        throw new axios.AxiosError('Synthetic CSRF rejection', undefined, config, {}, {
          status: 400, statusText: 'Bad Request', headers: {}, config,
          data: { exc_type: 'CSRFTokenError' },
        })
      }
    }
    return { data: { message }, status: 200, statusText: 'OK', headers: {}, config }
  }) as AxiosAdapter
})

afterEach(() => {
  axios.defaults.adapter = originalAdapter
  delete (window as Window & { csrf_token?: string }).csrf_token
})

it('a rejected write invalidates CSRF for both LIMS and account actions without replaying the write', async () => {
  const api = await import('@/services/frappeClient')
  await api.callFrappeAction('synthetic.lims_action')
  token = 'synthetic-session-B'
  await expect(api.callFrappePostMethod('synthetic.account_action')).rejects.toMatchObject({ code: 'CSRF_MISMATCH' })
  expect(writes).toEqual(['synthetic-session-A', 'synthetic-session-A'])
  await api.callFrappePostMethod('synthetic.account_action')
  await api.callFrappeAction('synthetic.lims_action')
  expect(writes.slice(2)).toEqual(['synthetic-session-B', 'synthetic-session-B'])
})

it('password login preserves its freshly issued security token instead of an older action token', async () => {
  const api = await import('@/services/frappeClient')
  await api.callFrappeAction('synthetic.lims_action')
  token = 'synthetic-session-B'
  await api.loginWithPassword('synthetic-user', 'synthetic-password')
  expect(writes.at(-1)).toBe('synthetic-session-B')
})

it('logout followed by password login uses Guest security and a fresh token for the new session', async () => {
  const fixtureAdapter = axios.defaults.adapter as AxiosAdapter
  let guest = false
  const passwordSubmissions: unknown[] = []
  axios.defaults.adapter = async config => {
    if (config.url?.endsWith('accounts.get_request_security') && guest) {
      return { data: { message: { csrf_token: null } }, status: 200, statusText: 'OK', headers: {}, config }
    }
    if (config.url?.endsWith('accounts.password_login')) {
      expect(guest).toBe(true)
      expect(config.headers.has('X-Frappe-CSRF-Token')).toBe(false)
      passwordSubmissions.push(config.data)
      guest = false
      token = 'synthetic-session-C'
      return { data: { message: { logged_in: true } }, status: 200, statusText: 'OK', headers: {}, config }
    }
    const result = await fixtureAdapter(config)
    if (config.url?.endsWith('/logout')) guest = true
    return result
  }
  const api = await import('@/services/frappeClient')
  await api.callFrappeAction('synthetic.first_session_action')
  await api.logoutFrappeSession()
  await expect(api.loginWithPassword('synthetic-user', 'synthetic-password')).resolves.toMatchObject({ logged_in: true })
  await api.callFrappeAction('synthetic.new_session_action')
  expect(passwordSubmissions).toHaveLength(1)
  expect(writes).toEqual(['synthetic-session-A', 'synthetic-session-A', 'synthetic-session-C'])
  expect(tokenReads).toBe(2)
})

it.each(['clearCachedCsrfToken', 'clearFrappeCsrfToken'] as const)('%s prevents reuse of a previous session and its injected page token', async clear => {
  const api = await import('@/services/frappeClient')
  ;(window as Window & { csrf_token?: string }).csrf_token = token
  await api.callFrappePostMethod('synthetic.account_action')
  token = 'synthetic-session-B'
  api[clear]()
  await api.callFrappeAction('synthetic.lims_action')
  expect(writes.at(-1)).toBe('synthetic-session-B')
})

it('concurrent authenticated writes share one Portal token request', async () => {
  const api = await import('@/services/frappeClient')
  await Promise.all([api.callFrappeAction('synthetic.lims_action'), api.callFrappePostMethod('synthetic.account_action')])
  expect(tokenReads).toBe(1)
})

it('a token request from an old session cannot write or sign out the newer session', async () => {
  const fixtureAdapter = axios.defaults.adapter as AxiosAdapter
  let releaseOldRequest: (() => void) | undefined
  axios.defaults.adapter = async config => {
    if (config.url?.endsWith('hbos_portal.api.csrf.get_token') && !releaseOldRequest) {
      return new Promise(resolve => {
        releaseOldRequest = () => resolve({
          data: { message: { ok: true, data: { csrf_token: 'synthetic-session-A' } } },
          status: 200, statusText: 'OK', headers: {}, config,
        })
      })
    }
    return fixtureAdapter(config)
  }
  const api = await import('@/services/frappeClient')
  const signOut = vi.fn()
  api.setUnauthorizedHandler(signOut)
  const oldWrite = expect(api.callFrappeAction('synthetic.old_session_action'))
    .rejects.toMatchObject({ code: 'CSRF_MISMATCH' })
  await vi.waitFor(() => expect(releaseOldRequest).toBeTypeOf('function'))
  token = 'synthetic-session-B'
  api.clearCachedCsrfToken()
  await api.callFrappePostMethod('synthetic.new_session_action')
  releaseOldRequest!()
  await oldWrite
  await api.callFrappeAction('synthetic.new_session_action')
  expect(writes).toEqual(['synthetic-session-B', 'synthetic-session-B'])
  expect(tokenReads).toBe(1)
  expect(signOut).not.toHaveBeenCalled()
})
