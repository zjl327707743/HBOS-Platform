// Mock 模式的业务实现路由，对应 frappe 模式下由业务 App 自己经
// hbos_portal.api.routes.resolve_route 解析出的结果。
//
// 不在表内的 App 保持其稳定 /hbos/... 门户路由（即由 Portal SPA 自己渲染，
// 例如 LIMS）。在表内的 App 解析到 Frappe 路径，由 iframe 承载。
// 当前为空：三个 App 的实现都已在 Portal SPA 内。
// 保留此表是因为它同时充当 iframe 白名单（见 isEmbeddedApp）——
// 将来某个 App 需要内嵌 Desk 页面时，在这里登记即可。
export const mockBusinessRoutes: Record<string, string> = {}
