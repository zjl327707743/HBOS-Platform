// Interaction contract only; this is never a server-side authorization executor.
export function evaluatePermission(data, employee, appId, actionId) {
 const deny = (reason, source='未授予', mode='inherit') => ({allowed:false,source,scope:[],reason,mode})
 if (!employee || employee.status !== 'active') return deny('账号未开通或已停用')
 const app=data.apps.find(a=>a.id===appId)
 if (!app) return deny('模块未注册')
 const department=data.depts.find(d=>d.id===employee.departmentId)
 const personal=employee.exceptions||{}, presets=department?.presets||{}
 const appRule=personal[`${appId}:*`]||presets[`${appId}:*`]
 const appSource=personal[`${appId}:*`]?'个人 APP 例外':`部门继承 · ${department?.name||'待核对'}`
 if (appRule?.mode==='deny') return deny('APP 整体禁止，所有动作均受约束',appSource,'deny')
 const action=app.actions.find(a=>a.id===actionId)
 if (actionId!=='*' && !action) return deny('动作未注册')
 const key=`${appId}:${actionId}`, own=personal[key]
 if (own?.mode==='deny') return deny('个人明确禁止优先', '个人明确禁止','deny')
 if (!appRule || appRule.mode!=='allow' || !appRule.scope?.length) return deny('无 APP 进入权限或 APP 范围为空',appSource)
 const rule=own || presets[key]
 const source=own?'个人额外允许':`部门继承 · ${department?.name||'待核对'}`
 if (!rule || rule.mode!=='allow') return deny('没有此操作的授权',source)
 if (action?.highRisk && (!own || !own.qualified)) return deny('高风险操作需具名授予及资格 / 领域校验','高风险门禁')
 const valid=app.scopes.map(s=>s.value)
 const scope=(rule.scope||[]).filter(s=>valid.includes(s) && appRule.scope.includes(s))
 if (!scope.length) return deny('范围为空或与 APP 范围没有交集；不会解释为全部',source,own?'allow':'inherit')
 return {allowed:true,source,scope,reason:'在所列演示范围内允许；领域硬约束仍需后端校验',mode:own?'allow':'inherit'}
}
