<script setup>
import { computed } from 'vue'
import { state } from '../model.js'
import { summarizeWorkApp } from '../work-policy.js'
const props = defineProps({ employeeId: { type: String, required: true }, canEdit: { type: Boolean, default: true } })
const emit = defineEmits(['modify'])
const business = computed(() => state.apps.filter(app => app.id !== 'platform').map(app => summarizeWorkApp(state, 'employee', props.employeeId, app.id)))
const management = computed(() => state.apps.filter(app => app.id === 'platform').map(app => summarizeWorkApp(state, 'employee', props.employeeId, app.id)))
</script>
<template>
  <div class="app-usage-list"><div v-for="app in business" :key="app.appId" class="usage-row"><div class="usage-title"><strong>{{ app.name }}</strong><a-tag :color="app.status === 'available' ? 'green' : app.status === 'review' ? 'orange' : 'default'">{{ app.statusLabel }}</a-tag></div><div class="usage-work"><p>{{ app.text }}</p><span>{{ app.sourceText }}</span><details v-if="app.sources.length > 1 || app.complex"><summary>按工作查看安排</summary><div v-for="row in app.actionRows" :key="row.id"><span>{{ row.text }}</span><span>{{ row.sourceText }}</span></div></details></div><a-button v-if="canEdit" @click="emit('modify', app.appId)">{{ app.status === 'none' ? '设置' : '修改' }}</a-button></div><a-empty v-if="!business.length" description="暂无已登记的业务应用" /><details v-if="management.length" class="management-list"><summary>平台管理能力</summary><p>管理能力独立核定，不随普通应用安排获得。</p><div v-for="app in management" :key="app.appId" class="usage-row"><strong>{{ app.name }}</strong><p>{{ app.text }}</p><a-button v-if="canEdit" @click="emit('modify', app.appId)">查看</a-button></div></details></div>
</template>
<style scoped>
.app-usage-list{min-width:0}.usage-row{display:grid;grid-template-columns:minmax(110px,.7fr) minmax(0,2fr) auto;align-items:start;gap:24px;padding:24px 0;border-bottom:1px solid #e3eae0}.usage-row:first-child{padding-top:0}.usage-title{display:flex;flex-direction:column;align-items:flex-start;gap:8px}.usage-title strong,.usage-work p,.usage-row>strong,.usage-row>p{font-size:16px;line-height:24px;margin:0}.usage-title .ant-tag{font-size:14px;line-height:22px;margin:0}.usage-work>span,.usage-work details,.management-list{font-size:14px;line-height:22px;color:#5f7465}.usage-work>span{display:block;margin-top:8px}.usage-work details{margin-top:12px}.usage-work summary,.management-list>summary{cursor:pointer;color:#42684c}.usage-work details>div{display:flex;flex-direction:column;gap:6px;padding-top:12px}.usage-work details>div>span:last-child{color:#708074}.usage-row>.ant-btn{min-height:40px;font-size:14px}.management-list{margin-top:24px}.management-list>p{margin:16px 0}.management-list .usage-row{padding-top:16px}@media(max-width:600px){.usage-row{grid-template-columns:1fr auto;gap:16px}.usage-work{grid-column:1/-1;grid-row:2}.usage-title{flex-direction:row;flex-wrap:wrap;align-items:center}.usage-row>.ant-btn{grid-column:2;grid-row:1}}
</style>
