<template>
  <a-drawer :open="open" title="连接个人助手" width="min(640px, 100vw)" root-class-name="kb-drawer kb-scope" :destroy-on-close="true" @close="close">
    <ol class="kb-connect-steps" aria-label="连接步骤">
      <li v-for="item in steps" :key="item.step" :class="{ active: step === item.step, done: step > item.step }">
        <span class="kb-step-no">{{ step > item.step ? '✓' : item.step }}</span>{{ item.title }}
      </li>
    </ol>

    <a-alert v-if="error" type="error" show-icon :message="error" />
    <a-skeleton v-if="loading && !info" active />

    <template v-if="info">
      <!-- 1 · 选择助手 -->
      <section v-show="step === 1" class="kb-wizard-body" data-step="1">
        <p class="kb-wizard-body-copy">选择你实际在用的助手。只列出经实测支持的版本；其它客户端暂未验证。</p>
        <button v-for="name in ['OpenClaw','Hermes'] as const" :key="name" :class="['kb-assistant-option', { selected: client === name }]" :disabled="busy" @click="client = name">
          <strong>{{ name }}</strong>
          <span>{{ clientPurpose(name) }}</span>
          <small class="kb-muted">支持版本：{{ clientVersion(name) }}</small>
          <CheckCircleOutlined v-if="client === name" />
        </button>
        <p v-if="info.deployment === 'LOCAL_UAT'" class="kb-muted">当前为本机验收入口，仅这台电脑可用；公司服务器上线后使用统一 HTTPS 地址。</p>
        <div class="kb-wizard-footer">
          <a-button type="primary" data-step-continue @click="step = 2">下一步：复制连接指引</a-button>
        </div>
      </section>

      <!-- 2 · 复制连接指引：复制出去的内容不含凭据 -->
      <section v-show="step === 2" class="kb-wizard-body" data-step="2">
        <p class="kb-wizard-body-copy">复制下面这段文字，粘贴到你的助手里。它只包含服务器地址、安装命令和使用规则，不含任何凭据，可以放心贴给助手看。</p>

        <button type="button" class="kb-copy-primary" :disabled="busy" data-copy-guidance @click="copyGuidance">
          <CopyOutlined />复制到我的助手
        </button>
        <p v-if="notice" class="kb-notice" role="status" data-copy-notice>{{ notice }}</p>

        <details class="kb-advanced" data-guidance-details>
          <summary>查看复制内容（可展开，不含凭据）</summary>
          <div class="kb-prompt-preview" tabindex="0" aria-label="连接指引全文">{{ guidanceText }}</div>
        </details>

        <div class="kb-credential">
          <h2>本人凭据</h2>
          <p class="kb-muted">凭据等同你的身份，只放进助手自己的私密设置或终端命令，<strong>不要粘贴到对话里</strong>。这里不显示凭据内容。</p>
          <a-button v-if="!createdId" data-create-connection :loading="busy" :disabled="busy" @click="prepareConnection">生成本人连接</a-button>
          <template v-else>
            <div class="kb-credential-row">
              <a-button :disabled="busy" data-copy-credential @click="copyCredential">复制本人凭据（仅剪贴板）</a-button>
              <a-button type="text" :disabled="busy" @click="copyEndpoint">复制服务器地址</a-button>
            </div>
            <p class="kb-muted">只在本页复制一次；关闭后无法再取回，需要时撤销旧连接后重新生成。</p>
          </template>
          <details class="kb-advanced" data-private-installer>
            <summary>高级：由本机安装文件写入客户端私密设置（凭据不进入对话）</summary>
            <p class="kb-muted">下载一个只在本机运行的安装文件，它会把这一个连接写进 {{ client }} 的私密配置并备份原有文件；成功后自动删除自身。凭据不经过任何模型。</p>
            <a-button v-if="!createdId" :disabled="busy" @click="prepareConnection">先生成本人连接</a-button>
            <a-button v-else :disabled="busy" data-download-installer @click="installPrivate"><DownloadOutlined />{{ installerName ? '复制安装指令' : '下载并复制安装指令' }}</a-button>
            <div v-if="installerName" class="kb-prompt-preview" data-install-command>{{ installCommand }}</div>
          </details>
        </div>

        <div class="kb-wizard-footer">
          <a-button @click="step = 1">上一步</a-button>
          <a-button type="primary" data-step-continue :disabled="!anyConnection" @click="goTrial">下一步：在助手里试问</a-button>
        </div>
      </section>

      <!-- 3 · 在助手里试问，服务端记录到真实检索才显示已连接 -->
      <section v-show="step === 3" class="kb-wizard-body" data-step="3">
        <p class="kb-wizard-body-copy">在你的助手里问下面这句。它检索并打开来源后，这里会自动变成“已连接”。</p>
        <button type="button" class="kb-copy-row" :disabled="busy" data-copy-example @click="copyExample">
          <CopyOutlined />复制例句：{{ exampleQuestion }}
        </button>

        <div class="kb-connection-state" data-connection-state :data-state="state">
          <a-spin v-if="state === 'checking'" size="small" />
          <CheckCircleOutlined v-else-if="state === 'connected'" class="kb-state-ok" />
          <ClockCircleOutlined v-else-if="state === 'waiting'" />
          <ExclamationCircleOutlined v-else class="kb-state-wait" />
          <div>
            <strong>{{ stateTitle }}</strong>
            <p>{{ stateDetail }}</p>
          </div>
        </div>

        <p class="kb-muted">复制成功、生成连接、只列出工具都不算连接成功；只有服务端记录到这条本人连接完成了检索并打开了来源，才显示“已连接”。</p>

        <div class="kb-wizard-footer">
          <a-button @click="step = 2">上一步</a-button>
          <a-button :disabled="busy" :loading="loading" data-refresh-state @click="refresh">刷新状态</a-button>
          <a-button type="primary" data-step-continue @click="step = 4">下一步：使用帮助</a-button>
        </div>
      </section>

      <!-- 4 · 使用帮助 -->
      <section v-show="step === 4" class="kb-wizard-body" data-step="4">
        <h2>四个受控工具</h2>
        <article v-for="tool in liveToolHelp" :key="tool.name" class="kb-tool-help">
          <strong>{{ tool.name }}</strong><p>{{ tool.purpose }}</p><p class="kb-tool-example">例：{{ tool.example }}</p>
        </article>
        <h2>还能问什么</h2>
        <button type="button" class="kb-copy-row" data-copy-example-2 @click="copyExample2">
          <CopyOutlined />{{ exampleQuestion2 }}
        </button>
        <h2>常见问题</h2>
        <details v-for="entry in CONNECTION_FAQ" :key="entry.question" class="kb-faq"><summary>{{ entry.question }}</summary><p class="kb-muted">{{ entry.answer }}</p></details>
        <div class="kb-connection-manage" data-connection-manage>
          <h2>连接管理</h2>
          <div v-if="currentConnection" class="connection-management">
            <div>
              <strong>{{ currentConnection.client }}</strong>
              <p class="kb-muted">{{ stateTitle }} · 到期 {{ date(currentConnection.expires_at) }}</p>
            </div>
            <a-popconfirm title="撤销后这个助手立即不能再访问公司知识，确认撤销？" ok-text="撤销" cancel-text="取消" @confirm="revoke(currentConnection!.id)">
              <a-button danger :disabled="busy" data-revoke-connection>断开连接</a-button>
            </a-popconfirm>
          </div>
          <p v-else class="kb-muted">还没有可用连接。</p>
          <details v-if="history.length"><summary>历史连接（{{ history.length }}）</summary><article v-for="item in history" :key="item.id" class="connection-management"><div><strong>{{ item.label }}</strong><p class="kb-muted">{{ item.client }} · {{ stageText(item) }}</p></div><a-popconfirm v-if="!item.revoked && !item.expired" title="确认撤销此连接？" ok-text="撤销" cancel-text="取消" @confirm="revoke(item.id)"><a-button danger size="small" :disabled="busy">撤销</a-button></a-popconfirm></article></details>
        </div>
        <div class="kb-wizard-footer">
          <a-button @click="step = 3">上一步</a-button>
          <a-button type="primary" @click="close">完成</a-button>
        </div>
      </section>
    </template>
  </a-drawer>
