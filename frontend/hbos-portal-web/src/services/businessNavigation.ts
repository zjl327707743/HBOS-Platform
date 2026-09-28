import type { Router } from 'vue-router'
import { resolveBusinessRoute } from '@/services/portalProvider'

// 稳定 /hbos/... 路由属于 Portal SPA 自己；解析到其他路径说明该 App 当前
// 由 Frappe 实现，交给门户内的 iframe 承载，而不是整页跳出门户。
export async function openBusinessRoute(
  router: Router,
  appId: string,
  stablePath: string,
) {
  try {
    const resolved = await resolveBusinessRoute(appId, stablePath)

    if (resolved.startsWith('/hbos/')) {
      await router.push(resolved)
      return
    }

    await router.push({
      name: 'business-embed',
      query: { app: appId, path: stablePath },
    })
  } catch (error) {
    // 解析失败不能表现成「点了没反应」：跳转到无权限视图并留下诊断。
    console.error('[hbos] 业务路由解析失败', error)
    await router.push({ name: 'forbidden' })
  }
}
