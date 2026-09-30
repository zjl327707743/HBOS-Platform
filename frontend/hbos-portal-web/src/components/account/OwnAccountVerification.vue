<template>
  <form class="proof-form" @submit.prevent="verify">
    <p>{{ passwordOnly ? '验证当前负责人的密码与已有 MFA。密码仅用于本人认证。' : '验证当前账号本人身份，已有 MFA 仍须完成。' }}</p>
    <a-radio-group v-if="!passwordOnly && status?.has_password && status.feishu_bound" v-model:value="useInbox" @change="reset"><a-radio :value="false">原密码</a-radio><a-radio :value="true" :disabled="!status.feishu_stepup_available">本人飞书验证码</a-radio></a-radio-group>
    <template v-if="passwordMode"><label :for="fieldId + '-password'">当前密码</label><a-input-password :id="fieldId + '-password'" v-model:value="password" autocomplete="current-password" /></template>
    <template v-else><a-button :disabled="busy || !status?.feishu_stepup_available" @click="sendCode">主动发送到本人飞书收件箱</a-button><label :for="fieldId + '-code'">本人收件验证码</label><a-input-password :id="fieldId + '-code'" v-model:value="code" autocomplete="one-time-code" /><p v-if="!status?.feishu_stepup_available">收件验证码尚未启用，请先使用已有密码或受控恢复。</p></template>
    <template v-if="tmpId"><label :for="fieldId + '-otp'">已有二次认证验证码</label><a-input-password :id="fieldId + '-otp'" v-model:value="otp" autocomplete="one-time-code" /></template>
    <a-alert v-if="error" :message="error" type="warning" show-icon />
    <a-button html-type="submit" :loading="busy" :disabled="verified || (passwordMode ? !password : !code)">{{ verified ? '本人已验证 · 仅供一次操作' : '验证本人身份' }}</a-button>
  </form>
</template>
<script setup lang="ts">
import { computed, onMounted, ref, useId } from 'vue'
import { getSecurity, reauthenticate, requestFeishuCode, verifyFeishuCode, type SecurityStatus } from '@/services/accountApi'
const props = defineProps<{ passwordOnly?: boolean }>(), emit = defineEmits<{ verified: [] }>()
const fieldId = useId(), status = ref<SecurityStatus | null>(null), useInbox = ref(false)
const password = ref(''), code = ref(''), otp = ref(''), tmpId = ref(''), error = ref(''), busy = ref(false), verified = ref(false)
const passwordMode = computed(() => props.passwordOnly || Boolean(status.value?.has_password && !useInbox.value))
function reset() { password.value = ''; code.value = ''; otp.value = ''; tmpId.value = ''; verified.value = false }
async function sendCode() { busy.value = true; error.value = ''; try { const result = await requestFeishuCode(); if (!result.sent) error.value = result.error || '飞书未确认发送。' } catch { error.value = '发送失败，未确认投递。' } finally { busy.value = false } }
async function verify() { busy.value = true; error.value = ''; try { const result = passwordMode.value ? await reauthenticate(password.value, otp.value, tmpId.value) : await verifyFeishuCode(code.value, otp.value, tmpId.value); if (result.mfa_required) { tmpId.value = result.tmp_id || ''; return }; reset(); verified.value = true; emit('verified') } catch { reset(); error.value = '本人验证未通过，请核对当前密码、验证码和已有 MFA。' } finally { busy.value = false } }
onMounted(async () => { try { status.value = await getSecurity() } catch { error.value = '请先在当前浏览器登录本人 HBOS 账号。' } })
</script>
<style scoped>.proof-form{display:grid;gap:10px;margin:18px 0}.proof-form label{font-weight:600}.proof-form p{color:#64748b;line-height:1.7}</style>
