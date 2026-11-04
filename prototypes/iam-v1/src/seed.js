// Every record is invented for this prototype. No HR export is imported here.
const permission = (scope) => ({mode:'allow',scope})
export function createSeed() {
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
