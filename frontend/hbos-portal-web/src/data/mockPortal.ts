import type {
  AppManifestDTO,
  BusinessPulseDTO,
  LimsQueueItemDTO,
  PortalUser,
  SearchResultDTO,
  SummaryMetricDTO,
  TwinStatusDTO,
  UnifiedTaskDTO,
} from '@/contracts/portal'

export const portalUser: PortalUser = {
  id: 'carlo@example.com',
  displayName: 'Carlo',
  avatarText: 'CZ',
  roleLabel: 'HBOS User',
  department: '新乡海滨',
}

export const appManifests: AppManifestDTO[] = [
  { id: 'lims', title: '实验室质量管理', shortTitle: 'LIMS', description: '检验、质量、留样与稳定性管理', icon: 'ExperimentOutlined', accent: 'lims', route: '/hbos/lims', migrationMode: 'native', capabilitySummary: true, capabilityTasks: true, capabilitySearch: true, pendingCount: 5, meta: '5 个待处理', featured: true },
  { id: 'inventory', title: '仓储库存', shortTitle: 'Inventory', description: '入库、出库、批次、货位与盘点', icon: 'InboxOutlined', accent: 'inventory', route: '/hbos/inventory', migrationMode: 'hybrid', capabilitySummary: true, capabilityTasks: true, capabilitySearch: true, pendingCount: 3, meta: '3 个待处理', featured: true },
  { id: 'attendance', title: '考勤管理', shortTitle: 'Attendance', description: '个人、团队、异常与排班', icon: 'ClockCircleOutlined', accent: 'attendance', route: '/hbos/attendance', migrationMode: 'legacy', capabilitySummary: true, capabilityTasks: true, capabilitySearch: true, pendingCount: 3, meta: '3 个异常', featured: true },
  { id: 'equipment', title: '设备管理', shortTitle: 'Equipment', description: '设备、点检、健康与数字孪生', icon: 'ToolOutlined', accent: 'equipment', route: '/hbos/equipment', migrationMode: 'native', capabilitySummary: true, capabilityTasks: false, capabilitySearch: true, meta: '98.5% 在线', featured: true },
  { id: 'production', title: '生产运营', shortTitle: 'Production', description: '未来生产运营应用', icon: 'ThunderboltOutlined', accent: 'production', route: '/hbos/production', migrationMode: 'native', capabilitySummary: false, capabilityTasks: false, capabilitySearch: false, meta: '规划中' },
  { id: 'ehs', title: 'EHS', shortTitle: 'EHS', description: '环境、健康与安全', icon: 'SafetyOutlined', accent: 'ehs', route: '/hbos/ehs', migrationMode: 'native', capabilitySummary: false, capabilityTasks: false, capabilitySearch: false, meta: '未来应用' },
  { id: 'training', title: '培训', shortTitle: 'Training', description: '人员培训与能力发展', icon: 'ReadOutlined', accent: 'training', route: '/hbos/training', migrationMode: 'native', capabilitySummary: false, capabilityTasks: false, capabilitySearch: false, meta: '未来应用' },
]

export const heroMetrics: SummaryMetricDTO[] = [
  { id: 'attendance-exception', label: '考勤异常', value: 3, appId: 'attendance', tone: 'info', meta: 'Attendance' },
  { id: 'lims-review', label: '待复核', value: 5, appId: 'lims', tone: 'success', meta: 'LIMS' },
  { id: 'inventory-work', label: '仓储待处理', value: 3, appId: 'inventory', tone: 'warning', meta: 'Inventory' },
  { id: 'equipment-online', label: '设备在线率', value: '98.5%', appId: 'equipment', tone: 'info', meta: 'Equipment' },
]

