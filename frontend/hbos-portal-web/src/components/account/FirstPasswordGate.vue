<script setup lang="ts">
import { ref, watch, onBeforeUnmount } from 'vue'
import { getIamSecurity, type IamSecurity } from '@/services/iamAccount'
import { setPassword, getSecurity } from '@/services/accountApi'
import { clearFrappeCsrfToken } from '@/services/frappeClient'
import { iamMessage } from '@/services/iamAccess'
import { useAccountProof } from '@/composables/useAccountProof'
import { isUncertainWrite } from '@/services/accountErrors'
import OwnAccountVerification from './OwnAccountVerification.vue'
import InitialPasswordDelivery from './InitialPasswordDelivery.vue'
const props = defineProps<{ subjectUser: string; security?: IamSecurity }>()
const emit = defineEmits<{ ready: []; blocked: [] }>()
const status = ref<IamSecurity | null>(null), loading = ref(true), busy = ref(false), error = ref(''), password = ref(''), confirmation = ref(''), uncertain = ref(false)
const proof = useAccountProof(() => { password.value = ''; confirmation.value = '' })
let generation = 0, requestId = ''
async function load() { const run = ++generation; loading.value = true; error.value = ''; emit('blocked'); try { const result = await getIamSecurity(props.subjectUser); if (run !== generation) return; status.value = result; if (!result.first_password_required) emit('ready') } catch (e) { if (run === generation) { status.value = null; error.value = iamMessage(e) } } finally { if (run === generation) loading.value = false } }
async function save() {
  if (busy.value || uncertain.value || !proof.valid.value || !password.value || password.value !== confirmation.value) return
  busy.value = true; error.value = ''; requestId = crypto.randomUUID()
  try { await setPassword(password.value, requestId); proof.invalidate(); clearFrappeCsrfToken(); await load() }
  catch (e) { uncertain.value = isUncertainWrite(e); error.value = iamMessage(e); proof.invalidate() }
  finally { busy.value = false; password.value = ''; confirmation.value = '' }
}
async function checkOutcome() { busy.value = true; try { const result = await getSecurity(requestId); if (result.user !== props.subjectUser) throw new Error('当前会话已改变。'); if (result.write_result?.completed) uncertain.value = false; await load() } catch (e) { error.value = iamMessage(e) } finally { busy.value = false } }
watch(() => props.subjectUser, () => { status.value = props.security || null; loading.value = !props.security; uncertain.value = false; proof.invalidate(); if (!props.security) void load() }, { immediate: true })
watch(() => props.security, value => { if (value) { status.value = value; loading.value = false } })
onBeforeUnmount(() => { generation++; proof.invalidate(); password.value = ''; confirmation.value = ''; requestId = '' })
</script>
<template>
  <a-skeleton v-if="loading" active />
  <section v-else-if="!status || status.first_password_required" class="first-gate glass-surface">
    <h1>先完成本人账号安全设置</h1><p>设置自己的正式密码后继续工作。当前临时状态下业务功能暂不开放。</p>
    <a-alert v-if="error" type="warning" :message="error" show-icon />
    <a-button v-if="!status" @click="load">重试读取安全状态</a-button>
    <template v-else>
      <InitialPasswordDelivery v-if="status.temporary_password_state.pending || status.temporary_password_state.can_claim" :can-claim="status.temporary_password_state.can_claim" />
      <OwnAccountVerification password-only @verified="proof.sync" @invalidated="proof.invalidate" />
      <a-alert v-if="uncertain" message="上次保存结果尚未确认。请先查询结果，避免重复提交。" type="warning" /><a-button v-if="uncertain" :loading="busy" @click="checkOutcome">查询上次保存结果</a-button>
      <a-form layout="vertical" @submit.prevent="save">
        <a-form-item label="新的正式密码"><a-input-password v-model:value="password" autocomplete="new-password" :disabled="busy || uncertain" /></a-form-item>
        <a-form-item label="再次输入正式密码" :help="confirmation && password !== confirmation ? '两次密码不一致。' : undefined"><a-input-password v-model:value="confirmation" autocomplete="new-password" :disabled="busy || uncertain" /></a-form-item>
        <a-button type="primary" html-type="submit" :loading="busy" :disabled="uncertain || !proof.valid.value || !password || password !== confirmation">保存密码并继续</a-button>
      </a-form>
      <RouterLink to="/hbos/reset-password">初始密码遗失或需要账号恢复</RouterLink>
    </template>
  </section>
  <slot v-else />
</template>
<style scoped>.first-gate{padding:var(--hbos-space-6);max-width:720px;display:grid;gap:var(--hbos-space-4);font-size:16px}.first-gate h1,.first-gate p{margin:0}.first-gate p{color:var(--hbos-text-secondary);line-height:1.6}</style>