</template>
<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { CheckCircleOutlined, ClockCircleOutlined, CopyOutlined, DownloadOutlined, ExclamationCircleOutlined } from '@ant-design/icons-vue'
import { getKnowledgeConnections, createKnowledgeConnection, revokeKnowledgeConnection, DomainApiError } from '@/services/p1Api'
import type { ConnectionInfo, PersonalConnection } from '@/services/p1Api'
import { connectionGuidance, credentialFreePrompt, guidanceHasNoSecret, TOOL_HELP, CONNECTION_FAQ } from '@/services/knowledgeHelp'
import { localInstaller } from '@/services/knowledgeInstaller'

/**
 * The journey: pick the assistant, copy one guidance block, (optionally)
 * generate the one personal connection, ask the example question, and only
 * then see "connected". The status is read from the server's own record of a
 * real search + opened source for this connection - copying, creating and
 * listing tools never light it up.
 */
const props = defineProps<{ open: boolean; subject: string }>()
const emit = defineEmits<{ close: [] }>()

const info = ref<ConnectionInfo | null>(null)
const client = ref<'OpenClaw' | 'Hermes'>('OpenClaw')
const loading = ref(false), busy = ref(false), error = ref(''), notice = ref('')
const step = ref<1 | 2 | 3 | 4>(1)
const createdId = ref('')
const createdCredential = ref('')

