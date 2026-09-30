<template>
  <main class="account-page"><section class="glass-surface change-card">
    <RouterLink to="/hbos/profile">HBOS · 账号与安全</RouterLink><h1>{{ kindLabel(kind) }}</h1>
    <a-alert v-if="error" :message="error" type="warning" show-icon /><a-alert v-if="notice" :message="notice" type="info" show-icon />
    <template v-if="completed"><p>安全变更已完成，请重新登录。旧访问路径已撤销，通知的实际发送结果可在账号与安全查看。</p><a-button type="primary" @click="router.replace('/hbos/login?status=account_changed')">重新登录</a-button></template>
    <template v-else-if="!change && !participant">
      <a-alert v-if="kind === 'custody'" message="此为独立高风险交接，需要 Site 专项许可。接任者在自己的浏览器验证身份、设置并验证新密码及 MFA，最终由当前负责人再次验证并确认。" type="warning" show-icon />
      <p v-else-if="kind === 'roles'">使用双方永久个人账号，仅交接逐项选择的角色。接任者须已有本人账号；不合并账号或业务资料。</p>
      <p v-else-if="kind === 'identity_restore'">原飞书身份不可用时，由获准组织管理员核验本人和归属。仅恢复到本人普通账号，保留历史，不继承原管理员权限。</p>
      <p v-else>原 HBOS User、密码、角色和资料保留。旧飞书在新身份验证、冲突检查和明确确认完成后才失效。</p>
      <form class="change-form" @submit.prevent="begin">
        <label for="change-reason">本人或组织核验依据（12–500 字，请勿填写密码、验证码或身份 Token）</label><a-textarea id="change-reason" v-model:value="reason" :maxlength="500" />
        <template v-if="kind === 'roles'"><label>明确选择交接的角色</label><a-checkbox-group v-model:value="roles" :options="actions?.role_choices || []" /></template>
        <template v-if="kind === 'identity_restore'"><a-checkbox v-model:checked="newPersonal">本人尚无个人账号，验证后开通永久普通账号</a-checkbox><template v-if="!newPersonal"><label for="change-target">已核验本人的普通账号登录名</label><a-input id="change-target" v-model:value="target" autocomplete="off" /></template></template>
        <OwnAccountVerification :key="proofKey" :password-only="kind !== 'rebind'" @verified="proven = true" />
        <a-button type="primary" html-type="submit" :loading="busy" :disabled="!proven || reason.trim().length < 12 || (kind === 'roles' && !roles.length)">发起短时验证申请</a-button>
      </form>
    </template>
    <template v-else-if="change">
      <a-steps :current="step" size="small" :items="[{title:'验证身份'},{title:'核对冲突'},{title:'双方确认'},{title:'一次提交'}]" />
      <p v-if="change.expires_in">申请剩余约 {{ Math.ceil(change.expires_in / 60) }} 分钟；超时或取消不改变旧绑定。</p>
      <template v-if="!participant && !change.new_identity">
        <p>将短时邀请私下交付已核验当事人。邀请只允许验证本次操作，不授予账号访问权。</p><a-button v-if="invitationUrl" @click="copyInvitation">复制短时邀请</a-button><a-button v-if="kind === 'rebind' && invitationUrl" @click="continueSameBrowser">在此浏览器验证本人新飞书</a-button><p v-if="!invitationUrl">邀请仅在发起时提供；遗失时请取消并重新发起。</p>
      </template>
      <template v-if="participant && change.requires_feishu_verification"><p>请授权本次操作中的本人飞书。此授权回调只验证身份，不会自动开户或登录目标账号。</p><a-button type="primary" :loading="busy" @click="authorize">授权验证新飞书身份</a-button></template>
      <template v-if="change.new_identity">
        <a-descriptions :column="1" size="small"><a-descriptions-item label="目标 HBOS User">{{ change.target?.display_name || '验证后开通本人普通账号' }} · {{ change.target?.login_name }}</a-descriptions-item><a-descriptions-item label="旧飞书">{{ change.old_identity?.fingerprint || '无当前有效绑定' }}</a-descriptions-item><a-descriptions-item label="新飞书">{{ change.new_identity.display_name }} · {{ change.new_identity.fingerprint }}</a-descriptions-item><a-descriptions-item label="身份范围">企业已验证 · 应用 {{ change.new_identity.app_id }}</a-descriptions-item><a-descriptions-item label="新身份已有账号">{{ change.source ? `${change.source.display_name} · ${change.source.login_name}` : '无' }}</a-descriptions-item></a-descriptions>
        <ul><li v-for="effect in change.effects" :key="effect">{{ effect }}</li></ul><p v-if="change.roles?.length">将交接的角色：{{ change.roles.join('、') }}</p>
        <a-alert v-if="change.conflict" message="新身份已有其他账号。默认不抢占或交换账号；管理员职责优先使用接任者个人账号。只有明确批准具体来源迁出，并验证来源账号仍有可用密码入口，才能继续。" type="warning" show-icon />
        <template v-if="participant && change.source && !change.source_proven">
          <form class="change-form" @submit.prevent="verifySource"><label for="source-password">上述来源账号的当前密码</label><a-input-password id="source-password" v-model:value="sourcePassword" autocomplete="current-password" /><template v-if="sourceTmp"><label for="source-otp">来源账号已有 MFA</label><a-input-password id="source-otp" v-model:value="sourceOtp" autocomplete="one-time-code" /></template><a-button html-type="submit" :loading="busy" :disabled="!sourcePassword">验证来源账号和保留的登录入口</a-button></form>
          <p v-if="!change.conflict">如该账号仅飞书登录，可先在当前浏览器登录本人账号，通过账号与安全验证码验证，再返回此页点击：</p><a-button v-if="!change.conflict" :loading="busy" @click="verifySourceWithSession">使用当前浏览器的本人验证</a-button>
        </template>
        <template v-if="participant && kind === 'custody' && change.source_proven && !change.credentials_verified">
          <form class="change-form" @submit.prevent="prepareCredentials"><label for="custody-new-password">接任者自行设置新 Administrator 密码（至少 16 字符）</label><a-input-password id="custody-new-password" v-model:value="newPassword" autocomplete="new-password" /><label for="custody-confirm">再次输入新密码</label><a-input-password id="custody-confirm" v-model:value="confirmation" autocomplete="new-password" /><a-button html-type="submit" :disabled="newPassword.length < 16 || newPassword !== confirmation" :loading="busy">准备新凭据和 MFA</a-button></form>
          <form v-if="mfaQr" class="change-form" @submit.prevent="verifyCredentials"><p>由接任者本人添加认证器，不截图或转发二维码。</p><img :src="mfaQr" alt="接任者本人 MFA 注册二维码" class="mfa-qr" /><label for="custody-proof-password">重新输入刚设置的新密码</label><a-input-password id="custody-proof-password" v-model:value="credentialPassword" autocomplete="new-password" /><label for="custody-new-otp">新认证器验证码</label><a-input-password id="custody-new-otp" v-model:value="credentialOtp" autocomplete="one-time-code" /><a-button html-type="submit" :loading="busy" :disabled="!credentialPassword || !credentialOtp">验证新密码与新 MFA</a-button></form>
        </template>
        <template v-if="participant && !change.recipient_accepted"><a-checkbox v-model:checked="accepted">我已核对本人身份、账号归属和上述生效影响</a-checkbox><a-button type="primary" :loading="busy" :disabled="!accepted || !change.source_proven || change.conflict || (kind === 'custody' && !change.credentials_verified)" @click="accept">确认本次参与</a-button></template>
        <p v-if="participant && change.recipient_accepted">本人已确认，等待发起人在原浏览器再次验证并最终提交。</p>
        <template v-if="!participant">
          <OwnAccountVerification :key="proofKey" :password-only="kind !== 'rebind'" @verified="proven = true" />
          <template v-if="change.conflict"><a-checkbox v-model:checked="migrationConfirmed">我明确批准已展示的新身份从该来源账号迁出，保留其账号、角色、数据及可用密码入口</a-checkbox><a-button :disabled="!proven || !migrationConfirmed" :loading="busy" @click="approveMigration">批准此具体迁出方案</a-button></template>
          <template v-else><a-checkbox v-model:checked="accepted">我明确确认上述目标、双方身份和生效影响</a-checkbox><a-button type="primary" danger :disabled="!proven || !accepted || !change.ready" :loading="busy" @click="commit">一次性提交安全变更</a-button></template>
        </template>
      </template>
      <div class="buttons"><a-button :loading="busy" @click="refresh">刷新实际验证状态</a-button><a-button v-if="participant && ownerOperation" @click="returnToOwner">返回发起人确认</a-button><a-button v-if="participant && change.new_identity" danger :loading="busy" @click="rejectParticipation">拒绝并取消本次变更</a-button><a-button v-if="!participant" danger :loading="busy" @click="cancel">取消申请，保留旧绑定</a-button></div>
    </template>
  </section></main>
