<script setup>
import { computed, ref } from 'vue'
import { message } from 'ant-design-vue'
import { SearchOutlined, PlusOutlined, ArrowRightOutlined, UserOutlined } from '@ant-design/icons-vue'
import { state, ui, deptName, effective, scopeLabel, saveDemo, activate, transfer, disable, resetPassword } from '../model'
import AccountSecurity from './AccountSecurity.vue'
const emit=defineEmits(['permissions','employee-view'])
const search=ref(''),deptFilter=ref('all'),statusFilter=ref('all'),selectedId=ref(null),tab=ref('basic')
const selected=computed({get:()=>state.employees.find(e=>e.id===selectedId.value)||null,set:e=>{selectedId.value=e?.id||null}})
const action=ref(''),targetDepartment=ref('d1'),checked=ref(false),linkAccount=ref('demo.unlinked@example.invalid'),temp=ref('')
const rows=computed(()=>state.employees.filter(e=>(!search.value||[e.name,e.code,e.accountId].join(' ').includes(search.value))&&(deptFilter.value==='all'||e.departmentId===deptFilter.value)&&(statusFilter.value==='all'||e.status===statusFilter.value)))
const statuses={active:['已开通','success'],pending:['待开通','warning'],disabled:['已停用','default']}
const titles={new:'新增合成员工',verify:'核验企业人员',activate:'受控开通账号',link:'关联已有演示账号',transfer:'调岗影响预览',disable:'停用账号',reset:'重置演示临时密码'}
const countStatus=s=>state.employees.filter(e=>e.status===s).length
const permissions=computed(()=>selected.value?state.apps.map(app=>({...app,result:effective(selected.value,app.id,'*')})):[])
const logs=computed(()=>state.logs.filter(l=>l.label.includes(selected.value?.name||'NOT_MATCH')).slice(0,15))
function open(e){selected.value=e;tab.value='basic'}
function begin(type){action.value=type;checked.value=false;targetDepartment.value=selected.value?.departmentId==='d1'?'d2':'d1'}
async function perform(){
 let result
 const e=selected.value
 if(action.value==='new')result=await saveDemo('新增待核验合成员工；未创建正式账号',()=>{const n=state.employees.length+1;const id=`e${n}`;state.employees.push({id,name:`演示员工 ${String(n).padStart(2,'0')}`,code:`DEMO-${100+n}`,departmentId:targetDepartment.value,secondaryDepartments:[],position:'待确认岗位',status:'pending',bound:false,feishuId:'',accountId:'',firstPassword:true,checked:false,exceptions:{}})})
 if(action.value==='verify')result=await saveDemo(`${e.name}企业人员核验完成（合成）`,()=>{if(!checked.value)throw new Error('请确认企业核验依据');e.checked=true})
 if(action.value==='activate')result=await activate(e.id)
 if(action.value==='link')result=await saveDemo(`${e.name}关联已有演示账号，未按姓名匹配`,()=>{if(!e.checked)throw new Error('人员未核验');if(e.accountId)throw new Error('已经关联唯一账号');if(state.employees.some(x=>x.accountId===linkAccount.value))throw new Error('此账号已关联其他员工，不能抢占');e.accountId=linkAccount.value;e.status='active';e.firstPassword=false})
 if(action.value==='transfer')result=await transfer(e.id,targetDepartment.value)
 if(action.value==='disable')result=await disable(e.id)
 if(action.value==='reset')result=await resetPassword(e.id)
 if(result?.ok){if(['activate','reset'].includes(action.value)){temp.value=`DEMO-${crypto.randomUUID().slice(0,8)}-Aa!`}message.success('演示已保存到本机');action.value=''}else if(result)message.error(result.error)
}
</script>
<template>
 <div class="page-heading"><div><div class="kicker">IDENTITY & ORGANIZATION</div><h1>人员管理<span class="heading-pill">合成演示</span></h1><p class="muted">一名员工，一个账号。清楚管理任职、登录与可用权限。</p></div><a-button type="primary" size="large" @click="begin('new')"><PlusOutlined/>新增合成员工</a-button></div>
 <div class="stats-row"><div class="stat"><span>人员总数</span><strong>{{state.employees.length}}<small>人</small></strong><p>仅合成演示名册</p></div><div class="stat"><span>已开通账号</span><strong>{{countStatus('active')}}<small>人</small></strong><p><i class="dot green"/>可使用已配置登录方式</p></div><div class="stat"><span>待核对 / 待开通</span><strong>{{state.employees.filter(e=>!e.checked||e.status==='pending').length}}<small>人</small></strong><p><i class="dot amber"/>企业核验后受控开通</p></div><div class="stat"><span>部门普通预设</span><strong>{{state.depts.length}}<small>个部门</small></strong><p>调岗自动撤旧授新</p></div></div>
 <section class="panel people-panel"><div class="panel-title"><h2>企业人员</h2><span class="muted">{{rows.length}} 条结果 · 点击姓名查看详情</span></div>
 <div class="toolbar"><a-input v-model:value="search" placeholder="搜索合成姓名、演示工号或账号" aria-label="搜索人员" allow-clear style="width:330px"><template #prefix><SearchOutlined/></template></a-input><a-select v-model:value="deptFilter" aria-label="部门筛选" style="width:180px"><a-select-option value="all">全部部门</a-select-option><a-select-option v-for="d in state.depts" :key="d.id" :value="d.id">{{d.name}}</a-select-option></a-select><a-select v-model:value="statusFilter" aria-label="账号状态筛选" style="width:150px"><a-select-option value="all">全部账号状态</a-select-option><a-select-option value="active">已开通</a-select-option><a-select-option value="pending">待开通</a-select-option><a-select-option value="disabled">已停用</a-select-option></a-select></div>
 <div class="table-scroll"><table class="people-table"><thead><tr><th>姓名 / 演示工号</th><th>主部门 / 岗位</th><th>账号状态</th><th>飞书绑定</th><th>核对状态</th><th>操作</th></tr></thead><tbody><tr v-for="e in rows" :key="e.id"><td><button class="person-link" @click="open(e)"><span class="avatar" :class="{admin:e.id==='admin'}">{{e.name.slice(-2)}}</span><span><b>{{e.name}}</b><small>{{e.code}}</small></span></button></td><td><b class="department-text">{{deptName(e.departmentId)}}</b><small>{{e.position}}<span v-if="e.secondaryDepartments.length"> · 兼岗 {{deptName(e.secondaryDepartments[0])}}</span></small></td><td><a-tag :color="statuses[e.status][1]">{{statuses[e.status][0]}}</a-tag><small v-if="e.firstPassword&&e.status==='active'">首次密码待改密</small></td><td><span :class="e.bound?'binding-good':'muted'"><i class="dot" :class="e.bound?'green':'gray'"/>{{e.bound?'已绑定':'未绑定'}}</span></td><td><a-tag v-if="!e.checked" color="orange">待核对</a-tag><span v-else class="muted">已核验（演示）</span></td><td><a-button type="link" @click="open(e)">查看<ArrowRightOutlined/></a-button></td></tr></tbody></table></div>
 <a-empty v-if="!rows.length" description="没有符合筛选条件的合成人员"/><div class="table-footer">所有账号和标识均为合成数据。源表导出用户 ID、姓名和部门文本不用于自动认定身份。</div></section>
 <div class="quiet-note"><UserOutlined/><div><b>普通员工看到自己的资料与账号安全</b><p>右上角切换到员工视角，检查部门继承、个人例外与无权限提示。</p></div></div>
 <a-drawer :open="!!selected" :title="selected?.name+' · 人员详情'" :width="650" @close="selected=null" :destroy-on-close="true">
  <template v-if="selected"><a-alert message="交互原型 / 合成数据 / 尚未连接 HBOS 后端" type="info" show-icon/><a-tabs v-model:activeKey="tab">
   <a-tab-pane key="basic" tab="基本资料"><a-descriptions :column="1" bordered size="small"><a-descriptions-item label="演示工号">{{selected.code}}</a-descriptions-item><a-descriptions-item label="主部门">{{deptName(selected.departmentId)}}</a-descriptions-item><a-descriptions-item label="兼岗">{{selected.secondaryDepartments.map(deptName).join('、')||'无'}} · 兼岗不自动叠加主部门预设</a-descriptions-item><a-descriptions-item label="岗位">{{selected.position}}</a-descriptions-item><a-descriptions-item label="唯一演示账号">{{selected.accountId||'未开通 / 未关联'}}</a-descriptions-item><a-descriptions-item label="核验">{{selected.checked?'已核验（演示）':'待核对'}}</a-descriptions-item></a-descriptions><div class="action-grid"><a-button v-if="!selected.checked" @click="begin('verify')">核验企业人员</a-button><a-button v-if="!selected.accountId" type="primary" @click="begin('activate')">受控开通账号</a-button><a-button v-if="!selected.accountId" @click="begin('link')">关联已有账号</a-button><a-button @click="begin('transfer')">调岗</a-button><a-button v-if="selected.status==='active'" @click="begin('reset')">重置临时密码</a-button><a-button v-if="selected.id!=='admin'&&selected.status==='active'" danger @click="begin('disable')">停用账号</a-button></div><p class="muted">开户不会自动绑定飞书；已开通员工需经过本人验证绑定。管理员不能查看员工已修改的当前密码。</p></a-tab-pane>
   <a-tab-pane key="security" tab="账号安全"><AccountSecurity :employee="selected"/></a-tab-pane>
   <a-tab-pane key="permissions" tab="有效权限"><div v-for="app in permissions" :key="app.id" class="permission-summary"><b>{{app.name}}</b><a-tag :color="app.result.allowed?'green':'default'">{{app.result.allowed?'可进入':'不可进入'}}</a-tag><p>{{app.result.source}} · {{app.result.scope.map(scopeLabel).join('、')||app.result.reason}}</p><div v-for="a in app.actions" :key="a.id" class="compact-right"><span>{{a.name}}</span><span>{{effective(selected,app.id,a.id).allowed?'允许':'禁止'}} · {{effective(selected,app.id,a.id).source}}</span></div></div><a-button type="primary" @click="emit('permissions',selected.id);selected=null">配置此人员权限</a-button></a-tab-pane>
   <a-tab-pane key="history" tab="变更记录"><a-timeline><a-timeline-item v-for="l in logs" :key="l.id"><b>{{l.label}}</b><p class="muted">{{l.time}} · {{l.actor}}</p></a-timeline-item></a-timeline><a-empty v-if="!logs.length" description="暂无此员工的演示变更"/></a-tab-pane>
  </a-tabs></template>
 </a-drawer>
 <a-modal :open="!!action" :title="titles[action]" :confirm-loading="ui.busy" :ok-button-props="{disabled:action==='verify'&&!checked}" ok-text="确认演示操作" cancel-text="取消" @ok="perform" @cancel="action=''">
  <p v-if="action==='new'">将新增自动命名的合成员工，账号为待开通。不会读取 Excel 或创建真实员工。</p>
  <a-alert v-if="action==='activate'" :type="selected?.checked?'info':'warning'" :message="selected?.checked?'企业人员已核验，将创建唯一合成账号并生成一次演示临时密码。':'此人员待核对；请先核验，开通会被拒绝。'" show-icon/>
  <a-checkbox v-if="action==='verify'" v-model:checked="checked">已核对演示人员名册与企业人员归属（无真实写入）</a-checkbox>
  <template v-if="action==='link'"><p>只关联明确核验的现有账号，不按姓名匹配，不抢占。</p><a-select v-model:value="linkAccount" aria-label="已有合成账号" style="width:100%"><a-select-option value="demo.unlinked@example.invalid">未关联演示账号</a-select-option><a-select-option value="demo.e2@example.invalid">陈宁已关联账号（冲突演示）</a-select-option></a-select></template>
  <template v-if="action==='new'||action==='transfer'"><label for="transfer-department">{{action==='transfer'?'新主部门':'演示部门'}}</label><a-select id="transfer-department" v-model:value="targetDepartment" style="width:100%" :options="state.depts.map(d=>({value:d.id,label:d.name}))"/><div v-if="action==='transfer'" class="impact-box"><b>{{deptName(selected?.departmentId)}} → {{deptName(targetDepartment)}}</b><p>原主部门的普通继承失效，新部门普通预设生效。个人例外保留；高风险不会自动授予。</p><div v-for="app in state.apps" :key="app.id"><span>{{app.name}}：</span>{{effective({...selected,departmentId:targetDepartment},app.id,'*').allowed?'新部门可进入':'新部门不可进入'}}</div></div></template>
  <a-alert v-if="action==='disable'" message="停用后模拟登录与业务访问拒绝，历史记录保留。真实会话撤销与后端拒绝尚未实现。" type="warning" show-icon/>
  <a-alert v-if="action==='reset'" message="将展示一次新的演示临时密码，下次密码入口必须先改密；管理员无法读取现用密码。" type="info" show-icon/>
 </a-modal>
 <a-modal :open="!!temp" title="一次演示临时密码" :footer="null" @cancel="temp=''"><a-alert message="仅合成演示。请勿将此值用于真实系统。关闭后不再展示。" type="warning" show-icon/><p class="temporary-password">{{temp}}</p><p>无需手工输入。切换至该员工 → 密码备用 → 使用演示临时密码 → 首次改密。此值没有发送给任何人。</p><a-button type="primary" @click="temp=''">已查看，关闭演示密码</a-button></a-modal>
</template>
<style scoped>
.action-grid{display:flex;gap:10px;flex-wrap:wrap;margin:22px 0}.permission-summary{border-bottom:1px solid #e5eee9;padding:14px 0}.permission-summary b{margin-right:12px}.compact-right{display:flex;justify-content:space-between;gap:12px;font-size:13px;margin:7px 0}.impact-box{padding:16px;background:#f0f7f3;border-radius:10px;margin-top:18px}.temporary-password{font-size:24px;background:#eff6f1;padding:18px;text-align:center;font-family:monospace}.heading-pill{font-size:12px;vertical-align:middle;margin-left:12px;font-weight:500;color:#4d7762;background:#e9f3ec;padding:5px 9px;border-radius:6px}.binding-good{color:#396c55}
</style>
