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

it.each(['AuthenticationError', 'ExpiredLoginException'])('A04: a native MFA %s explains the current verification step', exc_type => {
  const error = normalizeFrappeError({ isAxiosError: true, response: { status: 401, data: {
    exc_type, message: 'Incorrect Verification code',
  } } }, 'login_mfa')
  expect(error.message).toBe('二次认证未通过或已过期。请重新登录并输入当前验证码。')
})

it('A02: primary password failures still use the uniform credential message', () => {
  const error = normalizeFrappeError({ isAxiosError: true, response: { status: 401, data: {
    exc_type: 'AuthenticationError', message: 'Invalid login credentials',
  } } }, 'login')
  expect(error.message).toBe('账号或密码不正确。')
})

it('a rejected login origin explains the configured entry instead of asking for a page refresh', () => {
  const error = normalizeFrappeError({ isAxiosError: true, response: { status: 400, data: {
    exc_type: 'CSRFTokenError',
    _server_messages: JSON.stringify([JSON.stringify({ message: '请求来源无效。' })]),
  } } }, 'login')
  expect(error.code).toBe('INVALID_ORIGIN')
  expect(error.message).toBe('当前访问来源不是受信任的登录入口，请从正式入口重新登录。')
})

it('a real token mismatch still explains session renewal', () => {
  const error = normalizeFrappeError({ isAxiosError: true, response: { status: 400, data: {
    exc_type: 'CSRFTokenError', message: '安全会话已更新，请刷新后重试。',
  } } }, 'login')
  expect(error.code).toBe('CSRF_MISMATCH')
  expect(error.message).toBe('安全会话已更新，请刷新页面后重试。')
})
