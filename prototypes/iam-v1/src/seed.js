// Every record is invented for this prototype. No HR export is imported here.
const permission = (scope) => ({mode:'allow',scope})
function createBaseSeed() {
 return {
  version:3, revision:1, session:null,
  employees:[
   {id:'admin',name:'演示管理员',code:'DEMO-001',departmentId:'d1',secondaryDepartments:[],position:'人员与授权管理员',status:'active',bound:true,feishuId:'demo-feishu-admin',accountId:'demo.admin@example.invalid',firstPassword:false,checked:true,exceptions:{}},
   {id:'e1',name:'林舟',code:'DEMO-101',departmentId:'d1',secondaryDepartments:['d2'],position:'检验员',status:'active',bound:true,feishuId:'demo-feishu-e1',accountId:'demo.e1@example.invalid',firstPassword:false,checked:true,exceptions:{'inventory:*':permission(['warehouseA']),'inventory:view':permission(['warehouseA'])}},
   {id:'e2',name:'陈宁',code:'DEMO-102',departmentId:'d2',secondaryDepartments:[],position:'仓库操作员',status:'active',bound:true,feishuId:'demo-feishu-e2',accountId:'demo.e2@example.invalid',firstPassword:false,checked:true,exceptions:{'inventory:issue':{mode:'deny',scope:[]}}},
   {id:'e3',name:'沈禾',code:'DEMO-103',departmentId:'d1',secondaryDepartments:[],position:'新入职检验员',status:'pending',bound:false,feishuId:'',accountId:'',firstPassword:true,checked:false,exceptions:{}},
   {id:'e4',name:'许澄',code:'DEMO-104',departmentId:'d2',secondaryDepartments:[],position:'仓库操作员',status:'disabled',bound:true,feishuId:'demo-feishu-e4',accountId:'demo.e4@example.invalid',firstPassword:false,checked:true,exceptions:{}}
  ],
  depts:[
   {id:'d1',name:'质量研究部',parentId:'demo',description:'实验室与检验研究 · 演示部门',presets:{'attendance:*':permission(['self']),'attendance:view':permission(['self']),'lims:*':permission(['labA']),'lims:view':permission(['labA'])}},
   {id:'d2',name:'仓储运营部',parentId:'demo',description:'仓库业务与现场运营 · 演示部门',presets:{'attendance:*':permission(['self']),'attendance:view':permission(['self']),'inventory:*':permission(['warehouseA']),'inventory:view':permission(['warehouseA']),'inventory:issue':permission(['warehouseA'])}}
  ],
  apps:[
   {id:'attendance',name:'考勤管理',description:'本人记录与部门考勤',color:'#6f7fba',actions:[{id:'view',name:'查看考勤',highRisk:false},{id:'export',name:'导出记录',highRisk:false}],scopes:[{value:'self',label:'仅本人'},{value:'d1',label:'质量研究部'},{value:'d2',label:'仓储运营部'}]},
   {id:'inventory',name:'库存管理',description:'仓库查询与受控出库',color:'#ba9056',actions:[{id:'view',name:'查看库存',highRisk:false},{id:'issue',name:'办理出库',highRisk:false},{id:'adjust',name:'重要调账',highRisk:true}],scopes:[{value:'warehouseA',label:'演示仓库 A'},{value:'warehouseB',label:'演示仓库 B'}]},
   {id:'lims',name:'质量检验',description:'检验查询与质量签署',color:'#448b75',actions:[{id:'view',name:'查看检验',highRisk:false},{id:'sign',name:'质量签署',highRisk:true}],scopes:[{value:'labA',label:'演示检验组 A'},{value:'labB',label:'演示检验组 B'}]},
   {id:'platform',name:'平台管理',description:'人员与授权配置',color:'#5e788d',actions:[{id:'manage',name:'管理人员与权限',highRisk:true}],scopes:[{value:'platform',label:'演示平台管理范围'}]}
  ],
  logs:[{id:'seed',time:'2026-10-14 16:30',label:'建立合成场景：两个部门、管理员与普通员工',actor:'演示系统'}]
 }
}

// R4: Employee records and accounts without an Employee are distinct fixtures.
export function createSeed() {
 const data=createBaseSeed()
 data.version=4
 const admin=data.employees.shift()
 Object.assign(admin,{subjectType:'service',employeeId:null,departmentId:null,secondaryDepartments:[],position:'应急 / 管理主体（非员工）',username:'demo.admin',relationStatus:'not-applicable'})
 data.nonEmployeeAccounts=[admin]
 const aliases={e1:'linzhou',e2:'chenning',e3:'shenhe',e4:'xucheng'}
 for(const e of data.employees){
  const num=String(100+Number(e.id.slice(1))).padStart(5,'0')
  Object.assign(e,{subjectType:'employee',employeeId:'DEMO-EMP-'+num,employeeNumber:num,username:e.accountId?aliases[e.id]:'',company:'演示公司',gender:'未说明',birthDate:'1995-01-01',employmentDate:'2026-09-01',relationStatus:e.accountId?'confirmed':'unlinked',deviceId:'demo-device-'+num,attendanceIdentity:{source:'delicloud',namespace:'demo-company/tenant-a',externalPersonId:'demo-dl-'+num,employeeNum:num,status:e.id==='e3'?'pending':'confirmed'}})
 }
 data.employees.push({id:'e5',name:'叶知',code:'DEMO-105',employeeId:'DEMO-EMP-00105',employeeNumber:'00105',subjectType:'employee',company:'演示公司',gender:'未说明',birthDate:'1995-01-01',employmentDate:'2026-09-01',departmentId:'d1',secondaryDepartments:[],position:'管理员已预建账号',status:'active',bound:false,feishuId:'',accountId:'demo.e5@example.invalid',username:'yezhi',firstPassword:true,checked:true,relationStatus:'confirmed',exceptions:{},deviceId:'demo-device-00105',attendanceIdentity:{source:'delicloud',namespace:'demo-company/tenant-a',externalPersonId:'demo-dl-00105',employeeNum:'00105',status:'confirmed'}})
 data.employees.find(e=>e.id==='e2').exceptions['inventory:issue'].scope=['warehouseA']
 for(const d of data.depts){d.presets['attendance:read']=d.presets['attendance:view'];delete d.presets['attendance:view']}
 const app=data.apps.find(a=>a.id==='attendance')
 Object.assign(app,{description:'身份关联与本人 / 部门数据范围',actions:[{id:'read',name:'查看考勤',operationId:'attendance.read',highRisk:false},{id:'export',name:'导出考勤（候选，未接入）',operationId:'attendance.export',availability:'candidate',highRisk:false}]})
 const row=(id,employeeId,date,dept,confirmed=true)=>({id,employeeId,date,checkIn:'08:30',status:'出勤',eventDepartmentId:dept,departmentEvidenceConfirmed:!!dept,identityConfirmed:confirmed,owner:'demo-sync-service'})
 data.attendanceRecords=[row('DEMO-CI-101','DEMO-EMP-00101','2026-10-14','d1'),row('DEMO-CI-102','DEMO-EMP-00102','2026-10-14','d2'),row('DEMO-CI-103','DEMO-EMP-00101','2026-08-20','d2'),row('DEMO-CI-104','DEMO-EMP-00102','2026-08-20',null),row('DEMO-CI-105','DEMO-EMP-00105','2026-10-14','d1'),row('DEMO-CI-UNKNOWN',null,'2026-10-14',null,false)]
 data.logs=[{id:'r4-seed',time:'2026-10-15',label:'R4 合成场景：员工档案与非员工账号分开，考勤按明确 Employee 关联',actor:'演示系统'}]
 return data
}
