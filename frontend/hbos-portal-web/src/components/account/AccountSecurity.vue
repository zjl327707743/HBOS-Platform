<template>
  <section class="setting-card glass-surface account-security">
    <div class="account-security-heading"><div><h3>登录与安全</h3><p>选择适合你的登录方式，保护工作账号。</p></div><span>账号保护</span></div>
    <a-alert v-if="error && !modalOpen" :message="error" type="warning" show-icon role="alert" />
    <a-alert v-if="uncertain && !modalOpen" message="上次操作待核对。请先查询结果，避免重复提交。" type="warning" show-icon role="alert" />
    <a-button v-if="uncertain && !modalOpen && requestId" :loading="busy" @click="checkOutcome()">查询上次提交结果</a-button>
    <section v-if="uncertain && !modalOpen && unknownOutcome && requestId" class="account-section" aria-label="结束未决安全操作">
      <h4>结束未决安全操作</h4>
      <p class="aux">原提交结果已无法确认。结束该请求只会解除本条阻断，不会声称原操作成功，也不会再次执行原提交；不会延长恢复链接或验证有效期。</p>
      <OwnAccountVerification :key="proofKey" password-only @verified="proof.sync" @invalidated="proof.invalidate" />
      <a-checkbox v-model:checked="sealConfirm" :disabled="busy">我确认不知道原提交结果，要求安全结束该未决请求</a-checkbox>
      <div class="r6-modal-actions"><a-button danger :loading="busy" :disabled="busy || !sealConfirm || !proof.valid.value || proof.method.value !== 'password'" @click="sealUnknown">确认结果未知并安全结束</a-button></div>
    </section>
    <a-alert v-if="notice && !modalOpen" :message="notice" type="success" show-icon role="status" />
    <a-skeleton v-if="loading && !status" active />
    <a-button v-if="!loading && (!status || stale)" size="large" :loading="busy" @click="load">重试读取账号状态</a-button>
    <template v-if="status">
      <div class="r6-security-rows">
        <div class="r6-security-row">
          <span class="r6-security-icon"><LockOutlined /></span>
          <div class="r6-security-content">
            <div class="r6-security-title"><h4>登录密码</h4><StatusTag :tone="status.has_password && status.password_login_available !== false ? 'success' : 'warning'">{{ status.has_password ? status.password_login_available === false ? '密码登录暂不可用' : '已设置' : '尚未设置' }}</StatusTag></div>
            <p>使用账号和密码登录；修改前需验证本人，并确认可用的恢复渠道。</p>
          </div>
          <a-button :disabled="busy || stale" @click="open('password', $event)">{{ status.has_password ? '修改密码' : '设置密码' }} <RightOutlined /></a-button>
        </div>
        <div class="r6-security-row">
          <span class="r6-security-icon blue"><LinkOutlined /></span>
          <div class="r6-security-content">
            <div class="r6-security-title"><h4>飞书登录</h4><StatusTag :tone="feishuTag.tone">{{ feishuTag.label }}</StatusTag></div>
            <p>{{ status.feishu_bound ? status.feishu_configured ? '已绑定本人的飞书，可用飞书进入工作台。' : '已绑定本人的飞书，但当前渠道暂不可用；请继续使用密码登录。' : status.feishu_configured ? '飞书登录仅限已开放账号；绑定前将核对账号范围。' : '当前可用密码登录；飞书登录仅限已开放账号。' }}</p>
          </div>
          <a-button :disabled="busy || stale" @click="open('feishu', $event)">{{ status.feishu_bound ? '管理绑定' : '查看登录方式' }} <RightOutlined /></a-button>
        </div>
        <div class="r6-security-row">
          <span class="r6-security-icon amber"><KeyOutlined /></span>
          <div class="r6-security-content">
            <div class="r6-security-title"><h4>账号恢复</h4><StatusTag :tone="status.mail_recovery_available ? 'success' : 'warning'">{{ status.mail_recovery_available ? '恢复邮箱可用' : '暂无恢复邮箱' }}</StatusTag></div>
            <p>忘记密码时，可使用已验证的恢复邮箱，或联系管理员核对账号归属并协助恢复。</p>
          </div>
          <a-button :disabled="busy || stale" @click="open('recovery', $event)">查看恢复方式 <RightOutlined /></a-button>
        </div>
      </div>

      <a-collapse v-if="status.can_admin_recover" class="account-section">
        <a-collapse-panel key="admin" header="管理员协助">
          <div class="admin-panel-body">
          <a-button size="large" :disabled="busy" @click="open('admin', $event)">协助员工恢复账号</a-button>
          <section v-if="panel === 'admin'" class="account-section" aria-label="协助员工恢复">
            <div class="panel-heading"><h4>协助员工恢复</h4><a-button :disabled="busy" @click="close">取消</a-button></div>
            <OwnAccountVerification :key="proofKey" password-only :adopt-existing="false" @verified="onVerified" @invalidated="handleChildInvalidated" />
            <a-alert v-if="recoveryUncertain" message="上次签发操作待核对。请先查询结果，避免重复签发；旧链接状态以查询结果为准。" type="warning" show-icon role="alert" />
            <a-button v-if="recoveryUncertain" :loading="busy" @click="checkOutcome()">查询上次提交结果</a-button>
            <a-alert v-if="uncertain && !recoveryUncertain" message="另一项安全操作的结果尚未确认。请先回到对应步骤查询，避免重复提交。" type="warning" show-icon role="alert" />
            <a-form v-if="!uncertain" class="account-form" layout="vertical" @submit.prevent="issueRecovery">
              <p>核对员工本人和账号归属后签发短时单次链接，由员工本人设置密码。</p>
              <a-form-item label="员工登录名或账号" html-for="recovery-user"><a-input id="recovery-user" v-model:value="recoveryUser" size="large" autocomplete="off" :disabled="busy" /></a-form-item>
              <a-form-item label="身份核验依据" html-for="recovery-reason" help="至少 12 个字符，请勿填写密码或验证码。"><a-textarea id="recovery-reason" v-model:value="recoveryReason" :maxlength="500" :disabled="busy" /></a-form-item>
              <a-button size="large" html-type="submit" :disabled="busy || !proof.valid.value || proof.method.value !== 'password' || !recoveryUser || recoveryReason.trim().length < 12" :loading="busy">签发一次性重置链接</a-button>
              <template v-if="recoveryLink"><p>已签发给 {{ recoveryLink.target.display_name }}（{{ recoveryLink.target.login_name }}），仅私下交付本人。</p><a-button @click="copyRecoveryLink">复制一次性链接</a-button><p v-if="linkCopied">链接已复制。</p></template>
            </a-form>
          </section>
          </div>
        </a-collapse-panel>
      </a-collapse>

      <details class="account-more-tools">
        <summary>更多账号工具</summary>
        <p class="r6-tools-note">仅在需要更换飞书或交接职责时使用；不影响上方登录与安全操作。</p>
        <AccountChangeActions />
      </details>
    </template>
  </section>

  <a-modal :open="modalOpen" :title="panelTitle" :width="600" :footer="null" :get-container="false" :destroy-on-close="true" :closable="!busy" :mask-closable="!busy" :keyboard="!busy" @cancel="close">
      <div v-if="panel === 'password'" class="account-dialog">
        <a-alert v-if="error" :message="error" type="warning" show-icon role="alert" />
        <a-alert v-if="notice" :message="notice" type="success" show-icon role="status" />
        <div class="r6-dialog-lead"><span class="r6-security-icon"><LockOutlined /></span><div><h3>保护 {{ status?.login_name || '当前账号' }} 的登录密码</h3><p>只影响你的密码登录方式。</p></div></div>
        <a-steps size="small" :current="passwordStage" :items="[{ title: '验证本人' }, { title: '设置密码' }, { title: '完成' }]" />
        <div v-show="passwordStage === 0" class="r6-password-step">
          <a-alert v-if="uncertain && !passwordUncertain" message="另一项安全操作待核对。请先查询结果，再设置密码。" type="warning" show-icon role="alert" />
          <p v-show="verificationNotice" class="r6-verification-notice" role="status">{{ verificationNotice }}</p>
          <OwnAccountVerification :key="proofKey" :adopt-existing="false" @verified="onVerified" @invalidated="handleChildInvalidated" />
          <div v-if="passwordStage === 0" class="r6-modal-actions"><a-button @click="close">取消</a-button><a-button type="primary" :disabled="!proof.valid.value || (uncertain && !passwordUncertain)" @click="passwordStage = 1">继续设置</a-button></div>
        </div>
        <div v-if="passwordStage === 1" class="r6-password-step">
          <a-alert v-if="passwordUncertain" message="上次操作待核对。请先查询结果，避免重复提交。" type="warning" show-icon role="alert" />
          <a-button v-if="passwordUncertain" :loading="busy" @click="checkOutcome()">查询上次提交结果</a-button>
          <a-alert v-if="uncertain && !passwordUncertain" message="另一项安全操作待核对。请先查询结果，再设置密码。" type="warning" show-icon role="alert" />
          <a-form v-if="!uncertain" class="account-form" layout="vertical" @submit.prevent="changePassword">
            <a-form-item label="新登录密码" html-for="r6-new-password" :validate-status="passwordTooLong ? 'error' : undefined" :help="passwordTooLong ? '最多 512 字符。' : '请设置符合账号安全要求的新密码，最多 512 字符。'"><a-input-password id="r6-new-password" v-model:value="newPassword" size="large" autocomplete="new-password" :disabled="busy" /></a-form-item>
            <p class="r6-field-feedback" role="status">已输入 {{ newPassword.length }}/512 字符。</p>
            <a-form-item label="再次输入密码" html-for="r6-confirm-password" :validate-status="mismatch ? 'error' : undefined" :help="mismatch ? '两次密码不一致。' : confirmation ? '两次输入一致。' : '请再次输入同一密码。'"><a-input-password id="r6-confirm-password" v-model:value="confirmation" size="large" autocomplete="new-password" :disabled="busy" /></a-form-item>
            <div class="r6-modal-actions"><a-button :disabled="busy" @click="close">取消</a-button><a-button type="primary" html-type="submit" :loading="busy" :disabled="busy || !canSubmitPassword">确认设置</a-button></div>
          </a-form>
          <div v-else class="r6-modal-actions"><a-button @click="close">关闭</a-button></div>
        </div>
        <div v-if="passwordStage === 2" class="r6-password-complete">
          <a-result status="success" title="密码设置完成" :sub-title="`服务器已确认密码已保存${resolvedLoginName ? '，登录名：' + resolvedLoginName : ''}。其他旧会话已失效。`"><template #extra><a-button type="primary" @click="close">关闭</a-button></template></a-result>
        </div>
      </div>

      <div v-else-if="panel === 'feishu'" class="account-dialog">
        <a-alert v-if="error" :message="error" type="warning" show-icon role="alert" />
        <a-alert v-if="notice" :message="notice" type="success" show-icon role="status" />
        <div class="r6-dialog-lead"><span class="r6-security-icon blue"><LinkOutlined /></span><div><h3>本人的飞书</h3><p>{{ status?.feishu_bound ? '已绑定，可用于登录' : '飞书登录仅限已开放账号' }}</p></div></div>
        <div class="r6-binding-card">
          <span class="r6-security-icon blue"><LinkOutlined /></span>
          <div><h3>飞书登录</h3><p>{{ status?.feishu_bound ? status?.feishu_configured ? '已绑定本人的飞书，可用于进入工作台。' : '绑定仍在，但当前渠道暂不可用；请继续使用密码登录。' : status?.feishu_configured ? '绑定前将核对账号范围。' : '飞书登录仅限已开放账号。' }}</p></div>
          <StatusTag :tone="feishuTag.tone">{{ feishuTag.label }}</StatusTag>
        </div>
        <a-alert v-if="!status?.feishu_configured && !status?.feishu_bound" message="飞书登录服务当前不可用" description="继续使用密码登录；如需使用飞书登录，请联系人事或系统管理员核对账号可用范围。" type="info" show-icon />
        <a-alert v-else-if="!feishuScopeOpen && !status?.feishu_bound" message="继续使用密码登录" description="当前账号尚不具备管理员飞书专项授权。如需使用，请联系环境负责人核对。" type="info" show-icon />
        <a-alert v-if="status?.administrator && !status?.administrator_link_enabled && !status?.feishu_bound" message="管理员飞书绑定需要专门授权" description="请联系环境负责人核对是否允许内置 Administrator 绑定飞书；当前请继续使用密码登录。" type="info" show-icon />
        <a-alert v-if="status?.administrator && status?.feishu_bound" message="内置 Administrator 的飞书绑定属于专项保管" description="不能在此直接解绑。请使用下方“更多账号工具”中的 Administrator 保管人交接，完成双方核验与专项授权。" type="warning" show-icon />
        <a-alert v-if="status?.feishu_bound && !status?.has_password" message="飞书是当前唯一登录方式" description="请先设置密码，再解绑飞书；当前不能删除唯一登录方式。" type="warning" show-icon />
        <a-alert v-if="!status?.feishu_bound && !status?.has_password" message="当前没有可用的本人验证方式" description="请先设置登录密码，或联系管理员核对账号归属。" type="warning" show-icon />
        <a-alert v-if="feishuUncertain" message="上次操作待核对。请先查询结果，避免重复提交。" type="warning" show-icon role="alert" />
        <a-alert v-if="uncertain && !feishuUncertain" message="另一项安全操作待核对。请先查询结果，再管理飞书绑定。" type="warning" show-icon role="alert" />
        <template v-if="showFeishuProof">
          <OwnAccountVerification :key="proofKey" :password-only="Boolean(status?.feishu_bound || status?.administrator)" :adopt-existing="false" @verified="onVerified" @invalidated="handleChildInvalidated" />
          <a-checkbox v-if="status?.feishu_bound" v-model:checked="unlinkConfirmed" :disabled="busy || uncertain">确认解绑本人飞书，保留密码登录</a-checkbox>
          <div class="r6-modal-actions">
            <a-button :disabled="busy" @click="close">关闭</a-button>
            <a-button v-if="!status?.feishu_bound" type="primary" :disabled="busy || uncertain || !proof.valid.value || !status?.feishu_configured || (status?.administrator && !status.administrator_link_enabled)" @click="bind">授权绑定本人飞书</a-button>
            <a-button v-else danger :disabled="busy || uncertain || !unlinkConfirmed || !proof.valid.value || !status?.has_password || proof.method.value !== 'password'" @click="unlink">确认解绑飞书</a-button>
          </div>
        </template>
        <div v-else class="r6-modal-actions"><a-button v-if="feishuUncertain" :loading="busy" @click="checkOutcome()">查询上次提交结果</a-button><a-button v-if="feishuNeedsReverify" type="primary" @click="reverifyFor()">重新验证后管理飞书</a-button><a-button @click="close">关闭</a-button></div>
        <div class="r6-channel-list" aria-label="当前账号可用渠道"><div><span>密码登录</span><strong>{{ status?.has_password ? status?.password_login_available === false ? '已设置 · 暂不可用' : '已设置' : '尚未设置' }}</strong></div><div><span>飞书登录</span><strong>{{ status?.feishu_bound ? status?.feishu_configured ? '已绑定' : '已绑定 · 渠道暂不可用' : status?.feishu_configured ? '未绑定' : '暂未开放' }}</strong></div><div><span>恢复邮箱</span><strong>{{ status?.mail_recovery_available ? '可用' : '未设置' }}</strong></div></div>
      </div>

      <div v-else-if="panel === 'recovery'" class="account-dialog">
        <a-alert v-if="error" :message="error" type="warning" show-icon role="alert" />
        <a-alert v-if="notice" :message="notice" type="success" show-icon role="status" />
        <div class="r6-dialog-lead"><span class="r6-security-icon amber"><KeyOutlined /></span><div><h3>账号恢复方式</h3><p>核对可用渠道后继续账号恢复。</p></div></div>
        <a-alert v-if="uncertain" message="上次操作待核对。请先查询结果，避免重复提交。" type="warning" show-icon role="alert" />
        <div class="r6-recovery-item"><MailOutlined /><div><strong>邮箱恢复</strong><p>{{ recoveryAvailable ? '已登记并验证的恢复邮箱可用于重置密码。' : '当前没有可用的恢复邮箱。' }}</p></div><StatusTag :tone="recoveryAvailable ? 'success' : 'warning'">{{ recoveryAvailable ? '可用' : '未设置' }}</StatusTag></div>
        <div class="r6-recovery-item"><TeamOutlined /><div><strong>联系管理员</strong><p>{{ status?.administrator ? '内置 Administrator 的应急恢复由环境负责人按本机受控流程处理。' : '请由有权限的管理员核对本人和原账号归属，私下交付短时单次链接；最终密码由您自行设置。' }}</p></div></div>
        <a-alert v-if="!recoveryAvailable" message="暂无可用恢复邮箱" description="请继续使用密码登录，或联系管理员核对账号归属并协助恢复。" type="warning" show-icon />
        <a-alert v-else message="下一步：邮箱恢复" description="将进入现有账号恢复流程，并完成身份核验。" type="info" show-icon />
        <div class="r6-modal-actions"><a-button @click="close">关闭</a-button><a-button v-if="recoveryAvailable" type="primary" :href="recoveryTarget" @click.prevent="openRecoveryFlow">前往邮箱恢复</a-button></div>
      </div>
  </a-modal>
