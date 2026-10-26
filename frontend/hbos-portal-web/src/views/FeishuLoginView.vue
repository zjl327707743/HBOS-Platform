<template>
  <AccountLayout variant="login" title="登录工作台">
    <a-alert v-if="callbackMessage" id="login-feedback" :type="callbackTone" show-icon :message="callbackMessage" role="alert" />
    <template v-if="authenticated">
      <a-alert :message="exiting ? '正在退出当前账号，请稍候…' : submitting ? '已登录，正在加载工作台…' : '已登录，工作台暂未加载。请重试。'" type="info" show-icon role="status" />
      <a-button v-if="!submitting" size="large" type="primary" block @click="resumeWorkspace">重试加载</a-button>
      <a-button size="large" block :loading="exiting" :disabled="submitting && !exiting" @click="exitCurrentAccount">退出并换一个账号</a-button>
    </template>
    <template v-else>
      <div v-if="loading" role="status" aria-live="polite"><a-skeleton active :paragraph="{ rows: 1 }" /><p class="account-meta">正在读取可用的登录方式…</p></div>
      <template v-else>
        <template v-if="status?.configured && !statusError">
          <a-button size="large" :type="showPassword ? 'default' : 'primary'" block :disabled="submitting" @click="beginFeishuLogin"><MessageOutlined aria-hidden="true" />使用飞书登录</a-button>
          <div class="account-divider"><span>或</span></div>
          <a-button v-if="!showPassword" size="large" block @click="revealPassword"><KeyOutlined aria-hidden="true" />使用账号密码</a-button>
        </template>
        <a-alert v-else-if="statusError" :message="statusError" type="warning" show-icon role="alert" />
        <a-alert v-else message="飞书登录尚未开通，请使用已设置的账号密码。" type="info" show-icon role="status" />
        <a-button v-if="statusError" class="status-retry" :disabled="submitting" @click="retryLoginStatus">重试读取登录方式</a-button>
      </template>
      <a-form v-if="showPassword" id="password-login-form" class="account-form" layout="vertical" :aria-describedby="callbackMessage ? 'login-feedback' : undefined" @submit.prevent="submitAccountLogin" @keydown.enter="guardComposition">
        <a-form-item label="账号" html-for="hbos-username"><a-input id="hbos-username" v-model:value="username" size="large" autocomplete="username" placeholder="请输入登录名" :disabled="submitting" /></a-form-item>
        <a-form-item label="密码" html-for="hbos-password"><a-input-password id="hbos-password" v-model:value="password" size="large" autocomplete="current-password" placeholder="请输入密码" :disabled="submitting" /></a-form-item>
        <a-form-item v-if="tmpId" label="二次认证验证码" html-for="login-otp" help="请输入当前账号已有认证器或已授权渠道的验证码。"><a-input-password id="login-otp" v-model:value="otp" size="large" inputmode="numeric" autocomplete="one-time-code" :disabled="submitting" /><a-button html-type="button" :disabled="submitting" @click="cancelMfa">取消二次认证</a-button></a-form-item>
        <a-button size="large" type="primary" block html-type="submit" :loading="submitting" :disabled="!canSubmit">{{ tmpId ? '验证并进入工作台' : '登录' }}</a-button>
      </a-form>
      <div class="account-buttons"><RouterLink :to="username.trim().toLowerCase() === 'administrator' ? '/hbos/reset-password?administrator=1' : '/hbos/reset-password'">忘记密码？</RouterLink></div>
    </template>
    <template #footer>首次使用或无法登录，请联系系统管理员。</template>
    <template #version><span v-if="candidateLabel">{{ candidateLabel }}</span></template>
  </AccountLayout>
