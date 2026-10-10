/**
 * SPA 原生路由清单 —— **单一出处**。
 *
 * `businessNavigation.ts` 用它判断「这个路径是不是本 SPA 自己的」，
 * 从而决定**要不要问后端**。此前这个判断散在几处，加新模块时容易漏改
 * （生产看板就漏了：路由在 SPA 里，但入口仍去问后端，被拒后点了没反应）。
 *
 * 加新原生模块时**只需在这里加一行**。
 */

/** SPA 自己处理、且**不经过后端**的顶级路径前缀。 */
export const NATIVE_PORTAL_PREFIXES = [
  '/hbos/production',
] as const

/** 永远属于 SPA 的路径（首页 / 工作台 / 应用中心 / 我的）。 */
const PORTAL_CORE = ['/hbos', '/hbos/work', '/hbos/apps', '/hbos/profile'] as const

/**
 * 该路径是否由 SPA 自己渲染（不必问后端）。
 *
 * 注意：`/hbos/lims`、`/hbos/inventory` 等**不在**此列 ——
 * 它们的路由确实在 SPA 内，但「能不能进」由后端按权限决定（access 门禁），
 * 所以仍要问后端。只有**前端自有模块**（与 Frappe 无关、后端注册表里没有）
 * 才走这条短路。
 */
export function isNativePortalPath(path: string): boolean {
  // 用 `indexOf` 切掉 query/hash —— `split(...)[0]` 在 noUncheckedIndexedAccess
  // 下是 `string | undefined`，会让下面每处都报错。
  const raw = String(path || '')
  const cut = raw.search(/[?#]/)
  const p = cut === -1 ? raw : raw.slice(0, cut)

  if (!p.startsWith('/hbos')) return false
  if ((PORTAL_CORE as readonly string[]).includes(p)) return true
  return NATIVE_PORTAL_PREFIXES.some(
    (prefix) => p === prefix || p.startsWith(prefix + '/'),
  )
}