export const tasks: UnifiedTaskDTO[] = [
  { taskId: 'lims:review:RESULT-001', appId: 'lims', appTitle: 'LIMS', title: '复核阿莫西林含量结果', description: 'SAMPLE-001 · RESULT-001', priority: 'critical', dueLabel: '今天 16:00', dueGroup: 'today', status: 'open', overdue: true, deepLink: '/hbos/lims' },
  { taskId: 'attendance:exception:001', appId: 'attendance', appTitle: 'Attendance', title: '处理考勤异常申请', description: '生产二部 · 今日异常', priority: 'high', dueLabel: '今天 17:00', dueGroup: 'today', status: 'open', deepLink: '/hbos/work' },
  { taskId: 'inventory:inbound:PO-2024-0092', appId: 'inventory', appTitle: 'Inventory', title: '审核入库单 PO-2024-0092', description: '六车间中间库', priority: 'normal', dueLabel: '今天 18:00', dueGroup: 'today', status: 'open', deepLink: '/hbos/apps' },
  { taskId: 'equipment:inspection:M607B', appId: 'equipment', appTitle: 'Equipment', title: 'M607B 设备点检确认', description: '三合一设备', priority: 'normal', dueLabel: '明天 09:00', dueGroup: 'week', status: 'open', deepLink: '/hbos/work' },
  { taskId: 'lims:stability:TP-026', appId: 'lims', appTitle: 'LIMS', title: '稳定性时间点取样', description: 'STB-2026-023 · 6M', priority: 'high', dueLabel: '周五 14:00', dueGroup: 'week', status: 'open', deepLink: '/hbos/lims' },
  { taskId: 'inventory:count:3904', appId: 'inventory', appTitle: 'Inventory', title: '六车间中间库盘点', description: '3904 · 203 个货位', priority: 'normal', dueLabel: '周五 18:00', dueGroup: 'week', status: 'waiting', deepLink: '/hbos/apps' },
  { taskId: 'lims:done:RESULT-098', appId: 'lims', appTitle: 'LIMS', title: '复核头孢样品结果', description: 'RESULT-098', priority: 'normal', dueLabel: '昨天', dueGroup: 'later', status: 'done', deepLink: '/hbos/lims' },
]

export const businessPulse: BusinessPulseDTO[] = [
  { id: 'weekly-tests', label: '本周检验批量', value: '128', trend: '↑ 12% 较上周', tone: 'success', sparkline: [18, 25, 23, 31, 29, 36, 42] },
  { id: 'release-rate', label: '质量放行率', value: '98.2%', trend: '↑ 1.1%', tone: 'success', sparkline: [88, 94, 92, 95, 93, 97, 98] },
  { id: 'inventory-pending', label: '待处理仓储任务', value: '3', trend: '2 项今天截止', tone: 'warning' },
  { id: 'equipment-online', label: '设备在线率', value: '98.5%', trend: 'M607B 正常', tone: 'info' },
]

export const twinStatuses: TwinStatusDTO[] = [
  { id: 'production', label: '生产状态', value: '正常运行', progress: 84, tone: 'success' },
  { id: 'batch', label: '今日生产批次', value: '12', progress: 72, tone: 'info' },
  { id: 'health', label: '设备健康度', value: '98.5%', progress: 98.5, tone: 'success' },
  { id: 'environment', label: '环境监测', value: '正常', tone: 'success' },
]

export const searchResults: SearchResultDTO[] = [
  { id: 'batch-26092401', appId: 'inventory', appTitle: 'Inventory', title: '批次 26092401', subtitle: '已放行 · 六车间中间库', typeLabel: '批次', deepLink: '/hbos/apps' },
  { id: 'sample-001', appId: 'lims', appTitle: 'LIMS', title: 'SAMPLE-001 · 26092401', subtitle: '阿莫西林 · 检验中', typeLabel: '样品', deepLink: '/hbos/lims' },
  { id: 'attendance-ex', appId: 'attendance', appTitle: 'Attendance', title: '我的考勤异常', subtitle: '3 项待处理', typeLabel: '快捷操作', deepLink: '/hbos/work' },
  { id: 'm607b', appId: 'equipment', appTitle: 'Equipment', title: 'M607B 三合一设备', subtitle: '设备健康度 98.5%', typeLabel: '设备', deepLink: '/hbos' },
]

export const limsQueue: LimsQueueItemDTO[] = [
  { id: 'Q-001', sample: 'SAMPLE-001', material: '阿莫西林', action: '结果复核', owner: '角色待处理', due: '今天 16:00', status: '待复核', tone: 'critical' },
  { id: 'Q-002', sample: 'STB-023-6M', material: '美罗培南', action: '稳定性取样', owner: '指派给我', due: '周五 14:00', status: '待取样', tone: 'warning' },
  { id: 'Q-003', sample: 'SAMPLE-031', material: '头孢原料', action: '开始检验', owner: '指派给我', due: '明天 10:00', status: '已分配', tone: 'info' },
  { id: 'Q-004', sample: 'COA-024', material: '注射用原料', action: 'QA 审核', owner: '角色待处理', due: '周五 17:00', status: '待审核', tone: 'success' },
]
