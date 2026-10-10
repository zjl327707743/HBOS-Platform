import axios, { type AxiosAdapter } from 'axios'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
const originalAdapter = axios.defaults.adapter
const queries = ['get_management_context', 'list_positions', 'get_person_assignments', 'lookup_people']
const prefix = 'hbos_portal.api.organization_relations.'
let token: string, tokenReads: number, selected: { url: string; token: unknown; method: string | undefined }[]
beforeEach(() => {
  vi.resetModules(); token = 'synthetic-read-session-A'; tokenReads = 0; selected = []
  axios.defaults.adapter = (async config => {
    const url = String(config.url), supplied = config.headers.get('X-Frappe-CSRF-Token')
    if (url.endsWith('hbos_portal.api.csrf.get_token')) {
      tokenReads += 1; expect(supplied).toBeUndefined()
      return { data: { message: { ok: true, data: { csrf_token: token } } }, status: 200, statusText: 'OK', headers: {}, config }
    }
    expect(config.withCredentials).toBe(true)
    selected.push({ url, token: supplied, method: config.method })
    return { data: { message: { ok: true, data: {} } }, status: 200, statusText: 'OK', headers: {}, config }
  }) as AxiosAdapter
})
afterEach(() => { axios.defaults.adapter = originalAdapter; delete (window as Window & { csrf_token?: string }).csrf_token })
it('four managed reads share native CSRF while ordinary GET and token bootstrap remain unchanged', async () => {
  const api = await import('@/services/frappeClient')
  await Promise.all(queries.map(q => api.callFrappeMethod(prefix + q, {}, { requireCsrf: true })))
  await api.callFrappeMethod('hbos_portal.api.people_access.get_people')
  expect(tokenReads).toBe(1)
  expect(selected.slice(0, 4).every(r => r.method === 'get' && r.token === token)).toBe(true)
  expect(selected[4]?.token).toBeUndefined()
})
it('a failed token bootstrap sends no management query', async () => {
  axios.defaults.adapter = async config => { throw new axios.AxiosError('synthetic unavailable', undefined, config) }
  const api = await import('@/services/frappeClient')
  await expect(api.callFrappeMethod(prefix + queries[0], {}, { requireCsrf: true })).rejects.toMatchObject({ code: 'NETWORK_ERROR' })
  expect(selected).toEqual([])
})
it('an old pending token cannot query or log out a new session', async () => {
  const fixtureAdapter = axios.defaults.adapter as AxiosAdapter
  let release: (() => void) | undefined
  axios.defaults.adapter = async config => {
    if (config.url?.endsWith('hbos_portal.api.csrf.get_token') && !release) return new Promise(resolve => {
      release = () => resolve({ data: { message: { ok: true, data: { csrf_token: 'synthetic-read-session-A' } } }, status: 200, statusText: 'OK', headers: {}, config })
    })
    return fixtureAdapter(config)
  }
  const api = await import('@/services/frappeClient'), signOut = vi.fn(); api.setUnauthorizedHandler(signOut)
  const rejected = expect(api.callFrappeMethod(prefix + queries[0], {}, { requireCsrf: true })).rejects.toMatchObject({ code: 'CSRF_MISMATCH' })
  await vi.waitFor(() => expect(release).toBeTypeOf('function'))
  token = 'synthetic-read-session-B'; api.clearCachedCsrfToken()
  await api.callFrappeMethod(prefix + queries[1], {}, { requireCsrf: true }); release!(); await rejected
  expect(selected).toHaveLength(1); expect(selected[0]?.token).toBe(token); expect(signOut).not.toHaveBeenCalled()
})
it('cached-token invalidation between await and dispatch withholds the old query', async () => {
  const api = await import('@/services/frappeClient')
  await api.callFrappeMethod(prefix + queries[0], {}, { requireCsrf: true })
  const rejected = expect(api.callFrappeMethod(prefix + queries[1], {}, { requireCsrf: true })).rejects.toMatchObject({ code: 'CSRF_MISMATCH' })
  api.clearCachedCsrfToken(); await rejected; expect(selected).toHaveLength(1)
})
it.each([401, 403])('an old token bootstrap %s failure cannot invalidate a new session', async status => {
  const fixtureAdapter = axios.defaults.adapter as AxiosAdapter
  let release: (() => void) | undefined
  axios.defaults.adapter = async config => {
    const result = await fixtureAdapter(config)
    if (config.url?.endsWith('hbos_portal.api.csrf.get_token') && !release) return new Promise((_resolve, reject) => {
      release = () => reject(new axios.AxiosError('old token request', undefined, config, {}, { ...result, status, data: { exc_type: status === 401 ? 'AuthenticationError' : 'CSRFTokenError', message: 'old csrf token' } }))
    })
    return result
  }
  const api = await import('@/services/frappeClient'), signOut = vi.fn(); api.setUnauthorizedHandler(signOut)
  const rejected = expect(api.callFrappeMethod(prefix + queries[0], {}, { requireCsrf: true })).rejects.toMatchObject({ code: 'CSRF_MISMATCH' })
  await vi.waitFor(() => expect(release).toBeTypeOf('function'))
  token = 'synthetic-read-session-B'; api.clearCachedCsrfToken()
  await api.callFrappeMethod(prefix + queries[1], {}, { requireCsrf: true }); release!(); await rejected
  await api.callFrappeMethod(prefix + queries[2], {}, { requireCsrf: true })
  expect(tokenReads).toBe(2); expect(selected).toHaveLength(2); expect(signOut).not.toHaveBeenCalled()
})
it('a completed read from the old session cannot return data into the new session', async () => {
  const fixtureAdapter = axios.defaults.adapter as AxiosAdapter
  let release: (() => void) | undefined
  axios.defaults.adapter = async config => {
    const result = await fixtureAdapter(config)
    if (config.url?.endsWith(prefix + queries[0])) return new Promise(resolve => { release = () => resolve({ ...result, data: { message: { ok: true, data: { items: ['OLD-SESSION-ONLY'] } } } }) })
    return result
  }
  const api = await import('@/services/frappeClient'), signOut = vi.fn(); api.setUnauthorizedHandler(signOut)
  const rejected = expect(api.callFrappeMethod(prefix + queries[0], {}, { requireCsrf: true })).rejects.toMatchObject({ code: 'CSRF_MISMATCH' })
  await vi.waitFor(() => expect(release).toBeTypeOf('function'))
  token = 'synthetic-read-session-B'; api.clearCachedCsrfToken()
  await api.callFrappeMethod(prefix + queries[1], {}, { requireCsrf: true }); release!(); await rejected
  expect(selected).toHaveLength(2); expect(signOut).not.toHaveBeenCalled()
})
it.each([401, 403])('an old session %s response cannot clear the new token or sign it out', async status => {
  const fixtureAdapter = axios.defaults.adapter as AxiosAdapter
  let release: (() => void) | undefined
  axios.defaults.adapter = async config => {
    const result = await fixtureAdapter(config)
    if (config.url?.endsWith(prefix + queries[0])) return new Promise((_resolve, reject) => {
      release = () => reject(new axios.AxiosError('old session', undefined, config, {}, { ...result, status, data: { exc_type: status === 401 ? 'AuthenticationError' : 'CSRFTokenError', message: 'old csrf token' } }))
    })
    return result
  }
  const api = await import('@/services/frappeClient'), signOut = vi.fn(); api.setUnauthorizedHandler(signOut)
  const rejected = expect(api.callFrappeMethod(prefix + queries[0], {}, { requireCsrf: true })).rejects.toMatchObject({ code: 'CSRF_MISMATCH' })
  await vi.waitFor(() => expect(release).toBeTypeOf('function'))
  token = 'synthetic-read-session-B'; api.clearCachedCsrfToken()
  await api.callFrappeMethod(prefix + queries[1], {}, { requireCsrf: true }); release!(); await rejected
  await api.callFrappeMethod(prefix + queries[2], {}, { requireCsrf: true })
  expect(tokenReads).toBe(2); expect(selected.at(-1)?.token).toBe(token); expect(signOut).not.toHaveBeenCalled()
})
it.each([['FORBIDDEN', 403], ['NOT_SUPPORTED', 501], ['CONFLICT', 409], ['CONFLICT_RETRY_REQUIRED', 409], ['SOURCE_UNAVAILABLE', 503]] as const)('preserves %s without exposing server data or replaying reads', async (code, status) => {
  const fixtureAdapter = axios.defaults.adapter as AxiosAdapter
  axios.defaults.adapter = async config => {
    const result = await fixtureAdapter(config)
    if (config.url?.endsWith(prefix + queries[0])) throw new axios.AxiosError('synthetic private rejection', undefined, config, {}, {
      status, statusText: 'Rejected', headers: {}, config, data: { ok: false, error: { code, message: 'SYNTHETIC-PRIVATE-POLICY', retryable: true } },
    })
    return result
  }
  const api = await import('@/services/frappeClient'), signOut = vi.fn(); api.setUnauthorizedHandler(signOut)
  const error = await api.callFrappeMethod(prefix + queries[0], {}, { requireCsrf: true }).catch(e => e)
  expect(error.code).toBe(code); expect(error.message).not.toContain('SYNTHETIC-PRIVATE-POLICY')
  expect(error.retryable).toBe(true)
  expect(selected).toHaveLength(1); expect(tokenReads).toBe(1); expect(signOut).not.toHaveBeenCalled()
})
it('unknown codes and non-management endpoints keep a generic error', async () => {
  axios.defaults.adapter = async config => { throw new axios.AxiosError('private', undefined, config, {}, { status: 501, statusText: 'Rejected', headers: {}, config, data: { ok: false, error: { code: 'PRIVATE_CODE', message: 'SYNTHETIC-PRIVATE-POLICY' } } }) }
  const api = await import('@/services/frappeClient')
  for (const method of [prefix + queries[0], 'hbos_portal.api.people_access.get_people']) {
    const error = await api.callFrappeMethod(method).catch(e => e)
    expect(error.code).toBe('SERVICE_ERROR'); expect(error.message).not.toContain('SYNTHETIC-PRIVATE-POLICY')
  }
})
