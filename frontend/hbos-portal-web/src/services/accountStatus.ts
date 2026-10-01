import type { SecurityStatus } from './accountApi'

export function describeLoginMethods(status: SecurityStatus | null) {
  if (!status) return { enabled: '暂未取得账号状态', detail: '请在账号与安全重试读取。' }
  const enabled = []
  if (status.has_password && status.password_login_available !== false) enabled.push('密码')
  if (status.feishu_bound && status.feishu_configured) enabled.push('本人飞书')
  const detail = []
  if (!status.has_password) detail.push('尚未设置密码')
  else if (status.password_login_available === false) detail.push('密码登录暂不可用')
  if (!status.feishu_bound) detail.push('飞书未绑定')
  else if (!status.feishu_configured) detail.push('飞书已绑定 · 渠道暂不可用')
  return { enabled: enabled.join('、') || '暂无可用登录方式', detail: detail.join('；') }
}
