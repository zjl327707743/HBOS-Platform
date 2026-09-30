<template>
  <section v-if="actions?.migrated" class="change-actions">
    <h4>绑定与职责交接</h4>
    <p v-if="actions.rebind">更换本人飞书时先验证新身份和影响，最后一次提交。申请期间原绑定继续可用。</p>
    <div class="buttons"><a-button v-if="actions.rebind" @click="open('rebind')">更换绑定的飞书</a-button><a-button v-if="actions.roles" @click="open('roles')">管理员职责交接</a-button><a-button v-if="actions.builtin_administrator" :disabled="!actions.custody" @click="open('custody')">Administrator 保管人交接</a-button><a-button v-if="actions.identity_restore" @click="open('identity_restore')">旧身份的普通账号归属</a-button></div>
    <p v-if="actions.builtin_administrator">管理职责优先由双方各自的永久个人账号承接。{{ actions.custody ? '保管人交接已获专项许可，仍须双方验证与确认。' : '当前未启用 Administrator 保管人交接专项许可；本轮不会改变真实保管人。' }}</p>
    <p v-if="error">{{ error }}</p>
    <ul v-if="changes.length"><li v-for="change in changes" :key="change.name">{{ kindLabel(change.kind) }} · {{ change.state }} · {{ deliveryLabel(change.notification_status) }}</li></ul>
  </section>
</template>
<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { changeActions, recentChanges, kindLabel, type ChangeActions, type ChangeKind } from '@/services/accountChanges'
const actions = ref<ChangeActions | null>(null), changes = ref<{name: string; kind: ChangeKind; state: string; notification_status: string}[]>([]), error = ref(''), router = useRouter()
function open(kind: ChangeKind) { router.push({path:'/hbos/account-change',query:{kind}}) }
function deliveryLabel(status: string) { if (status === 'queued') return '通知待发送'; if (status === 'queue_failed' || status.includes('delivery_failed')) return '通知未确认送达，请联系管理员'; if (status.includes('provider_acknowledged')) return '飞书确认发送'; return '通知未发送' }
onMounted(async () => { try { actions.value = await changeActions(); changes.value = (await recentChanges()).changes } catch { error.value = '无法取得账号变更状态，请刷新后重试。' } })
</script>
<style scoped>.change-actions{margin-top:22px;border-top:1px solid #e2e8f0;padding-top:18px}.buttons{display:flex;flex-wrap:wrap;gap:10px}.change-actions p,.change-actions li{color:#64748b;line-height:1.7}</style>
