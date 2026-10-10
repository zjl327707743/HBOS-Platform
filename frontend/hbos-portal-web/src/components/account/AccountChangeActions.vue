<template>
  <section v-if="loading || error || (actions?.migrated && (actions.rebind || actions.roles || actions.builtin_administrator || actions.identity_restore || changes.length))" class="account-section change-actions">
    <h4>飞书绑定与职责交接</h4><a-skeleton v-if="loading" active :paragraph="{rows:1}" />
    <a-alert v-if="error" :message="error" type="warning" show-icon role="alert" /><a-button v-if="error" :loading="loading" @click="load">重试读取变更状态</a-button>
    <template v-if="actions?.migrated">
      <div class="account-buttons"><a-button v-if="actions.rebind" size="large" @click="open('rebind')">更换本人飞书</a-button></div>
      <a-collapse v-if="actions.roles || actions.builtin_administrator || actions.identity_restore"><a-collapse-panel key="management" header="有权限的账号管理"><div class="account-buttons"><a-button v-if="actions.roles" size="large" @click="open('roles')">管理员职责交接</a-button><a-button v-if="actions.builtin_administrator" size="large" :disabled="!actions.custody" @click="open('custody')">Administrator 保管人交接</a-button><a-button v-if="actions.identity_restore" size="large" @click="open('identity_restore')">恢复旧飞书的普通账号归属</a-button></div><p v-if="actions.builtin_administrator">{{ actions.custody ? '仍须双方验证身份、准备新凭据并明确确认。' : '保管人交接尚未获专项授权，当前绑定继续保留。' }}</p></a-collapse-panel></a-collapse>
      <ul v-if="changes.length"><li v-for="change in changes" :key="change.name">{{ kindLabel(change.kind) }} · {{ stateLabel(change.state) }} · {{ deliveryLabel(change.notification_status) }}</li></ul>
    </template>
  </section>
</template>
<script setup lang="ts">
import { onMounted, onBeforeUnmount, ref } from 'vue'
import { useRouter } from 'vue-router'
import { changeActions, recentChanges, kindLabel, stateLabel, type ChangeActions, type ChangeKind } from '@/services/accountChanges'
import { accountErrorMessage } from '@/services/accountErrors'
const actions = ref<ChangeActions|null>(null), changes = ref<{name:string;kind:ChangeKind;state:string;notification_status:string}[]>([]), error = ref(''), loading = ref(true), router = useRouter()
let disposed = false
function open(kind: ChangeKind) { router.push({path:'/hbos/account-change',query:{kind}}) }
function deliveryLabel(status: string) { if (status === 'queued') return '通知待发送'; if (status === 'queue_failed' || status.includes('delivery_failed')) return '通知未确认送达'; if (status.includes('provider_acknowledged')) return '飞书确认发送'; return '通知未发送' }
async function load() { loading.value = true; error.value = ''; try { const result = await changeActions(); if (disposed) return; actions.value = result; if (result.migrated) { const history = await recentChanges(); if (!disposed) changes.value = history.changes } } catch (e) { if (!disposed) error.value = accountErrorMessage(e, '无法取得账号变更状态，请重试。') } finally { if (!disposed) loading.value = false } }
onMounted(load); onBeforeUnmount(() => { disposed = true })
</script>
<style scoped>.change-actions li{color:var(--hbos-text-secondary);line-height:var(--hbos-line-body);overflow-wrap:anywhere}</style>
