import { state, saveDemo, isAdmin } from './model.js'
import { planWorkChanges, planRestoreDepartment, planSuspendApp, planReenableApp } from './work-policy.js'

function commitTarget(plan) {
  const target = (plan.subjectKind === 'department' ? state.depts : state.employees).find(item => item.id === plan.subjectId)
  if (!target) throw new Error('配置对象已变化，请重新打开。')
  // Only write the named target's touched rules and this app's suspension backup.
  // Never assign nextData/session or snapshot the whole effective application.
  for (const entry of plan.patch) {
    if (entry.remove) { if (target[entry.property]) delete target[entry.property][entry.key] }
    else { target[entry.property] ||= {}; target[entry.property][entry.key] = JSON.parse(JSON.stringify(entry.value)) }
  }
}
async function submit(label, planner, expectedRevision) {
  if (!isAdmin.value) return { ok: false, error: '当前账号没有工作安排的管理权限。' }
  if (expectedRevision !== undefined && state.revision !== expectedRevision) return { ok: false, error: '内容已更新，请保留草稿并重新核对后再保存。' }
  const initial = planner(state)
  if (!initial.ok) return initial
  if (!initial.changed) return { ok: true, changed: false, plan: initial, notice: '没有更改，继续按原来的安排执行。' }
  const targetName = (initial.subjectKind === 'department' ? state.depts : state.employees).find(item => item.id === initial.subjectId)?.name || '配置对象'
  const appName = state.apps.find(item => item.id === initial.appId)?.name || '应用'
  const result = await saveDemo(`${targetName} · ${appName}：${label}`, () => {
    if (!isAdmin.value) throw new Error('当前账号的管理权限已变化。')
    if (state.revision !== initial.baseRevision) throw new Error('内容已更新，本次更改未保存；草稿已保留。')
    const current = planner(state)
    if (!current.ok) throw new Error(current.error)
    commitTarget(current)
  }, { subjectId: initial.subjectId, ...(initial.subjectKind === 'employee' ? { employeeId: initial.subjectId } : {}), appId: initial.appId })
  return { ...result, changed: result.ok, plan: initial }
}
export const saveWorkChanges = (kind, id, appId, changes, expectedRevision) => submit('保存普通应用工作安排（合成原型）', data => planWorkChanges(data, kind, id, appId, changes), expectedRevision)
export const restoreDepartmentWork = (id, appId, expectedRevision) => submit('恢复此员工的部门普通应用安排（合成原型）', data => planRestoreDepartment(data, id, appId), expectedRevision)
export const suspendWorkApp = (id, appId, expectedRevision) => submit('仅停用此员工的一个应用，原设置保留（合成原型）', data => planSuspendApp(data, id, appId), expectedRevision)
export const reenableWorkApp = (id, appId, expectedRevision, options = {}) => submit('核对恢复清单后重新启用一个应用（合成原型）', data => planReenableApp(data, id, appId, options), expectedRevision)
