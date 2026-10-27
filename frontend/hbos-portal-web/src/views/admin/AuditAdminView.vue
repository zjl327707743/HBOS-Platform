<script setup lang="ts">
import { useManagementViewMemory } from '@/composables/useManagementViewMemory'
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { listAuditEvents, type AuditSubjectFilter } from '@/services/iamAudit'
import { iamMessage } from '@/services/iamAccess'
import type { AuditEvent } from '@/types/iam'
import PageHeading from '@/components/iam/PageHeading.vue'
import ResourceState from '@/components/iam/ResourceState.vue'
import StatusTag from '@/components/iam/StatusTag.vue'
const rows = ref<AuditEvent[]>([]), page = ref(1), total = ref(0), loading = ref(true), error = ref(''), subjectType = ref<string>(), subjectName = ref(''), selected = ref<AuditEvent | null>(null), filter = ref<AuditSubjectFilter>({})
const appliedType = ref<string>(), appliedName = ref('')
const columns = [{ title: '时间', dataIndex: 'occurred_at', width: 170 }, { title: '操作者', dataIndex: 'actor', width: 170 }, { title: '对象', key: 'subject', width: 200 }, { title: '操作', dataIndex: 'operation', width: 190 }, { title: '结果', key: 'result', width: 100 }, { title: '详情', key: 'detail', width: 90 }]
let generation = 0, disposed = false
async function load() {
  const run = ++generation; loading.value = true; error.value = ''
  try { const result = await listAuditEvents(page.value, 20, filter.value); if (!disposed && run === generation) { rows.value = result.items; total.value = result.total } }
  catch (e) { if (!disposed && run === generation) { rows.value = []; total.value = 0; error.value = iamMessage(e) } }
  finally { if (!disposed && run === generation) loading.value = false }
}
async function apply() { if (Boolean(subjectType.value) !== Boolean(subjectName.value.trim())) { error.value = '请同时选择对象类型并填写准确标识，或清除筛选查看全部可见记录。'; return }; appliedType.value = subjectType.value; appliedName.value = subjectName.value.trim(); filter.value = { subject_type: appliedType.value, subject_name: appliedName.value }; page.value = 1; await load() }
function clear() { subjectType.value = undefined; subjectName.value = ''; appliedType.value = undefined; appliedName.value = ''; filter.value = {}; page.value = 1; void load() }
onMounted(load)
onBeforeUnmount(() => { disposed = true; generation++; rows.value = []; selected.value = null })
useManagementViewMemory('AuditAdminView.vue', { subjectType, subjectName, appliedType, appliedName, page })
filter.value = { subject_type: appliedType.value, subject_name: appliedName.value }
</script>
<template>
  <section class="r6-page r6-audit-page">
    <PageHeading eyebrow="管理记录" title="变更记录" description="核对谁在何时调整了账号、角色与工作安排。" />
    <section class="r6-surface">
      <a-form class="r6-audit-filter" @submit.prevent="apply"><a-select v-model:value="subjectType" allow-clear aria-label="筛选对象类型" placeholder="全部对象"><a-select-option value="Employee">员工档案</a-select-option><a-select-option value="User">登录账号</a-select-option><a-select-option value="Department">部门</a-select-option><a-select-option value="HBOS IAM App Role">应用角色</a-select-option></a-select><a-input v-model:value="subjectName" allow-clear aria-label="准确对象标识" placeholder="填写准确对象标识" /><a-button type="primary" html-type="submit" :loading="loading">查询记录</a-button><a-button @click="clear">清除筛选</a-button></a-form>
      <p class="aux">仅显示当前账号获准读取的脱敏记录。对象筛选按准确标识匹配。</p>
      <ResourceState :loading="loading" :error="error" @retry="load">
      <a-table class="r6-desktop-people" :columns="columns" :data-source="rows" row-key="name" :loading="loading" :scroll="{ x: 920 }" :pagination="false"><template #bodyCell="{ column, record }"><template v-if="column.key === 'subject'">{{ record.subject_name }}<span class="iam-code">{{ record.subject_type }}</span></template><template v-else-if="column.key === 'result'"><StatusTag :tone="record.result === 'success' ? 'success' : 'warning'">{{ record.result === 'success' ? '成功' : record.result }}</StatusTag></template><template v-else-if="column.key === 'detail'"><button class="r6-audit-row-button" :aria-label="`查看${record.occurred_at}的变更记录`" @click="selected = record">查看详情</button></template></template></a-table>
      <div class="r6-mobile-people"><a-skeleton v-if="loading" active /><a-empty v-else-if="!rows.length" description="暂无可见变更记录" /><article v-for="row in rows" :key="row.name" class="r6-mobile-person"><strong>{{ row.operation }}</strong><p>{{ row.subject_name }}</p><p>{{ row.occurred_at }} · {{ row.actor }}</p><a-button @click="selected = row">查看详情</a-button></article></div>
      <footer class="r6-people-foot"><span class="aux">共 {{ total }} 条可见记录</span><a-pagination v-model:current="page" :total="total" :page-size="20" :show-size-changer="false" @change="load" /></footer>
    </ResourceState></section>
    <a-modal :open="Boolean(selected)" title="变更记录详情" :footer="null" @cancel="selected = null"><a-descriptions v-if="selected" :column="1" class="r6-audit-detail" bordered><a-descriptions-item label="时间">{{ selected.occurred_at }}</a-descriptions-item><a-descriptions-item label="操作者">{{ selected.actor }}</a-descriptions-item><a-descriptions-item label="对象">{{ selected.subject_type }} · {{ selected.subject_name }}</a-descriptions-item><a-descriptions-item label="操作">{{ selected.operation }}</a-descriptions-item><a-descriptions-item label="结果">{{ selected.result }}</a-descriptions-item><a-descriptions-item label="说明">{{ selected.reason || '未提供附加说明' }}</a-descriptions-item></a-descriptions><p class="aux">本记录暂未提供变更前后内容。</p><a-button @click="selected = null">关闭</a-button></a-modal>
  </section>
</template>
