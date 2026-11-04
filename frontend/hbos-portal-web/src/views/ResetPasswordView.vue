<template>
  <AccountLayout title="找回密码与账号恢复" description="选择可用恢复方式，核对目标账号后设置新密码。">
    <RouterLink to="/hbos/login">返回登录</RouterLink>
    <a-alert v-if="notice" :message="notice" type="info" show-icon role="status" /><a-alert v-if="error" :message="error" type="warning" show-icon role="alert" />
    <a-skeleton v-if="loading" active />
    <a-result v-else-if="completed" status="success" title="密码已保存" sub-title="原账号和角色保留，旧会话已失效。"><template #extra><a-button size="large" type="primary" @click="router.replace('/hbos/profile')">进入账号与安全</a-button></template></a-result>
    <template v-else-if="uncertain"><a-alert message="保存结果尚未确认。请先查询上次提交，或使用新密码登录后核对，避免重复重置。" type="warning" show-icon /><a-button :loading="busy" @click="checkOutcome">查询上次提交结果</a-button></template>
    <template v-else-if="validation">
      <p>本次只会修改以下账号，请核对后继续：</p><a-descriptions :column="1" size="small"><a-descriptions-item label="姓名">{{ validation.target.display_name }}</a-descriptions-item><a-descriptions-item label="登录名">{{ validation.target.login_name }}</a-descriptions-item></a-descriptions>
      <p role="status">链接单次使用，剩余 {{ remaining }} 秒。保留账号已有的二次认证。</p>
      <a-form class="account-form" layout="vertical" @submit.prevent="reset" @keydown.enter="guardComposition">
        <a-form-item label="新登录密码" html-for="reset-password" :validate-status="passwordError ? 'error' : undefined" :help="passwordError || '请使用符合站点要求的密码，最多 512 字符。'"><a-input-password id="reset-password" v-model:value="password" size="large" autocomplete="new-password" :disabled="busy" /></a-form-item>
        <a-form-item label="再次输入密码" html-for="reset-confirm" :validate-status="mismatch ? 'error' : undefined" :help="mismatch ? '两次密码不一致。' : undefined"><a-input-password id="reset-confirm" v-model:value="confirmation" size="large" autocomplete="new-password" :disabled="busy" /></a-form-item>
        <a-form-item v-if="tmpId" label="二次认证验证码" html-for="reset-otp"><a-input-password id="reset-otp" v-model:value="otp" size="large" inputmode="numeric" autocomplete="one-time-code" :disabled="busy" /><a-button :disabled="busy" @click="cancelMfa">取消二次认证</a-button></a-form-item>
        <a-button size="large" type="primary" html-type="submit" :loading="busy" :disabled="busy || !password || password !== confirmation || !remaining || Boolean(tmpId && !otp)">确认目标并保存密码</a-button>
      </a-form>
    </template>
    <template v-else-if="channels">
      <section v-if="channels.feishu_login && !administrator" class="account-section"><h2>使用本人飞书</h2><p>登录已绑定的本人飞书，进入账号与安全。</p><p>{{ channels.feishu_password_recovery ? '本人查收安全验证码并完成验证后，可按需设置或重设密码。' : '当前无法使用本人收件验证码重设密码，请联系管理员协助。' }}</p><a-button size="large" type="primary" @click="recoverWithFeishu">使用飞书登录</a-button></section>
      <section v-if="channels.verified_email && !administrator" class="account-section"><h2>使用已验证邮箱</h2><a-form class="account-form" layout="vertical" @submit.prevent="request"><a-form-item label="登录名或已验证邮箱" html-for="reset-user"><a-input id="reset-user" v-model:value="username" size="large" autocomplete="username" :disabled="busy" /></a-form-item><a-button size="large" html-type="submit" :loading="busy" :disabled="busy || !username.trim()">发送邮箱恢复说明</a-button></a-form></section>
      <section v-if="!administrator" class="account-section"><h2>联系管理员协助</h2><p>由管理员核对本人和原账号，私下交付短时单次链接。最终密码由您自行设置。</p></section>
      <details :open="administrator" class="account-section"><summary>管理员应急恢复</summary><p>Administrator 使用当前 Mac 的本地应急设密，由本人隐藏输入新密码并完成已有二次认证。普通员工请使用上述渠道。</p><p>在当前环境的 HBOS 启动器执行 <code>admin-password</code>，核对目标环境后由本人操作。</p></details>
    </template>
    <a-button v-if="!loading && !channels && !completed" size="large" @click="initialize">重试读取恢复方式</a-button>
  </AccountLayout>
