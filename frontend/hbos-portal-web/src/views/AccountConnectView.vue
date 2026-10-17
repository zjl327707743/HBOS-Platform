<template>
  <AccountLayout :title="completed ? '账号已就绪' : pending?.intent === 'link' ? '确认绑定本人飞书' : pending?.intent === 'login_mfa' ? '完成二次认证' : '确认账号归属'" description="核对本人身份和目标账号，再继续。">
    <a-alert v-if="error" :message="error" type="warning" show-icon role="alert" /><a-skeleton v-if="loading" active />
    <template v-else-if="completed"><a-result status="success" :title="completed.created ? '普通账号已开通' : '账号验证已完成'" sub-title="密码和飞书进入同一个账号。" /><p>登录名：<strong>{{ completed.login_name }}</strong></p><p v-if="completed.password_optional">可直接使用飞书工作。需要密码时，在账号与安全中按需设置。</p><a-alert v-if="workspaceError" :message="workspaceError" type="info" show-icon /><a-button size="large" type="primary" block :loading="busy" @click="enterWorkspace">{{ workspaceError ? '重试加载工作台' : '进入工作台' }}</a-button></template>
    <template v-else-if="uncertain"><a-alert message="账号操作的结果尚未确认。请先查询当前账号，避免重复绑定或开户。" type="warning" show-icon /><a-button size="large" :loading="busy" @click="checkOutcome">查询当前账号状态</a-button><div class="account-buttons"><RouterLink to="/hbos/profile">查看账号与安全</RouterLink><RouterLink to="/hbos/login">返回登录</RouterLink></div></template>
    <template v-else-if="pending && remaining">
      <p>本次飞书身份：{{ pending.display_name }}</p><p class="account-meta" role="status">剩余 {{ remaining }} 秒</p>
      <template v-if="pending.intent === 'link'"><p>将绑定到当前账号：<strong>{{ pending.user }}</strong>，保留原密码、角色和资料。</p><a-button size="large" type="primary" block :loading="busy" @click="complete('confirm_link')">确认绑定</a-button></template>
      <template v-else><p v-if="pending.intent === 'choose'">已有账号请验证并绑定原账号；首次开户使用永久普通账号。</p><a-form class="account-form" layout="vertical" @submit.prevent="complete(pending.intent === 'login_mfa' ? 'login_mfa' : 'bind_existing')">
        <template v-if="pending.intent === 'choose'"><a-form-item label="已有账号" html-for="connect-user"><a-input id="connect-user" v-model:value="username" size="large" autocomplete="username" :disabled="busy" /></a-form-item><a-form-item label="原账号密码" html-for="connect-password"><a-input-password id="connect-password" v-model:value="password" size="large" autocomplete="current-password" :disabled="busy" /></a-form-item></template>
        <a-form-item v-if="tmpId" label="二次认证验证码" html-for="connect-otp"><a-input-password id="connect-otp" v-model:value="otp" size="large" inputmode="numeric" autocomplete="one-time-code" :disabled="busy" /><a-button :disabled="busy" @click="cancelMfa">取消二次认证</a-button></a-form-item><a-button size="large" type="primary" html-type="submit" :loading="busy" :disabled="busy || Boolean(tmpId && !otp) || (pending.intent === 'choose' && (!username.trim() || !password))">{{ pending.intent === 'login_mfa' ? (tmpId ? '验证并登录' : '开始二次认证') : '验证并绑定已有账号' }}</a-button>
      </a-form><div class="account-buttons"><a-button v-if="pending.intent === 'choose' && !tmpId" size="large" :loading="busy" @click="complete('create_new')">开通本人普通账号</a-button></div></template>
      <div class="account-buttons"><RouterLink to="/hbos/reset-password">忘记密码或需要恢复</RouterLink><a-button :disabled="busy" @click="cancel">取消并返回登录</a-button></div>
    </template>
    <div v-else-if="!loading" class="account-buttons"><a-button size="large" @click="load">重试读取授权状态</a-button><RouterLink to="/hbos/login">返回登录，重新授权</RouterLink></div>
  </AccountLayout>
