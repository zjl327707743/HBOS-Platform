<template>
  <a-drawer :open="open" title="连接个人助手" width="min(620px, 100vw)" root-class-name="kb-drawer kb-scope" :destroy-on-close="true" @close="close">
    <ol class="kb-connect-steps" aria-label="连接步骤">
      <li v-for="item in steps" :key="item.step" :class="{active:step===item.step,done:step>item.step}"><span class="kb-step-no">{{ step > item.step ? '✓' : item.step }}</span>{{ item.title }}</li>
    </ol>
    <p class="kb-muted">按四步完成连接；可在助手设置中直接配置，不必运行 Python。</p>
    <a-alert v-if="error" type="error" show-icon :message="error"/><a-skeleton v-if="loading&&!info" active/>
    <template v-if="info">
      <!-- 步骤1 选择助手 -->
      <section v-show="step===1" class="kb-wizard-body">
        <button v-for="name in ['OpenClaw','Hermes'] as const" :key="name" :class="['kb-assistant-option',{selected:client===name}]" :disabled="busy" @click="client=name"><strong>{{name}}</strong><span>一次安装，连接公司知识库</span><small class="kb-muted">支持版本：{{clientVersion(name)}}</small><CheckCircleOutlined v-if="client===name"/></button>
        <p v-if="info.deployment==='LOCAL_UAT'" class="kb-muted">当前为本机验收入口，仅这台电脑可用。公司服务器上线后使用统一 HTTPS 地址。</p>
        <div class="kb-wizard-footer"><a-button type="primary" data-step-continue @click="step=2">下一步：连接知识库</a-button></div>
      </section>
      <!-- 步骤2 连接知识库：复制说明+无密钥提示词，Token 只走私密导入 -->
      <section v-show="step===2" class="kb-wizard-body">
        <p class="kb-wizard-body-copy">先在助手的 MCP 设置中添加 HTTP 连接，再复制下方无密钥提示词到助手规则。令牌只填写到连接的私密认证设置，绝不粘贴到对话中。若客户端没有设置页面，可使用下方高级安装选项。</p>
        <div class="kb-native-connection">
          <a-button type="primary" data-create-connection :loading="busy" :disabled="busy || !!createdSecret" @click="prepareConnection">{{createdSecret?'本人连接已创建':'创建本人连接'}}</a-button>
          <p>在 {{client}} 的 MCP 设置中添加服务器 <strong>hbos-knowledge</strong>，传输方式选择 HTTP（Streamable HTTP）。</p>
          <label>服务器地址<input :value="info.endpoint" readonly aria-label="MCP 服务器地址"></label>
          <button type="button" data-copy-endpoint :disabled="busy" @click="copyEndpoint">复制服务器地址</button>
          <template v-if="createdSecret">
            <label>认证 Header：Authorization<input type="password" :value="'Bearer '+createdSecret" readonly autocomplete="off" aria-label="本人连接认证值"></label>
            <button type="button" data-copy-credential :disabled="busy" @click="copyCredential">复制认证值（仅粘贴到私密设置）</button>
            <p class="kb-muted">凭据仅本次显示。保存后在客户端启用连接；关闭此面板会清除本页凭据。无法找回时，撤销旧连接后重新创建。</p>
          </template>
        </div>
        <button type="button" class="kb-copy-row" data-copy-prompt :disabled="busy" @click="copyPrompt"><CopyOutlined/>复制说明 + 无密钥提示词</button>
        <div class="kb-prompt-preview" tabindex="0" aria-label="无密钥提示词">{{credentialFreePrompt()}}</div>
        <p v-if="notice" class="kb-notice" role="status">{{notice}}</p>
        <details class="kb-advanced">
          <summary>高级选项：下载 Python 安装文件（本机导入令牌）</summary>
          <p class="kb-muted">适用于需要脚本导入令牌的环境。下载本人私密安装文件（含凭据，导入成功后自动删除自身），在终端运行。</p>
          <button type="button" class="kb-copy-row" data-legacy-install :disabled="busy" @click="install">{{installerName?'复制安装指令':'下载并复制安装指令'}}</button>
          <div v-if="installerName" class="kb-prompt-preview" tabindex="0" aria-label="本机安装指令">{{installCommand}}</div>
        </details>
        <div class="kb-wizard-footer">
          <a-button @click="step=1">上一步</a-button>
          <a-button type="primary" data-step-continue :disabled="busy || !currentConnection" @click="goTrial">下一步：实际试用</a-button>
        </div>
      </section>
      <!-- 步骤3 实际试用：服务端记录的真实使用才计入 -->
      <section v-show="step===3" class="kb-wizard-body">
        <p class="kb-wizard-body-copy">在自己的助手中正常提一个公司知识问题（例如：搜索培养箱使用前检查的 SOP）。完成后回到这里查看连接状态。</p>
        <div class="kb-check-rows">
          <div class="kb-check-row"><span>服务自检（浏览器核验身份与 4 个受控工具）</span><a-tag v-if="selfCheck.state==='passed'" color="green">已通过</a-tag><a-tag v-else-if="selfCheck.state==='failed'" color="red">未通过</a-tag><a-tag v-else>未开始</a-tag></div>
          <p v-if="selfCheck.error" class="kb-muted">{{selfCheck.error}}</p>
          <button type="button" class="kb-copy-row" data-self-check :disabled="selfCheck.state==='running'||busy||!createdSecret" @click="runSelfCheck"><SafetyOutlined/>{{selfCheck.state==='running'?'自检进行中…':'运行服务自检（不调用模型）'}}</button>
        </div>
        <div class="connection-list" aria-label="最近使用状态">
          <h2>实际试用状态</h2>
          <article v-if="currentConnection"><div><strong>{{currentConnection.client}}</strong><p>{{stage(currentConnection)}}</p></div></article>
          <p v-else class="kb-muted">尚未创建连接。请先完成第 2 步。</p>
          <a-button type="text" :loading="loading" :disabled="busy" @click="refresh">查看连接状态</a-button>
          <p class="kb-muted">只有服务端记录到该连接的真实工具调用并成功复开来源，才显示“已完成知识查询”。本页自检与安装配置不计入。</p>
        </div>
        <div class="kb-wizard-footer">
          <a-button @click="step=2">上一步</a-button>
          <a-button type="primary" data-step-continue @click="step=4">下一步：使用帮助</a-button>
        </div>
      </section>
      <!-- 步骤4 使用帮助 -->
      <section v-show="step===4" class="kb-wizard-body">
        <h2>四个受控工具</h2>
        <article v-for="tool in liveToolHelp" :key="tool.name" class="kb-tool-help"><strong>{{tool.name}}</strong><p>{{tool.purpose}}</p><p class="kb-tool-example">例：{{tool.example}}</p></article>
        <h2>常见问题</h2>
        <details v-for="entry in CONNECTION_FAQ" :key="entry.question" class="kb-faq"><summary>{{entry.question}}</summary><p class="kb-muted">{{entry.answer}}</p></details>
        <div class="kb-wizard-footer">
          <a-button @click="step=3">上一步</a-button>
          <a-button type="primary" @click="close">完成</a-button>
        </div>
      </section>
      <a-collapse ghost>
        <a-collapse-panel key="management" header="连接管理">
          <p class="kb-muted">连接仅属于本人，有效期 {{info.ttl_days}} 天。请勿转给他人；需要停用时撤销即可。</p>
          <div v-if="currentConnection" class="connection-management"><span>当前连接 · 到期 {{date(currentConnection.expires_at)}}</span><a-popconfirm title="撤销后此助手无法继续访问公司知识，确认撤销？" ok-text="撤销" cancel-text="取消" @confirm="revoke(currentConnection!.id)"><a-button danger :disabled="busy">撤销连接</a-button></a-popconfirm></div>
          <p v-else class="kb-muted">还没有可管理的连接。</p>
          <details v-if="history.length"><summary>历史连接（{{history.length}}）</summary><article v-for="item in history" :key="item.id" class="connection-management"><div><strong>{{item.label}}</strong><p>{{item.client}} · {{stage(item)}}</p></div><a-popconfirm v-if="!item.revoked&&!item.expired" title="确认撤销此历史连接？" ok-text="撤销" cancel-text="取消" @confirm="revoke(item.id)"><a-button danger :disabled="busy">撤销</a-button></a-popconfirm></article></details>
          <details><summary>知识使用规则</summary><p class="kb-muted">{{knowledgeUsageRules}}</p></details>
        </a-collapse-panel>
      </a-collapse>
    </template>
  </a-drawer>