const steps = computed(() => [
  { step: 1 as const, title: '选择助手' },
  { step: 2 as const, title: '复制连接指引' },
  { step: 3 as const, title: '在助手里试问' },
  { step: 4 as const, title: '使用帮助' },
])
const exampleQuestion = '搜索培养箱使用前检查的相关 SOP，并打开其中一条来源核对版本。'
const exampleQuestion2 = '我们岗位安全培训要用哪份资料？请给出来源和版本。'

const liveToolHelp = computed(() => TOOL_HELP.filter(tool => info.value?.tools.includes(tool.name)))
const anyConnection = computed(() => Boolean(info.value?.items.some(item => !item.revoked && !item.expired)))
const currentConnection = computed(() =>
  info.value?.items.find(item => item.id === createdId.value && !item.revoked && !item.expired)
  || info.value?.items.find(item => item.client === client.value && !item.revoked && !item.expired && !item.is_test))
const history = computed(() => info.value?.items.filter(item => item.id !== currentConnection.value?.id) || [])

function clientVersion(name: 'OpenClaw' | 'Hermes') { return info.value?.client_versions?.[name] || '以助手官方版本为准' }
function clientPurpose(name: 'OpenClaw' | 'Hermes') {
  return name === 'OpenClaw' ? '在 OpenClaw 里直接问公司知识与 SOP' : '在 Hermes 里直接问公司知识与 SOP'
}
function date(value: string) { return new Date(value).toLocaleString() }
function stageText(item: PersonalConnection) {
  if (item.revoked) return '已撤销'
  if (item.expired) return '已过期'
  if (item.knowledge_used_at || item.verification_state === 'KNOWLEDGE_USED') return '已连接 · ' + date(item.knowledge_used_at || '')
  return '已生成，等待首次成功查询'
}