</template>
<script setup lang="ts">
import { onMounted, onBeforeUnmount, ref, watch, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AccountLayout from '@/components/account/AccountLayout.vue'
import { getPending, getSecurity, guestAccountPost, type PendingAccount, type CompletedAccount } from '@/services/accountApi'
import { callFrappePostMethod, clearFrappeCsrfToken } from '@/services/frappeClient'
import { usePortalStore } from '@/stores/portal'
import { accountErrorMessage, isUncertainWrite } from '@/services/accountErrors'
import { accountRedirect } from '@/services/accountNavigation'
const route = useRoute(), router = useRouter(), portal = usePortalStore(), pending = ref<PendingAccount|null>(null), completed = ref<CompletedAccount|null>(null)
const error = ref(''), workspaceError = ref(''), busy = ref(false), loading = ref(true), uncertain = ref(false), username = ref(''), password = ref(''), otp = ref(''), tmpId = ref(''), expiry = ref(0), now = ref(Date.now()), remaining = computed(() => Math.max(0,Math.ceil((expiry.value-now.value)/1000)))
let disposed = false, generation = 0, timer: ReturnType<typeof setInterval>|undefined
function clearSecrets() { password.value = ''; otp.value = ''; tmpId.value = '' }
function cancelMfa() { clearSecrets(); error.value = '' }
watch(username, () => { if (tmpId.value) cancelMfa() })
async function cancel() { if (busy.value) return; await runCancelPending(); clearSecrets(); pending.value = null; await router.replace('/hbos/login?status=cancelled') }
async function runCancelPending() { try { if (pending.value?.intent === 'link') await callFrappePostMethod('hbos_portal.auth.accounts.complete_pending',{action:'cancel'},{'X-HBOS-Pending-CSRF':pending.value.csrf}); else await guestAccountPost('complete_pending',{action:'cancel'},pending.value?.csrf) } catch { /* The UI still clears its secrets; the server ticket has its fixed TTL. */ } }
async function enterWorkspace() { if (busy.value || !completed.value) return; busy.value = true; workspaceError.value = ''; try { await portal.bootstrap(); if (!disposed) await router.replace(accountRedirect(completed.value.redirect_to)) } catch { if (!disposed) workspaceError.value = '账号操作已完成，工作台暂未加载。可重试加载，无需重复绑定或开户。' } finally { if (!disposed) busy.value = false } }
async function complete(action:string) { if (busy.value || !pending.value || uncertain.value || !remaining.value) return; busy.value = true; error.value = ''; const version = generation; try {
 const data = {action,username:username.value,password:password.value,otp:otp.value,tmp_id:tmpId.value}
 const result: CompletedAccount = pending.value.intent === 'link' ? await callFrappePostMethod('hbos_portal.auth.accounts.complete_pending',data,{'X-HBOS-Pending-CSRF':pending.value.csrf}) : await guestAccountPost('complete_pending',data,pending.value.csrf)
 if (disposed || version !== generation) return
 if (result.mfa_required) { tmpId.value = result.tmp_id || ''; return }
 if (!result.completed) { clearSecrets(); error.value = result.error?.message || '账号操作未完成，请核对后重试。'; return }
 clearSecrets(); clearFrappeCsrfToken(); portal.clearSession(); completed.value = result; pending.value = null
 } catch (e) { if (!disposed && version === generation) { clearSecrets(); uncertain.value = isUncertainWrite(e); error.value = accountErrorMessage(e,'账号操作未确认，请先查询实际状态。') } } finally { if (!disposed && version === generation) busy.value = false } }
async function checkOutcome() { if (busy.value) return; busy.value = true; error.value = ''; try { const current = await getSecurity(); if (current.feishu_bound) { error.value = `当前登录名：${current.login_name}，已有飞书绑定。本次操作结果仍需在账号与安全核对。` } else error.value = '当前账号尚无已确认绑定，请返回账号与安全核对。' } catch { error.value = '当前会话无法确认结果，请返回登录后核对账号与安全。' } finally { busy.value = false } }
async function load() { const version = ++generation; clearSecrets(); username.value = ''; pending.value = null; completed.value = null; uncertain.value = false; loading.value = true; error.value = ''; try { const result = await getPending(); if (!disposed && version === generation) { pending.value = result; expiry.value = Date.now()+result.expires_in*1000 } } catch (e) { if (!disposed && version === generation) error.value = accountErrorMessage(e,'待处理授权无效或已过期，请重新授权。') } finally { if (!disposed && version === generation) loading.value = false } }
watch(() => route.fullPath, load)
onMounted(() => { void load(); timer = setInterval(() => { now.value = Date.now(); if (pending.value && !remaining.value) { clearSecrets(); pending.value = null; error.value = '待处理授权已过期，请返回登录重新授权。' } },1000) })
onBeforeUnmount(() => { disposed = true; generation++; clearSecrets(); pending.value = null; if (timer) clearInterval(timer) })
</script>
