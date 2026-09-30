<template>
  <section class="setting-card glass-surface account-security">
    <h3>账号与安全</h3><p>密码和飞书进入同一个账号，安全操作保留原有角色与业务资料。</p>
    <a-alert v-if="error" :message="error" type="warning" show-icon role="alert" />
    <a-alert v-if="notice" :message="notice" type="success" show-icon role="status" />
    <a-skeleton v-if="loading && !status" active />
    <a-button v-if="!loading && (!status || stale)" size="large" :loading="busy" @click="load">重试读取账号状态</a-button>
    <template v-if="status">
      <a-descriptions :column="1" size="small"><a-descriptions-item label="登录名">{{ status.login_name }}</a-descriptions-item><a-descriptions-item label="密码">{{ status.has_password ? '已设置' : '尚未设置 · 可使用飞书登录' }}</a-descriptions-item><a-descriptions-item label="飞书">{{ status.feishu_bound ? '已绑定' : '未绑定' }}</a-descriptions-item><a-descriptions-item label="邮箱恢复">{{ status.mail_recovery_available ? '可用' : '暂无可用恢复邮箱' }}</a-descriptions-item></a-descriptions>
      <div class="account-buttons"><a-button size="large" :disabled="busy" @click="open('password')">{{ status.has_password ? '修改密码' : '设置密码' }}</a-button><a-button size="large" :disabled="busy" @click="open('feishu')">{{ status.feishu_bound ? '管理飞书绑定' : '绑定本人飞书' }}</a-button><a-button size="large" @click="router.push(status.administrator ? '/hbos/reset-password?administrator=1' : '/hbos/reset-password')">找回密码与恢复</a-button></div>
      <section v-if="panel" class="account-section" :aria-label="panelTitle">
        <div class="panel-heading"><h4>{{ panelTitle }}</h4><a-button :disabled="busy" @click="close">取消</a-button></div>
        <a-alert v-if="panel === 'feishu' && !status.feishu_configured" message="飞书登录服务当前不可用，请稍后重试；已有密码仍可使用。" type="info" show-icon />
        <a-alert v-if="panel === 'feishu' && status.administrator && !status.administrator_link_enabled && !status.feishu_bound" message="管理员飞书绑定需要专门授权，请联系环境负责人。" type="info" show-icon />
        <OwnAccountVerification :key="proofKey" :password-only="panel === 'admin' || (panel === 'feishu' && (status.feishu_bound || status.administrator))" @verified="proof.sync" @invalidated="proof.invalidate" />
        <a-alert v-if="uncertain" message="上次提交的结果尚未确认。请先查询实际状态，避免重复提交；必要时使用新密码重新登录。" type="warning" show-icon /><a-button v-if="uncertain" @click="checkOutcome">查询上次提交结果</a-button>
        <a-form v-if="panel === 'password'" class="account-form" layout="vertical" @submit.prevent="changePassword">
          <a-form-item label="新登录密码" html-for="security-new-password" :validate-status="passwordError ? 'error' : undefined" :help="passwordError || '请使用符合站点要求的密码，最多 512 字符。'"><a-input-password id="security-new-password" v-model:value="newPassword" size="large" autocomplete="new-password" :disabled="busy || uncertain" /></a-form-item>
          <a-form-item label="再次输入密码" html-for="security-confirm-password" :validate-status="mismatch ? 'error' : undefined" :help="mismatch ? '两次密码不一致。' : undefined"><a-input-password id="security-confirm-password" v-model:value="confirmation" size="large" autocomplete="new-password" :disabled="busy || uncertain" /></a-form-item>
          <a-button size="large" type="primary" html-type="submit" :loading="busy" :disabled="busy || uncertain || !proof.valid.value || !newPassword || mismatch">保存密码</a-button>
        </a-form>
        <template v-if="panel === 'feishu'"><p v-if="status.feishu_bound && !status.has_password">飞书是当前唯一登录方式，请先设置密码再解绑。</p><p v-else-if="status.feishu_bound">解绑后可继续使用当前密码登录。解绑须验证原密码及已有二次认证。</p><a-checkbox v-if="status.feishu_bound && status.has_password" v-model:checked="unlinkConfirmed" :disabled="busy">确认解绑本人飞书，保留密码登录</a-checkbox><div class="account-buttons"><a-button v-if="!status.feishu_bound" size="large" type="primary" :disabled="busy || !proof.valid.value || !status.feishu_configured || (status.administrator && (!status.administrator_link_enabled || proof.method.value !== 'password'))" @click="bind">授权绑定本人飞书</a-button><a-button v-else size="large" danger :disabled="busy || uncertain || !unlinkConfirmed || !proof.valid.value || !status.has_password || proof.method.value !== 'password'" @click="unlink">确认解绑飞书</a-button></div></template>
        <a-form v-if="panel === 'admin'" class="account-form" layout="vertical" @submit.prevent="issueRecovery"><p>核对员工本人和账号归属后签发短时单次链接，由员工本人设置密码。</p><a-form-item label="员工登录名或账号" html-for="recovery-user"><a-input id="recovery-user" v-model:value="recoveryUser" size="large" autocomplete="off" :disabled="busy" /></a-form-item><a-form-item label="身份核验依据" html-for="recovery-reason" help="至少 12 个字符，请勿填写密码或验证码。"><a-textarea id="recovery-reason" v-model:value="recoveryReason" :maxlength="500" :disabled="busy" /></a-form-item><a-button size="large" html-type="submit" :disabled="busy || uncertain || !proof.valid.value || proof.method.value !== 'password' || !recoveryUser || recoveryReason.trim().length < 12" :loading="busy">签发一次性重置链接</a-button><template v-if="recoveryLink"><p>已签发给 {{ recoveryLink.target.display_name }}（{{ recoveryLink.target.login_name }}），仅私下交付本人。</p><a-button @click="copyRecoveryLink">复制一次性链接</a-button><p v-if="linkCopied">链接已复制。</p></template></a-form>
      </section>
      <a-collapse v-if="status.can_admin_recover" class="account-section"><a-collapse-panel key="admin" header="管理员协助"><a-button size="large" :disabled="busy" @click="open('admin')">协助员工恢复账号</a-button></a-collapse-panel></a-collapse>
      <AccountChangeActions />
    </template>
  </section>