// ---- status from the server's own record -----------------------------------
const state = computed<'none' | 'waiting' | 'checking' | 'connected'>(() => {
  const connection = currentConnection.value
  if (!connection) return 'none'
  if (connection.knowledge_used_at || connection.verification_state === 'KNOWLEDGE_USED') return 'connected'
  return loading.value ? 'checking' : 'waiting'
})
const stateTitle = computed(() => ({
  none: '还没有可用连接',
  waiting: '等待首次成功查询',
  checking: '正在核对连接状态',
  connected: '已连接',
}[state.value]))
const stateDetail = computed(() => {
  const connection = currentConnection.value
  if (state.value === 'none') return '先在第 2 步生成本人连接。'
  if (state.value === 'connected') return `助手已完成一次资料检索并打开了来源（${date(connection?.knowledge_used_at || '')}）。`
  return '在助手里问上面的例句；检索并打开来源后这里会自动更新。'
})

// ---- copy actions -----------------------------------------------------------
function commandFor(name: 'OpenClaw' | 'Hermes', endpoint: string) {
  return name === 'OpenClaw'
    ? `openclaw mcp add hbos --transport streamable-http --url ${endpoint} --header "Authorization=Bearer {credential}"`
    : `hermes mcp add hbos --url ${endpoint} --auth header`
}
const guidanceText = computed(() => {
  if (!info.value) return ''
  return connectionGuidance({
    client: client.value,
    endpoint: info.value.endpoint,
    command: commandFor(client.value, info.value.endpoint),
    rules: credentialFreePrompt(),
    example: exampleQuestion,
    version: clientVersion(client.value).slice(0, 40),
  })
})

async function copyText(text: string, message: string) {
  try {
    await navigator.clipboard.writeText(text)
    notice.value = message
  } catch {
    notice.value = '复制未成功，请展开复制内容后手动选择复制。'
  }
}

async function copyGuidance() {
  if (!info.value) return
  const text = guidanceText.value
  if (!guidanceHasNoSecret(text)) { error.value = '复制内容检查未通过，已停止复制。'; return }
  await copyText(text, '已复制连接指引（不含凭据）。粘贴到你的助手里，再按指引完成凭据设置。')
}
function copyEndpoint() {
  if (!info.value) return
  void copyText(info.value.endpoint, '服务器地址已复制。')
}
async function copyCredential() {
  if (!createdCredential.value) return
  // Clipboard only: the value is never rendered in the page or its DOM text.
  await copyText('Authorization: Bearer ' + createdCredential.value, '本人凭据已复制到剪贴板，只粘贴到助手私密设置或终端命令里。')
}
function copyExample() { void copyText(exampleQuestion, '例句已复制，粘贴到助手对话里即可。') }

// Advanced, opt-in path: the installer file carries this one credential to the
// client's private configuration; it is never part of the guidance text.
const installerName = ref('')
const installCommand = computed(() => installerName.value ? 'python3 "$HOME/Downloads/' + installerName.value + '"' : '')
async function installPrivate() {
  if (!info.value || !createdCredential.value || !createdId.value) return
  try {
    const source = localInstaller(client.value, info.value.endpoint, createdCredential.value, createdId.value)
    installerName.value = 'hbos-assistant-' + createdId.value.slice(0, 8) + '.py'
    const url = URL.createObjectURL(new Blob([source], { type: 'text/x-python' }))
    const link = document.createElement('a')
    link.href = url; link.download = installerName.value; link.click()
    setTimeout(() => URL.revokeObjectURL(url), 1000)
    await copyText(installCommand.value, '安装指令已复制，在终端运行即可。')
  } catch (e) { fail(e) }
}
function copyExample2() { void copyText(exampleQuestion2, '例句已复制。') }

// ---- server actions ---------------------------------------------------------
let generation = 0
let refreshGeneration = 0
let poller: ReturnType<typeof setInterval> | null = null
let pollDeadline = 0

