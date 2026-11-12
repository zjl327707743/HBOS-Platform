<script setup>
import {computed} from 'vue'
import {state,currentUser} from '../model.js'
import {previewAttendance} from '../permission.js'
const props=defineProps({employeeId:String,configurationPreview:{type:Boolean,default:false}})
const actor=computed(()=>state.employees.find(e=>e.id===props.employeeId)||state.nonEmployeeAccounts.find(e=>e.id===props.employeeId)||currentUser.value)
const result=computed(()=>previewAttendance(state,actor.value,{endpoint:'self',operation:'read'}))
const message=computed(()=>!actor.value?.employeeId||actor.value.relationStatus!=='confirmed'?'员工档案尚未确认，关联完成后才能查看考勤。':actor.value.status!=='active'?'账号当前不可用，暂时不能查看考勤。':actor.value.attendanceIdentity?.status==='conflict'?'考勤关联需要处理，请先核对员工资料。':'暂未安排查看考勤，请联系管理员。')
</script>
<template>
 <section class="attendance-card">
  <h3>{{configurationPreview?'可以看到哪些考勤':'我的考勤'}}</h3>
  <p v-if="result.ok">{{configurationPreview?actor?.name+'可以':'你可以'}}查看自己的考勤，包含同一员工档案下调岗前的记录。<strong>看不到同事的考勤。</strong></p>
  <p v-else class="availability-note">{{message}}</p>
  <template v-if="result.ok"><a-table :data-source="result.rows" :pagination="false" row-key="id" :columns="[{title:'日期',dataIndex:'date'},{title:'打卡时间',dataIndex:'checkIn'},{title:'结果',dataIndex:'status'}]" :locale="{emptyText:'暂无考勤记录。已关联不代表已经有打卡数据。'}" size="middle"/><p class="helper-text">{{configurationPreview?'以下为该员工可见内容的合成示例。':'当前显示合成记录。'}} 部门查询和导出暂未开放。</p></template>
 </section>
</template>
<style scoped>
.attendance-card{padding:24px;background:#f5f8f5;border:1px solid #dfe7df;border-radius:10px}.attendance-card h3{font-size:20px;line-height:28px;margin:0 0 12px}.attendance-card p{font-size:16px;line-height:24px;margin:0 0 16px;color:#435147}.attendance-card strong{font-weight:600}.attendance-card .helper-text{font-size:14px;line-height:22px;margin:16px 0 0;color:#59645d}.availability-note{margin-bottom:0!important}
</style>
