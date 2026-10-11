<template>
  <a-drawer :open="open" title="连接个人助手" width="min(620px, 100vw)" root-class-name="kb-drawer kb-scope" :destroy-on-close="true" @close="close">
    <p class="kb-muted">安装配置与使用规则后，在你自己的助手中核对一次来源。</p>
    <a-alert v-if="error" type="error" show-icon :message="error"/><a-skeleton v-if="loading&&!info" active/>
    <template v-if="info">
      <section class="kb-wizard-body">
        <h2>1 · 选择并安装本人助手</h2>
        <button v-for="name in ['OpenClaw','Hermes'] as const" :key="name" :class="['kb-assistant-option',{selected:client===name}]" :disabled="busy" @click="client=name"><strong>{{name}}</strong><span>配置与不含凭据的使用规则一起安装</span><CheckCircleOutlined v-if="client===name"/></button>
        <label for="mcp-label">连接名称</label><a-input id="mcp-label" v-model:value="label" :maxlength="80" :disabled="busy"/>
        <a-button type="primary" :loading="busy" :disabled="busy||!label.trim()" @click="install"><DownloadOutlined/>安装助手配置与使用规则</a-button>
        <p class="kb-muted">下载本地安装文件后，运行下方命令。它不访问模型；凭据仅写入本人客户端配置，使用规则不含 Token。</p>
        <div v-if="installerName" class="kb-prompt-preview">{{installCommand}}</div><a-button v-if="installerName" @click="copy(installCommand,'已复制不含凭据的本地安装命令。')"><CopyOutlined/>复制安装命令</a-button>
        <p class="kb-muted">{{client}} {{info.client_versions[client]}} · {{info.deployment==='LOCAL_UAT'?'本机地址只适用于这台电脑。':'使用受控 HTTPS 地址。'}} 安装文件成功导入后自动删除；请勿将文件或配置发给 LLM。</p>
        <a-collapse ghost><a-collapse-panel key="rules" header="查看使用规则（不含凭据）"><p>{{knowledgeUsageRules}}</p></a-collapse-panel></a-collapse>
        <h2>2 · 服务自检</h2>
        <p>仅检查本人认证和四个受控工具，不检索、不调用生成模型。通过后只表示“服务已就绪”。</p>
        <a-button :loading="busy" :disabled="busy||!credential" @click="detect">检查服务是否就绪</a-button><a-tag :color="checks.tools==='passed'?'cyan':'default'">{{checks.tools==='passed'?'服务已就绪':'服务待检查'}}</a-tag>
        <a-alert v-if="checks.error" type="warning" show-icon :message="checks.error"/>
        <h2>3 · 在真实客户端核验来源</h2>
        <label for="mcp-test-query">已共享资料的问题</label><a-input id="mcp-test-query" v-model:value="testQuery" :disabled="busy" :maxlength="280"/>
        <a-button @click="copyTest"><CopyOutlined/>复制无凭据测试问题</a-button><a-button :disabled="busy" :loading="loading" @click="refresh">读取客户端收据</a-button>
        <p class="kb-muted">导入不会自动测试。请在 {{client}} 明确运行一次 search_knowledge 和 get_evidence，再读取收据。挑战在创建后30分钟有效。</p>
        <p class="kb-muted">客户端收据证明绑定凭据和挑战完成了工具调用，不是应用本体的密码学认证。退出网页不撤销独立 Token；有效期 {{info.ttl_days}} 天，可立即撤销。</p>
      </section>
      <p v-if="notice" class="kb-notice" role="status">{{notice}}</p>
      <section class="connection-list"><h2>本人的连接与实测状态</h2><a-empty v-if="!info.items.length" description="还没有创建个人连接"/>
        <article v-for="item in info.items" :key="item.id"><div><strong>{{item.label}}</strong><p>{{item.client}} · {{stage(item)}}</p><small>到期 {{date(item.expires_at)}}</small><details v-if="item.client_receipt"><summary>查看本次客户端收据</summary><p>连接 {{item.id}}<br>挑战 {{item.client_receipt.challenge_id}}<br>认证 {{item.client_receipt.authenticated_at||'未完成'}}<br>工具 {{item.client_receipt.tools_at||'未发现'}}<br>来源核验 {{item.client_receipt.knowledge_used_at||'未完成'}}<br>检索请求 {{item.client_receipt.search_request_id||'未完成'}}<br>来源请求 {{item.client_receipt.evidence_request_id||'未完成'}}</p></details></div><a-button danger :disabled="busy||item.revoked" @click="revoke(item.id)">撤销连接</a-button></article>
      </section><div class="kb-wizard-footer"><a-button type="primary" @click="close">关闭</a-button></div>
    </template>
  </a-drawer>