</template>
<script setup lang="ts">
import { LockOutlined, LinkOutlined, KeyOutlined, RightOutlined, MailOutlined, TeamOutlined } from '@ant-design/icons-vue'
import StatusTag from '@/components/iam/StatusTag.vue'
import { computed, onMounted, onBeforeUnmount, ref, nextTick, watch } from 'vue'
import { useRouter } from 'vue-router'
import { getSecurity, startLink, setPassword, unlinkFeishu, adminIssueRecovery, sealUnknownWrite, type SecurityStatus, type RecoveryLink, type ProofStatus } from '@/services/accountApi'
import { clearFrappeCsrfToken, isUnauthenticatedError } from '@/services/frappeClient'
import { useAccountProof } from '@/composables/useAccountProof'
import { accountErrorMessage, isUncertainWrite } from '@/services/accountErrors'
import { readPendingAccountWrite, rememberPendingAccountWrite, clearPendingAccountWrite, accountWriteAction, type AccountWriteKind, type PendingAccountWrite } from '@/services/accountWriteRecovery'
import OwnAccountVerification from './OwnAccountVerification.vue'
import AccountChangeActions from './AccountChangeActions.vue'

const props = defineProps<{ identity?: string }>()
const emit = defineEmits<{ statusChange: [status: SecurityStatus | null] }>()
const router = useRouter()
type Panel = 'password' | 'feishu' | 'recovery' | 'admin' | null
type TagTone = 'neutral' | 'brand' | 'success' | 'warning' | 'error'
const status = ref<SecurityStatus | null>(null), panel = ref<Panel>(null), passwordStage = ref(0)
const newPassword = ref(''), confirmation = ref(''), recoveryUser = ref(''), recoveryReason = ref('')
const recoveryLink = ref<RecoveryLink | null>(null), linkCopied = ref(false), resolvedLoginName = ref('')
const loading = ref(true), busy = ref(false), error = ref(''), notice = ref(''), verificationNotice = ref(''), stale = ref(false), uncertain = ref(false), unknownOutcome = ref(false), sealConfirm = ref(false)
const proofKey = ref(0), unlinkConfirmed = ref(false), feishuNeedsReverify = ref(false)
const trigger = ref<HTMLElement | null>(null)
let disposed = false, requestId = '', pendingKind: AccountWriteKind | '' = '', loadGeneration = 0, autoQueriedRequest = '', busyGeneration = 0
function beginBusy() { const token = ++busyGeneration; busy.value = true; return token }
function endBusy(token: number) { if (!disposed && token === busyGeneration) busy.value = false }
// Definite receipt conflicts must not clear the pending marker: the original
// request is still unresolved and must be queried or explicitly sealed.
const RECEIPT_HOLD_PHRASES = ['仍在处理中', '已用于另一项安全操作', '提交过另一组恢复信息', '已按未知结果封存', '结果未知']
function isReceiptHold(error: unknown): boolean {
  const message = accountErrorMessage(error, '')
  return RECEIPT_HOLD_PHRASES.some(phrase => message.includes(phrase))
}
const proof = useAccountProof(onProofInvalidated)
const mismatch = computed(() => Boolean(confirmation.value && newPassword.value !== confirmation.value))
const passwordTooLong = computed(() => newPassword.value.length > 512)
const canSubmitPassword = computed(() => Boolean(proof.valid.value && newPassword.value && !passwordTooLong.value && newPassword.value === confirmation.value && !uncertain.value))
const modalOpen = computed(() => panel.value === 'password' || panel.value === 'feishu' || panel.value === 'recovery')
const panelTitle = computed(() => panel.value === 'password' ? (status.value?.has_password ? '修改登录密码' : '设置登录密码') : panel.value === 'feishu' ? '飞书登录' : panel.value === 'recovery' ? '账号恢复方式' : panel.value === 'admin' ? '协助员工恢复' : '')
const passwordUncertain = computed(() => uncertain.value && pendingKind === 'password')
const feishuUncertain = computed(() => uncertain.value && pendingKind === 'unlink')
const recoveryUncertain = computed(() => uncertain.value && pendingKind === 'recovery')
const feishuScopeOpen = computed(() => Boolean(status.value?.feishu_configured && (!status.value.administrator || status.value.administrator_link_enabled)))
const showFeishuProof = computed(() => {
  const current = status.value
  if (!current || uncertain.value || feishuNeedsReverify.value) return false
  if (current.administrator) return !current.feishu_bound && current.feishu_configured && current.administrator_link_enabled && current.has_password
  if (current.feishu_bound) return current.has_password
  return current.feishu_configured && current.has_password
})
const feishuTag = computed<{ tone: TagTone; label: string }>(() => {
  const current = status.value
  if (!current) return { tone: 'neutral', label: '暂未取得' }
  if (current.feishu_bound) return current.feishu_configured ? { tone: 'success', label: '已绑定' } : { tone: 'warning', label: '已绑定 · 渠道暂不可用' }
  if (current.feishu_configured) return { tone: 'neutral', label: '未绑定' }
  return { tone: 'neutral', label: '暂未开放' }
})
const recoveryAvailable = computed(() => Boolean(status.value?.mail_recovery_available))
const recoveryTarget = computed(() => status.value?.administrator ? '/hbos/reset-password?administrator=1' : '/hbos/reset-password')

