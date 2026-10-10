import type { DemoDepartment, DemoPermissionApp, DemoPerson, DemoPosition, DemoRole } from '@/contracts/peopleAccessDemo'

/** 全部为合成数据。只有 Mock 页面会加载；每个页面会话取得独立副本。 */
export function createPeopleAccessDemoData() {
  const departments: DemoDepartment[] = [
    { id: 'all', name: '海滨药业', parentId: null, level: 0 },
    { id: 'qc', name: '质量控制部', parentId: 'all', level: 1 },
    { id: 'lab1', name: '化验一组', parentId: 'qc', level: 2 },
    { id: 'lab2', name: '无菌检验组', parentId: 'qc', level: 2 },
    { id: 'qa', name: '质量管理部', parentId: 'all', level: 1 },
    { id: 'store', name: '仓储部', parentId: 'all', level: 1 },
    { id: 'admin', name: '综合管理部', parentId: 'all', level: 1 },
  ]
  const menu = (id: string, label: string, actions: [string, string][]) => ({
    id, label, actions: actions.map(([key, text]) => ({ id: `${id}.${key}`, label: text })),
  })
  const directory: DemoPermissionApp[] = [
    { id: 'platform', label: '平台基础', menus: [
      menu('platform.home', '工作台', [['read', '查看']]),
      menu('platform.people', '人员信息', [['read', '查看'], ['create', '新增'], ['edit', '编辑'], ['disable', '停用']]),
      menu('platform.roles', '权限管理', [['read', '查看'], ['create', '新增'], ['edit', '编辑'], ['bind', '关联岗位']]),
    ] },
    { id: 'lims', label: 'LIMS 实验室', menus: [
      menu('lims.sample', '样品管理', [['read', '查看'], ['create', '登记'], ['edit', '编辑']]),
      menu('lims.result', '检验记录', [['read', '查看'], ['edit', '录入'], ['submit', '提交']]),
      menu('lims.review', '检验复核', [['read', '查看'], ['review', '复核']]),
      menu('lims.quality', '质量审核', [['read', '查看'], ['approve', '审核']]),
    ] },
    { id: 'warehouse', label: '仓储管理（扩展示例）', menus: [
      menu('warehouse.stock', '库存台账', [['read', '查看']]),
      menu('warehouse.move', '出入库记录', [['read', '查看'], ['create', '登记']]),
    ] },
  ]
  const roles: DemoRole[] = [
    { id: 'r1', name: '检验员', createdAt: '2026-10-01', description: '登记样品、录入与提交本人负责的检验记录。', permissionIds: ['platform.home.read', 'lims.sample.read', 'lims.sample.create', 'lims.result.read', 'lims.result.edit', 'lims.result.submit'] },
    { id: 'r2', name: '检验复核员', createdAt: '2026-10-01', description: '查看岗位关联检验组的记录，完成检验复核。', permissionIds: ['platform.home.read', 'lims.result.read', 'lims.review.read', 'lims.review.review'] },
    { id: 'r3', name: 'QA 审核员', createdAt: '2026-10-01', description: '在岗位授权范围内查看检验结果并进行质量审核。', permissionIds: ['platform.home.read', 'lims.result.read', 'lims.quality.read', 'lims.quality.approve'] },
    { id: 'r4', name: '仓库操作员', createdAt: '2026-10-03', description: '查看库存台账，登记岗位所属仓库的出入库记录。', permissionIds: ['platform.home.read', 'warehouse.stock.read', 'warehouse.move.read', 'warehouse.move.create'] },
    { id: 'r5', name: '人员管理员', createdAt: '2026-10-03', description: '维护所负责部门的人员信息与任职岗位。', permissionIds: ['platform.home.read', 'platform.people.read', 'platform.people.create', 'platform.people.edit', 'platform.people.disable'] },
    { id: 'r6', name: '权限管理员', createdAt: '2026-10-03', description: '维护角色权限与岗位关联，不自动取得业务签署权限。', permissionIds: ['platform.home.read', 'platform.roles.read', 'platform.roles.create', 'platform.roles.edit', 'platform.roles.bind'] },
  ]
  const positions: DemoPosition[] = [
    { id: 'p1', departmentId: 'lab1', name: '检验员', scopeLabel: '化验一组 · 本人负责记录（口径待确认）', roleIds: ['r1'] },
    { id: 'p2', departmentId: 'lab1', name: '复核员', scopeLabel: '化验一组 · 复核范围', roleIds: ['r2'] },
    { id: 'p3', departmentId: 'lab2', name: '检验员', scopeLabel: '无菌检验组 · 本人负责记录（口径待确认）', roleIds: ['r1'] },
    { id: 'p4', departmentId: 'qa', name: 'QA 审核员', scopeLabel: '质量管理部 · 获准审核范围', roleIds: ['r3'] },
    { id: 'p5', departmentId: 'store', name: '仓库管理员', scopeLabel: '仓储部 · 一号仓库', roleIds: ['r4'] },
    { id: 'p6', departmentId: 'admin', name: '人事专员', scopeLabel: '综合管理部 · 人员维护范围', roleIds: ['r5'] },
    { id: 'p7', departmentId: 'admin', name: '权限管理专员', scopeLabel: '已获准管理的角色与岗位', roleIds: ['r6'] },
  ]
  const names = ['张明', '李晨', '王敏', '赵宁', '刘洋', '陈静', '周杰', '孙悦', '郑林', '何佳']
  const assignments = [['p1'], ['p1'], ['p2'], ['p3'], ['p3'], ['p4'], ['p5'], ['p6'], ['p7'], ['p1', 'p3']]
  const people: DemoPerson[] = names.map((name, index) => ({
    id: `HB${String(index + 1).padStart(3, '0')}`, name, phone: `138****${2001 + index}`,
    active: true, positionIds: [...assignments[index]!],
  }))
  return { departments, directory, roles, positions, people }
}
