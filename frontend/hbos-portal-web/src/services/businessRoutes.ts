// Mock 模式的业务实现路由，对应 frappe 模式下由业务 App 自己经
// hbos_portal.api.routes.resolve_route 解析出的结果。
//
// 不在表内的 App 保持其稳定 /hbos/... 门户路由（即由 Portal SPA 自己渲染，
// 例如 LIMS）。在表内的 App 解析到 Frappe 路径，由 iframe 承载。
export const mockBusinessRoutes: Record<string, string> = {
  attendance: '/desk/hbos-attendance-dashboard',
}
