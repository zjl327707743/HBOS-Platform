<script setup lang="ts">
import { onMounted,ref } from 'vue'
import { getMyAttendance } from '@/services/attendancePersonal'
import { iamMessage } from '@/services/iamAccess'
import type { AttendanceRow } from '@/types/iam'
const rows=ref<AttendanceRow[]>([]),page=ref(1),total=ref(0),from=ref(''),to=ref(''),loading=ref(true),error=ref('')
let generation=0
const columns=[{title:'日期',dataIndex:'date',width:'25%'},{title:'打卡时间',dataIndex:'time',width:'25%'},{title:'打卡类型',dataIndex:'log_type',width:'20%'},{title:'考勤结果',dataIndex:'status',width:'30%'}]
async function load(){const run=++generation;loading.value=true;error.value='';try{const result=await getMyAttendance({...(from.value?{date_from:from.value}:{}),...(to.value?{date_to:to.value}:{}),page:page.value,page_size:20});if(run===generation){rows.value=result.rows;total.value=result.total}}catch(e){if(run===generation){rows.value=[];total.value=0;error.value=iamMessage(e)}}finally{if(run===generation)loading.value=false}}
onMounted(load)
</script>
<template><section class="my-attendance"><div class="page-heading"><div><h1>我的考勤</h1><p>仅显示当前本人关联员工的考勤。同事记录不会返回。</p></div></div><section class="attendance-panel glass-surface"><div class="attendance-toolbar"><label>开始日期<a-input v-model:value="from" type="date" aria-label="考勤开始日期"/></label><label>结束日期<a-input v-model:value="to" type="date" aria-label="考勤结束日期"/></label><a-button type="primary" :loading="loading" @click="page=1;load()">查询本人考勤</a-button></div><a-alert v-if="error" :message="error" type="warning" show-icon/><a-table :columns="columns" :data-source="rows" row-key="id" table-layout="fixed" :scroll="{x:600}" :loading="loading" :pagination="{current:page,pageSize:20,total,showSizeChanger:false,onChange:(value:number)=>{page=value;load()}}" :locale="{emptyText:error?'当前无法读取本人考勤':'所选日期暂无本人考勤记录'}"/><p class="attendance-note">历史记录按原员工主键归属保留。当前未开放部门历史查询或导出。</p></section></section></template>
<style scoped>.my-attendance{font-size:16px;line-height:1.6;min-width:0}.attendance-panel{padding:24px;min-width:0}.attendance-toolbar{display:flex;flex-wrap:wrap;align-items:flex-end;gap:16px;margin-bottom:24px}.attendance-toolbar label{display:grid;gap:8px;font-size:14px}.attendance-note{font-size:14px;color:var(--hbos-text-secondary)}.my-attendance :deep(.ant-table-cell){font-size:16px}.my-attendance :deep(.ant-table-thead .ant-table-cell){font-size:14px}</style>
