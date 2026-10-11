<template>
  <a-drawer :open="open" title="连接个人助手" width="min(620px, 100vw)" root-class-name="kb-drawer kb-scope" :destroy-on-close="true" @close="close">
    <p class="kb-muted">安装后，在自己的助手中直接正常提问即可。</p>
    <a-alert v-if="error" type="error" show-icon :message="error"/><a-skeleton v-if="loading&&!info" active/>
    <template v-if="info">
      <section class="kb-wizard-body">
        <button v-for="name in ['OpenClaw','Hermes'] as const" :key="name" :class="['kb-assistant-option',{selected:client===name}]" :disabled="busy" @click="client=name"><strong>{{name}}</strong><span>一次安装，连接公司知识库</span><CheckCircleOutlined v-if="client===name"/></button>
        <a-button type="primary" :loading="busy" :disabled="busy" @click="install"><CopyOutlined/>复制安装指令</a-button>
        <p class="kb-muted">同时下载本人私密安装文件。在终端运行这条指令，确认后写入配置与使用规则；原配置会备份。</p>
        <div v-if="installerName" class="kb-prompt-preview" tabindex="0" aria-label="本机安装指令">{{installCommand}}</div>
        <p v-if="info.deployment==='LOCAL_UAT'" class="kb-muted">当前为本机验收入口，仅这台电脑可用。公司服务器上线后使用统一 HTTPS 地址。</p>
        <p v-if="notice" class="kb-notice" role="status">{{notice}}</p>
      </section>
      <section class="connection-list" aria-label="最近使用状态">
        <h2>最近使用状态</h2>
        <article v-if="currentConnection"><div><strong>{{currentConnection.client}}</strong><p>{{stage(currentConnection)}}</p></div></article>
        <p v-else class="kb-muted">未安装 / 未创建连接</p>
        <a-button type="text" :loading="loading" :disabled="busy" @click="refresh">查看连接状态</a-button>
      </section>
      <a-collapse ghost>
        <a-collapse-panel key="management" header="连接管理">
          <p class="kb-muted">连接仅属于本人，有效期 {{info.ttl_days}} 天。请勿转给他人；需要停用时撤销即可。</p>
          <div v-if="currentConnection" class="connection-management"><span>当前连接 · 到期 {{date(currentConnection.expires_at)}}</span><a-popconfirm title="撤销后此助手无法继续访问公司知识，确认撤销？" ok-text="撤销" cancel-text="取消" @confirm="revoke(currentConnection!.id)"><a-button danger :disabled="busy">撤销连接</a-button></a-popconfirm></div>
          <details v-if="history.length"><summary>历史连接（{{history.length}}）</summary><article v-for="item in history" :key="item.id" class="connection-management"><div><strong>{{item.label}}</strong><p>{{item.client}} · {{stage(item)}}</p></div><a-popconfirm v-if="!item.revoked&&!item.expired" title="确认撤销此历史连接？" ok-text="撤销" cancel-text="取消" @confirm="revoke(item.id)"><a-button danger :disabled="busy">撤销</a-button></a-popconfirm></article></details>
          <details><summary>知识使用规则</summary><p class="kb-muted">{{knowledgeUsageRules}}</p></details>
        </a-collapse-panel>
      </a-collapse>
      <div class="kb-wizard-footer"><a-button type="primary" @click="close">完成</a-button></div>
    </template>
  </a-drawer>
