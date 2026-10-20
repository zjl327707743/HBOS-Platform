<script setup lang="ts">
import { ref, watch } from 'vue'
import { message } from 'ant-design-vue'
import { previewWork, workAction, type WorkDraft } from '@/services/iamWork'
import { iamMessage } from '@/services/iamAccess'
import type { WorkApp, WorkPreview, WorkTarget } from '@/types/iam'
const props=defineProps<{app:WorkApp;target:WorkTarget}>()
const emit=defineEmits<{saved:[]}>()
const busy=ref(false),open=ref(false),error=ref(''),preview=ref<WorkPreview|null>(null),draft=ref<WorkDraft|null>(null),reenable=ref(false)
let generation=0
watch(()=>[props.target.subject_name,props.app.app_id],()=>{generation++;open.value=false;preview.value=null;draft.value=null;busy.value=false;error.value=''})
async function prepare(){
 if(busy.value)return
 const run=++generation
 busy.value=true;error.value='';preview.value=null;open.value=true;reenable.value=Boolean(props.app.suspended)
 draft.value={target:{...props.target},changes:[],expected_version:props.app.version,context_revision:props.app.context_revision}
 try{const result=await previewWork(draft.value,reenable.value?'reenable':'suspend');if(run===generation)preview.value=result}catch(e){if(run===generation)error.value=iamMessage(e)}finally{if(run===generation)busy.value=false}
}
async function commit(){
 if(busy.value||!preview.value||!draft.value)return
 const run=generation,confirmed=preview.value,input=draft.value
 busy.value=true;error.value=''
 try{await workAction(reenable.value?'reenable_app':'suspend_app',input.target,confirmed.version,confirmed.context_revision,crypto.randomUUID());if(run!==generation)return;open.value=false;message.success('应用访问状态已更新。');emit('saved')}catch(e){if(run===generation){error.value=iamMessage(e);preview.value=null}}finally{if(run===generation)busy.value=false}
}
function cancel(){if(!busy.value){generation++;open.value=false;preview.value=null;draft.value=null}}
</script>
<template>
 <a-dropdown :trigger="['click']"><a-button :disabled="busy" :aria-label="`${app.title}的更多操作`">更多</a-button><template #overlay><a-menu><a-menu-item key="access" @click="prepare">{{app.suspended?'解除临时禁用':`临时禁用${app.app_id==='attendance'?'考勤':app.title}`}}</a-menu-item></a-menu></template></a-dropdown>
 <a-modal :open="open" :title="reenable?'解除临时禁用':`临时禁用${app.app_id==='attendance'?'考勤':app.title}`" :confirm-loading="busy" :ok-button-props="{disabled:!preview || Boolean(error)}" :cancel-button-props="{disabled:busy}" :closable="!busy" :mask-closable="false" :ok-text="reenable?'确认解除临时禁用':'确认临时禁用'" cancel-text="取消" @ok="commit" @cancel="cancel">
  <p>{{reenable?'解除后重新核对账号状态、当前权限、其他限制和期限；不会返还已过期权限。':'仅停止该员工访问这个应用，保留现有权限和历史数据。'}}不会停止考勤机采集，也不会停用整个账号。</p>
  <a-alert v-if="error" :message="error" type="warning" show-icon/>
  <p v-else-if="!preview" role="status">正在核对实际结果…</p>
  <section v-if="preview" aria-live="polite"><h3>确认后的实际结果</h3><p>{{preview.after.suspended?'已临时禁用':preview.after.summary}}</p><p v-for="row in preview.after.operations.filter(item=>!item.important)" :key="row.operation_id">{{row.label}}：{{row.enabled?'按当前有效范围访问':row.reason || '当前不可用'}}</p><p>原权限来源保持，其他应用不受影响。</p></section>
 </a-modal>
</template>
