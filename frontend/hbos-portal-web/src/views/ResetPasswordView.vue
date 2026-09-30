<template>
  <main class="recovery-page"><section class="glass-surface recovery-card">
    <RouterLink to="/hbos/login">返回登录</RouterLink><h1>找回密码与账号恢复</h1>
    <a-alert v-if="notice" :message="notice" type="info" show-icon />
    <a-alert v-if="error" :message="error" type="warning" show-icon />
    <a-skeleton v-if="busy && (!channels || (key && !validation))" active />
    <template v-else-if="validation">
      <p>恢复链接已由服务器验证。本次只会修改以下账号，请核对后继续：</p>
      <a-descriptions :column="1" size="small">
        <a-descriptions-item label="姓名">{{ validation.target.display_name }}</a-descriptions-item>
        <a-descriptions-item label="登录名">{{ validation.target.login_name }}</a-descriptions-item>
        <a-descriptions-item label="账号标识">{{ validation.target.user }}</a-descriptions-item>
      </a-descriptions>
      <p>链接单次使用，剩余有效时间约 {{ Math.ceil(validation.expires_in / 60) }} 分钟。保留账号原有二次认证。</p>
      <form @submit.prevent="reset">
        <label for="reset-password">为以上账号设置新登录密码</label><a-input-password id="reset-password" v-model:value="password" autocomplete="new-password" />
        <label for="reset-confirm">再次输入</label><a-input-password id="reset-confirm" v-model:value="confirmation" autocomplete="new-password" />
        <template v-if="tmpId"><label for="reset-otp">账号原有二次认证</label><a-input-password id="reset-otp" v-model:value="otp" autocomplete="one-time-code" /></template>
        <a-button type="primary" html-type="submit" :loading="busy" :disabled="!password || password !== confirmation">确认目标并保存密码</a-button>
      </form>
    </template>
    <template v-else-if="channels">
      <section v-if="channels.feishu_login && !administrator" class="recovery-channel">
        <h2>使用飞书恢复</h2>
        <p>先登录已绑定的本人飞书，进入账号与安全。密码登录是可选项。</p>
        <p v-if="channels.feishu_password_recovery">在账号与安全中主动请求本人收件验证码，验证后设置或重设密码。</p>
        <p v-else>当前尚未启用本人收件验证码；飞书登录可用，重设密码请联系管理员协助。</p>
        <a-button type="primary" @click="recoverWithFeishu">使用飞书登录</a-button>
      </section>
      <section v-if="channels.verified_email && !administrator" class="recovery-channel">
        <h2>通过已验证邮箱重置</h2>
        <form @submit.prevent="request"><label for="reset-user">登录名或已验证邮箱</label><a-input id="reset-user" v-model:value="username" autocomplete="username" /><a-button html-type="submit" :loading="busy" :disabled="!username.trim()">发送邮箱恢复说明</a-button></form>
      </section>
      <section class="recovery-channel" v-if="!administrator">
        <h2>联系管理员协助</h2><p>请管理员核对您的身份和原账号，再私下交付短时有效的一次性重置链接。打开链接后由您设置密码；管理员不设置或知道最终密码。</p>
      </section>
      <details :open="administrator" class="recovery-channel">
        <summary>Administrator 忘记密码</summary>
        <p>Administrator 使用当前 Mac 的本地应急设密，不接受普通员工恢复链接。使用当前环境 HBOS 启动器执行 <code>admin-password</code>，在本机隐藏输入新密码并确认当前 Site。</p>
        <p>当前 Site：<strong>{{ channels.site }}</strong>。完成后返回登录，以 Administrator 和新密码登录，再完成原有 MFA。</p>
      </details>
    </template>
  </section></main>
</template>
<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getRecoveryChannels, guestAccountPost, type MfaResult, type RecoveryChannels, type RecoveryValidation } from '@/services/accountApi'
import { clearFrappeCsrfToken } from '@/services/frappeClient'
const route = useRoute(), router = useRouter()
const fragmentKey = new URLSearchParams(route.hash.replace(/^#/, '')).get('key')
const key = ref(fragmentKey || (typeof route.query.key === 'string' ? route.query.key : ''))
const administrator = route.query.administrator === '1'
const channels = ref<RecoveryChannels | null>(null), validation = ref<RecoveryValidation | null>(null)
const username = ref(''), password = ref(''), confirmation = ref(''), otp = ref(''), tmpId = ref('')
const busy = ref(false), notice = ref(''), error = ref('')
async function request() { busy.value = true; error.value = ''; try { const result = await guestAccountPost<{message: string}>('request_reset', { user: username.value }); notice.value = result.message } catch { error.value = '恢复请求未完成，请稍后重试或联系管理员。' } finally { busy.value = false } }
function recoverWithFeishu() { window.location.assign('/api/method/hbos_portal.auth.feishu.start?redirect_to=%2Fhbos%2Fprofile') }
async function reset() { if (!validation.value) return; busy.value = true; error.value = ''; try {
  const result = await guestAccountPost<string | MfaResult>('update_password', { key: key.value, recovery_context: validation.value.recovery_context, new_password: password.value, otp: otp.value, tmp_id: tmpId.value })
  if (typeof result !== 'string' && result.mfa_required) { tmpId.value = result.tmp_id || ''; return }
  password.value = ''; confirmation.value = ''; key.value = ''; validation.value = null; clearFrappeCsrfToken(); await router.replace('/hbos/profile')
} catch { password.value = ''; confirmation.value = ''; error.value = '保存未完成：链接无效、已使用或过期，二次认证未通过，或密码不符合站点策略。请核对后重试。' } finally { busy.value = false } }
onMounted(async () => {
  // Consume the URL into component memory, then remove it from browser history.
  // No key is stored in local/session storage or sent in a GET request.
  if (route.query.key || route.hash) await router.replace('/hbos/reset-password')
  busy.value = true
  try { channels.value = await getRecoveryChannels(); if (key.value) validation.value = await guestAccountPost<RecoveryValidation>('validate_recovery', { key: key.value }) }
  catch { key.value = ''; error.value = '恢复链接无效、已使用或已过期。Administrator 请使用本机应急设密；普通员工可选择下方可用渠道。' }
  finally { busy.value = false }
})
</script>
<style scoped>
.recovery-page{display:grid;min-height:100vh;place-items:center;padding:24px;background:linear-gradient(135deg,#edf4ff,#f5fcfa)}.recovery-card{width:min(540px,100%);padding:32px;border-radius:24px}.recovery-card h1{font-size:26px}.recovery-card p{color:#64748b;line-height:1.8}.recovery-card form{display:grid;gap:12px;margin-top:20px}.recovery-channel{padding:16px 0;border-top:1px solid rgba(80,105,140,.12)}.recovery-channel h2{font-size:17px}.recovery-channel summary{cursor:pointer;font-weight:600}
</style>
