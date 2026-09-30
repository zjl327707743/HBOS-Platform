<template>
  <main class="recovery-page"><section class="glass-surface recovery-card">
    <RouterLink to="/hbos/login">返回登录</RouterLink><h1>找回密码与账号恢复</h1>
    <a-alert v-if="notice" :message="notice" type="info" show-icon />
    <a-alert v-if="error" :message="error" type="warning" show-icon />
    <p>已有飞书绑定时，可先使用飞书登录，再在账号与安全中验证本人并重设密码。没有可用邮箱和飞书时，由管理员核验本人身份后签发一次性恢复凭据。</p>
    <form v-if="!key" @submit.prevent="request"><label for="reset-user">登录名或真实恢复邮箱</label><a-input id="reset-user" v-model:value="username" autocomplete="username" /><a-button html-type="submit" :loading="busy">发送邮箱恢复说明</a-button><label for="reset-key">管理员提供的一次性恢复凭据</label><a-input-password id="reset-key" v-model:value="enteredKey" autocomplete="off" /><a-button :disabled="!enteredKey" @click="key = enteredKey; enteredKey = ''">验证恢复凭据</a-button></form>
    <form v-else @submit.prevent="reset"><label for="reset-password">新登录密码</label><a-input-password id="reset-password" v-model:value="password" autocomplete="new-password" /><label for="reset-confirm">再次输入</label><a-input-password id="reset-confirm" v-model:value="confirmation" autocomplete="new-password" /><template v-if="tmpId"><label for="reset-otp">账号原有二次认证</label><a-input id="reset-otp" v-model:value="otp" autocomplete="one-time-code" /></template><a-button type="primary" html-type="submit" :loading="busy" :disabled="!password || password !== confirmation">保存密码</a-button></form>
  </section></main>
</template>
<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { guestAccountPost, type MfaResult } from '@/services/accountApi'
import { clearFrappeCsrfToken } from '@/services/frappeClient'
const route = useRoute(), router = useRouter()
const key = ref(typeof route.query.key === 'string' ? route.query.key : '')
const enteredKey = ref(''), username = ref(''), password = ref(''), confirmation = ref(''), otp = ref(''), tmpId = ref('')
const busy = ref(false), notice = ref(''), error = ref('')
async function request() { busy.value = true; error.value = ''; try { const result = await guestAccountPost<{message: string}>('request_reset', { user: username.value }); notice.value = result.message } catch { error.value = '恢复请求未完成，请稍后重试或联系管理员。' } finally { busy.value = false } }
async function reset() { busy.value = true; error.value = ''; try { const result = await guestAccountPost<string | MfaResult>('update_password', { key: key.value, new_password: password.value, otp: otp.value, tmp_id: tmpId.value }); if (typeof result !== 'string' && result.mfa_required) { tmpId.value = result.tmp_id || ''; return }; password.value = ''; confirmation.value = ''; key.value = ''; clearFrappeCsrfToken(); await router.replace('/hbos/profile') } catch { password.value = ''; confirmation.value = ''; error.value = '恢复凭据无效、已使用或已过期，或新密码不符合站点策略。' } finally { busy.value = false } }
onMounted(() => { if (route.query.key) window.history.replaceState(window.history.state, '', '/hbos/reset-password') })
</script>
<style scoped>
.recovery-page{display:grid;min-height:100vh;place-items:center;padding:24px;background:linear-gradient(135deg,#edf4ff,#f5fcfa)}.recovery-card{width:min(540px,100%);padding:32px;border-radius:24px}.recovery-card h1{font-size:26px}.recovery-card p{color:#64748b;line-height:1.8}.recovery-card form{display:grid;gap:12px;margin-top:20px}
</style>