</template>
<script setup lang="ts">
import { computed, onMounted, onBeforeUnmount, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AccountLayout from '@/components/account/AccountLayout.vue'
import { getRecoveryChannels, getSecurity, guestAccountPost, type MfaResult, type RecoveryChannels, type RecoveryValidation } from '@/services/accountApi'
import { clearFrappeCsrfToken } from '@/services/frappeClient'
import { accountErrorMessage, isUncertainWrite } from '@/services/accountErrors'
const route = useRoute(), router = useRouter(), administrator = computed(() => route.query.administrator === '1')
const channels = ref<RecoveryChannels|null>(null), validation = ref<RecoveryValidation|null>(null), key = ref(''), username = ref(''), password = ref(''), confirmation = ref(''), otp = ref(''), tmpId = ref('')
const loading = ref(true), busy = ref(false), notice = ref(''), error = ref(''), passwordError = ref(''), completed = ref(false), uncertain = ref(false), expiry = ref(0), now = ref(Date.now()), remaining = computed(() => Math.max(0, Math.ceil((expiry.value - now.value) / 1000))), mismatch = computed(() => Boolean(confirmation.value && password.value !== confirmation.value))
let generation = 0, disposed = false, internalNavigation = false, timer: ReturnType<typeof setInterval>|undefined, requestId = ''
function clearSecrets() { password.value = ''; confirmation.value = ''; otp.value = ''; tmpId.value = '' }
function cancelMfa() { clearSecrets(); notice.value = '已取消二次认证，请重新填写密码后验证。' }
function guardComposition(e: KeyboardEvent) { if (e.isComposing || e.keyCode === 229) { e.preventDefault(); e.stopPropagation() } }
async function initialize() {
 const version = ++generation; requestId = ''; clearSecrets(); key.value = ''; validation.value = null; channels.value = null; error.value = ''; notice.value = ''; passwordError.value = ''; completed.value = false; uncertain.value = false; expiry.value = 0; loading.value = true; busy.value = false
 const incoming = new URLSearchParams(route.hash.slice(1)).get('key') || (typeof route.query.key === 'string' ? route.query.key : '')
 key.value = incoming
 try {
  if (incoming) { internalNavigation = true; try { await router.replace({path:'/hbos/reset-password',query:administrator.value ? {administrator:'1'} : {}}) } finally { internalNavigation = false } }
  const loaded = await getRecoveryChannels(); if (disposed || version !== generation) return; channels.value = loaded
  if (incoming) { const result = await guestAccountPost<RecoveryValidation>('validate_recovery',{key:incoming}); if (disposed || version !== generation) return; validation.value = result; expiry.value = Date.now() + result.expires_in * 1000 }
 } catch (e) { if (!disposed && version === generation) { key.value = ''; validation.value = null; error.value = accountErrorMessage(e, incoming ? '恢复链接无效、已使用或过期，请选择可用恢复方式。' : '暂时无法读取恢复方式，请重试。') } }
 finally { if (!disposed && version === generation) loading.value = false }
}
async function request() { if (busy.value || !username.value.trim()) return; busy.value = true; error.value = ''; notice.value = ''; try { const result = await guestAccountPost<{message:string}>('request_reset',{user:username.value}); if (!disposed) notice.value = result.message } catch (e) { if (!disposed) error.value = accountErrorMessage(e, '恢复请求未完成，请稍后重试。') } finally { if (!disposed) busy.value = false } }
function recoverWithFeishu() { clearSecrets(); window.location.assign('/api/method/hbos_portal.auth.feishu.start?redirect_to=%2Fhbos%2Fprofile') }
function saved() { clearSecrets(); key.value = ''; validation.value = null; uncertain.value = false; completed.value = true; clearFrappeCsrfToken() }
async function reset() {
 if (!validation.value || busy.value || uncertain.value || !remaining.value || !password.value || password.value !== confirmation.value || (tmpId.value && !otp.value)) return
 const version = generation; busy.value = true; error.value = ''; passwordError.value = ''; requestId ||= crypto.randomUUID()
 try { const result = await guestAccountPost<string|MfaResult>('update_password',{key:key.value,recovery_context:validation.value.recovery_context,new_password:password.value,otp:otp.value,tmp_id:tmpId.value,request_id:requestId}); if (disposed || version !== generation) return; if (typeof result !== 'string' && result.mfa_required) { tmpId.value = result.tmp_id || ''; return }; saved() }
 catch (e) { if (!disposed && version === generation) { clearSecrets(); uncertain.value = isUncertainWrite(e); error.value = accountErrorMessage(e, '保存结果未确认，请先查询实际状态。'); passwordError.value = uncertain.value ? '' : error.value } }
 finally { if (!disposed && version === generation) busy.value = false }
}
async function checkOutcome() { if (busy.value) return; busy.value = true; error.value = ''; try { const status = await getSecurity(requestId); if (status.write_result?.completed) saved(); else error.value = '当前尚无法确认，请使用新密码登录后核对。' } catch { error.value = '当前会话无法查询，请使用新密码登录后核对。' } finally { busy.value = false } }
watch(() => route.fullPath, () => { if (!internalNavigation) void initialize() }, {flush:'sync'})
onMounted(() => { void initialize(); timer = setInterval(() => { now.value = Date.now(); if (validation.value && !remaining.value) { clearSecrets(); validation.value = null; key.value = ''; error.value = '恢复链接已过期，请重新获取。' } },1000) })
onBeforeUnmount(() => { disposed = true; generation++; clearSecrets(); key.value = ''; validation.value = null; requestId = ''; if (timer) clearInterval(timer) })
</script>
