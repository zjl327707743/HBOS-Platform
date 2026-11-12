<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { usePortalStore } from '@/stores/portal'
import { iamMessage } from '@/services/iamAccess'
import { createAttendanceExport, type AttendanceExport } from '@/services/attendanceExports'
const portal=usePortalStore(),caps=computed(()=>portal.apps.find(app=>app.id==='attendance')?.accessCapabilities||[])
const options=computed(()=>[{value:'monthly',label:'月度考勤汇总'},{value:'exceptions',label:'考勤异常'},{value:'roster',label:'班次人员表'}].filter(item=>caps.value.includes('attendance.export.'+item.value)))
const kind=ref(options.value[0]?.value||'monthly'),dateFrom=ref(''),dateTo=ref(''),busy=ref(false),error=ref(''),result=ref<AttendanceExport|null>(null)
let pending:{key:string;id:string}|null=null
async function create(){if(busy.value)return;busy.value=true;error.value='';try{const filters:Record<string,string>=kind.value==='roster'?{}:{from_date:dateFrom.value,to_date:dateTo.value};const key=JSON.stringify([kind.value,filters]);if(!pending||pending.key!==key)pending={key,id:crypto.randomUUID()};result.value=await createAttendanceExport(kind.value,filters,pending.id);pending=null}catch(e){error.value=iamMessage(e);if((e as {status?:number}).status===403||(e as {code?:string}).code==='FORBIDDEN')pending=null}finally{busy.value=false}}
watch(kind,()=>{result.value=null;error.value='';pending=null})
</script>
<template><section class="exports product-page app-product-page"><header class="glass-hero"><h1>考勤导出</h1><p>按当前角色负责公司生成私有文件；每次下载都会重新核验功能和文件内的员工范围。</p></header><section class="glass-surface section-panel"><a-space wrap><a-select v-model:value="kind" :options="options" aria-label="导出内容" style="min-width:220px"/><template v-if="kind!=='roster'"><a-input v-model:value="dateFrom" type="date" aria-label="导出开始日期"/><a-input v-model:value="dateTo" type="date" aria-label="导出结束日期"/></template><a-button type="primary" :loading="busy" :disabled="!options.length||(kind!=='roster'&&(!dateFrom||!dateTo))" @click="create">生成私有文件</a-button></a-space><p v-if="kind==='roster'">人员表使用今日的人员与班次配置。</p><a-alert v-if="error" type="warning" :message="error" show-icon/><section v-if="result" class="export-result"><p>{{result.scope}} · 实际范围 {{result.date_from}} 至 {{result.date_to}}</p><a-alert v-if="!result.coverage.complete" type="warning" show-icon message="部分历史归属待核对。文件仅含可证记录，范围说明已随文件保存。"/><a :href="result.download_url" target="_blank" rel="noopener noreferrer">下载已生成文件</a><p>若角色或范围已变化，服务器会拒绝下载；可在核对授权后重新生成。</p></section></section></section></template>
<style scoped>.exports{display:grid;gap:20px}.glass-hero,.section-panel{padding:24px}.ant-alert,.export-result{margin-top:20px}</style>
