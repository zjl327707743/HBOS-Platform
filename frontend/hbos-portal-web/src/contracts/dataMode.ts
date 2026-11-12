import type { PortalDataSource } from './portal'

/** 数据来源必须明确指定；拼写错误和缺省值都不能变成演示数据。 */
export function resolvePortalDataMode(value: unknown): PortalDataSource {
  if (value === 'mock' || value === 'frappe') return value
  throw new Error('VITE_PORTAL_DATA_MODE 必须显式设置为 mock 或 frappe。')
}

export function validatePortalBuildMode(value: unknown, command: string, mode: string) {
  const dataMode = resolvePortalDataMode(value)
  if (command === 'build' && mode !== 'mock' && dataMode !== 'frappe') {
    throw new Error('生产构建必须使用 frappe；演示构建请使用 npm run build:mock。')
  }
  return dataMode
}
