import { afterEach, describe, expect, it, vi } from 'vitest'
import { businessNavigationTarget } from '@/services/businessNavigation'

// 回归：ProfileSettingsView 的「管理个人资料」「进入管理后台」跳转的是 Frappe Desk
// （/app、/app/user/<id>），必须按数据源解析源头，不能再落到 Portal 自身 origin
// 而命中 404。开发态经 VITE_FRAPPE_APP_ORIGIN 打开 Frappe 源；生产同源时保持同源路径。
describe('Frappe Desk 跳转目标解析', () => {
  afterEach(() => vi.unstubAllEnvs())

  it('开发态指向 Frappe 源', () => {
    vi.stubEnv('VITE_FRAPPE_APP_ORIGIN', 'http://127.0.0.1:8080')
    expect(businessNavigationTarget('/app')).toBe('http://127.0.0.1:8080/app')
    expect(businessNavigationTarget('/app/user/Administrator')).toBe(
      'http://127.0.0.1:8080/app/user/Administrator',
    )
  })

  it('生产同源（未设 Frappe 源）保持同源路径', () => {
    vi.stubEnv('VITE_FRAPPE_APP_ORIGIN', '')
    expect(businessNavigationTarget('/app')).toBe('/app')
    expect(businessNavigationTarget('/app/user/Administrator')).toBe('/app/user/Administrator')
  })

  it('Portal 自身路由不跨源', () => {
    vi.stubEnv('VITE_FRAPPE_APP_ORIGIN', 'http://127.0.0.1:8080')
    expect(businessNavigationTarget('/hbos/profile')).toBe('/hbos/profile')
  })
})