</template>
<script setup lang="ts">
import { computed, onMounted, onBeforeUnmount, ref, watch, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { KeyOutlined, MessageOutlined } from '@ant-design/icons-vue'
import AccountLayout from '@/components/account/AccountLayout.vue'
import type { FeishuLoginStatus } from '@/contracts/p1'
import { FrappeRequestError, loginWithPassword } from '@/services/frappeClient'
import { getFeishuLoginStatus } from '@/services/p1Api'
import { usePortalStore } from '@/stores/portal'
import { accountRedirect } from '@/services/accountNavigation'
import { ensurePortalSession, resetPortalSession, signOutPortalSession } from '@/services/portalSessionCoordinator'
const route = useRoute(), router = useRouter(), portal = usePortalStore()
const loading = ref(true), submitting = ref(false), authenticated = ref(false), status = ref<FeishuLoginStatus|null>(null), statusError = ref(''), error = ref('')
const username = ref(''), password = ref(''), otp = ref(''), tmpId = ref('')
const candidateLabel = import.meta.env.VITE_ACCOUNT_PREVIEW_LABEL || ''
const callbackConsumed = ref(false)
const passwordExpanded = ref(false), exiting = ref(false)
function retryLoginStatus() { if (showPassword.value) passwordExpanded.value = true; void loadStatus() }
const showPassword = computed(() => passwordExpanded.value || (!loading.value && (!status.value?.configured || Boolean(statusError.value))) || Boolean(tmpId.value))
async function revealPassword() { passwordExpanded.value = true; await nextTick(); document.getElementById('hbos-username')?.focus() }
async function exitCurrentAccount() {
 if (submitting.value) return
 submitting.value = true; exiting.value = true; error.value = ''
 const redirect = accountRedirect(route.query.redirect_to)
 try { await signOutPortalSession(); if (!disposed) { authenticated.value = false; callbackConsumed.value = false; passwordExpanded.value = false; cancelMfa(); username.value = ''; await router.replace({ path: '/hbos/login', query: { status: 'signed_out', redirect_to: redirect } }) } }
 catch (e) { if (!disposed) error.value = e instanceof FrappeRequestError ? e.message : '服务端退出尚未确认，请重试退出。' }
 finally { if (!disposed) { submitting.value = false; exiting.value = false } }
}
let disposed = false
const statusMessages: Record<string,string> = {
 logout_unconfirmed:'本机内容已清理，服务端退出尚未确认。连接恢复后请重新登录，或返回后重试退出。',
 cancelled:'已取消飞书授权，您可以重新选择登录方式。', config_required:'飞书登录暂不可用，请改用账号密码或稍后重试。', invalid_state:'授权已过期、已使用或与当前浏览器不匹配，请重新发起。', identity_unmapped:'该飞书身份尚未关联 HBOS 账号，请联系系统管理员。', existing_account_requires_link:'当前浏览器已有账号，请在账号与安全中验证本人后绑定飞书。', identity_conflict:'此飞书身份与账号存在冲突，请联系管理员核对。', identity_revoked:'旧飞书绑定已撤销或更换，请使用原账号密码或联系管理员恢复。', account_busy:'账号正在完成另一项操作，请稍后重新授权。', same_identity:'新旧飞书身份相同，无需更换绑定。', personal_account_required:'接任者请先使用本人永久账号。', operation_invalid:'账号变更验证已失效，请重新发起。', account_changed:'账号登录方式已更换，请重新登录。', onboarding_dependency_missing:'开户服务暂不可用，请联系管理员。', member_scope_denied:'您尚未在此应用的获准成员范围内，请联系管理员。', account_disabled:'此账号当前不可用，请联系管理员。', tenant_rejected:'此企业身份未获准使用 HBOS。', tenant_evidence_missing:'暂时无法核验企业身份，请联系管理员。', application_tenant_mismatch:'企业身份核验未完成，请联系管理员。', member_identity_mismatch:'本人身份核验未通过，请重新授权。', member_status_missing:'无法核验当前成员状态，请联系管理员并提供诊断编号。', member_status_invalid:'无法核验当前成员状态，请联系管理员。', member_inactive:'您的飞书账号尚未激活。', member_disabled:'您的飞书账号已停用，请联系管理员。', member_departed:'此成员已离职或退出，无法登录。', member_department_missing:'成员准入信息不完整，请联系管理员。', member_api_failed:'暂时无法核验成员信息，请稍后重试或联系管理员。', external_member_rejected:'此入口仅供获准企业成员使用。', exchange_failed:'飞书身份核验未完成，请重新授权。', session_required:'请先登录，再继续访问原页面。', signed_out:'已安全退出当前账号。',
}
const callbackMessage = computed(() => { const message = error.value || (!callbackConsumed.value && !authenticated.value && statusMessages[String(route.query.status || '')]); const trace = typeof route.query.trace === 'string' && /^[a-f0-9]{16}$/.test(route.query.trace) ? route.query.trace : ''; return message && trace ? `${message} 诊断编号：${trace}` : message })
const callbackTone = computed(() => ['cancelled','signed_out'].includes(String(route.query.status || '')) ? 'info' : 'warning')
const canSubmit = computed(() => Boolean(username.value.trim() && password.value && (!tmpId.value || otp.value) && !submitting.value))
function cancelMfa() { password.value = ''; otp.value = ''; tmpId.value = ''; error.value = '' }
function guardComposition(e: KeyboardEvent) { if (e.isComposing || e.keyCode === 229) { e.preventDefault(); e.stopPropagation() } }
watch(username, () => { if (tmpId.value) cancelMfa() })
watch(() => route.query.status, () => { cancelMfa(); authenticated.value = false; callbackConsumed.value = false })
async function resumeWorkspace() { if (submitting.value) return; submitting.value = true; error.value = ''; try { await ensurePortalSession({ force: true }); if (!disposed) await router.replace(accountRedirect(route.query.redirect_to)) } catch (e) { if (!disposed) error.value = e instanceof FrappeRequestError ? e.message : '工作台暂时无法加载，请重试。' } finally { if (!disposed) submitting.value = false } }
async function submitAccountLogin() {
 if (!canSubmit.value) return; callbackConsumed.value = true; submitting.value = true; error.value = ''
 try { const result = await loginWithPassword(username.value.trim(),password.value,otp.value,tmpId.value); if (disposed) return; if (result.tmp_id && result.verification) { tmpId.value = result.tmp_id; return }; cancelMfa(); authenticated.value = true; resetPortalSession() }
 catch (e) { if (!disposed) { cancelMfa(); portal.clearSession(); error.value = e instanceof FrappeRequestError ? e.message : '登录请求未确认，请稍后重试。' } }
 finally { if (!disposed) submitting.value = false }
 if (authenticated.value && !disposed) await resumeWorkspace()
}
function beginFeishuLogin() { callbackConsumed.value = true; cancelMfa(); window.location.assign(`/api/method/hbos_portal.auth.feishu.start?redirect_to=${encodeURIComponent(accountRedirect(route.query.redirect_to))}`) }
async function loadStatus() { loading.value = true; statusError.value = ''; try { const loaded = await getFeishuLoginStatus(); if (!disposed) status.value = loaded } catch { if (!disposed) statusError.value = '飞书登录暂不可用，请改用账号密码或稍后重试。' } finally { if (!disposed) loading.value = false } }
onMounted(loadStatus); onBeforeUnmount(() => { disposed = true; cancelMfa() })
</script>
