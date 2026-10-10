<template>
  <AccountLayout title="登录 HBOS" eyebrow="企业内部使用" description="使用本人飞书或已有账号密码，进入海滨工作台。">
    <a-alert v-if="callbackMessage" :type="callbackTone" show-icon :message="callbackMessage" role="alert" />
    <template v-if="authenticated"><a-alert message="登录已完成，工作台暂未加载。请重试加载，无需再次输入密码。" type="info" show-icon role="status" /><a-button size="large" type="primary" block :loading="submitting" @click="resumeWorkspace">重试加载工作台</a-button></template>
    <template v-else>
      <a-skeleton v-if="loading" active :paragraph="{rows:1}" />
      <template v-else><a-button size="large" type="primary" block :disabled="submitting || !status?.configured || Boolean(statusError)" @click="beginFeishuLogin"><MessageOutlined /> 使用飞书登录</a-button><p v-if="status?.configured && !statusError" class="account-meta">已启用企业成员登录，新成员可按授权自动开通普通账号。</p><a-alert v-else-if="statusError" :message="statusError" type="warning" show-icon /><p v-else class="account-meta">飞书入口暂不可用，您仍可使用已有账号密码。</p><a-button v-if="statusError" @click="loadStatus">重试读取登录方式</a-button></template>
      <div class="account-divider"><span>账号密码登录</span></div>
      <a-form class="account-form" layout="vertical" @submit.prevent="submitAccountLogin" @keydown.enter="guardComposition">
        <a-form-item label="账号" html-for="hbos-username"><a-input id="hbos-username" v-model:value="username" size="large" autocomplete="username" placeholder="请输入登录名" :disabled="submitting" /></a-form-item>
        <a-form-item label="密码" html-for="hbos-password"><a-input-password id="hbos-password" v-model:value="password" size="large" autocomplete="current-password" placeholder="请输入密码" :disabled="submitting" /></a-form-item>
        <a-form-item v-if="tmpId" label="二次认证验证码" html-for="login-otp" help="请输入当前账号已有认证器或已授权渠道的验证码。"><a-input-password id="login-otp" v-model:value="otp" size="large" inputmode="numeric" autocomplete="one-time-code" :disabled="submitting" /><a-button html-type="button" :disabled="submitting" @click="cancelMfa">取消二次认证</a-button></a-form-item>
        <a-button size="large" block html-type="submit" :loading="submitting" :disabled="!canSubmit">{{ tmpId ? '验证并进入工作台' : '使用密码登录' }}</a-button>
      </a-form>
      <div class="account-buttons"><RouterLink :to="username.trim().toLowerCase() === 'administrator' ? '/hbos/reset-password?administrator=1' : '/hbos/reset-password'">忘记密码或账号恢复</RouterLink></div>
    </template>
    <template #footer>密码和飞书使用同一个账号。已有账号可在“账号与安全”验证本人后绑定飞书；自动开户没有默认密码。</template>
  </AccountLayout>