function stopPolling() {
  if (poller) { clearInterval(poller); poller = null }
}
function startPolling() {
  stopPolling()
  if (!props.open) return
  // Bounded polling only while the wizard is open; closing stops it.
  pollDeadline = Date.now() + 5 * 60 * 1000
  poller = setInterval(() => {
    if (Date.now() > pollDeadline) { stopPolling(); return }
    if (state.value === 'connected') { stopPolling(); return }
    void refresh()
  }, 8000)
}

function reset() {
  generation++; stopPolling()
  info.value = null; error.value = ''; notice.value = ''; busy.value = false; loading.value = false
  createdId.value = ''; createdCredential.value = ''; step.value = 1
}
function close() { reset(); emit('close') }
function fail(e: unknown) { error.value = e instanceof DomainApiError ? e.message : e instanceof Error ? e.message : '连接操作暂时不可用。' }

async function refresh() {
  const current = generation, seq = ++refreshGeneration
  loading.value = true
  try {
    const value = await getKnowledgeConnections()
    if (current !== generation || seq !== refreshGeneration) return
    info.value = value
    if (createdId.value && value.items.some(item => item.id === createdId.value && item.knowledge_used_at)) {
      createdCredential.value = ''
    }
  } catch (e) {
    if (current === generation && seq === refreshGeneration) fail(e)
  } finally {
    if (current === generation && seq === refreshGeneration) loading.value = false
  }
}

async function prepareConnection() {
  if (busy.value || !info.value || createdId.value) return
  const current = ++generation, selected = client.value
  busy.value = true; error.value = ''
  try {
    const value = await createKnowledgeConnection('我的' + selected, selected)
    if (current !== generation) return
    createdId.value = value.id
    createdCredential.value = value.token
    notice.value = '本人连接已生成。凭据只在剪贴板里，不显示在页面上。'
    await refresh()
  } catch (e) {
    if (current === generation) fail(e)
  } finally {
    if (current === generation) busy.value = false
  }
}

async function revoke(id: string) {
  if (busy.value) return
  const current = ++generation
  busy.value = true; error.value = ''
  try {
    await revokeKnowledgeConnection(id)
    if (current !== generation) return
    if (createdId.value === id) { createdId.value = ''; createdCredential.value = '' }
    notice.value = '连接已撤销，该助手不能再访问公司知识。'
    await refresh()
  } catch (e) {
    if (current === generation) fail(e)
  } finally {
    if (current === generation) busy.value = false
  }
}

