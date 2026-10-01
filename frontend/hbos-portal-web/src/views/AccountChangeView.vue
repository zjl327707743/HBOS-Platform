<template>
  <AccountLayout :title="kindLabel(kind)" wide description="逐步核对身份、账号归属与生效影响。提交前原绑定继续可用。">
    <RouterLink to="/hbos/profile">返回账号与安全</RouterLink>
    <a-alert v-if="error" :message="error" type="warning" show-icon /><a-alert v-if="notice" :message="notice" type="info" show-icon />
    <a-skeleton v-if="loading" active />
    <a-alert v-if="uncertain" message="提交结果尚未确认，请先刷新实际状态。若会话已变化，请重新登录后在账号与安全查询，避免再次提交。" type="warning" show-icon />
    <a-button v-if="uncertain" size="large" :loading="busy" @click="refresh">查询上次提交结果</a-button>
    <template v-if="completed || change?.state === 'Completed'"><p>安全变更已完成，请重新登录。旧访问路径已撤销，通知的实际发送结果可在账号与安全查看。</p><a-button size="large" type="primary" @click="router.replace('/hbos/login?status=account_changed')">重新登录</a-button></template>
    <template v-else-if="change && ['Cancelled','Expired'].includes(change.state || '')"><a-result status="info" :title="stateLabel(change.state || '')" sub-title="本次申请已结束，原绑定保留。"><template #extra><a-button size="large" @click="router.replace('/hbos/profile')">返回账号与安全</a-button></template></a-result></template>
    <template v-else-if="!loading && !change && !participant && actions && !error">
      <a-alert v-if="kind === 'custody'" message="此为独立高风险交接，需要 专项授权。接任者在自己的浏览器验证身份、设置并验证新密码及 MFA，最终由当前负责人再次验证并确认。" type="warning" show-icon />
      <p v-else-if="kind === 'roles'">使用双方永久个人账号，仅交接逐项选择的角色。接任者须已有本人账号；不合并账号或业务资料。</p>
      <p v-else-if="kind === 'identity_restore'">原飞书身份不可用时，由获准组织管理员核验本人和归属。仅恢复到本人普通账号，保留历史，不继承原管理员权限。</p>
      <p v-else>原账号、密码、角色和资料保留。旧飞书在新身份验证、冲突检查和明确确认完成后才失效。</p>
      <a-form class="change-form" layout="vertical" @submit.prevent="begin">
        <label for="change-reason">本人或组织核验依据（12–500 字，请勿填写密码或验证码）</label><a-textarea id="change-reason" v-model:value="reason" :maxlength="500" />
        <template v-if="kind === 'roles'"><label>明确选择交接的角色</label><a-checkbox-group v-model:value="roles" :options="actions?.role_choices || []" /></template>
        <template v-if="kind === 'identity_restore'"><a-checkbox v-model:checked="newPersonal">本人尚无个人账号，验证后开通永久普通账号</a-checkbox><template v-if="!newPersonal"><label for="change-target">已核验本人的普通账号登录名</label><a-input size="large" id="change-target" v-model:value="target" autocomplete="off" /></template></template>
        <OwnAccountVerification :key="proofKey" :password-only="kind !== 'rebind'" @verified="proof.sync" @invalidated="proof.invalidate" />
        <a-button size="large" type="primary" html-type="submit" :loading="busy" :disabled="busy || uncertain || !proven || reason.trim().length < 12 || (kind === 'roles' && !roles.length)">发起短时验证申请</a-button>
      </a-form>
    </template>
    <template v-else-if="change">
      <p role="status">{{ stateLabel(change.state || 'Invited') }}</p>
      <a-steps :current="step" size="small" :items="[{title:'验证身份'},{title:'核对冲突'},{title:'双方确认'},{title:'一次提交'}]" />
      <p v-if="change.expires_in">申请剩余约 {{ Math.ceil(remaining / 60) }} 分钟；超时或取消不改变旧绑定。</p>
      <template v-if="!participant && !change.new_identity">
        <p>将短时邀请私下交付已核验当事人。邀请只允许验证本次操作，不授予账号访问权。</p><a-button size="large" v-if="invitationUrl" @click="copyInvitation">复制短时邀请</a-button><a-button size="large" v-if="kind === 'rebind' && invitationUrl" @click="continueSameBrowser">在此浏览器验证本人新飞书</a-button><p v-if="!invitationUrl">邀请仅在发起时提供；遗失时请取消并重新发起。</p>
      </template>
      <template v-if="participant && change.requires_feishu_verification"><p>请授权本次操作中的本人飞书。此授权回调只验证身份，不会自动开户或登录目标账号。</p><a-button size="large" type="primary" :loading="busy" @click="authorize">授权验证新飞书身份</a-button></template>
      <template v-if="change.new_identity">
        <a-descriptions :column="1" size="small"><a-descriptions-item label="目标账号">{{ change.target?.display_name || '验证后开通本人普通账号' }} · {{ change.target?.login_name }}</a-descriptions-item><a-descriptions-item label="旧飞书">{{ change.old_identity?.fingerprint || '无当前有效绑定' }}</a-descriptions-item><a-descriptions-item label="新飞书">{{ change.new_identity.display_name }} · {{ change.new_identity.fingerprint }}</a-descriptions-item><a-descriptions-item label="企业身份">已核验</a-descriptions-item><a-descriptions-item label="新身份已有账号">{{ change.source ? `${change.source.display_name} · ${change.source.login_name}` : '无' }}</a-descriptions-item></a-descriptions>
        <ul><li v-for="effect in change.effects" :key="effect">{{ effect }}</li></ul><p v-if="change.roles?.length">将交接的角色：{{ change.roles.join('、') }}</p>
        <a-alert v-if="change.conflict" message="新身份已有其他账号。默认不抢占或交换账号；管理员职责优先使用接任者个人账号。只有明确批准具体来源迁出，并验证来源账号仍有可用密码入口，才能继续。" type="warning" show-icon />
        <template v-if="participant && change.source && !change.source_proven">
          <a-form class="change-form" layout="vertical" @submit.prevent="verifySource"><label for="source-password">上述来源账号的当前密码</label><a-input-password size="large" id="source-password" v-model:value="sourcePassword" autocomplete="current-password" /><template v-if="sourceTmp"><label for="source-otp">来源账号已有二次认证</label><a-input-password size="large" id="source-otp" v-model:value="sourceOtp" autocomplete="one-time-code" /></template><a-button size="large" html-type="submit" :loading="busy" :disabled="!sourcePassword">验证来源账号和保留的登录入口</a-button></a-form>
          <p v-if="!change.conflict">如该账号仅飞书登录，可先在当前浏览器登录本人账号，通过账号与安全验证码验证，再返回此页点击：</p><a-button size="large" v-if="!change.conflict" :loading="busy" @click="verifySourceWithSession">使用当前浏览器的本人验证</a-button>
        </template>
        <template v-if="participant && kind === 'custody' && change.source_proven && !change.credentials_verified">
          <a-form class="change-form" layout="vertical" @submit.prevent="prepareCredentials"><label for="custody-new-password">接任者自行设置新管理员密码（至少 16 字符）</label><a-input-password size="large" id="custody-new-password" v-model:value="newPassword" autocomplete="new-password" /><label for="custody-confirm">再次输入新密码</label><a-input-password size="large" id="custody-confirm" v-model:value="confirmation" autocomplete="new-password" /><a-button size="large" html-type="submit" :disabled="newPassword.length < 16 || newPassword !== confirmation" :loading="busy">准备新密码和二次认证</a-button></a-form>
          <a-form v-if="mfaQr" class="change-form" layout="vertical" @submit.prevent="verifyCredentials"><p>由接任者本人添加认证器，不截图或转发二维码。</p><img :src="mfaQr" alt="接任者本人 MFA 注册二维码" class="mfa-qr" /><label for="custody-proof-password">重新输入刚设置的新密码</label><a-input-password size="large" id="custody-proof-password" v-model:value="credentialPassword" autocomplete="new-password" /><label for="custody-new-otp">新认证器验证码</label><a-input-password size="large" id="custody-new-otp" v-model:value="credentialOtp" autocomplete="one-time-code" /><a-button size="large" html-type="submit" :loading="busy" :disabled="!credentialPassword || !credentialOtp">验证新密码与新 MFA</a-button></a-form>
        </template>
        <template v-if="participant && !change.recipient_accepted"><a-checkbox v-model:checked="accepted">我已核对本人身份、账号归属和上述生效影响</a-checkbox><a-button size="large" type="primary" :loading="busy" :disabled="busy || uncertain || !accepted || !change.source_proven || change.conflict || (kind === 'custody' && !change.credentials_verified)" @click="accept">确认本次参与</a-button></template>
        <p v-if="participant && change.recipient_accepted">本人已确认，等待发起人在原浏览器再次验证并最终提交。</p>
        <template v-if="!participant">
          <OwnAccountVerification :key="proofKey" :password-only="kind !== 'rebind'" @verified="proof.sync" @invalidated="proof.invalidate" />
          <template v-if="change.conflict"><a-checkbox v-model:checked="migrationConfirmed">我明确批准已展示的新身份从该来源账号迁出，保留其账号、角色、数据及可用密码入口</a-checkbox><a-button size="large" :disabled="busy || uncertain || !proven || !migrationConfirmed" :loading="busy" @click="approveMigration">批准此具体迁出方案</a-button></template>
          <template v-else><a-checkbox v-model:checked="accepted">我明确确认上述目标、双方身份和生效影响</a-checkbox><a-button size="large" type="primary" danger :disabled="busy || uncertain || !proven || !accepted || !change.ready" :loading="busy" @click="commit">一次性提交安全变更</a-button></template>
        </template>
      </template>
      <div class="buttons"><a-button size="large" :loading="busy" @click="refresh">刷新实际验证状态</a-button><a-button size="large" v-if="participant && ownerOperation" @click="returnToOwner">返回发起人确认</a-button><a-button size="large" v-if="participant && change.new_identity" danger :loading="busy" @click="rejectParticipation">拒绝并取消本次变更</a-button><a-button size="large" v-if="!participant" danger :loading="busy" @click="cancel">取消申请，保留旧绑定</a-button></div>
    </template>
  </AccountLayout>