</template>
<script setup lang="ts">
import { ref, watch, computed, onBeforeUnmount } from 'vue'
import { CopyOutlined, DownloadOutlined, CheckCircleOutlined } from '@ant-design/icons-vue'
import { getKnowledgeConnections,createKnowledgeConnection,revokeKnowledgeConnection,DomainApiError } from '@/services/p1Api'
import type { ConnectionInfo,PersonalConnection } from '@/services/p1Api'
import { checkKnowledgeConnection,type ConnectionChecks } from '@/services/knowledgeConnectionCheck'
import { localInstaller,knowledgeUsageRules } from '@/services/knowledgeInstaller'
const props=defineProps<{open:boolean;subject:string}>(),emit=defineEmits<{close:[]}>()
const info=ref<ConnectionInfo|null>(null),credential=ref<Awaited<ReturnType<typeof createKnowledgeConnection>>|null>(null)
const client=ref<'OpenClaw'|'Hermes'>('OpenClaw'),label=ref('我的个人助手'),loading=ref(false),busy=ref(false),error=ref(''),notice=ref(''),testQuery=ref('美罗培南粗品F13的包装容器应符合哪些要求？'),installerName=ref('')
const installCommand=computed(()=>installerName.value?'python3 "$HOME/Downloads/'+installerName.value+'"':'')
const emptyChecks=():ConnectionChecks=>({authentication:'pending',tools:'pending',search:'pending',evidence:'pending',error:''})
const checks=ref(emptyChecks())
let generation=0,refreshGeneration=0,controller:AbortController|null=null
function date(value:string){return new Date(value).toLocaleString()}
function stage(item:PersonalConnection){return item.revoked?'已撤销':item.expired?'已过期':({CLIENT_NOT_VERIFIED:'客户端未验证',SERVER_READY:'服务已就绪 · 客户端未验证',CLIENT_CONNECTED:'客户端完成认证与工具发现 · 来源待核验',KNOWLEDGE_USED:'客户端已用知识 · 来源已核验'}[item.verification_state||'CLIENT_NOT_VERIFIED'])}
function reset(){generation++;controller?.abort();controller=null;credential.value=null;info.value=null;error.value='';notice.value='';busy.value=false;loading.value=false;checks.value=emptyChecks();installerName.value=''}
function close(){reset();emit('close')}
function fail(e:unknown){error.value=e instanceof DomainApiError?e.message:e instanceof Error?e.message:'连接操作暂时不可用。'}
async function refresh(){const current=generation,seq=++refreshGeneration;loading.value=true;error.value='';try{const value=await getKnowledgeConnections();if(current===generation&&seq===refreshGeneration)info.value=value}catch(e){if(current===generation&&seq===refreshGeneration)fail(e)}finally{if(current===generation&&seq===refreshGeneration)loading.value=false}}
async function install(){if(busy.value||!info.value)return;const current=++generation;busy.value=true;error.value='';credential.value=null;checks.value=emptyChecks();try{const value=await createKnowledgeConnection(label.value.trim(),client.value);if(current!==generation)return;credential.value=value;const source=localInstaller(client.value,info.value.endpoint,value.token,value.id,value.challenge_id||'');installerName.value='hbos-assistant-'+value.id.slice(0,8)+'.py';const url=URL.createObjectURL(new Blob([source],{type:'text/x-python'})),link=document.createElement('a');link.href=url;link.download=installerName.value;link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);notice.value='本人连接已创建并下载本地安装文件。客户端仍未验证。';await refresh()}catch(e){if(current===generation)fail(e)}finally{if(current===generation)busy.value=false}}
async function revoke(id:string){if(busy.value)return;const current=++generation;controller?.abort();busy.value=true;error.value='';try{await revokeKnowledgeConnection(id);if(current===generation){if(credential.value?.id===id){credential.value=null;checks.value=emptyChecks();installerName.value=''}notice.value='连接已撤销，旧凭据不能继续访问。';await refresh()}}catch(e){if(current===generation)fail(e)}finally{if(current===generation)busy.value=false}}
async function copy(value:string,success:string){const current=generation;try{await navigator.clipboard.writeText(value);if(current===generation)notice.value=success}catch{if(current===generation)notice.value='复制受浏览器限制，请手动选择并复制。'}}
function copyTest(){void copy('请明确调用 HBOS search_knowledge 搜索“'+testQuery.value+'”，然后调用 get_evidence 核对本次检索返回的来源，列出真实资料标题和版本状态。不要调用 ask_knowledge，不要将配置或 Token 放入聊天。','已复制无凭据测试问题。')}
async function detect(){if(busy.value||!credential.value||!info.value)return;const current=generation;controller=new AbortController();busy.value=true;checks.value=emptyChecks();try{await checkKnowledgeConnection(info.value,credential.value.token,'',controller.signal,value=>{if(current===generation)checks.value=value});if(current===generation)await refresh()}catch(e){if(current===generation)fail(e)}finally{if(current===generation)busy.value=false}}
watch(()=>props.open,value=>{if(value&&props.subject)void refresh();else reset()},{immediate:true})
watch(()=>props.subject,()=>{reset();label.value='我的个人助手';if(props.open&&props.subject)void refresh()},{flush:'sync'})
watch(client,()=>{generation++;controller?.abort();credential.value=null;checks.value=emptyChecks();notice.value='';busy.value=false;installerName.value=''})
onBeforeUnmount(reset)
</script>
<style scoped>
.kb-wizard-body h2{margin:24px 0 16px}.kb-wizard-body>button{margin:12px 12px 12px 0}.connection-list{margin-top:24px}.connection-list article{display:flex;justify-content:space-between;align-items:center;gap:16px;padding:20px 0;border-bottom:1px solid var(--hbos-border-default)}.connection-list strong{font-size:16px;overflow-wrap:anywhere}.connection-list p{margin:8px 0;font-size:14px;overflow-wrap:anywhere}.connection-list small{font-size:12px;color:var(--hbos-text-muted)}
</style>
