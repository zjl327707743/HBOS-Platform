<script setup>
import { computed, ref, watch } from 'vue'
import { SafetyCertificateOutlined, LockOutlined, LinkOutlined, CheckCircleFilled, ArrowRightOutlined } from '@ant-design/icons-vue'
import { state, ui, currentUser, allSubjects, changePassword, rebind } from '../model.js'

const props = defineProps({ employee: { type: Object, default: null } })
const emit = defineEmits(['recover'])
const account = computed(() => props.employee || currentUser.value)
const isSelf = computed(() => account.value?.id === currentUser.value?.id)
const flow = ref('')
const step = ref(0)
const identityVerified = ref(false)
const mfaVerified = ref(false)
const confirmImpact = ref(false)
const newIdentity = ref('')
const flowError = ref('')
const resultMessage = ref('')
const working = ref(false)
const busy = computed(() => working.value || ui.busy)
const occupied = computed(() => allSubjects.value.find(person => person.id !== account.value?.id && person.bound && person.feishuId))
const ownNewIdentity = computed(() => `demo-feishu-${account.value?.id || 'self'}-new`)
const passwordSteps = [{ title: '重新验证' }, { title: '确认改密' }, { title: '结果' }]
const bindingSteps = [{ title: '重新验证' }, { title: '确认新身份' }, { title: '确认影响' }, { title: '结果' }]

watch(() => account.value?.id, () => { flow.value = '' })
function startFlow(type) {
  if (!isSelf.value || busy.value) return
  flow.value = type
  step.value = 0
  identityVerified.value = false
  mfaVerified.value = false
  confirmImpact.value = false
  newIdentity.value = ownNewIdentity.value
  flowError.value = ''
  resultMessage.value = ''
}
function nextIdentity() {
  flowError.value = ''
  if (!newIdentity.value) { flowError.value = '请选择本人新的演示飞书身份。'; return }
  if (allSubjects.value.some(person => person.id !== account.value.id && person.bound && person.feishuId === newIdentity.value)) {
    flowError.value = '此演示飞书身份已被其他员工账号占用，不能抢占。请选择本人未占用的演示身份。'
    return
  }
  step.value = 2
}
async function saveFlow() {
  if (busy.value || !isSelf.value || !identityVerified.value || !mfaVerified.value || !confirmImpact.value) return
  working.value = true
  flowError.value = ''
  try {
    const result = flow.value === 'password' ? await changePassword(account.value.id) : await rebind(account.value.id, newIdentity.value)
    if (!result.ok) { flowError.value = result.error; return }
    resultMessage.value = flow.value === 'password' ? '演示密码已修改' : '演示飞书换绑已完成'
    step.value = flow.value === 'password' ? 2 : 3
  } catch { flowError.value = '演示变更未保存，请重试。' }
  finally { working.value = false }
}
</script>

