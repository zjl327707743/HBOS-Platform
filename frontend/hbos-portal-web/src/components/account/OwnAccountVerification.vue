<template>
  <section class="proof-form" aria-label="本人身份验证" @keydown.enter="onEnter">
    <p>{{ passwordOnly ? '验证当前负责人的密码与已有二次认证。' : '安全操作前，请验证本人身份。' }}</p>
    <a-skeleton v-if="loading" active :paragraph="{ rows: 1 }" />
    <template v-else-if="status">
      <a-radio-group v-if="!passwordOnly && status.has_password && status.feishu_bound" v-model:value="useInbox" :disabled="busy" @change="reset"><a-radio :value="false">当前密码</a-radio><a-radio :value="true" :disabled="!status.feishu_stepup_available">本人飞书验证码</a-radio></a-radio-group>
      <template v-if="passwordMode"><label :for="fieldId + '-password'">当前密码</label><a-input-password :id="fieldId + '-password'" v-model:value="password" size="large" autocomplete="current-password" :disabled="busy" /></template>
      <template v-else><a-button size="large" html-type="button" :disabled="busy || !status.feishu_stepup_available" @click="sendCode">发送验证码到本人飞书</a-button><label :for="fieldId + '-code'">本人收件验证码</label><a-input-password :id="fieldId + '-code'" v-model:value="code" size="large" inputmode="numeric" autocomplete="one-time-code" :disabled="busy" /><p v-if="!status.feishu_stepup_available">当前无法发送安全验证码，请使用恢复邮箱或联系管理员协助。</p></template>
      <template v-if="tmpId"><label :for="fieldId + '-otp'">二次认证验证码</label><a-input-password :id="fieldId + '-otp'" v-model:value="otp" size="large" inputmode="numeric" autocomplete="one-time-code" :disabled="busy" /><a-button html-type="button" :disabled="busy" @click="reset">取消二次认证</a-button></template>
      <a-alert v-if="proof.valid.value" :message="`本人已验证 · 剩余 ${proof.remaining.value} 秒 · 可执行一次安全操作`" type="success" show-icon role="status" />
      <a-alert v-else-if="expired" message="本人验证已过期、已使用或会话已变化，请重新验证。" type="info" show-icon role="status" />
      <a-button size="large" html-type="button" :loading="busy" :disabled="busy || (passwordMode ? !password : !code) || Boolean(tmpId && !otp)" @click="verify">{{ proof.valid.value ? '重新验证本人身份' : '验证本人身份' }}</a-button>
    </template>
    <a-alert v-if="error" :message="error" type="warning" show-icon role="alert" />
    <a-alert v-if="notice" :message="notice" type="info" show-icon role="status" />
    <a-button v-if="!status && !loading" html-type="button" @click="load">重试读取验证方式</a-button>
  </section>
</template>
<script setup lang="ts">
import { computed, onMounted, ref, useId, onBeforeUnmount } from 'vue'
import { getSecurity, reauthenticate, requestFeishuCode, verifyFeishuCode, type SecurityStatus, type ProofStatus } from '@/services/accountApi'
import { useAccountProof } from '@/composables/useAccountProof'
import { accountErrorMessage } from '@/services/accountErrors'
const props = defineProps<{ passwordOnly?: boolean }>(), emit = defineEmits<{ verified: [proof: ProofStatus]; invalidated: [] }>()
const fieldId = useId(), status = ref<SecurityStatus | null>(null), useInbox = ref(false)
const password = ref(''), code = ref(''), otp = ref(''), tmpId = ref(''), error = ref(''), notice = ref(''), busy = ref(false), loading = ref(true), expired = ref(false)
const proof = useAccountProof(() => { clearSecrets(); expired.value = true; emit('invalidated') })
const passwordMode = computed(() => props.passwordOnly || Boolean(status.value?.has_password && !useInbox.value))
let generation = 0, disposed = false
function clearSecrets() { password.value = ''; code.value = ''; otp.value = ''; tmpId.value = '' }
function reset() { generation++; clearSecrets(); proof.invalidate(); error.value = ''; notice.value = '' }
async function load() { loading.value = true; error.value = ''; try { const result = await getSecurity(); if (!disposed) { status.value = result; if (result.proof?.valid && (!props.passwordOnly || result.proof.method === 'password')) { proof.sync(result.proof); emit('verified', result.proof) } } } catch (e) { if (!disposed) error.value = accountErrorMessage(e, '无法读取验证方式，请重试。') } finally { if (!disposed) loading.value = false } }
async function sendCode() { if (busy.value) return; busy.value = true; error.value = ''; notice.value = ''; try { const result = await requestFeishuCode(); if (!disposed) { if (!result.sent) error.value = result.error || '飞书未确认发送，请稍后重试。'; else notice.value = '飞书已确认发送，请本人查收验证码。' } } catch (e) { if (!disposed) error.value = accountErrorMessage(e, '发送未完成，请稍后重试。') } finally { if (!disposed) busy.value = false } }
function onEnter(event: KeyboardEvent) { if (event.isComposing || event.keyCode === 229) return; event.preventDefault(); event.stopPropagation(); void verify() }
async function verify() {
  if (busy.value || (passwordMode.value ? !password.value : !code.value) || (tmpId.value && !otp.value)) return
  busy.value = true; error.value = ''; notice.value = ''; const version = generation, method = passwordMode.value ? 'password' : 'feishu_inbox'
  try {
    const result = passwordMode.value ? await reauthenticate(password.value, otp.value, tmpId.value) : await verifyFeishuCode(code.value, otp.value, tmpId.value)
    if (disposed || version !== generation) return
    if (result.mfa_required) { tmpId.value = result.tmp_id || ''; notice.value = '请完成账号已有的二次认证。'; return }
    clearSecrets(); expired.value = false; proof.grant(result.expires_in || 0, method)
    if (proof.valid.value) emit('verified', { valid: true, expires_in: result.expires_in || 0, method })
  } catch (e) { if (!disposed && version === generation) { clearSecrets(); proof.invalidate(); error.value = accountErrorMessage(e, '本人验证未通过，请核对当前密码或验证码。') } }
  finally { if (!disposed && version === generation) busy.value = false }
}
onMounted(load)
onBeforeUnmount(() => { disposed = true; generation++; clearSecrets() })
</script>
<style src="@/theme/account.css"></style>
