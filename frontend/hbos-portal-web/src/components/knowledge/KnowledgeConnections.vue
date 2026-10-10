<template>
  <a-drawer :open="open" title="连接个人助手" width="min(620px, 100vw)" root-class-name="kb-drawer kb-scope" :destroy-on-close="true" @close="close">
    <p class="kb-muted">让你的助手在回答公司问题时，先核对知识库。</p>
    <a-alert v-if="error" type="error" show-icon :message="error"/><a-skeleton v-if="loading && !info" active/>
    <template v-if="info">
      <div class="kb-wizard-progress"><span>{{stepNames[step]}}</span><span>{{step+1}} / 6</span></div><a-progress :percent="Math.round((step+1)/6*100)" :show-info="false" stroke-color="#159b89"/>
      <section class="kb-wizard-body">
        <template v-if="step===0"><h2>你使用哪个助手？</h2><button v-for="name in ['OpenClaw','Hermes']" :key="name" :class="['kb-assistant-option',{selected:client===name}]" @click="client=name"><strong>{{name}}</strong><span>按已验证版本提供连接配置与操作步骤</span><CheckCircleOutlined v-if="client===name"/></button><p class="kb-muted">{{info.deployment==='LOCAL_UAT'?'本机地址仅供这台电脑使用。团队使用需受控 HTTPS 地址。':'使用部署者提供的受控 HTTPS 地址。'}}</p></template>
        <template v-else-if="step===1"><h2>创建绑定本人的连接</h2><p>连接只查阅你的授权资料，有效期 {{info.ttl_days}} 天，可随时撤销。</p><form @submit.prevent="create"><label class="sr-only" for="mcp-label">连接名称</label><a-input id="mcp-label" v-model:value="label" :maxlength="80" :disabled="busy" placeholder="我的个人助手"/><a-button type="primary" html-type="submit" :loading="busy" :disabled="busy||!label.trim()"><PlusOutlined/>{{credential?'重新创建连接':'创建本人连接'}}</a-button></form><p v-if="credential" class="kb-notice">本人连接已创建。凭据仅在本次向导中提供，关闭后不会再次显示。</p></template>
        <template v-else-if="step===2"><h2>将配置加入 {{client}}</h2><ol v-if="client==='OpenClaw'"><li>打开终端，运行下方配置命令。</li><li>保存后重新加载助手的 MCP 连接。</li></ol><ol v-else><li>打开本人 Hermes 的 config.yaml。</li><li>将连接条目加入 mcp_servers，重启本人助手。</li></ol><a-button type="primary" :disabled="!credential" @click="copyConfig"><CopyOutlined/>复制连接配置</a-button><a-collapse ghost><a-collapse-panel key="config" header="高级：查看本次配置"><textarea id="mcp-template" readonly :value="template" aria-label="本人 MCP 连接配置"/><p class="kb-muted">只在本人的客户端保存，不转发凭据。</p></a-collapse-panel></a-collapse><p class="kb-muted">已核验 {{client}} {{info.client_versions[client]}}。{{client==='OpenClaw'?'配置为 streamable-http 传输。':'本配置适配已安装的 Hermes。'}}</p></template>
        <template v-else-if="step===3"><h2>把这段话发给你的助手</h2><p>以后询问公司制度时，助手会先查资料，并给出来源。</p><div class="kb-prompt-preview">{{usagePrompt}}</div><a-button type="primary" @click="copyPrompt"><CopyOutlined/>复制中文使用提示词</a-button></template>
        <template v-else-if="step===4"><h2>连接后，做一次真实查询</h2><label for="mcp-test-query">测试问题</label><a-input id="mcp-test-query" v-model:value="testQuery" :maxlength="500" :disabled="busy" placeholder="输入已共享资料的标题或关键词"/><div class="kb-connection-check" v-for="check in checkRows" :key="check.key"><span>{{check.label}}</span><a-tag :color="checks[check.key]==='passed'?'green':checks[check.key]==='failed'?'red':'default'">{{checkNames[checks[check.key]]}}</a-tag></div><p class="kb-muted">检测会实际调用 MCP 检索与来源。助手配置是否已加载，还需在 {{client}} 发送测试问题。</p><a-button :loading="busy" :disabled="busy||!credential||!testQuery.trim()" @click="detect">检测连接</a-button><a-button @click="copyTest">复制助手测试问题</a-button><a-alert v-if="checks.error" type="warning" show-icon :message="checks.error"/></template>
        <template v-else><h2>{{checks.evidence==='passed'?'检索与来源检查通过':'连接配置已准备'}}</h2><p>{{checks.evidence==='passed'?'本人身份、四个工具、实际搜索和来源已经分别核验。请在助手里完成一次对话。':'配置完成后仍需实际检索与来源核验。配置已创建不代表连接成功。'}}</p><div class="kb-connection-summary"><strong>{{client}} · {{label}}</strong><a-tag :color="checks.evidence==='passed'?'green':'default'">{{checks.evidence==='passed'?'查询已验证':'查询待验证'}}</a-tag></div><a-button v-if="credential" danger :disabled="busy" @click="revoke(credential.id)">撤销本次连接</a-button></template>
      </section>
      <p v-if="notice" class="kb-notice" role="status">{{notice}}</p>
      <div class="kb-wizard-footer"><a-button v-if="step>0" :disabled="busy" @click="step--">上一步</a-button><a-button v-if="step<5" type="primary" :disabled="busy||(step===1&&!credential)" @click="step++">下一步<ArrowRightOutlined/></a-button><a-button v-else type="primary" @click="close">完成</a-button></div>
      <a-collapse ghost class="connection-list"><a-collapse-panel key="items" header="管理本人的连接"><a-button :loading="loading" :disabled="busy" @click="refresh">刷新连接状态</a-button><a-empty v-if="!info.items.length" description="还没有创建个人连接"/><article v-for="item in info.items" :key="item.id"><div><strong>{{item.label}}</strong><p>{{item.client}} · {{stage(item)}}</p><small>到期 {{date(item.expires_at)}}</small></div><a-button danger :disabled="busy||item.revoked" @click="revoke(item.id)">撤销连接</a-button></article></a-collapse-panel></a-collapse>
    </template>
  </a-drawer>
