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
let reports: typeof import('@/services/inventoryReports')
const fetchMock = vi.fn()
const token = (value: string) => ({ data: { message: { ok: true, data: { csrf_token: value } } } })
const failure = (status: number, excType: string) => ({
  ok: false, status, json: async () => ({ exc_type: excType }),
})

beforeEach(async () => {
  vi.resetModules()
  http.get.mockReset()
  http.post.mockReset()
  fetchMock.mockReset()
  vi.stubGlobal('fetch', fetchMock)
  client = await import('@/services/frappeClient')
  reports = await import('@/services/inventoryReports')
  client.clearFrappeCsrfToken()
})
afterEach(() => { vi.unstubAllGlobals() })

it('invalidates rejected export credentials without retrying the export', async () => {
  http.get.mockResolvedValueOnce(token('REJECTED-TOKEN'))
  fetchMock.mockResolvedValue(failure(400, 'CSRFTokenError'))
  await expect(reports.exportReport('合成库存报表', {})).rejects.toThrow('导出失败，请重试')
  expect(fetchMock).toHaveBeenCalledTimes(1)
  expect(fetchMock.mock.calls[0][1].headers['X-Frappe-CSRF-Token']).toBe('REJECTED-TOKEN')
  expect(http.get).toHaveBeenCalledTimes(1)
  http.get.mockResolvedValueOnce(token('REISSUED-TOKEN'))
  expect(await client.ensureCsrfToken()).toBe('REISSUED-TOKEN')
  expect(fetchMock).toHaveBeenCalledTimes(1)
})

it('does not let an old export CSRF failure erase new session credentials', async () => {
  let finish!: (response: ReturnType<typeof failure>) => void
  http.get.mockResolvedValueOnce(token('OLD-TOKEN'))
  fetchMock.mockReturnValue(new Promise(resolve => { finish = resolve }))
  const attempted = reports.exportReport('合成库存报表', {}).catch(error => error)
  await vi.waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1))
  client.clearFrappeCsrfToken()
  http.get.mockResolvedValueOnce(token('NEW-TOKEN'))
  await client.ensureCsrfToken()
  finish(failure(400, 'CSRFTokenError'))
  expect(await attempted).toMatchObject({ message: '导出失败，请重试；若反复失败请联系管理员。' })
  expect(await client.ensureCsrfToken()).toBe('NEW-TOKEN')
  expect(http.get).toHaveBeenCalledTimes(2)
  expect(fetchMock).toHaveBeenCalledTimes(1)
})

it('preserves business permission errors without invalidating a valid CSRF token', async () => {
  http.get.mockResolvedValueOnce(token('VALID-TOKEN'))
  fetchMock.mockResolvedValue(failure(403, 'PermissionError'))
  await expect(reports.exportReport('合成库存报表', {})).rejects.toThrow('你没有导出这张报表的权限。')
  expect(await client.ensureCsrfToken()).toBe('VALID-TOKEN')
  expect(http.get).toHaveBeenCalledTimes(1)
  expect(fetchMock).toHaveBeenCalledTimes(1)
})