function goTrial() { step.value = 3; void refresh(); startPolling() }
watch(client, () => {
  generation++; busy.value = false
  createdId.value = ''; createdCredential.value = ''; notice.value = ''
})
watch(() => props.subject, () => { reset(); if (props.open && props.subject) void refresh() }, { flush: 'sync' })
watch(() => props.open, value => {
  if (value && props.subject) { void refresh(); }
  else { reset() }
}, { immediate: true })
watch(state, value => { if (value === 'connected') stopPolling() })
onBeforeUnmount(() => { generation++; stopPolling(); reset() })
</script>
<style scoped>
.kb-connect-steps{display:flex;gap:4px;list-style:none;margin:0 0 12px;padding:0;font-size:14px;color:var(--hbos-text-muted);flex-wrap:wrap}
.kb-connect-steps li{display:flex;align-items:center;gap:6px;padding:6px 10px;border-radius:10px}
.kb-connect-steps li.active{background:#dff2ee;color:#147e70;font-weight:500}
.kb-connect-steps li.done{color:#159b89}
.kb-step-no{display:inline-grid;place-items:center;width:22px;height:22px;border-radius:999px;background:#edf3f3;font-size:12px}
.kb-connect-steps li.active .kb-step-no{background:#fff}
.kb-wizard-body{display:grid;gap:12px}
.kb-wizard-body-copy{font-size:14px;color:#425675;line-height:24px;margin:0}
.kb-wizard-body h2{font-size:16px;margin:8px 0 0;color:#203b66}
.kb-assistant-option{display:block;position:relative;text-align:left;width:100%;padding:18px;background:#f7fafb;border:1px solid #e0e9ee;border-radius:16px;cursor:pointer}
.kb-assistant-option strong{display:block;font-size:16px;color:#17253c}
.kb-assistant-option span{display:block;font-size:14px;color:#72829d;margin-top:6px}
.kb-assistant-option small{display:block;margin-top:6px}
.kb-assistant-option.selected{border-color:#68baac;background:#f0f8f5}
.kb-assistant-option svg{position:absolute;right:18px;top:18px;color:#159b89}
.kb-copy-primary{display:flex;align-items:center;justify-content:center;gap:10px;width:100%;padding:16px;border:0;border-radius:14px;background:#159b89;color:#fff;font-size:16px;font-weight:600;cursor:pointer}
.kb-copy-primary:disabled{opacity:.6}
.kb-copy-row{display:flex;align-items:center;gap:10px;width:100%;text-align:left;padding:12px 14px;background:#f0f8f5;border:1px solid #68baac;border-radius:12px;color:#147e70;font-size:14px;cursor:pointer;overflow-wrap:anywhere}
.kb-copy-row:disabled{opacity:.6}
.kb-notice{margin:0;color:#127a57;font-size:13px}
.kb-advanced summary{cursor:pointer;font-size:14px;color:var(--hbos-text-secondary)}
.kb-prompt-preview{overflow-wrap:anywhere;white-space:pre-wrap;background:#f2f8f6;border:1px solid #d6e9e3;border-radius:14px;padding:14px;font-size:13px;line-height:22px;margin-top:10px;max-height:320px;overflow:auto}
.kb-credential{border-top:1px solid var(--hbos-border-default);padding-top:12px;display:grid;gap:8px}
.kb-credential p{margin:0}
.kb-credential-row{display:flex;flex-wrap:wrap;gap:8px}
.kb-connection-state{display:flex;gap:12px;align-items:flex-start;padding:14px 16px;border-radius:14px;background:#f4f8fb;border:1px solid #e0e9ee}
.kb-connection-state[data-state=connected]{background:#eef8f4;border-color:#9fd6c8}
.kb-connection-state strong{display:block;font-size:15px;color:#17253c}
.kb-connection-state p{margin:4px 0 0;font-size:13px;line-height:20px;color:#5b6c85}
.kb-state-ok{color:#159b89;font-size:20px}
.kb-state-wait{color:#d48806;font-size:20px}
.kb-tool-help{padding:10px 0;border-bottom:1px solid var(--hbos-border-default)}
.kb-tool-help strong{font-size:14px;color:#147e70;font-family:var(--hbos-font-mono)}
.kb-tool-help p{margin:6px 0 0;font-size:14px;color:#425675;line-height:22px}
.kb-tool-example{color:var(--hbos-text-muted)!important}
.kb-faq{margin:8px 0}
.kb-faq summary{cursor:pointer;font-size:14px;color:#159b89}
.kb-faq p{margin:8px 0 0}
.kb-connection-manage{border-top:1px solid var(--hbos-border-default);padding-top:12px;display:grid;gap:8px}
.connection-management{display:flex;justify-content:space-between;align-items:center;gap:16px;padding:10px 0;border-bottom:1px solid var(--hbos-border-default);font-size:14px}
.connection-management>div{min-width:0;overflow-wrap:anywhere}
.kb-wizard-footer{display:flex;justify-content:flex-end;gap:10px;margin-top:16px;padding-top:14px;border-top:1px solid var(--hbos-border-default);flex-wrap:wrap}
@media (max-width:480px){
  .kb-connect-steps li{padding:4px 6px;font-size:12px}
  .kb-copy-primary{padding:14px;font-size:15px}
  .kb-wizard-footer .ant-btn{flex:1 1 auto}
}
</style>
