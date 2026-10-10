<template>
  <a-drawer :open="open" title="连接个人助手（MCP）" width="min(700px, 100vw)" :content-wrapper-style="{maxWidth:'100vw'}" :destroy-on-close="true" @close="close">
    <div class="connections">
      <p>用本人的知识库权限连接个人助手。连接有效期 7 天；退出 Portal 后仍可用，可在这里随时撤销。</p>
      <a-alert v-if="error" type="error" show-icon :message="error" />
      <a-skeleton v-if="loading" active />
      <template v-if="info">
        <a-alert v-if="info.deployment === 'LOCAL_UAT'" type="info" show-icon message="本机人工验收入口" description="此地址仅供本机客户端；从平板或其他电脑使用需要部署者提供受控 HTTPS 地址。" />
        <a-alert :type="info.query_blocked?'warning':'info'" show-icon :message="info.query_blocked?'本轮知识查询暂停':'客户端实测范围'" :description="verification" />
        <dl><dt>服务地址</dt><dd><code>{{ info.endpoint }}</code></dd><dt>认证</dt><dd>个人 Bearer Token · 不使用员工登录密码</dd><dt>受控工具</dt><dd>{{ info.tools.join('、') }}</dd></dl>
        <form @submit.prevent="create">
          <label for="mcp-client">助手客户端</label><select id="mcp-client" v-model="client" :disabled="busy"><option>OpenClaw</option><option>Hermes</option></select>
          <label for="mcp-label">连接名称</label><input id="mcp-label" v-model="label" maxlength="80" placeholder="例如：我的工作助手" :disabled="busy" />
          <a-button type="primary" html-type="submit" :loading="busy" :disabled="busy || !label.trim()">创建本人连接</a-button>
        </form>
        <section v-if="credential" class="credential" aria-live="polite">
          <h3>保存本次连接凭据</h3><p>凭据仅显示这一次，请保存在本人客户端；关闭后需要新建连接。不要转发给他人。</p>
          <label for="mcp-template">{{ client }} 配置</label><textarea id="mcp-template" readonly :value="template" aria-label="本人 MCP 连接配置" />
          <div class="actions"><a-button @click="copy">复制配置</a-button><a-button @click="credential = null">已保存，隐藏凭据</a-button></div>
          <p v-if="notice" role="status">{{ notice }}</p>
        </section>
        <section class="steps"><h3>连接并核验</h3><ol>
          <li>OpenClaw：执行 <code>openclaw mcp set hbos '&lt;上方配置 JSON&gt;'</code>，把引号中的占位内容替换为本人的配置。transport 为 streamable-http。已核验版本：{{ info.client_versions.OpenClaw }}。</li>
          <li>Hermes：把配置中的 hbos 条目加入本人的 config.yaml 的 mcp_servers，重启本人助手以加载。已测版本：{{ info.client_versions.Hermes }}。</li>
          <li>刷新工具列表，应出现上面的四个工具；先查部门，再用 search_knowledge 查询，接着用 get_evidence 展开返回的 evidence_id。</li>
          <li>向助手明确说“调用 HBOS 的 ask_knowledge 回答”，才使用知识库生成能力。标准检索不调用外部 rerank，向量查询仍计量；客户端自身生成也可能产生其账户费用。</li>
          <li>完成后查看下方阶段是否到“已查询知识”；撤销后原连接下一次请求会被拒绝。</li>
        </ol></section>
        <div class="section-title"><h3>本人的连接</h3><a-button :disabled="busy || loading" @click="refresh">刷新连接状态</a-button></div>
        <a-empty v-if="!info.items.length" description="还没有创建个人连接" />
        <article v-for="item in info.items" :key="item.id"><div><strong>{{ item.label }}</strong><p>{{ item.client }} · {{ stage(item) }}</p><small>到期 {{ date(item.expires_at) }}<span v-if="item.last_used_at"> · 最近使用 {{ date(item.last_used_at) }}</span></small></div><a-button danger size="small" :disabled="busy || item.revoked" @click="revoke(item.id)">撤销连接</a-button></article>
      </template>
    </div>
  </a-drawer>
