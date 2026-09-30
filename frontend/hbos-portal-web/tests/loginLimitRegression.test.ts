import { expect, it } from 'vitest'
import { normalizeFrappeError } from '@/services/frappeClient'

it.each(['login', 'hbos_portal.auth.accounts.reauthenticate'])('E06: native account lock explains retry for %s', method => {
  // The installed Frappe SecurityException currently arrives with HTTP 500.
  const error = normalizeFrappeError({ isAxiosError: true, response: { status: 500, data: {
    exc_type: 'SecurityException',
    _server_messages: JSON.stringify([JSON.stringify({ message: 'Your account has been locked and will resume after 300 seconds' })]),
  } } }, method)
  expect(error.code).toBe('RATE_LIMITED')
  expect(error.message).toBe('验证尝试较多，当前暂不可用。请稍后重试。')
})

it('E06: an unrelated server exception keeps the service failure result', () => {
  const error = normalizeFrappeError({ isAxiosError: true, response: { status: 500, data: {
    exc_type: 'SecurityException', exception: 'An unrelated security policy failed',
  } } }, 'login')
  expect(error.code).toBe('SERVICE_ERROR')
})
