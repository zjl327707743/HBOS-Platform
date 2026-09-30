<template>
  <main class="account-page"><section class="glass-surface account-card">
    <RouterLink to="/hbos/login">HBOS · 企业工作台</RouterLink>
    <h1>{{ completed ? '账号已就绪' : pending?.intent === 'link' ? '确认绑定本人飞书' : pending?.intent === 'login_mfa' ? '完成账号二次认证' : '选择账号归属' }}</h1>
    <a-alert v-if="error" :message="error" type="warning" show-icon />
    <template v-if="completed">
      <p>{{ completed.created ? '永久普通账号已开通。' : '本人飞书与原账号已连接。' }} 密码和飞书进入同一个 User。</p>
      <p>可使用的登录名：<strong>{{ completed.login_name }}</strong></p>
      <p v-if="completed.password_optional">现在可直接使用飞书工作。密码登录是可选项；如需设置，在账号与安全中主动请求本人飞书验证码。</p>
      <a-button type="primary" @click="router.replace(completed.redirect_to || '/hbos')">进入工作台</a-button>
    </template>
    <template v-else-if="pending">
      <p>已验证的飞书身份：{{ pending.display_name }}</p>
      <template v-if="pending.intent === 'link'"><p>将绑定到当前 HBOS 账号：<strong>{{ pending.user }}</strong>。原密码、角色和业务资料保留。</p><a-button type="primary" :loading="busy" @click="complete('confirm_link')">确认绑定</a-button></template>
      <template v-else>
        <p v-if="pending.intent === 'choose'">已有 HBOS 账号时，请绑定原账号，保留原有角色和业务资料。真正新用户可开通永久普通账号。</p>
        <form class="account-form" @submit.prevent="complete(pending.intent === 'login_mfa' ? 'login_mfa' : 'bind_existing')">
          <template v-if="pending.intent === 'choose'"><label for="connect-user">已有账号</label><a-input id="connect-user" v-model:value="username" autocomplete="username" /><label for="connect-password">原账号密码</label><a-input-password id="connect-password" v-model:value="password" autocomplete="current-password" /></template>
          <template v-if="tmpId"><label for="connect-otp">原有二次认证验证码</label><a-input-password id="connect-otp" v-model:value="otp" autocomplete="one-time-code" /></template>
          <a-button type="primary" html-type="submit" :loading="busy">{{ pending.intent === 'login_mfa' ? (tmpId ? '验证并登录' : '开始二次认证') : '验证并绑定已有账号' }}</a-button>
        </form>
        <a-button v-if="pending.intent === 'choose' && !tmpId" :loading="busy" @click="complete('create_new')">我是新用户，开通账号</a-button>
      </template>
      <p><RouterLink to="/hbos/reset-password">忘记原密码或需要恢复</RouterLink></p>
    </template>
    <a-skeleton v-else-if="!error" active />
  </section></main>
</template>
<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { getPending, guestAccountPost, type PendingAccount, type CompletedAccount } from '@/services/accountApi'
import { callFrappePostMethod, clearFrappeCsrfToken } from '@/services/frappeClient'
import { usePortalStore } from '@/stores/portal'
const router = useRouter(), portal = usePortalStore()
const pending = ref<PendingAccount | null>(null), error = ref(''), busy = ref(false)
const completed = ref<CompletedAccount | null>(null)
const username = ref(''), password = ref(''), otp = ref(''), tmpId = ref('')
async function complete(action: string) { if (!pending.value) return; busy.value = true; error.value = ''; try {
  const data = { action, username: username.value, password: password.value, otp: otp.value, tmp_id: tmpId.value }
  let result: CompletedAccount
  if (pending.value.intent === 'link') {
    // Authenticated link uses the standard Frappe CSRF header as well as the
    // pending token. The post helper accepts the extra cookie-bound token.
    result = await callFrappePostMethod('hbos_portal.auth.accounts.complete_pending', data, { 'X-HBOS-Pending-CSRF': pending.value.csrf })
  } else { result = await guestAccountPost('complete_pending', data, pending.value.csrf) }
  if (result.mfa_required) { tmpId.value = result.tmp_id || ''; return }
  if (!result.completed) { error.value = result.error?.message || '账号操作未完成，请核对后重试。'; return }
  password.value = ''; otp.value = ''; tmpId.value = ''; clearFrappeCsrfToken(); portal.clearSession(); await portal.bootstrap(); completed.value = result
} catch { error.value = '无法完成绑定或开户。请检查原账号验证、身份冲突或已撤销绑定；过期时重新发起飞书登录。' } finally { busy.value = false } }
onMounted(async () => { try { pending.value = await getPending() } catch { error.value = '待处理身份已过期，请重新发起飞书授权。' } })
</script>
<style scoped>
.account-page{display:grid;min-height:100vh;place-items:center;padding:24px;background:linear-gradient(135deg,#edf4ff,#f5fcfa)}.account-card{width:min(540px,100%);padding:32px;border-radius:24px}.account-card h1{font-size:26px}.account-card p{color:#64748b;line-height:1.8}.account-form{display:grid;gap:10px;margin:20px 0}
</style>