</template>
<script setup lang="ts">
import { ref, watch, computed, onBeforeUnmount } from 'vue'
import { CopyOutlined, CheckCircleOutlined, SafetyOutlined } from '@ant-design/icons-vue'
import { getKnowledgeConnections,createKnowledgeConnection,revokeKnowledgeConnection,DomainApiError } from '@/services/p1Api'
import type { ConnectionInfo,PersonalConnection } from '@/services/p1Api'
import { localInstaller,knowledgeUsageRules } from '@/services/knowledgeInstaller'
import { credentialFreePrompt,TOOL_HELP,CONNECTION_FAQ } from '@/services/knowledgeHelp'
import { checkKnowledgeConnection } from '@/services/knowledgeConnectionCheck'
const props=defineProps<{open:boolean;subject:string}>(),emit=defineEmits<{close:[]}>()
const info=ref<ConnectionInfo|null>(null),client=ref<'OpenClaw'|'Hermes'>('OpenClaw')
const loading=ref(false),busy=ref(false),error=ref(''),notice=ref(''),installerName=ref(''),createdId=ref('')
const step=ref<1|2|3|4>(1)
const createdSecret=ref('')
const liveToolHelp=computed(()=>TOOL_HELP.filter(tool=>info.value?.tools.includes(tool.name)))
const selfCheck=ref<{state:'idle'|'running'|'passed'|'failed';error:string}>({state:'idle',error:''})
const steps=computed(()=>[
  {step:1 as const,title:'选择助手'},
  {step:2 as const,title:'连接知识库'},
  {step:3 as const,title:'实际试用'},
  {step:4 as const,title:'使用帮助'},
])
function clientVersion(name:'OpenClaw'|'Hermes'){return info.value?.client_versions?.[name]||'以助手官方版本为准'}
const installCommand=computed(()=>installerName.value?'python3 "$HOME/Downloads/'+installerName.value+'"':'')
const currentConnection=computed(()=>info.value?.items.find(i=>i.id===createdId.value&&!i.revoked&&!i.expired)||info.value?.items.find(i=>i.client===client.value&&!i.revoked&&!i.expired&&!i.is_test))
const history=computed(()=>info.value?.items.filter(i=>i.id!==currentConnection.value?.id)||[])
let generation=0,refreshGeneration=0,selfCheckAbort:AbortController|null=null,selfCheckGeneration=0
function date(value:string){return new Date(value).toLocaleString()}
function stage(item:PersonalConnection){
  if(item.revoked)return '已撤销'
  if(item.expired)return '已过期'
  // Only a server-recorded real tool call with an opened source counts as a
  // completed knowledge query; receipts without it stay "prepared".
  if(item.verification_state==='KNOWLEDGE_USED'||item.knowledge_used_at)return '已完成知识查询：'+date(item.knowledge_used_at||item.client_receipt?.knowledge_used_at||'')
  return '已准备连接（尚无实际使用记录）'
}
function reset(){generation++;selfCheckGeneration++;selfCheckAbort?.abort();selfCheckAbort=null;info.value=null;error.value='';notice.value='';busy.value=false;loading.value=false;installerName.value='';createdId.value='';createdSecret.value='';step.value=1;selfCheck.value={state:'idle',error:''}}
function close(){reset();emit('close')}
function fail(e:unknown){error.value=e instanceof DomainApiError?e.message:e instanceof Error?e.message:'连接操作暂时不可用。'}
async function refresh(){const current=generation,seq=++refreshGeneration;loading.value=true;error.value='';try{const value=await getKnowledgeConnections();if(current===generation&&seq===refreshGeneration){info.value=value;if(createdId.value&&value.items.some(i=>i.id===createdId.value&&i.knowledge_used_at)){installerName.value='';createdId.value='';createdSecret.value=''}}}catch(e){if(current===generation&&seq===refreshGeneration)fail(e)}finally{if(current===generation&&seq===refreshGeneration)loading.value=false}}
async function copyPrompt(){const current=generation;const text=credentialFreePrompt();try{await navigator.clipboard.writeText(text);if(current===generation)notice.value='已复制说明与无密钥提示词（不含令牌）。粘贴到助手规则后，进行第 3 步实际试用。'}catch{if(current===generation)notice.value='复制未成功，请手动选择上方提示词文本复制。'}}
async function prepareConnection(){
  if(busy.value||!info.value||createdSecret.value)return
  const current=++generation,selected=client.value
  busy.value=true;error.value=''
  try{
    const value=await createKnowledgeConnection('我的'+selected,selected)
    if(current!==generation)return
    createdId.value=value.id;createdSecret.value=value.token
    notice.value='连接已创建，请将服务器地址和认证值保存到助手的私密 MCP 设置。尚未验证实际使用。'
    await refresh()
  }catch(e){if(current===generation)fail(e)}finally{if(current===generation)busy.value=false}
}
async function copyEndpoint(){
  if(!info.value)return
  try{await navigator.clipboard.writeText(info.value.endpoint);notice.value='服务器地址已复制。'}catch{notice.value='复制未成功，请选择地址手动复制。'}
}
async function copyCredential(){
  if(!createdSecret.value)return
  try{await navigator.clipboard.writeText('Bearer '+createdSecret.value);notice.value='认证值已复制；仅粘贴到助手的私密认证设置，不要发送给模型。'}catch{notice.value='复制未成功，请重新创建连接或使用高级安装选项。'}
}
// Legacy advanced path: private installer file holds the token; never the prompt.
async function copyCommand(){const current=generation;try{await navigator.clipboard.writeText(installCommand.value);if(current===generation)notice.value='安装指令已复制。运行后直接在自己的助手中正常提问即可。'}catch{if(current===generation)notice.value='安装文件已下载。请选择上方指令复制，在终端运行即可。'}}
async function install(){
  if(busy.value||!info.value)return
  if(installerName.value){await copyCommand();return}
  if(!createdSecret.value)await prepareConnection()
  if(!createdSecret.value||!createdId.value||!info.value)return
  try{
    const source=localInstaller(client.value,info.value.endpoint,createdSecret.value,createdId.value)
    installerName.value='hbos-assistant-'+createdId.value.slice(0,8)+'.py'
    const url=URL.createObjectURL(new Blob([source],{type:'text/x-python'})),link=document.createElement('a')
    link.href=url;link.download=installerName.value;link.click();setTimeout(()=>URL.revokeObjectURL(url),1000)
    await copyCommand()
  }catch(e){fail(e)}
}