</template>
<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import OwnAccountVerification from '@/components/account/OwnAccountVerification.vue'
import { changeActions, getChange, getParticipant, changePost, kindLabel, type ChangeKind, type ChangeActions, type AccountChange } from '@/services/accountChanges'
import { clearFrappeCsrfToken } from '@/services/frappeClient'
const route = useRoute(), router = useRouter(), change = ref<AccountChange | null>(null), actions = ref<ChangeActions | null>(null)
const participant = ref(false), ownerOperation = ref(String(route.query.operation || '')), kind = ref<ChangeKind>(['rebind','roles','custody','identity_restore'].includes(String(route.query.kind)) ? route.query.kind as ChangeKind : 'rebind')
const reason = ref(''), roles = ref<string[]>([]), target = ref(''), newPersonal = ref(false), invitationUrl = ref(''), proven = ref(false), proofKey = ref(0)
const busy = ref(false), error = ref(''), notice = ref(''), completed = ref(false), accepted = ref(false), migrationConfirmed = ref(false)
const sourcePassword = ref(''), sourceOtp = ref(''), sourceTmp = ref(''), newPassword = ref(''), confirmation = ref(''), mfaQr = ref(''), credentialPassword = ref(''), credentialOtp = ref('')
const step = computed(() => !change.value?.new_identity ? 0 : change.value.conflict || !change.value.source_proven ? 1 : !change.value.recipient_accepted ? 2 : 3)
function consumeProof() { proven.value = false; proofKey.value++; accepted.value = false }
async function run(action: () => Promise<void>) { busy.value = true; error.value = ''; notice.value = ''; try { await action() } catch (e) { error.value = e instanceof Error ? e.message : '无法完成操作，请刷新实际状态。'; consumeProof() } finally { busy.value = false } }
async function load() { change.value = participant.value ? await getParticipant() : await getChange(ownerOperation.value); kind.value = change.value.kind; if (participant.value && change.value.can_return_to_initiator) ownerOperation.value = change.value.operation }
async function refresh() { await run(load) }
async function begin() { await run(async () => { const result = await changePost<{operation: string; invitation_url: string}>('begin', {kind:kind.value,reason:reason.value,roles:roles.value,target_user:target.value,new_personal_account:Number(newPersonal.value)}); ownerOperation.value = result.operation; invitationUrl.value = result.invitation_url; consumeProof(); await router.replace({path:'/hbos/account-change',query:{operation:result.operation}}); await load() }) }
async function copyInvitation() { await run(async () => { await navigator.clipboard.writeText(invitationUrl.value); notice.value = '短时邀请已复制，请私下交付已核验本人。' }) }
async function continueSameBrowser() { await run(async () => { const hash = new URL(invitationUrl.value).hash.slice(1), parts = new URLSearchParams(hash); await changePost('redeem_invitation', {operation:parts.get('operation'),invitation:parts.get('invitation')}); invitationUrl.value = ''; participant.value = true; await load() }) }
async function authorize() { await run(async () => { const result = await changePost<{authorize_url:string}>('start_authorization'); window.location.assign(result.authorize_url) }) }
async function verifySource() { await run(async () => { const result = await changePost<{mfa_required?:boolean;tmp_id?:string}>('verify_source',{password:sourcePassword.value,otp:sourceOtp.value,tmp_id:sourceTmp.value}); if (result.mfa_required) { sourceTmp.value = result.tmp_id || ''; return }; sourcePassword.value = ''; sourceOtp.value = ''; sourceTmp.value = ''; await load() }) }
async function verifySourceWithSession() { await run(async () => { await changePost('verify_source'); await load() }) }
async function approveMigration() { await run(async () => { await changePost('authorize_source_migration',{operation:ownerOperation.value,confirm:1}); consumeProof(); migrationConfirmed.value = false; await load() }) }
async function prepareCredentials() { await run(async () => { try { mfaQr.value = (await changePost<{mfa_qr:string}>('prepare_custody_credentials',{new_password:newPassword.value,confirmation:confirmation.value})).mfa_qr } finally { newPassword.value = ''; confirmation.value = '' } }) }
async function verifyCredentials() { await run(async () => { try { await changePost('verify_custody_credentials',{password:credentialPassword.value,otp:credentialOtp.value}); mfaQr.value = ''; await load() } finally { credentialPassword.value = ''; credentialOtp.value = '' } }) }
async function accept() { await run(async () => { await changePost('accept_participation',{confirm:1}); accepted.value = false; await load() }) }
async function returnToOwner() { participant.value = false; consumeProof(); await refresh() }
async function commit() { await run(async () => { const result = await changePost<{completed:boolean}>('commit_change',{operation:ownerOperation.value,confirm:1}); completed.value = result.completed; consumeProof(); mfaQr.value = ''; invitationUrl.value = ''; clearFrappeCsrfToken() }) }
async function cancel() { await run(async () => { await changePost('cancel',{operation:ownerOperation.value}); invitationUrl.value = ''; await router.replace('/hbos/profile') }) }
async function rejectParticipation() { await run(async () => { await changePost('cancel_participation'); mfaQr.value = ''; change.value = null; notice.value = '本次变更已取消，原绑定与账号保留。'; await router.replace('/hbos/login?status=cancelled') }) }
onMounted(async () => { await run(async () => { const parts = new URLSearchParams(window.location.hash.slice(1)); if (parts.has('invitation')) { const token = parts.get('invitation'), operation = parts.get('operation'); window.history.replaceState(null,'',window.location.pathname); await changePost('redeem_invitation',{operation,invitation:token}); participant.value = true; await load() } else if (ownerOperation.value) { await load() } else if (route.query.kind) { actions.value = await changeActions(); if (!actions.value[kind.value]) throw new Error('当前账号或 Site 尚未获准执行此操作。Administrator 绑定本人飞书请使用账号与安全的原密码验证入口。') } else { participant.value = true; await load() } }) })
</script>
<style scoped>.account-page{min-height:100vh;padding:30px 20px;background:linear-gradient(135deg,#edf4ff,#f5fcfa)}.change-card{max-width:720px;margin:auto;padding:28px;border-radius:24px}.change-card h1{font-size:25px}.change-card p,.change-card li{color:#64748b;line-height:1.8}.change-form{display:grid;gap:10px;margin:20px 0}.change-form label{font-weight:600}.buttons{display:flex;gap:10px;flex-wrap:wrap;margin-top:20px}.change-card :deep(.ant-alert){margin:14px 0}.change-card :deep(.ant-checkbox-wrapper){margin:12px 0}.mfa-qr{max-width:240px;width:100%}</style>
