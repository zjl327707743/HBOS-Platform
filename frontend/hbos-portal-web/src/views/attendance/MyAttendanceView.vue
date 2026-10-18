<script setup lang="ts">
import { developmentObservation } from '@/services/frappeClient'
import { onMounted,onBeforeUnmount,getCurrentInstance,ref,reactive,computed,watch,nextTick } from 'vue'
import { getMyAttendance } from '@/services/attendancePersonal'
import { getMyEmployeeStatus } from '@/services/iamAccount'
import { iamMessage } from '@/services/iamAccess'
import type { AttendanceRow } from '@/types/iam'
import { attendanceStateLease, restoreAttendanceState, saveAttendanceState, type AttendanceFilters } from '@/services/attendancePageState'
import { attendanceObservation, observeAttendance } from '@/services/attendanceObservation'
const lease = attendanceStateLease(), restored = restoreAttendanceState(lease)
const draft = reactive<AttendanceFilters>(restored?.draft || {date_from:'',date_to:'',page:1})
const applied = ref<AttendanceFilters|null>(restored?.applied || null)
const rows=ref<AttendanceRow[]>([]),total=ref(0),loading=ref(true),error=ref(''),initialized=ref(!!restored?.applied),succeeded=ref(false),timezone=ref('')
const modified = computed(() => !!applied.value && (draft.date_from !== applied.value.date_from || draft.date_to !== applied.value.date_to))
const viewInstance = import.meta.env.DEV ? getCurrentInstance()?.uid : undefined
let generation=0
const logLabels:Record<string,string>={IN:'签到',OUT:'签退'}, statusLabels:Record<string,string>={Present:'出勤',Absent:'缺勤', 'On Leave':'请假','Half Day':'半天','Work From Home':'居家办公'}
const columns=[{title:'记录类型',key:'source',width:'20%'},{title:'日期',dataIndex:'date',width:'20%'},{title:'打卡时间',dataIndex:'time',width:'25%'},{title:'打卡类型',key:'log_type',width:'15%'},{title:'考勤结果',key:'status',width:'20%'}]
function persist() { saveAttendanceState(lease, {draft:{...draft},applied:applied.value,scroll:window.scrollY}) }
function observation() { observeAttendance({draft:JSON.stringify(draft),applied:JSON.stringify(applied.value),range:applied.value ? `${applied.value.date_from}～${applied.value.date_to} / ${applied.value.page}` : ''}) }
watch(draft,()=>{persist();observation()})
function validDates(filters: AttendanceFilters) {
  const iso = (value:string) => /^\d{4}-\d{2}-\d{2}$/.test(value) && Number.isFinite(Date.parse(value)) && new Date(value).toISOString().slice(0,10) === value
  return iso(filters.date_from) && iso(filters.date_to) && filters.date_from <= filters.date_to && Date.parse(filters.date_to)-Date.parse(filters.date_from) <= 366*86400000
}
async function load(filters: AttendanceFilters|null = applied.value, restorePosition = false) {
  const snapshot = filters ? {...filters} : null, run=++generation
  loading.value=true;error.value=''
  const request = `attendance-${run}`
  observeAttendance({requests:attendanceObservation.requests+1,request})
  try {
    if(snapshot && !validDates(snapshot)) throw new Error('请选择完整有效的起止日期，开始不能晚于结束，最多查询367天。')
    const association=await getMyEmployeeStatus()
    if(run!==generation)return
    if(association.status!=='linked') throw new Error(association.status==='conflict'?'员工档案关联存在冲突，请联系负责人核对。':'当前账号尚未关联有效员工档案，请联系负责人完成关联。')
    const result=await getMyAttendance({...snapshot,page:snapshot?.page||1,page_size:20})
    if(run!==generation){observeAttendance({stale:attendanceObservation.stale+1});return}
    const confirmed = {date_from:result.date_from||'',date_to:result.date_to||'',page:result.page}
    if(!validDates(confirmed) || (snapshot && (snapshot.date_from!==confirmed.date_from || snapshot.date_to!==confirmed.date_to || snapshot.page!==confirmed.page)) || result.rows.some(row=>row.date<confirmed.date_from || row.date>confirmed.date_to)) throw new Error('返回记录与查询范围不一致，请重新查询或联系管理员。')
    // A first, server-default query initializes visible controls from Site dates.
    // An edited draft never labels or changes an in-flight query's result.
    if(!initialized.value){Object.assign(draft,confirmed);initialized.value=true}
    applied.value=confirmed; rows.value=result.rows;total.value=result.total;succeeded.value=true;timezone.value=result.site_timezone||''
    observeAttendance({completed:attendanceObservation.completed+1});observation();persist()
    if(restorePosition && restored){await nextTick();window.scrollTo({top:restored.scroll,behavior:'instant'})}
  } catch(e) {
    if(run===generation){rows.value=[];total.value=0;succeeded.value=false;error.value=(e as {code?:string}).code==='FORBIDDEN'?'当前本人考勤访问未获授权，可能已暂停或权限已到期。请联系负责人核对应用权限。':iamMessage(e)}
  } finally { if(run===generation)loading.value=false }
}
function query(){draft.page=1;void load({...draft})}
function changePage(page:number){if(applied.value){draft.page=page;void load({...applied.value,page})}}
const permissionsChanged=(event:Event)=>{const apps=(event as CustomEvent<{apps:string[]|null}>).detail?.apps;if(apps && !apps.includes('attendance'))return;observeAttendance({permissions:attendanceObservation.permissions+1});rows.value=[];total.value=0;void load()}
onMounted(()=>{observeAttendance({mounts:attendanceObservation.mounts+1,instance:viewInstance||0});observation();void load(applied.value,true);window.addEventListener('hbos:permissions-changed',permissionsChanged);window.addEventListener('scroll',persist,{passive:true})})
onBeforeUnmount(()=>{persist();generation++;observeAttendance({unmounts:attendanceObservation.unmounts+1});window.removeEventListener('hbos:permissions-changed',permissionsChanged);window.removeEventListener('scroll',persist)})
</script>
<template><section class="my-attendance" :data-view-instance="viewInstance"><output v-if="developmentObservation">本机页面实例 {{ viewInstance }}</output><div class="page-heading"><div><h1>我的考勤</h1><p>查看本人的原始打卡与每日考勤结果。</p></div></div><section class="attendance-panel glass-surface"><div v-if="initialized" class="attendance-toolbar"><label>开始日期<a-input v-model:value="draft.date_from" type="date" aria-label="考勤开始日期"/></label><label>结束日期<a-input v-model:value="draft.date_to" type="date" aria-label="考勤结束日期"/></label><a-button type="primary" @click="query">查询本人考勤</a-button><span v-if="loading" role="status">正在查询…</span></div><p v-else>正在读取站点日期与本人关联… <a-button v-if="error" @click="load(null)">重试读取</a-button></p><p v-if="applied" class="applied-range" aria-live="polite">{{ succeeded ? '结果查询范围' : '上次成功查询范围' }}：{{applied.date_from}} 至 {{applied.date_to}} · 第 {{applied.page}} 页<span v-if="timezone">（{{timezone}}）</span></p><p v-if="modified" role="status" class="draft-notice">条件已修改，点击查询生效。下方结果仍属于已应用范围。</p><a-alert v-if="error" :message="error" type="warning" show-icon/><a-table :columns="columns" :data-source="rows" row-key="id" table-layout="fixed" :scroll="{x:600}" :loading="loading" :pagination="{current:applied?.page||1,pageSize:20,total,showSizeChanger:false,onChange:changePage}" :locale="{emptyText:error?'当前无法读取本人考勤':'所选日期暂无本人考勤记录'}"><template #bodyCell="{column,record}"><template v-if="column.key === 'source'">{{ record.source === 'Attendance' ? '每日考勤结果' : record.source === 'Employee Checkin' ? '原始打卡' : '待核对的记录类型' }}</template><template v-else-if="column.key === 'log_type'">{{ record.source === 'Attendance' ? '—' : logLabels[record.log_type || ''] || '未识别类型' }}</template><template v-else-if="column.key === 'status'">{{ record.source === 'Employee Checkin' ? '—' : statusLabels[record.status || ''] || '未识别状态' }}</template></template></a-table><p class="attendance-note">历史记录随原员工档案保留。</p></section></section></template>
<style scoped>.my-attendance{font-size:16px;line-height:1.6;min-width:0}.attendance-panel{padding:24px;min-width:0}.attendance-toolbar{display:flex;flex-wrap:wrap;align-items:flex-end;gap:16px;margin-bottom:24px}.attendance-toolbar label{display:grid;gap:8px;font-size:14px}.attendance-note{font-size:14px;color:var(--hbos-text-secondary)}.my-attendance :deep(.ant-table-cell){font-size:16px}.my-attendance :deep(.ant-table-thead .ant-table-cell){font-size:14px}</style>
