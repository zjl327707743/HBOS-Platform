/**
 * Mock 数据加载器：仅被 portalProvider 在 `portalDataSource !== 'frappe'`
 * 的分支中动态引用。frappe 构建里该模块的引用点是 `null`（编译期由
 * dataMode 常量决定），Rollup 会整体剔除本模块及其数据，正式产物不携带
 * 任何 Mock 数据（由 scripts/portal/mock_content_gate.mjs 门禁保证）。
 */
export async function loadMockPortalData() {
  return import('@/data/mockPortal')
}
