import { beforeEach, describe, expect, it, vi } from 'vitest'

const capabilities = vi.hoisted(() => new Set<string>())
vi.mock('@/services/iamAccess', () => ({ canIam: (capability: string) => capabilities.has(capability) }))

import { managementLinks } from '@/services/managementNavigation'

describe('management navigation capability fallback', () => {
  beforeEach(() => capabilities.clear())

  it('shows the access workspace when access is the only management capability', () => {
    capabilities.add('iam.access.read')
    expect(managementLinks()).toContainEqual({
      path: '/hbos/admin/access', label: '原应用权限', cap: 'iam.access.read', icon: 'access',
    })
  })

  it('keeps access diagnostics in more tools when a primary management page exists', () => {
    capabilities.add('iam.access.read')
    capabilities.add('iam.people.read')
    expect(managementLinks().map(row => row.path)).toEqual(['/hbos/admin/people'])
  })
})