</template>
<script setup lang="ts">
import { computed, onMounted, onBeforeUnmount, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { MessageOutlined } from '@ant-design/icons-vue'
import AccountLayout from '@/components/account/AccountLayout.vue'
import type { FeishuLoginStatus } from '@/contracts/p1'
import { FrappeRequestError, loginWithPassword } from '@/services/frappeClient'
import { getFeishuLoginStatus } from '@/services/p1Api'
import { usePortalStore } from '@/stores/portal'
import { accountRedirect } from '@/services/accountNavigation'
const route = useRoute(), router = useRouter(), portal = usePortalStore()
const loading = ref(true), submitting = ref(false), authenticated = ref(false), status = ref<FeishuLoginStatus|null>(null), statusError = ref(''), error = ref('')
const username = ref(''), password = ref(''), otp = ref(''), tmpId = ref('')
let disposed = false
const statusMessages: Record<string,string> = {
 cancelled:'已取消飞书授权，您可以重新选择登录方式。', config_required:'飞书登录当前不可用，请稍后重试或联系管理员。', invalid_state:'授权已过期、已使用或与当前浏览器不匹配，请重新发起。', identity_unmapped:'当前成员尚未获准开通账号，请联系管理员。', existing_account_requires_link:'当前浏览器已有账号，请在账号与安全中验证本人后绑定飞书。', identity_conflict:'此飞书身份与账号存在冲突，请联系管理员核对。', identity_revoked:'旧飞书绑定已撤销或更换，请使用原账号密码或联系管理员恢复。', account_busy:'账号正在完成另一项操作，请稍后重新授权。', same_identity:'新旧飞书身份相同，无需更换绑定。', personal_account_required:'接任者请先使用本人永久账号。', operation_invalid:'账号变更验证已失效，请重新发起。', account_changed:'账号登录方式已更换，请重新登录。', onboarding_dependency_missing:'开户服务暂不可用，请联系管理员。', member_scope_denied:'您尚未在此应用的获准成员范围内，请联系管理员。', account_disabled:'此账号当前不可用，请联系管理员。', tenant_rejected:'此企业身份未获准使用 HBOS。', tenant_evidence_missing:'暂时无法核验企业身份，请联系管理员。', application_tenant_mismatch:'企业身份核验未完成，请联系管理员。', member_identity_mismatch:'本人身份核验未通过，请重新授权。', member_status_missing:'无法核验当前成员状态，请联系管理员并提供诊断编号。', member_status_invalid:'无法核验当前成员状态，请联系管理员。', member_inactive:'您的飞书账号尚未激活。', member_disabled:'您的飞书账号已停用，请联系管理员。', member_departed:'此成员已离职或退出，无法登录。', member_department_missing:'成员准入信息不完整，请联系管理员。', member_api_failed:'暂时无法核验成员信息，请稍后重试或联系管理员。', external_member_rejected:'此入口仅供获准企业成员使用。', exchange_failed:'飞书身份核验未完成，请重新授权。', session_required:'请先登录，再继续访问原页面。', signed_out:'已安全退出当前账号。',
}
const callbackMessage = computed(() => { const message = error.value || statusMessages[String(route.query.status || '')]; const trace = typeof route.query.trace === 'string' && /^[a-f0-9]{16}$/.test(route.query.trace) ? route.query.trace : ''; return message && trace ? `${message} 诊断编号：${trace}` : message })
const callbackTone = computed(() => ['cancelled','signed_out'].includes(String(route.query.status || '')) ? 'info' : 'warning')
const canSubmit = computed(() => Boolean(username.value.trim() && password.value && (!tmpId.value || otp.value) && !submitting.value))
function cancelMfa() { password.value = ''; otp.value = ''; tmpId.value = ''; error.value = '' }
function guardComposition(e: KeyboardEvent) { if (e.isComposing || e.keyCode === 229) { e.preventDefault(); e.stopPropagation() } }
watch(username, () => { if (tmpId.value) cancelMfa() })
watch(() => route.query.status, () => { cancelMfa(); authenticated.value = false })
async function resumeWorkspace() { if (submitting.value) return; submitting.value = true; error.value = ''; try { await portal.bootstrap(); if (!disposed) await router.replace(accountRedirect(route.query.redirect_to)) } catch (e) { if (!disposed) error.value = e instanceof FrappeRequestError ? e.message : '工作台暂时无法加载，请重试。' } finally { if (!disposed) submitting.value = false } }
async function submitAccountLogin() {
 if (!canSubmit.value) return; submitting.value = true; error.value = ''
 try { const result = await loginWithPassword(username.value.trim(),password.value,otp.value,tmpId.value); if (disposed) return; if (result.tmp_id && result.verification) { tmpId.value = result.tmp_id; return }; cancelMfa(); authenticated.value = true; portal.clearSession() }
 catch (e) { if (!disposed) { cancelMfa(); portal.clearSession(); error.value = e instanceof FrappeRequestError ? e.message : '登录请求未确认，请稍后重试。' } }
 finally { if (!disposed) submitting.value = false }
 if (authenticated.value && !disposed) await resumeWorkspace()
}
function beginFeishuLogin() { cancelMfa(); window.location.assign(`/api/method/hbos_portal.auth.feishu.start?redirect_to=${encodeURIComponent(accountRedirect(route.query.redirect_to))}`) }
async function loadStatus() { loading.value = true; statusError.value = ''; try { const loaded = await getFeishuLoginStatus(); if (!disposed) status.value = loaded } catch { if (!disposed) statusError.value = '无法读取飞书登录状态，请重试。' } finally { if (!disposed) loading.value = false } }
onMounted(loadStatus); onBeforeUnmount(() => { disposed = true; cancelMfa() })
</script>
