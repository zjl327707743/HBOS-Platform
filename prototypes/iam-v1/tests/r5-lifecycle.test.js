import test from 'node:test'
import assert from 'node:assert/strict'
import {createSeed} from '../src/seed.js'

const saved=new Map([['hbos.iam-v1.r3.synthetic.v3','preserved-r3'],['hbos.iam-v1.r4.synthetic.v4','preserved-r4']])
globalThis.localStorage={getItem:key=>saved.get(key)||null,setItem:(key,value)=>saved.set(key,value)}
const model=await import('../src/model.js')
const reset=()=>{Object.assign(model.state,createSeed({expanded:true}));model.ui.fault='none';model.ui.busy=false}

test('R5 打开员工工作台，仅重置自身命名空间，保留冻结的 R3/R4 本机记录',async()=>{
 assert.equal(model.state.session.employeeId,'admin')
 assert.equal(model.STORAGE_KEY,'hbos.iam-v1.r5.synthetic.v5')
 assert.equal((await model.resetDemo()).ok,true)
 assert.equal(saved.get('hbos.iam-v1.r3.synthetic.v3'),'preserved-r3')
 assert.equal(saved.get('hbos.iam-v1.r4.synthetic.v4'),'preserved-r4')
 assert.equal(model.state.employees.length,29)
})
test('未确认组织不能用于新增员工或调岗，不留下部分改动',async()=>{
 reset()
 const before=JSON.stringify(model.state)
 const draft={name:'演示新员工',employeeNumber:'000401',company:'演示公司',departmentId:'d-unconfirmed',gender:'未说明',birthDate:'1995-02-03',employmentDate:'2026-10-01',position:'演示岗位'}
 assert.equal((await model.createEmployee(draft)).ok,false)
 assert.equal(JSON.stringify(model.state),before)
 assert.equal((await model.transfer('e1','d-unconfirmed')).ok,false)
 assert.equal(JSON.stringify(model.state),before)
})
test('合成多页与长名称场景不污染 R4 的固定五人行为夹具',()=>{
 const original=createSeed(),expanded=createSeed({expanded:true})
 assert.equal(original.employees.length,5)
 assert.deepEqual(expanded.employees.slice(0,5),original.employees)
 assert.equal(expanded.depts.find(d=>d.id==='d-long').confirmed,true)
 assert.equal(expanded.employees.find(e=>e.id==='e6').employeeNumber,'00106')
 assert.ok(expanded.employees.find(e=>e.id==='e6').name.length>20)
})
