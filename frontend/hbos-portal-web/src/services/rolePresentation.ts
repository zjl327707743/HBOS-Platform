import type { RoleFeature } from './iamRoles'
export const roleFeatureKey = (feature: RoleFeature) => JSON.stringify([feature.operation_id, feature.scope_binding])
export const sameRoleFeatures = (left: RoleFeature[], right: RoleFeature[]) => JSON.stringify(left.map(roleFeatureKey).sort()) === JSON.stringify(right.map(roleFeatureKey).sort())
export const roleScopeLabel = (binding: string) => binding === 'SELF' ? '仅本人' : binding === 'RESPONSIBLE_DEPARTMENTS' ? '仅限员工明确负责的部门，不包含下级' : binding === 'RESPONSIBLE_COMPANIES' ? '仅限员工明确负责的一个公司' : '范围需核对'
export const roleGroups = [ ['self', '本人的考勤'], ['board', '部门看板'], ['records', '员工考勤'], ['company', '公司考勤'], ['schedule', '班次与排班'], ['correction', '考勤更正'], ['import', '数据导入'], ['rules', '规则与重算'], ['reports', '考勤报表'], ['export', '数据导出'] ] as const
