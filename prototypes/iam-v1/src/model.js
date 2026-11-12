import { reactive, computed } from 'vue'
import { createSeed } from './seed.js'
import { evaluatePermission } from './permission.js'
export const STORAGE_KEY='hbos.iam-v1.r3.synthetic.v3'
export const ui=reactive({busy:false,fault:'none',notice:'',error:''})
let initial=createSeed()
try {
 const saved=localStorage.getItem(STORAGE_KEY)
 if(saved){const parsed=JSON.parse(saved);if(parsed.version===3&&Array.isArray(parsed.employees)&&Array.isArray(parsed.depts)&&Array.isArray(parsed.apps)&&Array.isArray(parsed.logs)){initial=parsed;initial.session=null}else ui.error='旧演示记录不兼容，已载入初始合成场景。'}
} catch {ui.error='本机演示记录无法读取，已载入初始合成场景；保存时会显示失败。'}
export const state=reactive(initial)
export const currentUser=computed(()=>state.employees.find(e=>e.id===state.session?.employeeId)||null)
export const isAdmin=computed(()=>currentUser.value?.id==='admin'&&currentUser.value.status==='active'&&state.session?.phase==='active')
export const deptName=id=>state.depts.find(d=>d.id===id)?.name||'待核对'
export const scopeLabel=id=>state.apps.flatMap(a=>a.scopes).find(s=>s.value===id)?.label||id
export const effective=(employee,appId,actionId)=>evaluatePermission(state,employee,appId,actionId)
const pause=()=>new Promise(resolve=>setTimeout(resolve,420))
export async function saveDemo(label,fn){
 if(ui.busy)return {ok:false,error:'正在保存，请稍后再试。'}
 ui.busy=true;ui.error='';ui.notice='演示保存中…'
 const snapshot=JSON.stringify(state)
 try {
  await pause()
  if(ui.fault==='save-failure')throw new Error('演示保存失败：本机存储不可用。改动未生效，请切回正常后重试。')
  if(ui.fault==='conflict')throw new Error('演示版本冲突：请核对当前记录后重新保存。改动未生效。')
  fn()
  state.revision++
  state.logs.unshift({id:crypto.randomUUID(),time:new Date().toLocaleString('zh-CN',{hour12:false}),label,actor:currentUser.value?.name||'演示系统'})
  localStorage.setItem(STORAGE_KEY,JSON.stringify({...state,session:null}))
  ui.notice='演示已保存到本机';return {ok:true}
 }catch(e){Object.assign(state,JSON.parse(snapshot));ui.notice='';ui.error=e.message||'演示保存失败';return {ok:false,error:ui.error}}
 finally{ui.busy=false}
}
export async function login(id,method){
 const employee=state.employees.find(e=>e.id===id)
 if(ui.fault==='service-failure'&&method==='feishu')return {ok:false,error:'演示登录服务失败，请重试或使用密码备用入口。'}
 if(!employee||employee.status==='pending'||!employee.accountId)return {ok:false,error:'此员工尚未受控开通账号，请联系管理员；不会自动注册。'}
 if(employee.status==='disabled')return {ok:false,error:'账号已停用，请联系管理员。'}
 if(method==='feishu'&&!employee.bound)return {ok:false,error:'飞书身份未绑定已有账号，请联系管理员核对；不会自动创建账号。'}
 const result=await saveDemo(`${employee.name}通过${method==='feishu'?'模拟飞书':'演示密码'}登录同一账号`,()=>{
  state.session={employeeId:id,method,phase:method==='password'&&employee.firstPassword?'first-password':'active'}
 })
 return {...result,firstPassword:result.ok&&state.session?.phase==='first-password'}
}
export function logout(reason=''){state.session=null;ui.notice=reason;ui.error=''}
export function expireSession(){logout('演示会话已过期，请重新登录。')}
export async function changePassword(id){return saveDemo(`${state.employees.find(e=>e.id===id)?.name}完成演示改密，旧会话撤销体验已模拟`,()=>{
 const employee=state.employees.find(e=>e.id===id);if(!employee||employee.status!=='active')throw new Error('账号不可用')
 employee.firstPassword=false
 if(state.session?.employeeId===id)state.session.phase='active'
})}
export async function recover(id){return saveDemo(`${state.employees.find(e=>e.id===id)?.name}完成演示本人找回核验，待首次改密`,()=>{
 const employee=state.employees.find(e=>e.id===id);if(!employee||employee.status!=='active')throw new Error('请联系管理员核对未开通或停用账号')
 employee.firstPassword=true;state.session=null
})}
export async function rebind(id,newIdentity){return saveDemo(`${state.employees.find(e=>e.id===id)?.name}完成演示飞书换绑`,()=>{
 if(state.employees.some(e=>e.id!==id&&e.feishuId===newIdentity))throw new Error('此演示飞书身份已被其他账号占用，换绑已拒绝；不会抢占。')
 if(!newIdentity?.startsWith('demo-'))throw new Error('仅允许合成演示身份')
 const employee=state.employees.find(e=>e.id===id);if(!employee||employee.status!=='active')throw new Error('账号不可用')
 employee.bound=true;employee.feishuId=newIdentity
})}
export async function registerDemoApp(){
 if(state.apps.some(a=>a.id==='equipment'))return {ok:false,error:'设备演示模块已经注册'}
 return saveDemo('注册设备演示模块：只验证交互契约，未接入业务执行器',()=>state.apps.push({id:'equipment',name:'设备管理',description:'新模块 · 演示注册',color:'#498999',actions:[{id:'view',name:'查看设备',highRisk:false}],scopes:[{value:'equipmentA',label:'演示设备组 A'}]}))
}
export async function resetDemo(){return saveDemo('重置为初始合成场景',()=>{Object.assign(state,createSeed());ui.fault='none'})}
export async function activate(id){return saveDemo(`${state.employees.find(e=>e.id===id)?.name}经企业核验后受控开通演示账号`,()=>{
 const employee=state.employees.find(e=>e.id===id)
 if(!employee?.checked)throw new Error('请先完成企业人员核验')
 if(employee.accountId)throw new Error('已有账号请关联，不创建第二账号')
 employee.accountId=`demo.${employee.id}@example.invalid`;employee.status='active';employee.firstPassword=true
})}
export async function transfer(id,departmentId){return saveDemo(`${state.employees.find(e=>e.id===id)?.name}调岗：普通部门继承撤旧授新，高风险不自动增加`,()=>{
 if(!state.depts.some(d=>d.id===departmentId))throw new Error('部门未映射，待核对')
 state.employees.find(e=>e.id===id).departmentId=departmentId
})}
export async function disable(id){return saveDemo(`${state.employees.find(e=>e.id===id)?.name}停用账号，演示登录和访问已拒绝`,()=>{
 if(id==='admin')throw new Error('保留演示管理员入口')
 state.employees.find(e=>e.id===id).status='disabled'
 if(state.session?.employeeId===id)state.session=null
})}
export async function resetPassword(id){return saveDemo(`${state.employees.find(e=>e.id===id)?.name}管理员重置演示临时密码，现用密码不可读取`,()=>{
 const employee=state.employees.find(e=>e.id===id);if(employee.status!=='active')throw new Error('仅可重置已开通的账号')
 employee.firstPassword=true
 if(state.session?.employeeId===id)state.session=null
})}