</template>
<script setup lang="ts">
import { computed, onMounted, onBeforeUnmount, ref, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { getSecurity, startLink, setPassword, unlinkFeishu, adminIssueRecovery, type SecurityStatus, type RecoveryLink } from '@/services/accountApi'
import { clearFrappeCsrfToken } from '@/services/frappeClient'
import { useAccountProof } from '@/composables/useAccountProof'
import { accountErrorMessage, isUncertainWrite } from '@/services/accountErrors'
import OwnAccountVerification from './OwnAccountVerification.vue'
import AccountChangeActions from './AccountChangeActions.vue'
const router = useRouter(), status = ref<SecurityStatus | null>(null), panel = ref<'password'|'feishu'|'admin'|null>(null)
const newPassword = ref(''), confirmation = ref(''), recoveryUser = ref(''), recoveryReason = ref(''), recoveryLink = ref<RecoveryLink|null>(null), linkCopied = ref(false)
const loading = ref(true), busy = ref(false), error = ref(''), notice = ref(''), stale = ref(false), uncertain = ref(false), proofKey = ref(0), passwordError = ref(''), unlinkConfirmed = ref(false)
const proof = useAccountProof(clearSecrets), mismatch = computed(() => Boolean(confirmation.value && newPassword.value !== confirmation.value))
const panelTitle = computed(() => panel.value === 'password' ? (status.value?.has_password ? '修改密码' : '设置密码') : panel.value === 'admin' ? '协助员工恢复' : '本人飞书绑定')
let disposed = false, trigger: HTMLElement|null = null, requestId = '', pendingKind = ''
function invalidateProof() { proof.invalidate(); proofKey.value++ }
function clearSecrets() { newPassword.value = ''; confirmation.value = ''; recoveryLink.value = null; recoveryUser.value = ''; recoveryReason.value = ''; unlinkConfirmed.value = false }
async function open(action: typeof panel.value) { trigger = document.activeElement as HTMLElement; clearSecrets(); invalidateProof(); error.value = ''; passwordError.value = ''; panel.value = action; await nextTick(); document.querySelector<HTMLElement>('.account-security .proof-form input')?.focus() }
async function close() { if (busy.value) return; clearSecrets(); invalidateProof(); panel.value = null; await nextTick(); trigger?.focus() }
async function load() { loading.value = true; error.value = ''; try { const loaded = await getSecurity(); if (!disposed) { status.value = loaded; stale.value = false; if (!uncertain.value) proof.sync(loaded.proof) } } catch (e) { if (!disposed) { stale.value = true; invalidateProof(); error.value = accountErrorMessage(e, '无法读取账号状态，请重试。') } } finally { if (!disposed) loading.value = false } }
async function run(fn: () => Promise<void>) { if (busy.value) return; busy.value = true; error.value = ''; notice.value = ''; try { await fn() } catch (e) { if (!disposed) { invalidateProof(); error.value = accountErrorMessage(e) } } finally { if (!disposed) busy.value = false } }
async function refreshAfterWrite() { try { status.value = await getSecurity(); stale.value = false } catch { stale.value = true; error.value = '操作已完成，但最新账号状态暂未读取。请重试读取状态，不需要再次提交。' } }
async function bind() { await run(async () => { const result = await startLink(); invalidateProof(); window.location.assign(result.authorize_url) }) }
async function changePassword() { if (uncertain.value || !proof.valid.value || !newPassword.value || newPassword.value !== confirmation.value) return; await run(async () => { requestId = crypto.randomUUID(); pendingKind = 'password'; try { const result = await setPassword(newPassword.value, requestId); invalidateProof(); clearFrappeCsrfToken(); notice.value = `密码已保存，登录名：${result.login_name}。其他旧会话已失效。`; await refreshAfterWrite() } catch (e) { uncertain.value = isUncertainWrite(e); passwordError.value = uncertain.value ? '' : accountErrorMessage(e); throw e } finally { newPassword.value = ''; confirmation.value = '' } }) }
async function unlink() { if (!unlinkConfirmed.value || !proof.valid.value || uncertain.value) return; await run(async () => { requestId = crypto.randomUUID(); pendingKind = 'unlink'; try { await unlinkFeishu(requestId); invalidateProof(); notice.value = '飞书已解绑，原账号和业务资料保留。'; unlinkConfirmed.value = false; await refreshAfterWrite() } catch (e) { uncertain.value = isUncertainWrite(e); throw e } }) }
async function checkOutcome() { await run(async () => { const loaded = await getSecurity(requestId); status.value = loaded; stale.value = false; if (loaded.write_result?.completed || (pendingKind === 'unlink' && !loaded.feishu_bound)) { uncertain.value = false; notice.value = pendingKind === 'password' ? '密码已保存，服务器已确认上次提交。' : pendingKind === 'unlink' ? '飞书已解绑，服务器已确认上次提交。' : '服务器已确认链接签发。若链接未读取，请核对员工后重新验证并签发新链接，旧链接将失效。' } else error.value = '当前尚无法确认上次提交。请重新登录后核对账号状态，避免重复提交。' }) }
async function issueRecovery() { if (!proof.valid.value) return; recoveryLink.value = null; linkCopied.value = false; await run(async () => { if (uncertain.value) return; requestId = crypto.randomUUID(); pendingKind = 'recovery'; try { const result = await adminIssueRecovery(recoveryUser.value, recoveryReason.value, requestId); recoveryLink.value = result.already_issued ? null : result; invalidateProof(); notice.value = '重置链接已签发，请私下交付已核验本人。' } catch (e) { uncertain.value = isUncertainWrite(e); throw e } }) }
async function copyRecoveryLink() { if (!recoveryLink.value) return; try { await navigator.clipboard.writeText(recoveryLink.value.recovery_url); linkCopied.value = true } catch { error.value = '链接未复制，请允许本机页面使用剪贴板后重试。' } }
onMounted(load); onBeforeUnmount(() => { disposed = true; clearSecrets(); requestId = '' })
</script>
<style src="@/theme/account.css"></style>
<style scoped>.account-security{padding:var(--hbos-space-6)}.account-security h3{margin:0 0 var(--hbos-space-2)}.panel-heading{display:flex;align-items:center;justify-content:space-between;gap:var(--hbos-space-3)}.panel-heading h4{margin:0}</style>