</template>
<script setup lang="ts">
import { ref, watch, computed, onBeforeUnmount } from 'vue'
import { CopyOutlined, CheckCircleOutlined } from '@ant-design/icons-vue'
import { getKnowledgeConnections,createKnowledgeConnection,revokeKnowledgeConnection,DomainApiError } from '@/services/p1Api'
import type { ConnectionInfo,PersonalConnection } from '@/services/p1Api'
import { localInstaller,knowledgeUsageRules } from '@/services/knowledgeInstaller'
const props=defineProps<{open:boolean;subject:string}>(),emit=defineEmits<{close:[]}>()
const info=ref<ConnectionInfo|null>(null),client=ref<'OpenClaw'|'Hermes'>('OpenClaw')
const loading=ref(false),busy=ref(false),error=ref(''),notice=ref(''),installerName=ref(''),createdId=ref('')
const installCommand=computed(()=>installerName.value?'python3 "$HOME/Downloads/'+installerName.value+'"':'')
const currentConnection=computed(()=>info.value?.items.find(i=>i.id===createdId.value&&!i.revoked&&!i.expired)||info.value?.items.find(i=>i.client===client.value&&!i.revoked&&!i.expired&&!i.is_test))
const history=computed(()=>info.value?.items.filter(i=>i.id!==currentConnection.value?.id)||[])
let generation=0,refreshGeneration=0
function date(value:string){return new Date(value).toLocaleString()}
function stage(item:PersonalConnection){return item.revoked?'已撤销':item.expired?'已过期':item.knowledge_used_at?'最近通过此连接查阅知识：'+date(item.knowledge_used_at):'已准备连接（尚无实际使用记录）'}
function reset(){generation++;info.value=null;error.value='';notice.value='';busy.value=false;loading.value=false;installerName.value='';createdId.value=''}
function close(){reset();emit('close')}
function fail(e:unknown){error.value=e instanceof DomainApiError?e.message:e instanceof Error?e.message:'连接操作暂时不可用。'}
async function refresh(){const current=generation,seq=++refreshGeneration;loading.value=true;error.value='';try{const value=await getKnowledgeConnections();if(current===generation&&seq===refreshGeneration){info.value=value;if(createdId.value&&value.items.some(i=>i.id===createdId.value&&i.knowledge_used_at)){installerName.value='';createdId.value=''}}}catch(e){if(current===generation&&seq===refreshGeneration)fail(e)}finally{if(current===generation&&seq===refreshGeneration)loading.value=false}}
async function copyCommand(){const current=generation;try{await navigator.clipboard.writeText(installCommand.value);if(current===generation)notice.value='安装指令已复制。运行后直接在自己的助手中正常提问即可。'}catch{if(current===generation)notice.value='安装文件已下载。请选择上方指令复制，在终端运行即可。'}}
async function install(){
  if(busy.value||!info.value)return
  if(installerName.value){await copyCommand();return}
  const current=++generation,selected=client.value,endpoint=info.value.endpoint
  busy.value=true;error.value=''
  try{
    const value=await createKnowledgeConnection('我的'+selected,selected)
    if(current!==generation)return
    const source=localInstaller(selected,endpoint,value.token,value.id)
    installerName.value='hbos-assistant-'+value.id.slice(0,8)+'.py';createdId.value=value.id
    const url=URL.createObjectURL(new Blob([source],{type:'text/x-python'})),link=document.createElement('a')
    link.href=url;link.download=installerName.value;link.click();setTimeout(()=>URL.revokeObjectURL(url),1000)
    await copyCommand();await refresh()
  }catch(e){if(current===generation)fail(e)}finally{if(current===generation)busy.value=false}
}
async function revoke(id:string){if(busy.value)return;const current=++generation;busy.value=true;error.value='';try{await revokeKnowledgeConnection(id);if(current===generation){if(createdId.value===id){createdId.value='';installerName.value=''}notice.value='连接已撤销。重新安装请复制一条新的安装指令。';await refresh()}}catch(e){if(current===generation)fail(e)}finally{if(current===generation)busy.value=false}}
watch(()=>props.open,value=>{if(value&&props.subject)void refresh();else reset()},{immediate:true})
watch(()=>props.subject,()=>{reset();if(props.open&&props.subject)void refresh()},{flush:'sync'})
watch(client,()=>{generation++;installerName.value='';createdId.value='';notice.value=''})
onBeforeUnmount(reset)
</script>
<style scoped>
.kb-wizard-body>button{margin:12px 12px 12px 0}.connection-list{margin-top:24px}.connection-list h2{font-size:20px}.connection-list article{padding:12px 0}.connection-list p{margin:8px 0}.connection-management{display:flex;justify-content:space-between;align-items:center;gap:16px;padding:16px 0;border-bottom:1px solid var(--hbos-border-default);font-size:14px}.connection-management>div,.connection-management>span{min-width:0;overflow-wrap:anywhere}details{margin:16px 0}summary{cursor:pointer;font-size:14px}.kb-prompt-preview{overflow-wrap:anywhere}
</style>
