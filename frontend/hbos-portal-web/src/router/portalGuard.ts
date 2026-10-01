import type { RouteLocationNormalized } from 'vue-router'
import type { PortalDataSource } from '@/contracts/portal'
import type { usePortalStore } from '@/stores/portal'
import { resolveLimsShellCapabilities, type LimsShellCapability } from '@/services/limsCapabilities'

type PortalSession = Pick<ReturnType<typeof usePortalStore>, 'ensureSession' | 'bootstrapError' | 'apps'>

export async function checkPortalAccess(
  to: Pick<RouteLocationNormalized, 'meta' | 'fullPath'>,
  portal: PortalSession,
  dataSource: PortalDataSource,
) {
  if (!to.meta.requiresAuth) return true
  if (!(await portal.ensureSession())) {
    return { name: 'login', query: { redirect: to.fullPath } }
  }

  // An unavailable bootstrap is not an access denial. Keep the requested
  // route so the shell can show its error and retry control.
  if (portal.bootstrapError) return true

  // Bootstrap only includes apps whose provider grants access. Apply that
  // check to copied URLs as well as clicks from the App Center.
  if (
    dataSource === 'frappe' &&
    to.meta.appId === 'lims' &&
    !portal.apps.some((app) => app.id === 'lims')
  ) {
    return { name: 'forbidden' }
  }

  if (
    dataSource === 'frappe' &&
    to.meta.appId === 'lims' &&
    typeof to.meta.limsCapability === 'string'
  ) {
    const limsApp = portal.apps.find((app) => app.id === 'lims')
    const capabilities = resolveLimsShellCapabilities(limsApp, dataSource)
    if (!capabilities.has(to.meta.limsCapability as LimsShellCapability)) {
      // A declared Provider capability without the user's semantic access is
      // a permission result; an undeclared capability is still pending design.
      return limsApp?.capabilities?.includes(to.meta.limsCapability) ? { name: 'forbidden' } : { name: 'lims-pending' }
    }
  }

  return true
}
