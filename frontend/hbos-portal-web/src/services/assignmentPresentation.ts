// Display-only adapter. It never decides authorization; it turns server facts
// into the user's vocabulary and keeps unknown values visibly unknown.
export const ROLE_KEYS = ['staff', 'clerk', 'admin'] as const
export type RoleKey = typeof ROLE_KEYS[number]

export const rolePurpose: Record<string, string> = {
  staff: '查看自己的考勤',
  clerk: '协助负责部门核对日常考勤',
  admin: '在获准公司内办理考勤管理',
}
export const roleTitle = (key?: string | null, fallback?: string) =>
  fallback || ({ staff: '普通员工', clerk: '部门考勤员', admin: '考勤管理员' } as Record<string, string>)[key || ''] || '角色待核对'
export const boundaryText = (kind?: string) =>
  kind === 'SELF' ? '仅本人' : kind === 'DEPARTMENT' ? '明确负责的部门，不含下级' : kind === 'COMPANY' ? '明确指定的一个公司' : '范围类型待核对'

export type MemberSource = 'FOLLOW_DEPARTMENT' | 'DIRECT' | 'NONE' | 'LEGACY' | 'UNKNOWN'
export const sourceLabel = (source: MemberSource) => ({
  FOLLOW_DEPARTMENT: '跟随部门',
  DIRECT: '单独设置',
  NONE: '未分配',
  LEGACY: '历史安排',
  UNKNOWN: '来源待核对',
} as Record<MemberSource, string>)[source]

export interface MemberStatus {
  tone: 'neutral' | 'brand' | 'success' | 'warning' | 'error'
  label: string
  detail: string
  /** Only a server-verified admission row can be confirmed or revoked. */
  admissionAction: 'confirm' | 'revoke' | ''
}

/**
 * §5.6 mapping. Every branch is explicit: an unknown admission value or a
 * failed read is `暂无法确认`, never automatic inheritance and never success.
 */
export function memberStatus(input: {
  source: MemberSource
  admissionState?: string
  revoked?: boolean
  confirmed?: boolean
  effective?: boolean | null
  reason?: string
  accountStatus?: string
}): MemberStatus {
  const reason = input.reason || ''
  if (input.accountStatus === 'unopened') {
    return { tone: 'neutral', label: '待开通账号', detail: '员工档案已存在；核验归属并开通账号后，部门安排才会生效。', admissionAction: '' }
  }
  if (input.accountStatus === 'disabled') {
    return { tone: 'neutral', label: '账号已停用', detail: '账号停用期间不能使用该角色；停用不等于撤销角色安排。', admissionAction: '' }
  }
  if (input.source === 'NONE') return { tone: 'neutral', label: '未通过此来源分配', detail: '不等于账号停用；个人安排与其他应用保持。', admissionAction: '' }
  if (input.source === 'LEGACY') return { tone: 'neutral', label: '沿用原有安排', detail: reason || '尚未使用新的部门默认；不会自动转换。', admissionAction: '' }
  if (input.source === 'DIRECT') return { tone: 'brand', label: '单独设置', detail: reason || '此人的考勤角色由个人设置决定，不受部门默认改变。', admissionAction: '' }
  if (input.source === 'UNKNOWN') return { tone: 'neutral', label: '暂无法确认', detail: '当前无法读取此人的状态；未显示为可用，也未按零处理。', admissionAction: '' }
  const state = (input.admissionState || '').toUpperCase()
  if (state === 'PENDING') return { tone: 'warning', label: '待确认角色', detail: reason || '确认前不能使用此角色。', admissionAction: 'confirm' }
  if (state === 'REVOKED' || input.revoked) return { tone: 'neutral', label: '已撤销确认', detail: reason || '需重新预览并逐人确认后才能使用。', admissionAction: 'confirm' }
  if (state === 'CONFIRMED' || input.confirmed) {
    if (input.effective === false) return { tone: 'warning', label: '已确认 · 仍受限', detail: reason || '已确认角色，但仍有个别限制；不会因确认自动解除。', admissionAction: 'revoke' }
    if (input.effective === true) return { tone: 'success', label: '可使用', detail: reason || '已按当前发布版本与负责范围生效。', admissionAction: 'revoke' }
    return { tone: 'neutral', label: '已确认 · 实际状态待核对', detail: '已确认角色，但服务端未返回实际可用结果；不据此声称可用。', admissionAction: 'revoke' }
  }
  if (state === 'AUTO') return { tone: input.effective === false ? 'warning' : 'success', label: input.effective === false ? '跟随部门 · 暂不可用' : '跟随部门 · 可使用', detail: reason || '普通员工角色不需要逐人确认。', admissionAction: '' }
  return { tone: 'neutral', label: '暂无法确认', detail: '服务端未返回可识别的状态；没有授予动作，也不按零处理。', admissionAction: '' }
}

export const managementRole = (roleKey?: string | null) => roleKey === 'clerk' || roleKey === 'admin'

export function scopeRefsOf(rows?: Array<{ scope_ref?: string }> | null) {
  return (rows || []).map(row => row.scope_ref || '').filter(Boolean)
}
