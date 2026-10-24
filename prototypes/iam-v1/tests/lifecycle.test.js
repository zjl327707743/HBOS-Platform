import test from 'node:test'
import assert from 'node:assert/strict'
import { createSeed } from '../src/seed.js'
const storage=new Map()
globalThis.localStorage={getItem:key=>storage.get(key)||null,setItem:(key,value)=>storage.set(key,value)}
const model=await import('../src/model.js')
const {state,ui,login,changePassword,activate,rebind,resetPassword,saveDemo,STORAGE_KEY}=model
function reset(){Object.assign(state,createSeed());ui.fault='none';ui.busy=false;storage.clear()}
test('飞书与密码演示进入同一账号，人数不增加',async()=>{reset();const count=state.employees.length;await login('e1','feishu');const a=model.currentUser.value.accountId;await login('e1','password');assert.equal(model.currentUser.value.accountId,a);assert.equal(state.employees.length,count);assert.equal(JSON.parse(storage.get(STORAGE_KEY)).session,null)})
test('未开通、未绑定、停用均拒绝相应登录',async()=>{reset();assert.equal((await login('e3','feishu')).ok,false);assert.equal((await login('e4','password')).ok,false);state.employees.find(e=>e.id==='e1').bound=false;assert.equal((await login('e1','feishu')).ok,false);assert.equal((await login('e1','password')).ok,true)})
test('受控开通先核验，首次密码必须进入改密阶段',async()=>{reset();assert.equal((await activate('e3')).ok,false);state.employees.find(e=>e.id==='e3').checked=true;assert.equal((await activate('e3')).ok,true);assert.equal((await login('e3','password')).firstPassword,true);assert.equal(state.session.phase,'first-password');await changePassword('e3');assert.equal(state.session.phase,'active');assert.equal(state.employees.find(e=>e.id==='e3').firstPassword,false)})
test('管理员重置只恢复演示首次改密标记，不存储现用密码',async()=>{reset();await resetPassword('e1');assert.equal((await login('e1','password')).firstPassword,true);assert.equal(state.employees.some(e=>'password' in e),false)})
test('换绑冲突拒绝，成功仍保留原员工和账号',async()=>{reset();const account=state.employees.find(e=>e.id==='e1').accountId;assert.equal((await rebind('e1','demo-feishu-e2')).ok,false);assert.equal(state.employees.find(e=>e.id==='e1').feishuId,'demo-feishu-e1');assert.equal((await rebind('e1','demo-feishu-e1-new')).ok,true);assert.equal(state.employees.find(e=>e.id==='e1').accountId,account)})
test('保存失败或冲突不留改动/成功日志，随后可正常重试',async()=>{for(const fault of ['save-failure','conflict']){reset();const before=JSON.stringify(state);ui.fault=fault;assert.equal((await saveDemo('失败操作',()=>{state.employees.find(e=>e.id==='e3').checked=true})).ok,false);assert.equal(JSON.stringify(state),before);ui.fault='none';assert.equal((await saveDemo('重试核验',()=>{state.employees.find(e=>e.id==='e3').checked=true})).ok,true);assert.equal(state.employees.find(e=>e.id==='e3').checked,true)}})
test('飞书服务失败可使用同账号的密码备用入口',async()=>{reset();ui.fault='service-failure';assert.equal((await login('e1','feishu')).ok,false);assert.equal((await login('e1','password')).ok,true)})
