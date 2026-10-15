import { evaluatePermission } from './permission.js'

// R5 adapter for synthetic UI only. The R4 evaluator remains authoritative.
const clone = value => JSON.parse(JSON.stringify(value))
const unique = values => [...new Set(values)]
const own = (object, key) => Object.prototype.hasOwnProperty.call(object || {}, key)
const ruleKey = (appId, actionId) => `${appId}:${actionId}`
const scopeName = (app, id) => id === 'self' ? '本人' : (app.scopes.find(scope => scope.value === id)?.label || id).replace(/演示仓库\s*([AB])/g, '$1 仓库').replace(/演示/g, '')
function readableScope(app, id) {
  if (id.includes('!')) { const [allowed, denied] = id.split('!'); return `${readableScope(app, allowed)}，不含${denied.split('&').map(part => readableScope(app, part)).join('、')}` }
  return id.split('&').map(part => scopeName(app, part)).join('且属于')
}
function subject(data, kind, id) {
  return kind === 'department' ? data.depts.find(item => item.id === id) : typeof id === 'object' ? id : [...data.employees, ...(data.nonEmployeeAccounts || [])].find(item => item.id === id)
}
function rulesFor(target, kind) { return kind === 'department' ? target.presets || {} : target.exceptions || {} }
function policyActor(target, kind) {
  if (kind === 'department') return { id: `preview-${target.id}`, name: '本部门员工', employeeId: `preview-${target.id}`, accountId: 'preview@example.invalid', status: 'active', checked: true, relationStatus: 'confirmed', attendanceIdentity: { status: 'confirmed' }, departmentId: target.id, exceptions: {} }
  return { ...target, status: 'active', accountId: target.accountId || 'preview@example.invalid', employeeId: target.employeeId || `preview-${target.id}`, relationStatus: 'confirmed', checked: true, attendanceIdentity: { ...target.attendanceIdentity, status: 'confirmed' } }
}
function actionName(app, action) {
  if (app.id === 'inventory') return ({ view: '查询库存', issue: '办理出库', adjust: '重要库存调整' })[action.id] || action.name
  if (app.id === 'attendance') return action.id === 'read' ? '查看自己的考勤' : action.id === 'export' ? '导出考勤' : action.name
  return action.name.replace(/（候选，未接入）/g, '')
}
export function getWorkMetadata(data, appId) {
  const app = data.apps.find(item => item.id === appId)
  if (!app) return null
  const actions = app.actions.map(action => ({ ...action, name: actionName(app, action), important: app.id === 'platform' || !!action.highRisk, available: (!action.availability || action.availability === 'available') && !(app.id === 'attendance' && action.id !== 'read'), scopeOptions: app.scopes.filter(scope => app.id !== 'attendance' || scope.value === 'self').map(scope => ({ value: scope.value, label: scopeName(app, scope.value) })) }))
  return { ...app, actions, ordinaryActions: actions.filter(action => !action.important), importantActions: actions.filter(action => action.important), management: app.id === 'platform' }
}
function unavailableReason(target, appId) {
  if (!target.accountId || target.status === 'pending') return '账号尚未开通'
  if (target.status === 'disabled') return '员工账号已停用'
  if (appId === 'attendance' && (!target.employeeId || target.relationStatus !== 'confirmed' || ['pending', 'conflict', 'revoked'].includes(target.attendanceIdentity?.status))) return '员工档案或考勤关联待确认'
  return ''
}
function rowText(app, action, allowed, scope) {
  if (!action.available) return `${action.name}暂未开放`
  if (!allowed) return `不能${action.name}`
  const text = scope.map(id => readableScope(app, id)).join('、')
  if (app.id === 'attendance' && action.id === 'read' && scope.length === 1 && scope[0] === 'self') return '查看自己的考勤'
  if (app.id === 'inventory' && action.id === 'view') return `查询 ${text}库存`
  return `${action.name}（${text}）`
}
export function summarizeWorkApp(data, subjectKind, idOrEmployee, appId) {
  const target = subject(data, subjectKind, idOrEmployee)
  const app = getWorkMetadata(data, appId)
  if (!target || !app) return { appId, name: app?.name || '未知应用', status: 'review', statusLabel: '设置需处理', text: '资料不存在或尚未确认', sourceText: '—', sources: [], actionRows: [], importantRows: [], complex: true, canEdit: false, reason: '资料不存在或尚未确认' }
  const rules = rulesFor(target, subjectKind)
  const probe = policyActor(target, subjectKind)
  const actualActor = subjectKind === 'department' ? probe : target
  const valid = app.scopes.map(scope => scope.value)
  const dept = data.depts.find(item => item.id === target.departmentId)
  const row = action => {
    const key = ruleKey(appId, action.id), direct = rules[key]
    const base = subjectKind === 'employee' ? dept?.presets?.[key] : direct
    const actual = evaluatePermission(data, actualActor, appId, action.id)
    const configured = evaluatePermission(data, probe, appId, action.id)
    const limitedDeny = [direct, base].some(rule => rule?.mode === 'deny' && (!rule.scope?.length || !valid.every(value => rule.scope.includes(value))))
    const compound = configured.scope.some(value => /[!&]/.test(value))
    const unsupportedAttendance = appId === 'attendance' && configured.scope.some(value => value !== 'self')
    const unknown = [direct, base].some(rule => rule?.scope?.some(value => !valid.includes(value)))
    const complex = limitedDeny || compound || unsupportedAttendance || unknown
    let sourceText = subjectKind === 'department' ? '部门默认安排' : direct ? '已单独设置' : base ? '按部门安排' : '尚未安排'
    if (subjectKind === 'employee' && !direct && base && own(rules, ruleKey(appId, '*')) && rules[ruleKey(appId, '*')].mode !== 'deny') {
      const withoutGate = { ...probe, exceptions: { ...probe.exceptions } }
      delete withoutGate.exceptions[ruleKey(appId, '*')]
      const limited = vector(data, probe, app, action.id)
      const inherited = vector(data, withoutGate, app, action.id)
      if (inherited.some((allowed, index) => allowed && !limited[index])) sourceText = '按部门安排，已限定使用范围'
    }
    return { id: action.id, name: action.name, important: action.important, available: action.available, enabled: actual.allowed, configuredEnabled: configured.allowed, scope: [...actual.scope], configuredScope: [...configured.scope], scopeText: actual.scope.map(value => readableScope(app, value)).join('、') || '无可用范围', text: rowText(app, action, actual.allowed, actual.scope), configuredText: rowText(app, action, configured.allowed, configured.scope), sourceText, editable: action.available && !action.important && !complex && !(subjectKind === 'department' && app.management), complex, reason: complex ? '已有范围限制或特别安排，当前仅显示明细，避免覆盖原设置。' : '', scopeOptions: action.scopeOptions, storedRule: direct ? clone(direct) : null }
  }
  const allRows = app.actions.map(row)
  const actionRows = allRows.filter(item => !item.important), importantRows = allRows.filter(item => item.important)
  const gate = rules[ruleKey(appId, '*')] || (subjectKind === 'employee' ? dept?.presets?.[ruleKey(appId, '*')] : null)
  const suspended = gate?.mode === 'deny'
  const reason = subjectKind === 'employee' ? unavailableReason(target, appId) : target.confirmed === false ? '这个部门尚未确认' : ''
  const complex = actionRows.some(item => item.complex)
  const anyAllowed = allRows.some(item => item.enabled && item.available)
  const status = reason ? 'unavailable' : suspended ? 'suspended' : complex ? 'review' : anyAllowed ? 'available' : 'none'
  const statusLabel = ({ available: '可以使用', none: '未开通', suspended: '已停用', unavailable: '暂不可用', review: '设置需处理' })[status]
  const sources = unique(actionRows.filter(item => item.sourceText !== '尚未安排').map(item => item.sourceText))
  const positive = actionRows.filter(item => item.enabled && item.available).map(item => item.text)
  const negative = actionRows.filter(item => !item.enabled && item.available && !item.complex).map(item => item.text)
  let text = reason ? `暂不可用：${reason}` : suspended ? '已停用这个应用，原有安排仍保留' : positive.length ? [...positive, ...negative].join('；') : importantRows.some(item => item.enabled) ? '仅有单独核定的重要操作，请查看明细' : complex ? '有特别范围限制，请查看明细' : '暂未安排可使用的工作'
  if (appId === 'inventory' && positive.length) {
    const view = actionRows.find(item => item.id === 'view')
    const excluded = view?.enabled && !view.complex ? valid.filter(value => !view.scope.includes(value)) : []
    if (excluded.length) text += `；不能查询 ${excluded.map(value => scopeName(app, value)).join('、')}`
  }
  return { appId, name: app.name, status, statusLabel, text, sourceText: subjectKind === 'employee' && rules[ruleKey(appId, '*')]?.mode === 'deny' ? '已单独停用' : sources.length > 1 ? '按工作分别安排' : sources[0] || '—', sources, actionRows, importantRows, hasPersonalOrdinary: subjectKind === 'employee' && (actionRows.some(item => !!item.storedRule) || own(rules, ruleKey(appId, '*'))), suspended, complex, reason, canEdit: !app.management && !(subjectKind === 'department' && target.confirmed === false) && actionRows.some(item => item.editable), targetName: target.name }
}
export function buildWorkDraft(data, kind, id, appId) {
  const summary = summarizeWorkApp(data, kind, id, appId)
  return { baseRevision: data.revision || 0, changes: {}, rows: summary.actionRows.map(row => ({ id: row.id, enabled: row.configuredEnabled, scope: [...row.configuredScope] })) }
}
function objectTargets(data, actor, app) {
  if (app.id !== 'attendance') return app.scopes.map(scope => ({ scopeId: scope.value }))
  const employees = unique([actor.employeeId, ...data.employees.map(item => item.employeeId)].filter(Boolean))
  return employees.flatMap(employeeId => [null, ...data.depts.map(dept => dept.id)].map(eventDepartmentId => ({ employeeId, identityConfirmed: true, eventDepartmentId, departmentEvidenceConfirmed: !!eventDepartmentId })))
}
function vector(data, actor, app, actionId) {
  const probe = policyActor(actor, 'employee')
  return objectTargets(data, probe, app).map(target => evaluatePermission(data, probe, app.id, actionId, target).allowed)
}
function sameVector(before, after, actorBefore, actorAfter, app, actionId) { return JSON.stringify(vector(before, actorBefore, app, actionId)) === JSON.stringify(vector(after, actorAfter, app, actionId)) }
function patchFor(kind, key, value, remove = false, property = kind === 'department' ? 'presets' : 'exceptions') { return { property, key, ...(remove ? { remove: true } : { value: clone(value) }) } }
export function applyWorkPlan(data, plan) {
  const next = clone(data)
  const target = subject(next, plan.subjectKind, plan.subjectId)
  if (!target) throw new Error('配置对象不存在')
  for (const entry of plan.patch || []) {
    if (entry.remove) { if (target[entry.property]) delete target[entry.property][entry.key] }
    else { target[entry.property] ||= {}; target[entry.property][entry.key] = clone(entry.value) }
  }
  return next
}
function impactOf(data, next, kind, id, appId) {
  const affected = kind === 'department' ? data.employees.filter(employee => employee.departmentId === id) : data.employees.filter(employee => employee.id === id)
  const rows = affected.map(employee => {
    const before = summarizeWorkApp(data, 'employee', employee.id, appId), after = summarizeWorkApp(next, 'employee', employee.id, appId)
    const details = before.actionRows.map(row => { const changed = after.actionRows.find(item => item.id === row.id); return { name: row.name, before: row.configuredText, after: changed.configuredText, sourceText: changed.sourceText, changed: JSON.stringify([row.configuredEnabled, row.configuredScope]) !== JSON.stringify([changed.configuredEnabled, changed.configuredScope]) } })
    const gateKey = ruleKey(appId, '*'), nextEmployee = next.employees.find(item => item.id === employee.id)
    const gateKept = own(employee.exceptions, gateKey) && JSON.stringify(employee.exceptions[gateKey]) === JSON.stringify(nextEmployee?.exceptions?.[gateKey])
    return { id: employee.id, name: employee.name, beforeText: before.text, afterText: after.text, changed: details.some(item => item.changed), keptPersonal: gateKept || before.actionRows.some(row => row.storedRule && JSON.stringify(row.storedRule) === JSON.stringify(after.actionRows.find(item => item.id === row.id)?.storedRule)), unavailable: after.status === 'unavailable', details }
  })
  return { followingChanged: rows.filter(row => row.changed).length, personalUnchanged: rows.filter(row => row.keptPersonal).length, unavailable: rows.filter(row => row.unavailable).length, rows }
}
function beginPlan(data, kind, id, appId) {
  const target = subject(data, kind, id), app = getWorkMetadata(data, appId)
  const before = summarizeWorkApp(data, kind, id, appId)
  const plan = { ok: true, error: '', changed: false, baseRevision: data.revision || 0, subjectKind: kind, subjectId: typeof id === 'object' ? id.id : id, appId, before, after: before, patch: [], warnings: [] }
  if (!target || !app) return { ...plan, ok: false, error: '应用或配置对象不存在。' }
  if (kind === 'employee' && !data.employees.some(employee => employee.id === target.id)) return { ...plan, ok: false, error: '此账号尚未关联员工档案，不能按员工安排应用。' }
  if (kind === 'department' && (target.confirmed === false || target.mapped === false || ['pending', 'unconfirmed'].includes(target.status))) return { ...plan, ok: false, error: '这个部门尚未确认，暂不能用于分配人员或应用权限。' }
  if (app.management) return { ...plan, ok: false, error: '平台管理权限独立核定，不能通过普通工作安排调整。' }
  return plan
}
function finishPlan(data, plan) {
  plan.changed = plan.patch.length > 0
  plan.nextData = plan.changed ? applyWorkPlan(data, plan) : clone(data)
  plan.after = summarizeWorkApp(plan.nextData, plan.subjectKind, plan.subjectId, plan.appId)
  plan.impact = impactOf(data, plan.nextData, plan.subjectKind, plan.subjectId, plan.appId)
  return plan
}
function unintendedChanges(data, next, kind, id, app, touched) {
  const actors = kind === 'department' ? data.employees.filter(employee => employee.departmentId === id) : [subject(data, kind, id)]
  if (kind === 'department') actors.push(policyActor(subject(data, kind, id), kind))
  for (const actor of actors.filter(Boolean)) {
    const afterActor = next.employees.find(employee => employee.id === actor.id) || { ...actor }
    for (const action of app.actions) {
      const personallyFixed = kind === 'department' && actor.exceptions?.[ruleKey(app.id, action.id)]?.mode === 'allow'
      if ((!touched.includes(action.id) || personallyFixed) && !sameVector(data, next, actor, afterActor, app, action.id)) return `${actor.name}的“${action.name}”也会随之变化。请先单独核对这项安排，本次尚未保存。`
    }
  }
  return ''
}
export function planWorkChanges(data, kind, id, appId, changes = {}) {
  const plan = beginPlan(data, kind, id, appId)
  if (!plan.ok) return plan
  const target = subject(data, kind, id), app = getWorkMetadata(data, appId), rules = rulesFor(target, kind)
  const touched = []
  const needed = []
  for (const [actionId, change] of Object.entries(changes)) {
    const row = plan.before.actionRows.find(item => item.id === actionId)
    if (!row) return { ...plan, ok: false, error: '此项工作未注册，不能通过普通安排开启。' }
    const scope = unique(change.scope || [])
    if (!!change.enabled === row.configuredEnabled && (!change.enabled || JSON.stringify([...scope].sort()) === JSON.stringify([...row.configuredScope].sort()))) continue
    if (!row.editable) return { ...plan, ok: false, error: row.available ? '这项工作已有特别限制，请在只读明细中核对；普通配置不会覆盖。' : '这项工作暂未开放，不能通过勾选开启。' }
    if (plan.before.suspended) return { ...plan, ok: false, error: '这个应用已停用，请先重新启用并检查将恢复的权限。' }
    if (change.enabled && (!scope.length || scope.some(value => !row.scopeOptions.some(option => option.value === value)))) return { ...plan, ok: false, error: `请为“${row.name}”选择明确且已开放的对象范围。` }
    touched.push(actionId)
    if (change.enabled) needed.push(...scope)
    plan.patch.push(patchFor(kind, ruleKey(appId, actionId), { mode: change.enabled ? 'allow' : 'deny', scope: change.enabled ? scope : app.scopes.map(item => item.value) }))
  }
  if (!touched.length) return finishPlan(data, plan)
  const dept = kind === 'employee' ? data.depts.find(item => item.id === target.departmentId) : null
  const gate = rules[ruleKey(appId, '*')] || dept?.presets?.[ruleKey(appId, '*')]
  if (needed.length && (gate?.mode !== 'allow' || needed.some(value => !gate.scope?.includes(value)))) {
    const scope = unique([...(gate?.mode === 'allow' ? gate.scope || [] : []), ...needed])
    plan.patch.push(patchFor(kind, ruleKey(appId, '*'), { mode: 'allow', scope }))
  }
  const next = applyWorkPlan(data, plan)
  const unexpected = unintendedChanges(data, next, kind, typeof id === 'object' ? id.id : id, app, touched)
  if (unexpected) return { ...plan, ok: false, error: unexpected }
  const after = summarizeWorkApp(next, kind, id, appId)
  for (const actionId of touched) {
    const requested = changes[actionId], row = after.actionRows.find(item => item.id === actionId)
    if (row.configuredEnabled !== !!requested.enabled || (requested.enabled && JSON.stringify([...row.configuredScope].sort()) !== JSON.stringify(unique(requested.scope).sort()))) return { ...plan, ok: false, error: `已有特别限制使“${row.name}”无法按此范围生效，本次不会覆盖原设置。` }
  }
  return finishPlan(data, plan)
}
export function planRestoreDepartment(data, employeeId, appId) {
  const plan = beginPlan(data, 'employee', employeeId, appId)
  if (!plan.ok) return plan
  const target = subject(data, 'employee', employeeId), app = getWorkMetadata(data, appId), rules = target.exceptions || {}
  const ordinary = app.ordinaryActions.filter(action => action.available)
  for (const action of ordinary) if (own(rules, ruleKey(appId, action.id))) plan.patch.push(patchFor('employee', ruleKey(appId, action.id), null, true))
  const preserveGate = app.actions.some(action => (action.important || !action.available) && own(rules, ruleKey(appId, action.id)))
  const backup = target.suspendedAppGates?.[appId]
  if (backup && preserveGate && backup.hadOwn) plan.patch.push(patchFor('employee', ruleKey(appId, '*'), backup.rule))
  else if (own(rules, ruleKey(appId, '*')) && !preserveGate) plan.patch.push(patchFor('employee', ruleKey(appId, '*'), null, true))
  else if (backup && !backup.hadOwn) plan.patch.push(patchFor('employee', ruleKey(appId, '*'), null, true))
  if (backup) plan.patch.push(patchFor('employee', appId, null, true, 'suspendedAppGates'))
  const next = applyWorkPlan(data, plan)
  const unexpected = unintendedChanges(data, next, 'employee', employeeId, app, ordinary.map(action => action.id))
  if (unexpected) return { ...plan, ok: false, error: `恢复部门安排前需核对：${unexpected}` }
  return finishPlan(data, plan)
}
export function planSuspendApp(data, employeeId, appId) {
  const plan = beginPlan(data, 'employee', employeeId, appId)
  if (!plan.ok || plan.before.suspended) return plan.ok ? finishPlan(data, plan) : plan
  const employee = subject(data, 'employee', employeeId), key = ruleKey(appId, '*')
  plan.patch.push(patchFor('employee', appId, { hadOwn: own(employee.exceptions, key), rule: employee.exceptions?.[key] || null }, false, 'suspendedAppGates'))
  plan.patch.push(patchFor('employee', key, { mode: 'deny', scope: [] }))
  return finishPlan(data, plan)
}
export function planReenableApp(data, employeeId, appId, options = {}) {
  const plan = beginPlan(data, 'employee', employeeId, appId)
  if (!plan.ok || !plan.before.suspended) return plan.ok ? finishPlan(data, plan) : plan
  const employee = subject(data, 'employee', employeeId), app = getWorkMetadata(data, appId), backup = employee.suspendedAppGates?.[appId]
  if (!backup && employee.exceptions?.[ruleKey(appId, '*')]?.mode !== 'deny') return { ...plan, ok: false, error: '部门安排仍停用这个应用，请先核对部门设置；不能在员工页直接重新启用。' }
  plan.patch.push(backup?.hadOwn ? patchFor('employee', ruleKey(appId, '*'), backup.rule) : patchFor('employee', ruleKey(appId, '*'), null, true))
  if (backup) plan.patch.push(patchFor('employee', appId, null, true, 'suspendedAppGates'))
  finishPlan(data, plan)
  if (plan.after.suspended) return { ...plan, ok: false, error: '部门或其他安排仍停用这个应用，本次不会记录为重新启用成功。' }
  const restoredImportant = plan.after.importantRows.filter(row => row.configuredEnabled)
  const restoredUnavailable = plan.after.actionRows.filter(row => !row.available && row.configuredEnabled)
  if (restoredImportant.length || restoredUnavailable.length) {
    plan.warnings.push(`重新启用将恢复：${[...restoredImportant, ...restoredUnavailable].map(row => row.name).join('、')}。这些既有权限不由普通工作配置授予。`)
    if (!options.acknowledgeImportant) return { ...plan, ok: false, requiresImportantReview: true, error: '将恢复重要操作或暂未开放的既有配置，不能直接重新启用。请先查看并明确确认恢复清单。' }
  }
  return plan
}