</template>
<script setup lang="ts">
import { computed, onMounted, onBeforeUnmount, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AccountLayout from '@/components/account/AccountLayout.vue'
import { useAccountProof } from '@/composables/useAccountProof'
import { isUncertainWrite } from '@/services/accountErrors'
import OwnAccountVerification from '@/components/account/OwnAccountVerification.vue'
import { changeActions, getChange, getParticipant, changePost, kindLabel, stateLabel, type ChangeKind, type ChangeActions, type AccountChange } from '@/services/accountChanges'
import { clearFrappeCsrfToken } from '@/services/frappeClient'
const route = useRoute(), router = useRouter(), change = ref<AccountChange | null>(null), actions = ref<ChangeActions | null>(null)
const participant = ref(false), ownerOperation = ref(String(route.query.operation || '')), kind = ref<ChangeKind>(['rebind','roles','custody','identity_restore'].includes(String(route.query.kind)) ? route.query.kind as ChangeKind : 'rebind')
const reason = ref(''), roles = ref<string[]>([]), target = ref(''), newPersonal = ref(false), invitationUrl = ref(''), proofKey = ref(0)
const busy = ref(false), error = ref(''), notice = ref(''), completed = ref(false), accepted = ref(false), migrationConfirmed = ref(false)
const sourcePassword = ref(''), sourceOtp = ref(''), sourceTmp = ref(''), newPassword = ref(''), confirmation = ref(''), mfaQr = ref(''), credentialPassword = ref(''), credentialOtp = ref('')
const loading = ref(true), uncertain = ref(false), proof = useAccountProof(), proven = computed(() => proof.valid.value), expiry = ref(0), now = ref(Date.now()), remaining = computed(() => Math.max(0, Math.ceil((expiry.value - now.value) / 1000)))
let generation = 0, disposed = false, internalNavigation = false, ticker: ReturnType<typeof setInterval> | undefined, beginRequest = ''
const step = computed(() => !change.value?.new_identity ? 0 : change.value.conflict || !change.value.source_proven ? 1 : !change.value.recipient_accepted ? 2 : 3)
function consumeProof() { proof.invalidate(); proofKey.value++; accepted.value = false }
async function post<T>(method: string, data: Record<string,unknown> = {}): Promise<T> { const version = generation; const result = await changePost<T>(method,data); if (disposed || version !== generation) throw new Error('route changed'); return result }
async function navigate(query: Record<string,string>) { internalNavigation = true; try { await router.replace({path:'/hbos/account-change',query}) } finally { internalNavigation = false } }
async function run(action: () => Promise<void>, writing = true) { if (busy.value || (writing && uncertain.value)) return; const version = generation; busy.value = true; error.value = ''; notice.value = ''; try { await action() } catch (e) { if (!disposed && version === generation) { uncertain.value = writing && isUncertainWrite(e); error.value = e instanceof Error ? e.message : '无法完成操作，请重试。'; consumeProof() } } finally { if (!disposed && version === generation) busy.value = false } }
async function load() { const version = generation; const loaded = participant.value ? await getParticipant() : await getChange(ownerOperation.value); if (disposed || version !== generation) return; change.value = loaded; kind.value = loaded.kind; expiry.value = loaded.expires_in === undefined ? 0 : Date.now() + loaded.expires_in * 1000; if (participant.value && loaded.can_return_to_initiator) ownerOperation.value = loaded.operation }
async function afterWrite(message: string) { notice.value = message; try { await load() } catch { error.value = '操作已完成，但后续状态未读取。请刷新实际状态，不需要再次提交。' } }
async function refresh() { await run(async () => {
 if (!ownerOperation.value && beginRequest && uncertain.value) {
  const found = await getChange('', beginRequest); ownerOperation.value = found.operation; await navigate({operation:found.operation})
  notice.value = '已查到申请。邀请未重新发送；可以取消此申请后再发起。'
 }
 await load(); uncertain.value = false
 if (change.value?.state === 'Completed') { completed.value = true; clearSecrets() }
}, false) }
async function begin() { if (!proven.value || reason.value.trim().length < 12) return; await run(async () => { beginRequest ||= crypto.randomUUID(); const result = await post<{operation:string;invitation_url:string}>('begin',{kind:kind.value,reason:reason.value,roles:roles.value,target_user:target.value,new_personal_account:Number(newPersonal.value),request_id:beginRequest}); ownerOperation.value = result.operation; invitationUrl.value = result.invitation_url; consumeProof(); await navigate({operation:result.operation}); await afterWrite('申请已发起，原绑定继续可用。') },true) }
async function copyInvitation() { await run(async () => { await navigator.clipboard.writeText(invitationUrl.value); notice.value = '短时邀请已复制，请私下交付已核验本人。' },false) }
async function continueSameBrowser() { await run(async () => { const hash = new URL(invitationUrl.value).hash.slice(1), parts = new URLSearchParams(hash); await post('redeem_invitation', {operation:parts.get('operation'),invitation:parts.get('invitation')}); invitationUrl.value = ''; participant.value = true; await load() }) }
async function authorize() { await run(async () => { const result = await post<{authorize_url:string}>('start_authorization'); window.location.assign(result.authorize_url) },false) }
async function verifySource() { await run(async () => { const result = await post<{mfa_required?:boolean;tmp_id?:string}>('verify_source',{password:sourcePassword.value,otp:sourceOtp.value,tmp_id:sourceTmp.value}); if (result.mfa_required) { sourceTmp.value = result.tmp_id || ''; return }; sourcePassword.value = ''; sourceOtp.value = ''; sourceTmp.value = ''; await afterWrite('来源账号已验证。') }) }
async function verifySourceWithSession() { await run(async () => { await post('verify_source'); await afterWrite('来源账号已验证。') }) }
async function approveMigration() { await run(async () => { await post('authorize_source_migration',{operation:ownerOperation.value,confirm:1}); consumeProof(); migrationConfirmed.value = false; await afterWrite('迁出方案已批准。') }) }
async function prepareCredentials() { await run(async () => { try { mfaQr.value = (await post<{mfa_qr:string}>('prepare_custody_credentials',{new_password:newPassword.value,confirmation:confirmation.value})).mfa_qr } finally { newPassword.value = ''; confirmation.value = '' } }) }
async function verifyCredentials() { await run(async () => { try { await post('verify_custody_credentials',{password:credentialPassword.value,otp:credentialOtp.value}); mfaQr.value = ''; await afterWrite('新密码与二次认证已验证。') } finally { credentialPassword.value = ''; credentialOtp.value = '' } }) }
async function accept() { await run(async () => { await post('accept_participation',{confirm:1}); accepted.value = false; await afterWrite('本次参与已确认，等待最终提交。') }) }
async function returnToOwner() { participant.value = false; consumeProof(); await refresh() }
async function commit() { if (!proven.value || !accepted.value || !change.value?.ready) return; await run(async () => { const result = await post<{completed:boolean}>('commit_change',{operation:ownerOperation.value,confirm:1}); completed.value = result.completed; consumeProof(); mfaQr.value = ''; invitationUrl.value = ''; clearFrappeCsrfToken() },true) }
async function cancel() { await run(async () => { await post('cancel',{operation:ownerOperation.value}); invitationUrl.value = ''; await router.replace('/hbos/profile') }) }
async function rejectParticipation() { await run(async () => { await post('cancel_participation'); mfaQr.value = ''; change.value = null; notice.value = '本次变更已取消，原绑定与账号保留。'; await router.replace('/hbos/login?status=cancelled') }) }
function clearSecrets() { sourcePassword.value = ''; sourceOtp.value = ''; sourceTmp.value = ''; newPassword.value = ''; confirmation.value = ''; mfaQr.value = ''; credentialPassword.value = ''; credentialOtp.value = ''; invitationUrl.value = ''; accepted.value = false; migrationConfirmed.value = false; reason.value = ''; roles.value = []; target.value = ''; newPersonal.value = false; consumeProof() }
async function initialize() {
 generation++; const version = generation; clearSecrets(); change.value = null; actions.value = null; error.value = ''; notice.value = ''; completed.value = false; uncertain.value = false; beginRequest = ''; participant.value = false; busy.value = false; loading.value = true; ownerOperation.value = String(route.query.operation || '')
 kind.value = ['rebind','roles','custody','identity_restore'].includes(String(route.query.kind)) ? route.query.kind as ChangeKind : 'rebind'
 const parts = new URLSearchParams(route.hash.slice(1)), token = parts.get('invitation'), operation = parts.get('operation')
 try {
  if (token) { await navigate({}); await post('redeem_invitation',{operation,invitation:token}); participant.value = true; await load() }
  else if (ownerOperation.value) await load()
  else if (route.query.kind) { const available = await changeActions(); if (disposed || version !== generation) return; actions.value = available; if (!available[kind.value]) throw new Error('当前账号尚未获准执行此操作，请返回账号与安全。') }
  else { participant.value = true; await load() }
 } catch (e) { if (!disposed && version === generation) error.value = e instanceof Error ? e.message : '无法读取申请，请重试。' }
 finally { if (!disposed && version === generation) loading.value = false }
}
watch(() => route.fullPath, () => { if (!internalNavigation) void initialize() }, {flush:'sync'})
onMounted(() => { void initialize(); ticker = setInterval(() => { now.value = Date.now(); if (change.value && expiry.value && remaining.value === 0 && !['Completed','Cancelled','Expired'].includes(change.value.state || '')) { clearSecrets(); change.value = {...change.value,state:'Expired',ready:false} } },1000) })
onBeforeUnmount(() => { disposed = true; generation++; clearSecrets(); if (ticker) clearInterval(ticker) })
</script>
<style scoped>.change-form{margin:var(--hbos-space-5) 0;display:grid;gap:var(--hbos-space-3)}.change-form label{font-weight:var(--hbos-weight-medium);font-size:var(--hbos-font-body)}.buttons{display:flex;flex-wrap:wrap;gap:var(--hbos-space-3);margin-top:var(--hbos-space-5)}.mfa-qr{max-width:240px;width:100%}.ant-checkbox-wrapper{margin:var(--hbos-space-3) 0}</style>
