<script setup lang="ts">
import { onMounted,ref } from 'vue'
import { listAuditEvents } from '@/services/iamAudit'
import { iamMessage } from '@/services/iamAccess'
import type { AuditEvent } from '@/types/iam'
const rows=ref<AuditEvent[]>([]),page=ref(1),total=ref(0),loading=ref(true),error=ref('')
const columns=[{title:'时间',dataIndex:'occurred_at',width:180},{title:'操作者',dataIndex:'actor',width:180},{title:'对象',dataIndex:'subject_name',width:180},{title:'操作',dataIndex:'operation',width:180},{title:'结果',dataIndex:'result',width:100},{title:'说明',dataIndex:'reason'}]
async function load(){loading.value=true;error.value='';try{const result=await listAuditEvents(page.value);rows.value=result.items;total.value=result.total}catch(e){rows.value=[];error.value=iamMessage(e)}finally{loading.value=false}}
onMounted(load)
</script>
<template><section><div class="iam-heading"><div><h1>变更审计</h1><p>只读脱敏记录，审计读取由独立能力及管理范围控制。</p></div></div><section class="iam-panel"><a-alert v-if="error" :message="error" type="warning"/><a-table :columns="columns" :data-source="rows" row-key="name" :loading="loading" :scroll="{x:1000}" :pagination="{current:page,pageSize:20,total,showSizeChanger:false,onChange:(value:number)=>{page=value;load()}}"/><a-button v-if="error" @click="load">重试读取</a-button></section></section></template>