</template>
<script setup lang="ts">
import { computed, ref, watch, onBeforeUnmount } from 'vue'
import { getKnowledgeConnections, createKnowledgeConnection, revokeKnowledgeConnection, DomainApiError } from '@/services/p1Api'
import type { ConnectionInfo, PersonalConnection } from '@/services/p1Api'
const props=defineProps<{open:boolean;subject:string}>()
const emit=defineEmits<{close:[]}>()
const info=ref<ConnectionInfo|null>(null), credential=ref<{id:string;token:string;expires_at:string}|null>(null)
const client=ref('OpenClaw'), label=ref('我的工作助手'), loading=ref(false), busy=ref(false), error=ref(''), notice=ref('')
let generation=0, refreshGeneration=0
const template=computed(()=> !info.value || !credential.value ? '' : JSON.stringify(client.value==='OpenClaw' ? {transport:'streamable-http',url:info.value.endpoint,headers:{Authorization:'Bearer '+credential.value.token}} : {mcp_servers:{hbos:{url:info.value.endpoint,headers:{Authorization:'Bearer '+credential.value.token},timeout:90}}},null,2))
const verification=computed(()=>{const status=info.value?.client_verification[client.value];return status==='VERIFIED_TOOLS_ONLY_QUERY_BLOCKED' ? 'OpenClaw 的认证、四个工具发现和部门读取已实测；知识查询和完整助手回答尚未通过。费用待核验期间不会发送新模型请求。' : status==='VERIFIED_QUERY_AND_SOURCE_BEFORE_BUDGET_STOP' ? 'Hermes 已装版本的知识查询和来源展开在暂停前实测通过；完整助手生成尚未验证。当前费用待核验，查询已暂停。' : '客户端完整查询尚未验证。请查看知识库服务状态；当前存在未结算请求。'})
function date(s:string){return new Date(s).toLocaleString()}
function stage(item:PersonalConnection){return item.revoked ? '已撤销' : item.expired ? '已过期' : ({Configured:'已配置',Authenticated:'已认证','Tools Discovered':'已发现工具','Knowledge Used':'已查询知识'}[item.stage] || '待核验')}
function close(){generation++;credential.value=null;info.value=null;error.value='';busy.value=false;loading.value=false;emit('close')}
function fail(e:unknown){error.value=e instanceof DomainApiError ? e.message : '连接操作暂时不可用。'}
async function refresh(){const current=generation, seq=++refreshGeneration;loading.value=true;error.value='';try{const result=await getKnowledgeConnections();if(current===generation && seq===refreshGeneration)info.value=result}catch(e){if(current===generation && seq===refreshGeneration)fail(e)}finally{if(current===generation && seq===refreshGeneration)loading.value=false}}
async function create(){if(busy.value)return;const current=++generation;busy.value=true;credential.value=null;error.value='';notice.value='';try{const result=await createKnowledgeConnection(label.value.trim(),client.value);if(current===generation){credential.value=result;await refresh()}}catch(e){if(current===generation)fail(e)}finally{if(current===generation)busy.value=false}}
async function revoke(id:string){if(busy.value)return;const current=++generation;busy.value=true;error.value='';try{await revokeKnowledgeConnection(id);if(current===generation){if(credential.value?.id===id)credential.value=null;await refresh()}}catch(e){if(current===generation)fail(e)}finally{if(current===generation)busy.value=false}}
async function copy(){try{await navigator.clipboard.writeText(template.value);notice.value='已复制，请粘贴到本人客户端。'}catch{notice.value='复制受浏览器限制，请手动选择并复制上方配置。'}}
watch(()=>props.open,value=>{if(value&&props.subject)void refresh();else{generation++;credential.value=null;info.value=null;busy.value=false;loading.value=false}})
watch(()=>props.subject,()=>{generation++;credential.value=null;info.value=null;error.value='';notice.value='';busy.value=false;loading.value=false;label.value='我的工作助手';if(props.open&&props.subject)void refresh()})
watch(client,()=>{generation++;credential.value=null;notice.value=''})
onBeforeUnmount(()=>{generation++;credential.value=null})
</script>
<style scoped>
.connections{display:grid;gap:16px;font-size:var(--hbos-font-body);line-height:var(--hbos-line-body);overflow-wrap:anywhere;min-width:0}.connections p{margin:0;color:var(--hbos-text-secondary)}.connections h3{font-size:var(--hbos-font-card-title);margin:0 0 8px}.connections form{display:grid;gap:8px}.connections input,.connections select,.connections textarea{width:100%;padding:10px;border:1px solid var(--hbos-border-strong);border-radius:10px;background:var(--hbos-bg-surface);font:inherit}.connections textarea{min-height:230px;resize:vertical;font-size:var(--hbos-font-meta);white-space:pre;overflow:auto}.connections label,.connections dt{font-weight:var(--hbos-weight-strong)}.connections dd{margin:4px 0 12px}.credential{padding:16px;border-radius:16px;border:1px solid var(--hbos-border-strong);display:grid;gap:10px}.actions,.section-title{display:flex;gap:10px;justify-content:space-between;flex-wrap:wrap}.connections article{display:flex;gap:12px;justify-content:space-between;border-top:1px solid var(--hbos-border-strong);padding:12px 0}.connections article>div{min-width:0}.connections small{font-size:var(--hbos-font-meta);color:var(--hbos-text-muted)}.steps li{margin:8px 0}
</style>