<template>
  <section v-if="account" class="account-security stack">
    <div class="security-heading"><div><span class="kicker">ACCOUNT SECURITY</span><h3>账号安全</h3><p class="muted">同一员工身份，安全地管理登录方式。</p></div><span class="safe-badge"><SafetyCertificateOutlined /> 合成账号</span></div>
    <a-alert v-if="!isSelf" message="当前为管理员查看。本人验证、修改密码与飞书换绑由员工自己的账号安全入口完成；管理员无法查看当前密码。" type="info" show-icon />
    <div class="account-overview"><span class="account-avatar">{{ account.name.slice(0, 1) }}</span><div><strong>{{ account.name }}</strong><span>{{ account.code }} · {{ account.accountId || '待受控开通' }}</span></div><a-tag :color="account.status === 'active' ? 'green' : account.status === 'disabled' ? 'red' : 'gold'">{{ account.status === 'active' ? '已开通' : account.status === 'disabled' ? '已停用' : '待开通' }}</a-tag></div>
    <div class="security-item"><div class="item-icon"><LockOutlined /></div><div class="item-copy"><strong>密码登录</strong><p>{{ account.firstPassword ? '演示临时密码待首次修改' : '当前密码不可查看；修改需重新验证本人身份与 MFA' }}</p></div><a-button v-if="isSelf" :disabled="busy || account.status !== 'active'" @click="startFlow('password')">修改密码</a-button><a-tag v-else>密码不可查看</a-tag></div>
    <div class="security-item"><div class="item-icon"><LinkOutlined /></div><div class="item-copy"><strong>飞书绑定 <a-tag :color="account.bound ? 'green' : 'gold'">{{ account.bound ? '已绑定' : '未绑定' }}</a-tag></strong><p>{{ account.bound ? account.feishuId : '核对本人身份后，由受控流程绑定' }}</p></div><a-button v-if="isSelf" :disabled="busy || account.status !== 'active'" @click="startFlow('binding')">{{ account.bound ? '更换绑定' : '绑定演示身份' }}</a-button></div>
    <div class="mfa-note"><CheckCircleFilled /><div><strong>保留重新验证与 MFA 步骤</strong><p>这里演示身份验证结果，使用合成身份，不发送验证码或真实恢复链接。</p></div></div>
    <a-button v-if="isSelf" type="link" class="recovery-entry" :disabled="busy" @click="emit('recover')">忘记密码 / 找回账号</a-button>
    <p class="prototype-note">交互原型 / 合成数据 / 尚未连接 HBOS 后端</p>
  </section>

  <a-modal :open="Boolean(flow)" :title="flow === 'password' ? '修改密码' : '飞书换绑'" :footer="null" :mask-closable="false" :closable="!busy" :width="590" @cancel="flow = ''">
    <div class="stack flow-body">
      <a-steps size="small" :current="step" :items="flow === 'password' ? passwordSteps : bindingSteps" />
      <template v-if="step === 0">
        <div class="proof-card"><SafetyCertificateOutlined /><div><strong>先确认这是本人操作</strong><p>安全变更保留原有重新验证与 MFA 要求。以下只模拟验证结果。</p></div></div>
        <a-checkbox v-model:checked="identityVerified">模拟通过本人身份重新验证</a-checkbox>
        <a-checkbox v-model:checked="mfaVerified">模拟通过已配置的 MFA 验证</a-checkbox>
        <a-button type="primary" block :disabled="!identityVerified || !mfaVerified" @click="step = 1">验证完成，继续 <ArrowRightOutlined /></a-button>
      </template>
      <template v-else-if="flow === 'password' && step === 1">
        <a-alert message="演示新密码不会显示或保存为真实密码。管理员不能查看已修改的当前密码。" type="info" show-icon />
        <div class="impact-card"><strong>确认修改 {{ account?.name }} 的演示密码</strong><p>密码与飞书继续登录同一个账号；原有员工资料和权限来源保持关联。此处仅保存合成演示状态。</p></div>
        <a-checkbox v-model:checked="confirmImpact">确认使用新的演示密码替换原演示密码</a-checkbox>
        <a-alert v-if="flowError" :message="flowError" type="error" show-icon />
        <a-button type="primary" block :disabled="!confirmImpact" :loading="busy" @click="saveFlow">确认修改演示密码</a-button>
        <a-button :disabled="busy" @click="step = 0">返回验证</a-button>
      </template>
      <template v-else-if="flow === 'binding' && step === 1">
        <p class="muted">选择本人新的演示飞书身份。其他员工已经使用的身份会被拒绝。</p>
        <a-radio-group v-model:value="newIdentity" class="identity-options">
          <a-radio :value="ownNewIdentity"><strong>本人新的演示身份</strong><small>{{ ownNewIdentity }}</small></a-radio>
          <a-radio v-if="occupied" :value="occupied.feishuId"><strong>模拟占用身份 · {{ occupied.name }}</strong><small>{{ occupied.feishuId }} · 用于验证拒绝抢占</small></a-radio>
        </a-radio-group>
        <a-alert v-if="flowError" :message="flowError" type="error" show-icon />
        <a-button type="primary" block @click="nextIdentity">确认新身份，查看影响</a-button>
        <a-button @click="step = 0">返回验证</a-button>
      </template>
      <template v-else-if="flow === 'binding' && step === 2">
        <div class="impact-card"><strong>请确认绑定变更的影响</strong><dl><dt>原演示身份</dt><dd>{{ account?.feishuId || '尚未绑定' }}</dd><dt>新演示身份</dt><dd>{{ newIdentity }}</dd><dt>统一账号</dt><dd>{{ account?.accountId }}</dd></dl></div>
        <a-alert message="换绑后原身份不再用于此演示账号的飞书登录；员工身份、密码备用入口与有效权限仍对应同一账号。" type="warning" show-icon />
        <a-checkbox v-model:checked="confirmImpact">已确认这是本人新身份并理解上述影响</a-checkbox>
        <a-alert v-if="flowError" :message="flowError" type="error" show-icon />
        <a-button type="primary" block :disabled="!confirmImpact" :loading="busy" @click="saveFlow">确认执行演示换绑</a-button>
        <a-button :disabled="busy" @click="step = 1">返回选择新身份</a-button>
      </template>
      <template v-else>
        <a-result status="success" :title="resultMessage" sub-title="演示已保存到本机。未修改任何真实账号、密码或飞书绑定。" />
        <a-button type="primary" block @click="flow = ''">返回账号安全</a-button>
      </template>
      <p class="prototype-note">交互原型 / 合成数据 / 尚未连接 HBOS 后端</p>
    </div>
  </a-modal>
