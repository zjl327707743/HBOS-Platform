export * from '../../src/data/mockPortal'
import type { AppManifestDTO, PortalUser } from '../../src/contracts/portal'
import { appManifests as defaults } from '../../src/data/mockPortal'

const reader = new URLSearchParams(location.search).get('state') === 'reader'
export const portalUser: PortalUser = {
  id: 'knowledge-v17-synthetic',
  displayName: reader ? '合成员工' : '合成维护者',
  avatarText: '测',
  roleLabel: reader ? '员工' : '资料维护',
  department: '合成质量管理部',
}
export const appManifests: AppManifestDTO[] = [{
  id: 'knowledge', title: '知识库', shortTitle: '知识库', description: '查阅共享资料',
  icon: 'ReadOutlined', accent: 'knowledge', route: '/hbos/knowledge', migrationMode: 'native',
  capabilitySummary: false, capabilitySearch: false, capabilityTasks: false, featured: true,
}, ...defaults]
