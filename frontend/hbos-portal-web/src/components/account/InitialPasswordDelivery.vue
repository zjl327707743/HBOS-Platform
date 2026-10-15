<script setup lang="ts">
import { ref, onBeforeUnmount } from 'vue'
import OwnAccountVerification from './OwnAccountVerification.vue'
import { useAccountProof } from '@/composables/useAccountProof'
import { claimInitialPassword } from '@/services/iamAccount'
import { iamMessage } from '@/services/iamAccess'
defineProps<{ canClaim: boolean }>()
const emit = defineEmits<{ claimed: [] }>()
const password = ref(''), error = ref(''), busy = ref(false), attempted = ref(false)
const proof = useAccountProof(() => { password.value = '' })
let disposed=false
async function claim() {
  if (busy.value || !proof.valid.value || attempted.value) return
  busy.value = true; error.value = ''; password.value = ''; attempted.value = true
  try { const result = await claimInitialPassword(); if(disposed)return; proof.invalidate(); if (result.claimed && result.temporary_password) password.value = result.temporary_password; else error.value = '初始密码已领取或不可再次显示，请使用已领取密码；丢失时联系管理员受控重置。'; emit('claimed') }
  catch (e) { error.value = iamMessage(e) + ' 如领取结果不明，请核对当前状态，不要反复领取。'; emit('claimed') }
  finally { busy.value = false }
}
onBeforeUnmount(() => { disposed=true; password.value = ''; proof.invalidate() })
</script>
<template>
  <section class="initial-delivery">
    <h3>领取本人初始密码</h3><p>验证本人后领取一次，请立即设置自己的密码。关闭页面后无法再次查看。</p>
    <a-alert v-if="error" :message="error" type="warning" show-icon />
    <template v-if="password"><label for="initial-password">本次初始密码</label><a-input-password id="initial-password" :value="password" readonly autocomplete="off" /><a-button @click="password = ''">我已记录，隐藏密码</a-button></template>
    <template v-else-if="canClaim && !attempted"><OwnAccountVerification @verified="proof.sync" @invalidated="proof.invalidate" /><a-button type="primary" :disabled="!proof.valid.value" :loading="busy" @click="claim">验证后领取一次</a-button></template>
    <p v-else>没有可再次读取的初始密码。遗失后请通过现有账号恢复或受控重置处理。</p>
  </section>
</template>
<style scoped>.initial-delivery{display:grid;gap:var(--hbos-space-3);font-size:16px}.initial-delivery h3,.initial-delivery p{margin:0}.initial-delivery p{color:var(--hbos-text-secondary);line-height:1.6}</style>