</template>

<style scoped>
.stack { display: flex; flex-direction: column; gap: 18px; }.account-security { color: #273e30; }.security-heading { display: flex; align-items: flex-start; justify-content: space-between; gap: 15px; }.security-heading .kicker { color: #759581; font-size: 10px; letter-spacing: .12em; }.security-heading h3 { font-size: 22px; font-weight: 600; margin: 7px 0 7px; }.security-heading p { margin: 0; font-size: 12px; }.safe-badge { display: inline-flex; gap: 6px; white-space: nowrap; background: #eef7ef; padding: 7px 10px; border-radius: 7px; color: #5e8568; font-size: 11px; }.account-overview { display: flex; align-items: center; gap: 12px; padding: 18px; background: #f7faf7; border: 1px solid #e4ece4; border-radius: 10px; }.account-avatar { display: grid; place-items: center; background: #e2efe4; color: #51815b; font-size: 18px; width: 44px; height: 44px; border-radius: 12px; }.account-overview strong { display: block; font-size: 14px; }.account-overview div > span { display: block; margin-top: 4px; font-size: 11px; color: #849087; overflow-wrap: anywhere; }.account-overview .ant-tag { margin-left: auto; flex-shrink: 0; }.security-item { display: flex; align-items: center; gap: 14px; border: 1px solid #e7ece7; border-radius: 10px; padding: 18px; background: white; }.item-icon { display: grid; place-items: center; width: 40px; height: 40px; background: #f1f6f1; border-radius: 10px; color: #7b9781; font-size: 19px; flex-shrink: 0; }.item-copy { flex: 1; min-width: 0; }.item-copy strong { display: block; font-size: 13px; }.item-copy strong .ant-tag { margin-left: 7px; font-weight: 400; }.item-copy p { font-size: 11px; color: #839087; margin: 6px 0 0; line-height: 1.7; overflow-wrap: anywhere; }.security-item > .ant-btn { flex-shrink: 0; font-size: 12px; }.mfa-note { display: flex; gap: 9px; color: #75a181; background: #f4f9f3; border-radius: 8px; padding: 13px 15px; }.mfa-note .anticon { margin-top: 2px; }.mfa-note strong { font-size: 11px; font-weight: 500; }.mfa-note p { font-size: 10px; color: #87948a; line-height: 1.7; margin: 4px 0 0; }.prototype-note { font-size: 10px; color: #9ca89e; margin: 0; line-height: 1.7; }.flow-body { padding-top: 12px; }.proof-card { background: #f5f9f5; display: flex; align-items: flex-start; gap: 13px; border-radius: 9px; padding: 18px; }.proof-card > .anticon { color: #5c966b; font-size: 23px; }.proof-card strong { font-size: 13px; color: #42674c; }.proof-card p { font-size: 12px; color: #849487; line-height: 1.7; margin: 5px 0 0; }.impact-card { border: 1px solid #e2eae2; padding: 18px; border-radius: 10px; background: #f9fbf9; }.impact-card strong { font-size: 14px; }.impact-card p { font-size: 12px; color: #7b8d80; line-height: 1.8; margin: 8px 0 0; }.impact-card dl { display: grid; grid-template-columns: 95px 1fr; gap: 10px; font-size: 12px; margin: 15px 0 0; }.impact-card dt { color: #849087; }.impact-card dd { margin: 0; color: #56725e; overflow-wrap: anywhere; }.identity-options { display: flex; flex-direction: column; gap: 12px; }.identity-options > .ant-radio-wrapper { margin: 0; border: 1px solid #dde9de; border-radius: 9px; padding: 14px; display: flex; align-items: flex-start; }.identity-options strong { font-size: 12px; font-weight: 500; }.identity-options small { display: block; font-size: 11px; color: #8a9a8d; margin-top: 5px; overflow-wrap: anywhere; }
.recovery-entry { align-self: flex-start; padding-left: 0; font-size: 12px; }
@media (max-width: 600px) { .security-item { flex-wrap: wrap; }.security-item .item-copy { min-width: calc(100% - 60px); }.security-item > .ant-btn, .security-item > .ant-tag { margin-left: 54px; }.security-heading { flex-wrap: wrap; }.account-overview { flex-wrap: wrap; } }
</style>
