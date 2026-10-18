// Synthetic object-scope demonstration only. Never copy into a production executor.
const split=scope=>scope.split('&')
function intersects(a,b,app){
 if(a===b)return a
 const department=app.id==='attendance'&&[a,b].find(t=>t!=='self'&&app.scopes.some(s=>s.value===t))
 return department&&[a,b].includes('self')?`self&${department}`:null
}
function covers(token,denied){return denied.some(d=>split(token).includes(d))}
function matches(token,target,actor,appId){
 return split(token).every(t=>t==='self'?!!actor.employeeId&&target.identityConfirmed===true&&target.employeeId===actor.employeeId:appId==='attendance'?target.departmentEvidenceConfirmed===true&&target.eventDepartmentId===t:target.scopeId===t)
}
export function evaluatePermission(data,actor,appId,actionId,target){
 const refuse=(reason,source='未授予',mode='inherit')=>({allowed:false,source,scope:[],deniedScope:[],reason,mode})
 if(!actor||actor.status!=='active'||!actor.accountId)return refuse('账号未开通或已停用')
 const app=data.apps.find(a=>a.id===appId);if(!app)return refuse('模块未注册')
 if(appId==='attendance'&&(!actor.employeeId||actor.relationStatus!=='confirmed'||['conflict','pending','revoked'].includes(actor.attendanceIdentity?.status)))return refuse('尚未确认唯一 Employee 关联，不开放考勤数据','身份关联门禁')
 const department=data.depts.find(d=>d.id===actor.departmentId),personal=actor.exceptions||{},presets=department?.presets||{}
 const gate=personal[`${appId}:*`]||presets[`${appId}:*`]
 const gateSource=personal[`${appId}:*`]?'个人 APP 例外':`部门继承 · ${department?.name||'无主部门'}`
 if(gate?.mode==='deny')return refuse('APP 整体禁止，全部动作与对象拒绝',gateSource,'deny')
 const valid=app.scopes.map(s=>s.value)
 const invalid=r=>!r?.scope?.length||r.scope.some(s=>!valid.includes(s))
 if(gate?.mode!=='allow'||invalid(gate))return refuse('无 APP 进入权限，或范围为空 / 未知',gateSource)
 const action=app.actions.find(a=>a.id===actionId)
 if(actionId!=='*'&&!action)return refuse('动作未注册')
 const key=`${appId}:${actionId}`,own=personal[key],base=presets[key]
 if(own&&invalid(own)&&actionId!=='*')return refuse('个人范围为空 / 未知，演示配置拒绝生效','个人例外',own.mode)
 if(base?.mode==='deny'&&actionId!=='*'&&invalid(base))return refuse('部门禁止范围为空 / 未知，配置需核对','部门范围门禁')
 const rule=own?.mode==='allow'?own:base
 const source=own?.mode==='allow'?'个人额外允许':`部门继承 · ${department?.name||'无主部门'}`
 if(rule?.mode!=='allow'||invalid(rule))return own?.mode==='deny'?refuse('个人明确禁止此范围，且没有可用的允许授权','个人明确禁止','deny'):refuse('没有此操作的完整允许范围',source,own?.mode||'inherit')
 if(action?.highRisk&&(!own||own.mode!=='allow'||!own.qualified||!actor.checked))return refuse('高风险需具名授予及资格 / 领域校验','高风险门禁')
 const denied=[...(own?.mode==='deny'?own.scope:[]),...(base?.mode==='deny'?base.scope:[])]
 const atoms=[...new Set(rule.scope.flatMap(a=>gate.scope.map(b=>intersects(a,b,app)).filter(Boolean)))]
 const intersection=atoms.filter(t=>!t.includes('&')||!split(t).some(part=>atoms.includes(part)))
 const remaining=intersection.filter(s=>!covers(s,denied))
 if(!remaining.length)return refuse(denied.length?'明确禁止覆盖此操作的全部允许范围':'动作与 APP 范围没有可用交集',denied.length?'个人明确禁止':source,own?.mode||'inherit')
 if(target){
  if(appId==='attendance'&&(!target.employeeId||target.identityConfirmed!==true))return refuse('记录没有已确认 Employee 归属','记录身份门禁')
  if(!intersection.some(s=>matches(s,target,actor,appId)))return refuse('请求对象不在成对授权范围内',source)
  if(denied.some(s=>matches(s,target,actor,appId)))return refuse('此对象命中限定范围的明确禁止','限定范围禁止','deny')
 }
 const display=remaining.map(s=>denied.length?`${s}!${denied.join('&')}`:s)
 return {allowed:true,source:denied.length?`${source}；扣除个人禁止范围`:source,scope:display,deniedScope:denied,reason:denied.length?'仅允许未命中禁止范围的对象；并非整 APP 禁止':'按明确 Employee 与对象范围演示；不是后端验收',mode:own?.mode||'inherit'}
}
export function previewAttendance(data,actor,request={}){
 const operation=request.operation||'read',operationId=`attendance.${operation}`
 const refuse=error=>({ok:false,error,rows:[],total:0,operationId,source:'演示请求已拒绝'})
 if(!['read','export'].includes(operation))return refuse('未知操作，默认拒绝')
 if(!['self','department'].includes(request.endpoint||'self'))return refuse('未知考勤入口，默认拒绝')
 const entry=evaluatePermission(data,actor,'attendance',operation)
 if(!entry.allowed)return refuse(entry.reason)
 if(request.endpoint==='self'&&request.requestedEmployeeId&&request.requestedEmployeeId!==actor.employeeId)return refuse('本人接口不接受他人 employee 参数，不能替换当前账号主体')
 if(request.endpoint==='department'){
  const id=request.requestedDepartmentId
  const dept=data.depts.find(d=>d.id===actor.departmentId),own=actor.exceptions?.[`attendance:${operation}`]
  const rule=own?.mode==='allow'?own:dept?.presets?.[`attendance:${operation}`]
  if(!id||!data.depts.some(d=>d.id===id)||!rule?.scope?.includes(id))return refuse('没有此指定部门的具名操作范围；不会自动包含子部门')
 }
 const eligible=data.attendanceRecords.filter(record=>request.endpoint==='department'?record.departmentEvidenceConfirmed&&record.eventDepartmentId===request.requestedDepartmentId:record.employeeId===actor.employeeId)
 const rows=eligible.filter(record=>evaluatePermission(data,actor,'attendance',operation,record).allowed).map(record=>({id:record.id,employeeId:record.employeeId,date:record.date,checkIn:record.checkIn,status:record.status,eventDepartmentId:record.eventDepartmentId,departmentEvidenceConfirmed:record.departmentEvidenceConfirmed}))
 return {ok:true,error:'',rows,total:rows.length,operationId,source:entry.source}
}