function publishStatus(loaded: SecurityStatus) {
  if (props.identity && loaded.user !== props.identity) return
  status.value = loaded; emit('statusChange', loaded)
}
function clearPasswordSecrets() { newPassword.value = ''; confirmation.value = '' }
function clearAdminSecrets() { recoveryUser.value = ''; recoveryReason.value = ''; recoveryLink.value = null; linkCopied.value = false }
function clearCredentialSecrets() { clearPasswordSecrets(); unlinkConfirmed.value = false }
function clearAllSecrets() { clearCredentialSecrets(); clearAdminSecrets() }
function currentUserId() { return props.identity || status.value?.user || '' }
function restorePending(pending: PendingAccountWrite) {
  requestId = pending.requestId; pendingKind = pending.kind; uncertain.value = true
}
function reverifyFor() { feishuNeedsReverify.value = false; invalidateProof() }
function clearRejectedPending(user: string, error: unknown, receiptId: string) {
  if (user && (isUnauthenticatedError(error) || !isUncertainWrite(error))) clearPendingAccountWrite(user, receiptId)
}
function settlePendingFor(user: string) {
  if (user) clearPendingAccountWrite(user, requestId || undefined)
  requestId = ''; pendingKind = ''; uncertain.value = false; unknownOutcome.value = false; sealConfirm.value = false; autoQueriedRequest = ''
}
function reserveWrite(kind: AccountWriteKind): { id: string; user: string } | null {
  const user = currentUserId()
  if (!user) { error.value = '无法确认当前账号，请重新登录后再试。'; return null }
  const existing = readPendingAccountWrite(user)
  if (existing) {
    restorePending(existing); error.value = '上次操作待核对。请先查询结果，避免重复提交。'; return null
  }
  let id: string
  try { id = crypto.randomUUID() }
  catch { error.value = '当前浏览器无法建立安全提交记录，请在安全连接下重试。'; return null }
  if (!rememberPendingAccountWrite(user, kind, id)) {
    const raced = readPendingAccountWrite(user)
    if (raced) { restorePending(raced); error.value = '上次操作待核对。请先查询结果，避免重复提交。' }
    else error.value = '无法保留本次核对记录，未提交安全操作。请检查浏览器存储后重试。'
    return null
  }
  requestId = id; pendingKind = kind; uncertain.value = false; unknownOutcome.value = false; sealConfirm.value = false
  return { id, user }
}
function restorePendingFor(user: string) {
  const pending = readPendingAccountWrite(user)
  if (!pending) return
  restorePending(pending)
  if (!busy.value && autoQueriedRequest !== pending.requestId) {
    autoQueriedRequest = pending.requestId
    void checkOutcome()
  }
}
function invalidateProof() { proof.invalidate(); proofKey.value++ }
function onProofInvalidated() {
  clearAllSecrets()
  if (panel.value === 'password' && passwordStage.value === 1 && !passwordUncertain.value) {
    passwordStage.value = 0; verificationNotice.value = '本人验证已失效，请重新验证后再设置密码。'
  }
}
function handleChildInvalidated() { proof.invalidate(); onProofInvalidated() }
function onVerified(value: ProofStatus) {
  verificationNotice.value = ''; proof.sync(value)
  if (panel.value === 'password' && passwordStage.value === 0 && proof.valid.value) passwordStage.value = 1
}
function resetAfterSessionLoss(clearMarkerFor: string | null | undefined = undefined) {
  const markerUser = clearMarkerFor === null ? '' : clearMarkerFor || currentUserId()
  if (markerUser) clearPendingAccountWrite(markerUser)
  autoQueriedRequest = ''; feishuNeedsReverify.value = false
  loadGeneration++; proof.invalidate(); proofKey.value++; clearAllSecrets(); panel.value = null; passwordStage.value = 0; requestId = ''; pendingKind = ''
  error.value = ''; notice.value = ''; verificationNotice.value = ''; resolvedLoginName.value = ''
  uncertain.value = false; unknownOutcome.value = false; sealConfirm.value = false; loading.value = false; busyGeneration++; busy.value = false; status.value = null; emit('statusChange', null)
}
async function open(action: Panel, event?: Event) {
  if (busy.value) return
  trigger.value = (event?.currentTarget as HTMLElement | null) ?? (document.activeElement instanceof HTMLElement ? document.activeElement : null)
  error.value = ''; notice.value = ''; verificationNotice.value = ''; feishuNeedsReverify.value = false; sealConfirm.value = false; clearAllSecrets()
  passwordStage.value = action === 'password' && passwordUncertain.value ? 1 : 0
  panel.value = action
  invalidateProof()
  await nextTick()
  document.querySelector<HTMLElement>('.account-dialog .proof-form input, .account-dialog input')?.focus()
}
async function close() {
  if (busy.value) return
  clearAllSecrets()
  passwordStage.value = 0
  panel.value = null
  invalidateProof()
  await nextTick()
  trigger.value?.focus()
}
async function load() {
  const run = ++loadGeneration
  loading.value = true; error.value = ''
  try {
    const loaded = await getSecurity()
    if (disposed || run !== loadGeneration) return
    if (!loaded?.user || (props.identity && loaded.user !== props.identity)) throw new Error('账号状态已变化，请重新登录或重试。')
    publishStatus(loaded); stale.value = false
    if (!uncertain.value) proof.sync(loaded.proof)
    restorePendingFor(loaded.user)
  } catch (e) {
    if (disposed || run !== loadGeneration) return
    const markerUser = status.value?.user || props.identity || ''
    stale.value = true; status.value = null; emit('statusChange', null); invalidateProof()
    if (isUnauthenticatedError(e)) { resetAfterSessionLoss(markerUser || undefined); error.value = accountErrorMessage(e, '会话已失效，请重新登录。') }
    else error.value = accountErrorMessage(e, '无法读取账号状态，请重试。')
  } finally { if (!disposed && run === loadGeneration) loading.value = false }
}
async function run(fn: () => Promise<void>) {
  if (busy.value) return
  const attempt = loadGeneration, busyToken = beginBusy()
  error.value = ''; notice.value = ''
  try { await fn() }
  catch (e) {
    if (!disposed && attempt === loadGeneration) {
      if (isUnauthenticatedError(e)) { resetAfterSessionLoss(); error.value = accountErrorMessage(e, '会话已失效，请重新登录。') }
      else { invalidateProof(); error.value = accountErrorMessage(e) }
    }
  } finally { endBusy(busyToken) }
}
async function refreshAfterWrite() {
  const run = loadGeneration
  try { const loaded = await getSecurity(); if (disposed || run !== loadGeneration) return; if (!loaded?.user || (props.identity && loaded.user !== props.identity)) throw new Error('账号状态已变化，请重新登录后核对。'); publishStatus(loaded); stale.value = false }
  catch (e) {
    if (disposed || run !== loadGeneration) return
    if (isUnauthenticatedError(e)) { resetAfterSessionLoss(); error.value = accountErrorMessage(e, '会话已失效，请重新登录。'); return }
    stale.value = true; emit('statusChange', null); error.value = '操作已完成，但最新账号状态暂未读取。请重试读取状态，不需要再次提交。'
  }
}
async function changePassword() {
  if (busy.value || !canSubmitPassword.value || passwordStage.value !== 1) return
  const reservation = reserveWrite('password')
  if (!reservation) return
  const id = reservation.id, writeUser = reservation.user, run = loadGeneration, busyToken = beginBusy()
  error.value = ''; notice.value = ''
  try {
    const result = await setPassword(newPassword.value, id)
    if (disposed || run !== loadGeneration) return
    if (result?.changed !== true) {
      uncertain.value = true; passwordStage.value = 1; error.value = ''; notice.value = ''
      invalidateProof(); return
    }
    invalidateProof(); clearFrappeCsrfToken(); clearPasswordSecrets(); settlePendingFor(writeUser)
    resolvedLoginName.value = result.login_name || status.value?.login_name || ''
    notice.value = `密码已保存，登录名：${resolvedLoginName.value || status.value?.login_name || '当前账号'}。其他旧会话已失效。`
    passwordStage.value = 2
    await refreshAfterWrite()
  } catch (e) {
    clearRejectedPending(writeUser, e, id)
    if (disposed || run !== loadGeneration) return
    if (isUnauthenticatedError(e)) { resetAfterSessionLoss(); error.value = accountErrorMessage(e, '会话已失效，请重新登录。'); return }
    invalidateProof(); clearPasswordSecrets()
    if (isUncertainWrite(e) || isReceiptHold(e)) { uncertain.value = true; passwordStage.value = 1; error.value = isReceiptHold(e) ? accountErrorMessage(e) : ''; notice.value = '' }
    else { settlePendingFor(writeUser); passwordStage.value = 0; error.value = accountErrorMessage(e) }
  } finally { endBusy(busyToken) }
}
async function bind() {
  if (busy.value || uncertain.value || !proof.valid.value || !status.value?.feishu_configured) return
  if (status.value.administrator && !status.value.administrator_link_enabled) return
  const run = loadGeneration
  busy.value = true; error.value = ''; notice.value = ''
  try { const result = await startLink(); if (disposed || run !== loadGeneration) return; invalidateProof(); window.location.assign(result.authorize_url) }
  catch (e) {
    if (!disposed && run === loadGeneration) {
      if (isUnauthenticatedError(e)) { resetAfterSessionLoss(); error.value = accountErrorMessage(e, '会话已失效，请重新登录。') }
      else { invalidateProof(); error.value = accountErrorMessage(e) }
    }
  } finally { if (!disposed && run === loadGeneration) busy.value = false }
}
async function unlink() {
  const current = status.value
  if (!current || busy.value || uncertain.value || !unlinkConfirmed.value || !proof.valid.value || current.administrator || !current.has_password || proof.method.value !== 'password') return
  const reservation = reserveWrite('unlink')
  if (!reservation) return
  const id = reservation.id, writeUser = reservation.user, run = loadGeneration, busyToken = beginBusy()
  error.value = ''; notice.value = ''
  try {
    const result = await unlinkFeishu(id) as { unlinked?: boolean } | null
    if (disposed || run !== loadGeneration) return
    if (result?.unlinked !== true) {
      uncertain.value = true; error.value = ''; notice.value = ''
      invalidateProof(); return
    }
    invalidateProof(); unlinkConfirmed.value = false; settlePendingFor(writeUser)
    notice.value = '飞书已解绑，原账号和业务资料保留。'
    await refreshAfterWrite()
  } catch (e) {
    clearRejectedPending(writeUser, e, id)
    if (disposed || run !== loadGeneration) return
    if (isUnauthenticatedError(e)) { resetAfterSessionLoss(); error.value = accountErrorMessage(e, '会话已失效，请重新登录。'); return }
    invalidateProof(); unlinkConfirmed.value = false
    if (isUncertainWrite(e) || isReceiptHold(e)) { uncertain.value = true; error.value = isReceiptHold(e) ? accountErrorMessage(e) : ''; notice.value = '' }
    else { settlePendingFor(writeUser); error.value = accountErrorMessage(e) }
  } finally { endBusy(busyToken) }
}
async function checkOutcome() {
  if (busy.value) return
  if (!requestId) {
    const user = currentUserId()
    const pending = user ? readPendingAccountWrite(user) : null
    if (!pending) return
    restorePending(pending)
  }
  const action = pendingKind, attempt = loadGeneration
  await run(async () => {
    const loaded = await getSecurity(requestId)
    if (disposed || attempt !== loadGeneration) return
    if (!loaded?.user || (props.identity && loaded.user !== props.identity)) throw new Error('账号状态已变化，请重新登录后核对。')
    publishStatus(loaded); stale.value = false
    const expectedAction = action === 'recovery' ? 'recovery_issue' : action
    const receipt = loaded.write_result
    const receiptConfirmed = receipt?.completed === true && receipt.action === expectedAction
    const unlinkStateConfirmed = action === 'unlink' && !receipt && !loaded.feishu_bound
    if (receiptConfirmed || unlinkStateConfirmed) {
      proof.invalidate(); settlePendingFor(currentUserId() || loaded.user)
      if (action === 'password') { clearFrappeCsrfToken(); resolvedLoginName.value = loaded.login_name || ''; passwordStage.value = 2; notice.value = '密码已保存，服务器已确认上次提交。' }
      else if (action === 'unlink') { feishuNeedsReverify.value = true; unlinkConfirmed.value = false; notice.value = '飞书已解绑，服务器已确认上次提交。' }
      else { panel.value = null; notice.value = '服务器已确认上次重置链接已签发。原链接无法再次读取；请与员工本人核对后，重新验证并明确签发新链接。新签发会替换此前恢复密钥。' }
      return
    }
    if (receipt?.state === 'ABORTED' || receipt?.retryable) {
      settlePendingFor(currentUserId() || loaded.user)
      notice.value = '服务器已确认上次提交未执行，账号没有因此改变。如需继续，请重新发起安全操作并重新验证本人身份。'
      return
    }
    if (receipt?.sealed) {
      unknownOutcome.value = false
      settlePendingFor(currentUserId() || loaded.user)
      notice.value = '该未决请求此前已安全结束，不会再次执行；未声称原操作成功。'
      return
    }
    if (receipt?.state === 'PENDING' && receipt.processing) {
      error.value = ''
      notice.value = '服务器仍在处理上次提交，请稍后再次查询；不要重复提交。'
      return
    }
    unknownOutcome.value = true
    if (receipt?.state === 'PENDING' && receipt.unknown) {
      error.value = ''
      notice.value = '上次提交已超过处理租约，结果无法确认。请完成本人验证后安全结束该未决请求，或使用新密码登录核对。'
      return
    }
    error.value = ''
    notice.value = '上次操作尚未确认：服务器记录的该提交编号不属于当前操作，也未找到匹配的可读收据。请核对账号实际状态；如结果无法确认，可完成本人验证后安全结束该未决请求。'
  })
}
async function sealUnknown() {
  if (busy.value || !requestId || !pendingKind || !sealConfirm.value || !proof.valid.value || proof.method.value !== 'password') return
  const action = accountWriteAction(pendingKind), attempt = loadGeneration
  await run(async () => {
    const result = await sealUnknownWrite(requestId, action, 'unknown-outcome')
    if (disposed || attempt !== loadGeneration) return
    proof.invalidate(); sealConfirm.value = false
    if (result?.state === 'COMMITTED' || result?.completed) {
      unknownOutcome.value = false
      notice.value = '服务器显示原提交已完成。请重新查询账号状态核对，不会再次执行原提交。'
      return
    }
    if (result?.state === 'ABORTED' || result?.retryable) {
      settlePendingFor(currentUserId() || status.value?.user || '')
      notice.value = '服务器已确认原提交未执行，已解除本条阻断。如需继续，请重新发起安全操作并重新验证本人身份。'
      return
    }
    settlePendingFor(currentUserId() || status.value?.user || '')
    notice.value = '已记录原结果未知并安全结束该未决请求；未声称原操作成功。如需继续，请重新发起并重新验证本人身份。'
  })
}
async function issueRecovery() {
  if (busy.value || uncertain.value || !proof.valid.value || proof.method.value !== 'password' || !recoveryUser.value || recoveryReason.value.trim().length < 12) return
  const reservation = reserveWrite('recovery')
  if (!reservation) return
  const id = reservation.id, writeUser = reservation.user, run = loadGeneration, busyToken = beginBusy()
  recoveryLink.value = null; linkCopied.value = false
  error.value = ''; notice.value = ''
  try {
    const result = await adminIssueRecovery(recoveryUser.value, recoveryReason.value, id)
    if (disposed || run !== loadGeneration) return
    invalidateProof()
    if (result?.already_issued) {
      settlePendingFor(writeUser); recoveryLink.value = null
      notice.value = '该请求已签发过；为避免重复交付，请核对原链接，或重新验证后签发新链接。'
      return
    }
    if (typeof result?.recovery_url !== 'string' || !result.recovery_url || !result.target) {
      uncertain.value = true; error.value = ''; notice.value = ''
      return
    }
    await nextTick()
    if (disposed || run !== loadGeneration) return
    recoveryLink.value = result; settlePendingFor(writeUser)
    notice.value = '重置链接已签发，请私下交付已核验本人。'
  } catch (e) {
    clearRejectedPending(writeUser, e, id)
    if (disposed || run !== loadGeneration) return
    if (isUnauthenticatedError(e)) { resetAfterSessionLoss(); error.value = accountErrorMessage(e, '会话已失效，请重新登录。'); return }
    invalidateProof()
    if (isUncertainWrite(e) || isReceiptHold(e)) { uncertain.value = true; error.value = isReceiptHold(e) ? accountErrorMessage(e) : ''; notice.value = '' }
    else { settlePendingFor(writeUser); error.value = accountErrorMessage(e) }
  } finally { endBusy(busyToken) }
}
async function copyRecoveryLink() {
  if (!recoveryLink.value) return
  try { await navigator.clipboard.writeText(recoveryLink.value.recovery_url); linkCopied.value = true }
  catch { error.value = '链接未复制，请允许本机页面使用剪贴板后重试。' }
}
async function openRecoveryFlow() {
  if (busy.value) return
  await close()
  await router.push(recoveryTarget.value)
}
function onSessionBoundary() {
  resetAfterSessionLoss(null)
  error.value = '登录状态已变化，请重新登录或重新验证。'
}
watch(() => props.identity, (next, previous) => { if (next !== previous) { if (previous && next) clearPendingAccountWrite(previous); resetAfterSessionLoss(null); if (next) void load() } })
watch(proof.valid, valid => {
  if (!valid) { sealConfirm.value = false; onProofInvalidated(); proofKey.value++ }
})
onMounted(() => { window.addEventListener('hbos:session-boundary', onSessionBoundary); void load() })
onBeforeUnmount(() => {
  disposed = true; loadGeneration++
  window.removeEventListener('hbos:session-boundary', onSessionBoundary)
  clearAllSecrets(); requestId = ''; pendingKind = ''; uncertain.value = false
})
</script>
<style src="@/theme/account.css"></style>
<style scoped>
.account-security{padding:var(--hbos-space-6)}
.account-security-heading{display:flex;align-items:center;justify-content:space-between;gap:var(--hbos-space-4);padding-bottom:var(--hbos-space-4);border-bottom:1px solid var(--hbos-border-default)}
.account-security-heading h3{margin:0 0 var(--hbos-space-2)}
.account-security-heading p{margin:0;color:var(--hbos-text-secondary)}
.account-security-heading>span{flex:none;padding:4px 10px;border-radius:999px;background:var(--hbos-bg-subtle,#f4f2ff);color:var(--hbos-text-secondary);font-size:var(--hbos-font-meta)}
.r6-security-rows>.r6-security-row:first-child{border-top:0}
.panel-heading{display:flex;align-items:center;justify-content:space-between;gap:var(--hbos-space-3)}
.panel-heading h4{margin:0}
.account-dialog{max-height:calc(100dvh - 180px);overflow-y:auto;padding-right:2px}
.account-dialog .r6-dialog-lead{display:flex;align-items:center;gap:var(--hbos-space-4);margin-bottom:var(--hbos-space-5)}
.account-dialog .r6-dialog-lead h3{margin:0 0 var(--hbos-space-1);font-size:var(--hbos-font-section-title)}
.account-dialog .r6-dialog-lead p{margin:0;color:var(--hbos-text-secondary)}
.account-dialog .ant-steps{margin-bottom:var(--hbos-space-5)}
.account-dialog .proof-form{margin:0 0 var(--hbos-space-4)}
.r6-verification-notice{margin:0 0 var(--hbos-space-4);padding:var(--hbos-space-3) var(--hbos-space-4);border:1px solid var(--hbos-border-default);border-radius:var(--hbos-radius-control);background:var(--hbos-bg-canvas);color:var(--hbos-text-secondary);line-height:var(--hbos-line-body)}
.r6-password-step .r6-field-feedback{margin:calc(var(--hbos-space-1) * -1) 0 var(--hbos-space-4);color:var(--hbos-text-secondary);font-size:var(--hbos-font-meta);line-height:var(--hbos-line-small)}
.r6-password-complete .ant-result{padding:var(--hbos-space-4) 0}
.r6-binding-card{display:flex;align-items:center;gap:var(--hbos-space-3);padding:var(--hbos-space-4);border:1px solid var(--hbos-border-default);border-radius:var(--hbos-radius-card);margin:var(--hbos-space-4) 0}
.r6-binding-card>div{flex:1;min-width:0}
.r6-binding-card h3{margin:0 0 var(--hbos-space-1)}
.r6-binding-card p{margin:0;color:var(--hbos-text-secondary)}
.r6-recovery-item{display:flex;align-items:center;gap:var(--hbos-space-3);padding:var(--hbos-space-4) 0;border-bottom:1px solid var(--hbos-border-default)}
.r6-recovery-item>.anticon{color:var(--hbos-brand-violet);font-size:var(--hbos-font-section-title)}
.r6-recovery-item>div{flex:1;min-width:0}
.r6-recovery-item p{margin:var(--hbos-space-1) 0 0;color:var(--hbos-text-secondary)}
.r6-channel-list{display:grid;gap:var(--hbos-space-2);margin-top:var(--hbos-space-4);padding:var(--hbos-space-3) var(--hbos-space-4);background:var(--hbos-bg-canvas);border-radius:var(--hbos-radius-control)}
.r6-channel-list>div{display:flex;align-items:center;justify-content:space-between;gap:var(--hbos-space-3)}
.r6-channel-list span{color:var(--hbos-text-secondary);font-size:var(--hbos-font-meta)}
.r6-channel-list strong{font-size:var(--hbos-font-meta);font-weight:var(--hbos-weight-medium);overflow-wrap:anywhere;text-align:right}
.r6-modal-actions{display:flex;align-items:center;justify-content:flex-end;flex-wrap:wrap;gap:var(--hbos-space-3);margin-top:var(--hbos-space-5);padding-top:var(--hbos-space-4);border-top:1px solid var(--hbos-border-default)}
.account-more-tools{margin-top:var(--hbos-space-4);border-top:1px solid var(--hbos-border-default)}
.account-more-tools>summary{cursor:pointer;min-height:44px;padding:var(--hbos-space-3) 0;color:var(--hbos-text-primary);font-weight:var(--hbos-weight-medium)}
.r6-tools-note{margin:0 0 var(--hbos-space-3);color:var(--hbos-text-secondary);font-size:var(--hbos-font-meta);line-height:var(--hbos-line-small)}
@media(max-width:767px){.account-security{padding:var(--hbos-space-5)}.account-dialog{max-height:calc(100dvh - 130px);padding-right:0}.account-dialog{max-height:calc(100dvh - 180px);overflow-y:auto;padding-right:2px}
.account-dialog .r6-dialog-lead{align-items:flex-start}.r6-modal-actions>.ant-btn{flex:1;min-height:44px;height:auto;white-space:normal}}
</style>
