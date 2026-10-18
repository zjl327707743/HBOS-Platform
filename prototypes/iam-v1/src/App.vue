<script setup>
import {computed,ref,watch,nextTick} from 'vue'
import {message} from 'ant-design-vue'
import {TeamOutlined,ApartmentOutlined,SafetyCertificateOutlined,HistoryOutlined,AppstoreOutlined,SwapOutlined,ReloadOutlined,ExperimentOutlined,LogoutOutlined,LockOutlined} from '@ant-design/icons-vue'
import {state,ui,currentUser,allSubjects,isAdmin,login,logout,expireSession,resetDemo,registerDemoApp} from './model.js'
import PeopleView from './components/PeopleView.vue'
import DepartmentsView from './components/DepartmentsView.vue'
import PermissionsView from './components/PermissionsView.vue'
import EmployeeDrawer from './components/EmployeeDrawer.vue'
import AppUsageList from './components/AppUsageList.vue'
import AttendanceCard from './components/AttendanceCard.vue'
import AttendancePreview from './components/AttendancePreview.vue'
import LoginView from './components/LoginView.vue'
import AccountSecurity from './components/AccountSecurity.vue'
const page=ref('people'),switcher=ref(false),identity=ref('admin'),history=ref(false),loading=ref(false),loginView=ref(null)
const drawerRef=ref(null),drawer=ref(false),targetEmployee=ref('e1'),targetTab=ref('basic'),targetApp=ref(null),regressionEmployee=ref('e1')
const ready=computed(()=>state.session?.phase==='active'&&currentUser.value?.status==='active')
const titles={people:'员工管理',departments:'部门管理',permissions:'应用权限',workbench:'我的工作台',security:'账号安全'}
const navs=[{id:'people',label:'员工管理',icon:TeamOutlined},{id:'departments',label:'部门管理',icon:ApartmentOutlined},{id:'permissions',label:'应用权限',icon:SafetyCertificateOutlined}]
watch([ready,()=>state.session?.employeeId],()=>{drawer.value=false;if(ready.value)page.value=isAdmin.value?'people':'workbench'})
async function openEmployee(id,tab='basic',appId=null){if(!isAdmin.value)return;if(drawer.value&&drawerRef.value?.requestLeave&&!(await drawerRef.value.requestLeave()))return;targetEmployee.value=id;targetTab.value=tab;targetApp.value=appId;drawer.value=true}
async function switchUser(){const result=await login(identity.value,'password');if(result.ok)switcher.value=false;else message.error(result.error)}
async function openRecovery(){const id=currentUser.value?.id;logout();await nextTick();loginView.value?.openRecovery(id)}
async function reset(){ui.fault='none';const r=await resetDemo();if(r.ok){drawer.value=false;await login('admin','password');page.value='people';message.success('已恢复 R5 合成场景，R3/R4 本机记录保留。')}}
async function addModule(){const r=await registerDemoApp();if(!r.ok)message.info(r.error)}
async function mockLoading(){loading.value=true;await new Promise(r=>setTimeout(r,700));loading.value=false}
</script>
<template>
<a-config-provider :theme="{token:{colorPrimary:'#396c50',colorSuccess:'#427b59',colorText:'#26362c',colorBgLayout:'#f5f7f5',fontFamily:'Inter, PingFang SC, Microsoft YaHei, system-ui, sans-serif',fontSize:ready?16:14,controlHeight:ready?40:32,borderRadius:8}}">
 <div class="prototype-banner"><ExperimentOutlined/><strong>合成原型</strong><span>未连接后端</span><span class="version-mark">IAM · R5</span></div>
 <header class="global-header"><div class="brand"><span class="brand-symbol">H<span></span></span><div><b>HBOS</b><small>海滨智能运营管理平台</small></div></div><span class="header-divider"></span><span class="header-context">员工与应用安排</span><div class="header-actions"><a-button @click="switcher=true"><SwapOutlined/>切换演示身份</a-button><template v-if="ready"><span class="header-user"><span class="mini-avatar">{{currentUser.name.slice(-2)}}</span>{{currentUser.name}}</span><a-button type="text" aria-label="退出演示账号" @click="logout('已退出演示账号')"><LogoutOutlined/></a-button></template></div></header>
 <div v-if="!ready" class="login-container"><a-alert v-if="ui.error" type="error" show-icon :message="ui.error"/><LoginView ref="loginView"/></div>
 <div v-else class="app-shell">
  <aside class="sidebar"><div class="side-label">{{isAdmin?'管理中心':'个人工作台'}}</div><nav aria-label="主要页面"><template v-if="isAdmin"><button v-for="nav in navs" :key="nav.id" class="nav-button" :class="{active:page===nav.id}" @click="page=nav.id"><component :is="nav.icon"/><span>{{nav.label}}</span></button></template><template v-else><button class="nav-button" :class="{active:page==='workbench'}" @click="page='workbench'"><AppstoreOutlined/><span>我的工作台</span></button><button class="nav-button" :class="{active:page==='security'}" @click="page='security'"><LockOutlined/><span>账号安全</span></button></template></nav><div class="side-separator"></div><button class="nav-button compact" @click="history=true"><HistoryOutlined/><span>{{isAdmin?'变更记录':'我的变更记录'}}</span></button><div class="sidebar-spacer"></div><div class="sidebar-footer"><i class="dot green"/>本机原型<span>使用合成资料，可随时重置</span></div></aside>
  <main class="main-content"><div class="page-container">
   <div class="breadcrumb"> <span>{{isAdmin?'管理中心':'个人'}}</span><span>/</span><b>{{titles[page]}}</b></div>
   <a-alert v-if="ui.error" type="error" show-icon closable :message="ui.error" @close="ui.error=''" class="page-notice"/>
   <a-alert v-if="ui.fault==='load-failure'" message="暂时无法加载，已保存内容不变。" type="error" show-icon><template #action><a-button @click="ui.fault='none'">重试加载</a-button></template></a-alert>
   <a-skeleton v-else-if="loading" active :paragraph="{rows:10}" class="panel"/>
   <template v-else>
    <div v-if="isAdmin" v-show="page==='people'"><PeopleView @open="openEmployee"/></div>
    <div v-if="isAdmin" v-show="page==='departments'"><DepartmentsView @open="openEmployee"/></div>
    <div v-if="isAdmin" v-show="page==='permissions'"><PermissionsView @open="openEmployee"/></div>
    <template v-if="!isAdmin&&page==='workbench'"><div class="page-heading"><div><h1>你好，{{currentUser.name}}</h1><p class="muted">查看自己的考勤和应用安排。</p></div><a-button @click="page='security'">账号安全</a-button></div><div class="stack"><AttendanceCard :employee-id="currentUser.id"/><section class="panel"><h2>我的应用</h2><AppUsageList :employee-id="currentUser.id" :can-edit="false"/></section></div></template>
    <template v-if="!isAdmin&&page==='security'"><div class="page-heading"><div><h1>账号安全</h1><p class="muted">验证本人身份后管理自己的登录方式。</p></div></div><section class="panel"><AccountSecurity :employee="currentUser" @recover="openRecovery"/></section></template>
   </template>
   <footer class="content-footer"><span role="status">{{ui.busy?'正在保存…':ui.notice||'所有更改仅保存在本机合成原型'}}</span></footer>
   <details class="review-tools"><summary>演示工具</summary><div class="demo-tools"><a-select v-model:value="ui.fault" aria-label="演示异常场景" :options="[{value:'none',label:'正常保存'},{value:'save-failure',label:'模拟保存失败'},{value:'conflict',label:'模拟版本冲突'},{value:'load-failure',label:'模拟加载失败'},{value:'service-failure',label:'模拟登录服务失败'}]"/><a-button @click="mockLoading">模拟加载中</a-button><a-button @click="expireSession">模拟会话过期</a-button><a-button @click="addModule">注册合成设备应用</a-button><a-button @click="reset"><ReloadOutlined/>重置 R5 合成场景</a-button></div><p class="helper-text">后端、真实账号、数据库和正式站点均未接入。R3/R4 本机记录保留。</p><details v-if="isAdmin"><summary>考勤范围回归场景</summary><a-select v-model:value="regressionEmployee" aria-label="考勤回归对象" :options="state.employees.map(e=>({value:e.id,label:e.name}))"/><AttendancePreview :employee="state.employees.find(e=>e.id===regressionEmployee)" :can-configure="true"/></details></details>
  </div></main>
 </div>
 <EmployeeDrawer ref="drawerRef" v-if="isAdmin" v-model:open="drawer" :employee-id="targetEmployee" :initial-tab="targetTab" :app-id="targetApp"/>
 <div v-if="!ready" class="login-foot-tools"><a-button @click="reset">返回员工管理</a-button></div>
 <a-modal v-model:open="switcher" title="切换合成演示身份" ok-text="进入所选账号" cancel-text="取消" :confirm-loading="ui.busy" @ok="switchUser"><p>仅切换原型身份。员工本人和管理员配置目标保持分开。</p><a-select v-model:value="identity" aria-label="选择演示身份" style="width:100%" :options="allSubjects.map(e=>({value:e.id,label:e.name+' · '+(e.id==='admin'?'管理员':e.accountId?(e.status==='disabled'?'已停用':'员工账号'):'未开通')}))"/></a-modal>
 <a-drawer v-model:open="history" :title="isAdmin?'变更记录':'我的变更记录'" :width="720" class="r5-drawer"><p class="helper-text">仅为本机合成操作记录。</p><a-timeline><a-timeline-item v-for="l in state.logs.filter(l=>isAdmin||l.label.includes(currentUser?.name))" :key="l.id"><b>{{l.label}}</b><p class="helper-text">{{l.time}} · {{l.actor}}</p></a-timeline-item></a-timeline></a-drawer>
</a-config-provider>
</template>
