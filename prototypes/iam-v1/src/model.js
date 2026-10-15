import { reactive, computed } from 'vue'
import { createSeed } from './seed.js'
import { evaluatePermission } from './permission.js'
export const STORAGE_KEY='hbos.iam-v1.r4.synthetic.v4'
export const ui=reactive({busy:false,fault:'none',notice:'',error:''})
let initial=createSeed()
try {
 const saved=localStorage.getItem(STORAGE_KEY)
 if(saved){const p=JSON.parse(saved);if(p.version===4&&['employees','nonEmployeeAccounts','depts','apps','logs','attendanceRecords'].every(k=>Array.isArray(p[k]))){initial=p;initial.session=null}else ui.error='R4 演示记录不兼容，已载入初始合成场景；R3 本机记录保留。'}
}catch{ui.error='R4 演示记录无法读取，已载入合成场景。'}
export const state=reactive(initial)
export const allSubjects=computed(()=>[...state.employees,...state.nonEmployeeAccounts])
const find=id=>allSubjects.value.find(e=>e.id===id)
export const currentUser=computed(()=>find(state.session?.employeeId)||null)
export const isAdmin=computed(()=>currentUser.value?.id==='admin'&&currentUser.value.status==='active'&&state.session?.phase==='active')
export const deptName=id=>state.depts.find(d=>d.id===id)?.name||'待关联 / 不适用'
export const scopeLabel=id=>id.includes('!')?id.split('!').map(scopeLabel).join('，排除 '):id.includes('&')?id.split('&').map(scopeLabel).join(' 且 '):state.apps.flatMap(a=>a.scopes).find(s=>s.value===id)?.label||id
export const effective=(employee,appId,actionId,context)=>evaluatePermission(state,employee,appId,actionId,context)
const tempToken=()=>`DEMO-${crypto.randomUUID().slice(0,8)}-Aa!`
const pause=()=>new Promise(resolve=>setTimeout(resolve,250))
export async function saveDemo(label,fn){
 if(ui.busy)return {ok:false,error:'正在保存，请稍后再试。'}
 ui.busy=true;ui.error='';ui.notice='演示保存中…'
 const snapshot=JSON.stringify(state)
 try{
  await pause()
  if(ui.fault==='save-failure')throw new Error('演示保存失败：本机存储不可用。改动未生效，请切回正常后重试。')
  if(ui.fault==='conflict')throw new Error('演示版本冲突：改动未生效，请核对后重试。')
  fn();state.revision++
  state.logs.unshift({id:crypto.randomUUID(),time:new Date().toLocaleString('zh-CN',{hour12:false}),label,actor:currentUser.value?.name||'演示系统'})
  localStorage.setItem(STORAGE_KEY,JSON.stringify({...state,session:null}))
  ui.notice='演示已保存到本机';return {ok:true}
 }catch(e){Object.assign(state,JSON.parse(snapshot));ui.notice='';ui.error=e.message||'演示保存失败';return {ok:false,error:ui.error}}
 finally{ui.busy=false}
}
export async function login(id,method){
 const e=find(id)
 if(ui.fault==='service-failure'&&method==='feishu')return {ok:false,error:'演示飞书服务失败，可用同账号的密码备用入口。'}
 if(!e||e.status==='pending'||!e.accountId)return {ok:false,error:'此员工暂无登录账号。管理员可提前开通；本企业首次飞书开户请走企业核验与员工关联场景。'}
 if(e.status==='disabled')return {ok:false,error:'账号已停用，不因再次飞书登录重新创建。'}
 if(method==='feishu'&&!e.bound)return {ok:false,error:'已有账号尚未绑定飞书，请先验证原账号归属再绑定，避免产生第二账号。'}
 const result=await saveDemo(`${e.name}通过${method==='feishu'?'模拟飞书':'演示密码'}进入同一账号`,()=>{state.session={employeeId:id,method,phase:method==='password'&&e.firstPassword?'first-password':'active'}})
 return {...result,firstPassword:result.ok&&state.session?.phase==='first-password'}
}
export function logout(reason=''){state.session=null;ui.notice=reason;ui.error=''}
export function expireSession(){logout('演示会话已过期，请重新登录。')}
export async function changePassword(id){return saveDemo(`${find(id)?.name}完成本人演示改密`,()=>{const e=find(id);if(!e||e.status!=='active')throw new Error('账号不可用');if(state.session?.employeeId!==id)throw new Error('只能修改当前本人演示账号');e.firstPassword=false;state.session.phase='active'})}
export async function recover(id){return saveDemo(`${find(id)?.name}完成演示恢复核验`,()=>{const e=find(id);if(!e||e.status!=='active')throw new Error('请联系管理员核对账号');e.firstPassword=true;state.session=null})}
export async function rebind(id,newIdentity){return saveDemo(`${find(id)?.name}完成本人演示换绑`,()=>{
 if(state.session?.employeeId!==id)throw new Error('仅当前本人账号可换绑，不能替换成管理页面选中的员工')
 if(allSubjects.value.some(e=>e.id!==id&&e.feishuId===newIdentity))throw new Error('此演示飞书身份已被其他账号占用，拒绝抢占。')
 if(!newIdentity?.startsWith('demo-'))throw new Error('仅允许合成演示身份')
 const e=find(id);if(!e||e.status!=='active')throw new Error('账号不可用');e.bound=true;e.feishuId=newIdentity
})}
export async function activate(id){const result=await saveDemo(`${find(id)?.name}已有员工档案受控开户`,()=>{
 const e=state.employees.find(e=>e.id===id);if(!e?.checked)throw new Error('请先核验企业员工档案');if(e.accountId)throw new Error('已有关联账号，不能重复开户')
 e.accountId=`demo.${e.id}@example.invalid`;e.username=e.id==='e3'?'shenhe':`member${e.id}`;e.status='active';e.firstPassword=true;e.relationStatus='confirmed'
});return result.ok?{...result,temporaryPassword:tempToken()}:result}
export async function linkExistingAccount(id,accountId){return saveDemo(`${find(id)?.name}按明确归属关联已有账号`,()=>{
 const e=state.employees.find(x=>x.id===id);if(!e?.checked||e.accountId)throw new Error('请先核验无账号员工档案')
 if(state.employees.some(x=>x.accountId===accountId))throw new Error('账号已关联其他员工，不能抢占')
 const index=state.nonEmployeeAccounts.findIndex(x=>x.accountId===accountId&&x.subjectType==='pending-employee');if(index<0)throw new Error('账号不存在或属于服务 / 应急主体，不能伪造 Employee')
 const account=state.nonEmployeeAccounts[index]
 for(const key of ['accountId','username','bound','feishuId','firstPassword','status'])e[key]=account[key]
 e.relationStatus='confirmed';state.nonEmployeeAccounts.splice(index,1)
 if(state.session?.employeeId===account.id)state.session.employeeId=id
})}
export async function createEmployee(draft){return saveDemo('新增完整合成员工档案，尚未创建登录账号',()=>{
 for(const key of ['name','employeeNumber','company','departmentId','gender','birthDate','employmentDate','position'])if(typeof draft[key]!=='string'||!draft[key].trim())throw new Error('请完整填写合成必填资料，日期不自动编造')
 if(!state.depts.some(d=>d.id===draft.departmentId))throw new Error('部门未映射')
 if(state.employees.some(e=>e.employeeNumber===draft.employeeNumber))throw new Error('工号冲突，待核对；不选择第一条')
 if(!/^\d{4}-\d{2}-\d{2}$/.test(draft.birthDate)||!/^\d{4}-\d{2}-\d{2}$/.test(draft.employmentDate)||draft.birthDate>=draft.employmentDate)throw new Error('请填写有效的合成生日和入职日期')
 const id='demo-emp-'+crypto.randomUUID().slice(0,8)
 state.employees.push({...draft,id,employeeId:'DEMO-EMP-'+crypto.randomUUID().slice(0,8),code:'DEMO-'+draft.employeeNumber,subjectType:'employee',secondaryDepartments:[],accountId:'',username:'',status:'pending',firstPassword:true,bound:false,feishuId:'',checked:false,relationStatus:'unlinked',deviceId:'',attendanceIdentity:{source:'delicloud',namespace:'demo-company/tenant-a',externalPersonId:'',employeeNum:draft.employeeNumber,status:'pending'},exceptions:{}})
})}
export async function transfer(id,departmentId){return saveDemo(`${find(id)?.name}调岗：${deptName(find(id)?.departmentId)} → ${deptName(departmentId)}，本人历史外键保留`,()=>{if(!state.depts.some(d=>d.id===departmentId))throw new Error('部门未映射');state.employees.find(e=>e.id===id).departmentId=departmentId})}
export async function disable(id){return saveDemo(`${find(id)?.name}停用演示账号`,()=>{if(id==='admin')throw new Error('保留演示管理入口');find(id).status='disabled';if(state.session?.employeeId===id)state.session=null})}
export async function resetPassword(id){const result=await saveDemo(`${find(id)?.name}管理员重置临时状态，现用密码不可读取`,()=>{const e=find(id);if(e.status!=='active')throw new Error('仅可重置已开通账号');e.firstPassword=true;if(state.session?.employeeId===id)state.session=null});return result.ok?{...result,temporaryPassword:tempToken()}:result}
export async function registerDemoApp(){if(state.apps.some(a=>a.id==='equipment'))return {ok:false,error:'演示模块已注册'};return saveDemo('注册合成扩展元数据；无真实执行器',()=>state.apps.push({id:'equipment',name:'设备管理',description:'演示注册，未接入后端',color:'#498999',actions:[{id:'view',name:'查看设备',highRisk:false}],scopes:[{value:'equipmentA',label:'演示设备组 A'}]}))}
export async function resetDemo(){return saveDemo('重置 R4 合成场景（保留 R3 命名空间记录）',()=>{Object.assign(state,createSeed());ui.fault='none'})}
// Explicit synthetic verified identity fixtures. No OAuth, credentials or real API.
export async function enterpriseLogin(scenario){
 if(scenario==='foreign')return {ok:false,error:'非本企业 tenant / app 的身份已拒绝，没有创建账号。'}
 if(scenario==='conflict')return {ok:false,error:'身份已被其他账号占用，拒绝抢占或按同名合并。'}
 if(scenario==='precreated'){const e=find('e5');if(e.status!=='active')return {ok:false,error:'预建账号已停用，不可重新开户'};return e.bound&&e.feishuId==='demo-feishu-e5'?{ok:true,employeeId:e.id,reused:true}:{ok:true,needsVerification:true,employeeId:e.id}}
 if(!['first-linked','first-unlinked'].includes(scenario))return {ok:false,error:'未知企业身份场景'}
 const targetId=scenario==='first-linked'?'e3':'u-zhoulan'
 const accountId=scenario==='first-linked'?'demo.e3@example.invalid':'demo.user.zhoulan@example.invalid'
 const identity=scenario==='first-linked'?'demo-feishu-e3':'demo-feishu-zhoulan'
 const existing=allSubjects.value.find(x=>x.feishuId===identity||x.accountId===accountId)||find(targetId)
 if(existing?.status==='disabled')return {ok:false,error:'停用账号不可因首次回调重建'}
 if(existing?.accountId){if(!existing.bound)return {ok:true,needsVerification:true,employeeId:existing.id};return {ok:true,employeeId:existing.id,pendingEmployee:!existing.employeeId,reused:true}}
 const result=await saveDemo('企业核验合成凭据完成：首次创建唯一账号，姓名仅生成别名',()=>{
  if(allSubjects.value.some(x=>x.accountId===accountId||x.feishuId===identity))throw new Error('并发已开户，请重试以复用唯一账号')
  if(scenario==='first-linked'){
   const e=state.employees.find(x=>x.id==='e3');if(e.accountId)throw new Error('并发已开通，请重试归属验证')
   Object.assign(e,{accountId:'demo.e3@example.invalid',username:'shenhe',status:'active',bound:true,feishuId:'demo-feishu-e3',checked:true,firstPassword:true,relationStatus:'confirmed'})
   e.attendanceIdentity.status='confirmed'
  }else state.nonEmployeeAccounts.push({id:targetId,name:'周岚（演示）',subjectType:'pending-employee',employeeId:null,employeeNumber:'',code:'待员工关联',departmentId:null,secondaryDepartments:[],position:'仅基础体验',accountId:'demo.user.zhoulan@example.invalid',username:'zhoulan',status:'active',bound:true,feishuId:'demo-feishu-zhoulan',firstPassword:true,checked:false,relationStatus:'pending',exceptions:{}})
 })
 return result.ok?{...result,employeeId:targetId,pendingEmployee:scenario==='first-unlinked',temporaryPassword:tempToken()}:result
}
export async function verifyPrecreatedBinding(id,proof){
 if(!proof?.identityVerified||!proof?.mfaVerified)return {ok:false,error:'请以此原账号完成本人重新验证及 MFA（合成）'}
 const e=find(id);if(!e?.accountId||e.bound||e.status!=='active')return {ok:false,error:'预建账号状态不符，请重新核对'}
 const result=await saveDemo('原账号重新验证后绑定本人演示飞书，未创建第二账号',()=>{const e=find(id);const identity=`demo-feishu-${id}`;if(allSubjects.value.some(x=>x.id!==id&&x.feishuId===identity))throw new Error('身份占用冲突');e.bound=true;e.feishuId=identity})
 return {...result,employeeId:id,reused:true}
}