function goTrial(){step.value=3;void refresh()}
async function runSelfCheck(){
  if(selfCheck.value.state==='running'||!info.value||!createdSecret.value)return
  // Browser self-check only: identity + controlled tool list through the same
  // MCP endpoint. It never searches, never opens evidence and never calls a
  // model, so a pass here is displayed as 服务自检, never as 已完成知识查询.
  const current=++selfCheckGeneration,subject=props.subject
  selfCheckAbort=new AbortController()
  selfCheck.value={state:'running',error:''}
  try{
    const result=await checkKnowledgeConnection(info.value,createdSecret.value,'SYNTHETIC 自检',selfCheckAbort.signal,()=>{})
    if(current!==selfCheckGeneration||subject!==props.subject)return
    if(result.authentication==='passed'&&result.tools==='passed')selfCheck.value={state:'passed',error:''}
    else selfCheck.value={state:'failed',error:result.error||'服务自检未完成。'}
  }catch(e){
    if(current!==selfCheckGeneration||subject!==props.subject)return
    selfCheck.value={state:'failed',error:e instanceof Error?e.message:'服务自检未完成。'}
  }finally{
    selfCheckAbort=null
  }
}
async function revoke(id:string){if(busy.value)return;const current=++generation;busy.value=true;error.value='';try{await revokeKnowledgeConnection(id);if(current===generation){if(createdId.value===id){createdId.value='';installerName.value='';createdSecret.value=''}notice.value='连接已撤销。重新安装请复制一条新的安装指令。';await refresh()}}catch(e){if(current===generation)fail(e)}finally{if(current===generation)busy.value=false}}
watch(()=>props.open,value=>{if(value&&props.subject)void refresh();else reset()},{immediate:true})
watch(()=>props.subject,()=>{reset();if(props.open&&props.subject)void refresh()},{flush:'sync'})
watch(client,()=>{generation++;busy.value=false;installerName.value='';createdId.value='';createdSecret.value='';notice.value=''})
onBeforeUnmount(()=>{selfCheckGeneration++;selfCheckAbort?.abort();reset()})
</script>
<style scoped>
.kb-native-connection{display:grid;gap:10px;margin:16px 0}.kb-native-connection label{display:grid;gap:6px;font-size:14px}.kb-native-connection input{width:100%;min-width:0;padding:10px;border:1px solid #d6e9e3;border-radius:8px}.kb-native-connection p{margin:0;line-height:1.7}
.kb-connect-steps{display:flex;gap:4px;list-style:none;margin:0 0 8px;padding:0;font-size:14px;color:var(--hbos-text-muted);flex-wrap:wrap}
.kb-connect-steps li{display:flex;align-items:center;gap:6px;padding:6px 10px;border-radius:10px}
.kb-connect-steps li.active{background:#dff2ee;color:#147e70;font-weight:500}
.kb-connect-steps li.done{color:#159b89}
.kb-step-no{display:inline-grid;place-items:center;width:22px;height:22px;border-radius:999px;background:#edf3f3;font-size:12px}
.kb-connect-steps li.active .kb-step-no{background:#fff}
.kb-wizard-body-copy{font-size:14px;color:#425675;line-height:24px}
.kb-copy-row{display:block;width:100%;text-align:left;padding:14px 16px;margin-top:12px;background:#f0f8f5;border:1px solid #68baac;border-radius:12px;color:#147e70;font-size:15px}
.kb-copy-row:disabled{opacity:.6}
.kb-advanced{margin-top:16px}
.kb-advanced summary{cursor:pointer;font-size:14px;color:var(--hbos-text-secondary)}
.kb-advanced p{margin:12px 0 0}
.kb-check-rows{margin-top:8px}
.kb-check-row{display:flex;justify-content:space-between;align-items:center;gap:16px;padding:12px 0;font-size:14px;border-bottom:1px solid var(--hbos-border-default)}
.connection-list{margin-top:20px}.connection-list h2{font-size:18px;margin:0 0 4px}.connection-list article{padding:12px 0}.connection-list p{margin:8px 0}
.kb-tool-help{padding:12px 0;border-bottom:1px solid var(--hbos-border-default)}
.kb-tool-help strong{font-size:14px;color:#147e70;font-family:var(--hbos-font-mono)}
.kb-tool-help p{margin:6px 0 0;font-size:14px;color:#425675;line-height:22px}
.kb-tool-example{color:var(--hbos-text-muted)!important}
.kb-faq{margin:8px 0}
.kb-faq summary{cursor:pointer;font-size:14px;color:#159b89}
.kb-faq p{margin:8px 0 0}
.kb-wizard-body>button{margin:12px 12px 12px 0}
.kb-wizard-body h2{font-size:18px;margin:16px 0 8px}
.kb-wizard-body h2:first-child{margin-top:0}
.kb-assistant-option small{display:block;margin-top:6px}
.kb-assistant-option{display:block;position:relative;text-align:left;width:100%;padding:20px;margin-top:16px;background:#f7fafb;border:1px solid #e0e9ee;border-radius:16px}
.kb-assistant-option strong{display:block;font-size:16px;color:#17253c}
.kb-assistant-option span{display:block;font-size:14px;color:#72829d;margin-top:8px}
.kb-assistant-option.selected{border-color:#68baac;background:#f0f8f5}
.kb-assistant-option svg{position:absolute;right:20px;top:20px;color:#159b89}
.connection-management{display:flex;justify-content:space-between;align-items:center;gap:16px;padding:16px 0;border-bottom:1px solid var(--hbos-border-default);font-size:14px}
.connection-management>div,.connection-management>span{min-width:0;overflow-wrap:anywhere}
details{margin:16px 0}
summary{cursor:pointer;font-size:14px}
.kb-prompt-preview{overflow-wrap:anywhere;white-space:pre-wrap;background:#f2f8f6;border:1px solid #d6e9e3;border-radius:16px;padding:16px;font-size:14px;line-height:24px;margin-top:12px}
.kb-wizard-footer{display:flex;justify-content:flex-end;gap:12px;margin-top:24px;padding-top:16px;border-top:1px solid var(--hbos-border-default)}
@media (max-width:480px){
  .kb-connect-steps{gap:2px}
  .kb-connect-steps li{padding:4px 6px;font-size:12px}
  .kb-copy-row{padding:12px;font-size:14px}
  .kb-prompt-preview{padding:12px}
  .kb-wizard-footer{flex-wrap:wrap}
  .kb-wizard-footer .ant-btn{flex:1 1 auto}
  .kb-check-row{flex-wrap:wrap}
}
</style>
