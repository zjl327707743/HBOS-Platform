import type { AppManifestDTO, PortalDataSource } from '@/contracts/portal'

export type LimsShellCapability =
  | 'dashboard'
  | 'tasks'
  | 'results'
  | 'samples'
  | 'ledger'
  | 'coa'
  | 'specifications'
  | 'retains'
  | 'stability'
  | 'audit'

/**
 * A Provider capability is data access, not a permission to render a route.
 * Keep the page target list explicit so a backend manifest cannot accidentally
 * publish a link to a pending or write-capable page.
 */
const IMPLEMENTED_PAGE_TARGETS: Record<PortalDataSource, ReadonlySet<LimsShellCapability>> = {
  mock: new Set<LimsShellCapability>(['dashboard', 'tasks', 'results', 'ledger', 'coa', 'specifications', 'retains', 'stability', 'audit']),
  frappe: new Set<LimsShellCapability>(['dashboard', 'tasks', 'results', 'ledger', 'coa', 'specifications', 'retains', 'stability', 'audit']),
}

const REQUIRED_ACCESS_CAPABILITY: Partial<Record<LimsShellCapability, string>> = {
  results: 'lims.results.read',
  ledger: 'lims.ledger.read',
  retains: 'lims.retention.read',
}

export function resolveLimsShellCapabilities(
  app: AppManifestDTO | undefined,
  dataSource: PortalDataSource,
): ReadonlySet<LimsShellCapability> {
  const providerCapabilities = new Set(app?.capabilities || [])
  const implementedTargets = IMPLEMENTED_PAGE_TARGETS[dataSource]
  const resolved = new Set<LimsShellCapability>()
  if (implementedTargets.has('dashboard') && providerCapabilities.has('summary')) {
    resolved.add('dashboard')
  }
  if (implementedTargets.has('tasks') && providerCapabilities.has('tasks')) {
    resolved.add('tasks')
  }
  for (const capability of ['results', 'samples', 'ledger', 'coa', 'specifications', 'retains', 'stability', 'audit'] as const) {
    if (!implementedTargets.has(capability) || !providerCapabilities.has(capability)) continue
    const requiredAccess = REQUIRED_ACCESS_CAPABILITY[capability]
    if (dataSource === 'frappe' && requiredAccess && !app?.accessCapabilities?.includes(requiredAccess)) continue
    if (capability === 'audit' && dataSource === 'frappe' && !app?.accessCapabilities?.includes('lims.audit.read')) {
      continue
    }
    resolved.add(capability)
  }
  return resolved
}