</template>
<script setup lang="ts">
import { computed, ref, watch, onBeforeUnmount } from 'vue'
import { CopyOutlined, PlusOutlined, ArrowRightOutlined, CheckCircleOutlined } from '@ant-design/icons-vue'
import { getKnowledgeConnections, createKnowledgeConnection, revokeKnowledgeConnection, DomainApiError } from '@/services/p1Api'
import type { ConnectionInfo, PersonalConnection } from '@/services/p1Api'
import { checkKnowledgeConnection, type ConnectionChecks } from '@/services/knowledgeConnectionCheck'
const props=defineProps<{open:boolean;subject:string}>(),emit=defineEmits<{close:[]}>()
const info=ref<ConnectionInfo|null>(null), credential=ref<{id:string;token:string;expires_at:string}|null>(null)
const step=ref(0),client=ref('OpenClaw'),label=ref('我的个人助手'),loading=ref(false),busy=ref(false),error=ref(''),notice=ref(''),testQuery=ref('培养箱操作规程')
const stepNames=['选择助手','创建本人连接','复制配置','复制使用提示词','测试连接与查询','完成']
const usagePrompt='以后涉及新乡海滨药业公司制度、SOP、生产、质量、安全或人事问题时，请优先调用 HBOS MCP 的 list_knowledge_spaces、search_knowledge；必要时调用 get_evidence 核对来源，再用你自己的模型组织回答并列出标题、版本状态与依据。资料不足时明确说明，不得凭记忆编造公司规定；不索取原始文件或调用 get_source。只有我明确要求由 HBOS 生成答案时才调用 ask_knowledge。'
const checkRows=[{key:'authentication' as const,label:'本人身份认证'},{key:'tools' as const,label:'四个受控工具'},{key:'search' as const,label:'实际搜索'},{key:'evidence' as const,label:'来源展开'}]
const checkNames={pending:'待检查',passed:'已通过',failed:'未通过'}
const emptyChecks=():ConnectionChecks=>({authentication:'pending',tools:'pending',search:'pending',evidence:'pending',error:''})
const checks=ref<ConnectionChecks>(emptyChecks())
let generation=0,refreshGeneration=0,controller:AbortController|null=null
const config=computed(()=>!info.value||!credential.value?'':JSON.stringify(client.value==='OpenClaw'?{transport:'streamable-http',url:info.value.endpoint,headers:{Authorization:'Bearer '+credential.value.token}}:{mcp_servers:{hbos:{url:info.value.endpoint,headers:{Authorization:'Bearer '+credential.value.token},timeout:90}}},null,2))
const template=computed(()=>client.value==='OpenClaw'&&config.value ? "openclaw mcp set hbos '"+config.value+"'" : config.value)
function date(s:string){return new Date(s).toLocaleString()}
function stage(item:PersonalConnection){return item.revoked?'已撤销':item.expired?'已过期':({Configured:'已配置，查询待验证',Authenticated:'已认证','Tools Discovered':'已发现工具','Knowledge Used':'已查询知识'}[item.stage]||'待核验')}
function reset(){generation++;controller?.abort();controller=null;credential.value=null;info.value=null;error.value='';notice.value='';busy.value=false;loading.value=false;checks.value=emptyChecks();step.value=0}
function close(){reset();emit('close')}
function fail(e:unknown){error.value=e instanceof DomainApiError?e.message:'连接操作暂时不可用。'}
async function refresh(){const current=generation,seq=++refreshGeneration;loading.value=true;error.value='';try{const result=await getKnowledgeConnections();if(current===generation&&seq===refreshGeneration)info.value=result}catch(e){if(current===generation&&seq===refreshGeneration)fail(e)}finally{if(current===generation&&seq===refreshGeneration)loading.value=false}}
async function create(){if(busy.value)return;const current=++generation;busy.value=true;credential.value=null;checks.value=emptyChecks();error.value='';notice.value='';try{const result=await createKnowledgeConnection(label.value.trim(),client.value);if(current===generation){credential.value=result;await refresh()}}catch(e){if(current===generation)fail(e)}finally{if(current===generation)busy.value=false}}
async function revoke(id:string){if(busy.value)return;const current=++generation;controller?.abort();busy.value=true;error.value='';try{await revokeKnowledgeConnection(id);if(current===generation){if(credential.value?.id===id){credential.value=null;checks.value=emptyChecks()}notice.value='连接已撤销，旧凭据不能继续访问。';await refresh()}}catch(e){if(current===generation)fail(e)}finally{if(current===generation)busy.value=false}}
async function copy(value:string,success:string){const current=generation;try{await navigator.clipboard.writeText(value);if(current===generation)notice.value=success}catch{if(current===generation)notice.value='复制受浏览器限制，请手动选择并复制。'}}
function copyConfig(){if(credential.value)void copy(template.value,'已复制本人配置，请保存在所选助手。')}
function copyPrompt(){void copy(usagePrompt,'已复制中文提示词，其中不含连接凭据或公司资料。')}
function copyTest(){void copy('请调用 HBOS search_knowledge 搜索“'+testQuery.value+'”，再调用 get_evidence 核对返回的来源。请列出资料标题及版本状态；资料不足时说明。','已复制助手测试问题。')}
async function detect(){if(busy.value||!credential.value||!info.value)return;const current=generation;controller=new AbortController();busy.value=true;checks.value=emptyChecks();try{await checkKnowledgeConnection(info.value,credential.value.token,testQuery.value,controller.signal,value=>{if(current===generation)checks.value=value});if(current===generation)await refresh()}catch(e){if(current===generation)error.value=e instanceof Error?e.message:'检测未完成。'}finally{if(current===generation)busy.value=false}}
watch(()=>props.open,value=>{if(value&&props.subject){step.value=0;void refresh()}else reset()},{immediate:true})
watch(()=>props.subject,()=>{reset();label.value='我的个人助手';if(props.open&&props.subject)void refresh()},{flush:'sync'})
watch(client,()=>{generation++;controller?.abort();credential.value=null;checks.value=emptyChecks();notice.value='';busy.value=false})
onBeforeUnmount(reset)
</script>
<style scoped>
.kb-wizard-body form{display:grid;gap:20px}.kb-wizard-body textarea{width:100%;min-height:240px;border:1px solid var(--hbos-border-default);border-radius:12px;padding:16px;font-size:14px;line-height:24px;white-space:pre-wrap;overflow-wrap:anywhere}.connection-list{margin-top:24px}.connection-list article{display:flex;justify-content:space-between;align-items:center;gap:16px;padding:20px 0;border-bottom:1px solid var(--hbos-border-default)}.connection-list strong{font-size:16px;overflow-wrap:anywhere}.connection-list p{margin:8px 0;font-size:14px}.connection-list small{font-size:12px;color:var(--hbos-text-muted)}
</style>
