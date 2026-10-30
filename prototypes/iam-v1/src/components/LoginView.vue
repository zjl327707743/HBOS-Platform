<script setup>
import { computed, ref, watch } from 'vue'
import { ArrowRightOutlined, SafetyCertificateOutlined, TeamOutlined, AppstoreOutlined, LockOutlined } from '@ant-design/icons-vue'
import { state, ui, login, changePassword, recover } from '../model.js'

const emit = defineEmits(['logged-in'])
const mode = ref('feishu')
const selectedId = ref('e1')
const scenario = ref('success')
const error = ref('')
const working = ref(false)
const selected = computed(() => state.employees.find(person => person.id === selectedId.value))
const identities = computed(() => state.employees.map(person => ({ value: person.id, label: `${person.name} · ${person.code}${person.id === 'admin' ? ' · 管理员' : ''}` })))
const busy = computed(() => working.value || ui.busy)
const firstPasswordId = ref('')
const firstPasswordError = ref('')
const firstPasswordConfirmed = ref(false)
const recoveryOpen = ref(false)
const recoveryStep = ref(0)
const recoveryIdentity = ref(false)
const recoveryMfa = ref(false)
const recoveryError = ref('')
const recoveryResult = ref(false)

watch(() => [state.session?.phase, state.session?.employeeId], ([phase, employeeId]) => {
  if (phase === 'first-password' && employeeId) {
    selectedId.value = employeeId
    firstPasswordId.value = employeeId
    firstPasswordConfirmed.value = false
    firstPasswordError.value = ''
  } else { firstPasswordId.value = '' }
}, { immediate: true })

function resetMessage() { error.value = '' }
async function signIn() {
  if (busy.value) return
  error.value = ''
  if (mode.value === 'feishu' && scenario.value !== 'success') {
    const failures = {
      unbound: '当前演示飞书身份未绑定员工账号。请联系管理员核对身份并完成绑定。',
      unopened: '企业尚未为当前演示员工开通账号。请联系管理员受控开通。',
      'service-failure': '飞书登录服务暂时不可用（模拟）。可稍后重试，或使用已开通账号的密码备用入口。'
    }
    error.value = failures[scenario.value]
    return
  }
  working.value = true
  try {
    const result = await login(selectedId.value, mode.value)
    if (!result.ok) { error.value = result.error; return }
    if (result.firstPassword) {
      firstPasswordId.value = selectedId.value
      firstPasswordConfirmed.value = false
      firstPasswordError.value = ''
      return
    }
    emit('logged-in')
  } catch { error.value = '演示登录未完成，请重试。' }
  finally { working.value = false }
}
async function finishFirstPassword() {
  if (!firstPasswordConfirmed.value || busy.value) return
  working.value = true
  firstPasswordError.value = ''
  try {
    const result = await changePassword(firstPasswordId.value)
    if (!result.ok) { firstPasswordError.value = result.error; return }
    firstPasswordId.value = ''
    emit('logged-in')
  } catch { firstPasswordError.value = '演示改密未保存，请重试。' }
  finally { working.value = false }
}
function openRecovery(employeeId) {
  if (typeof employeeId === 'string' && state.employees.some(person => person.id === employeeId)) selectedId.value = employeeId
  recoveryOpen.value = true
  recoveryStep.value = 0
  recoveryIdentity.value = false
  recoveryMfa.value = false
  recoveryError.value = ''
  recoveryResult.value = false
}
async function finishRecovery() {
  if (busy.value) return
  working.value = true
  recoveryError.value = ''
  try {
    const result = await recover(selectedId.value)
    if (!result.ok) { recoveryError.value = result.error; return }
    recoveryResult.value = true
    recoveryStep.value = 2
  } catch { recoveryError.value = '演示恢复未保存，请重试。' }
  finally { working.value = false }
}
function useRecoveredPassword() {
  recoveryOpen.value = false
  mode.value = 'password'
  scenario.value = 'success'
  error.value = ''
}
defineExpose({ openRecovery })
</script>

<template>
  <div class="login-page">
    <div class="login-topline">
      <a-tag color="green">IAM V1 · 原型评审</a-tag>
    </div>
    <div class="login-layout">
      <section class="login-story">
        <span class="kicker">ONE IDENTITY. YOUR WORKSPACE.</span>
        <h1>让每一位同事，<br />进入自己的工作空间。</h1>
        <p class="story-description">一个员工身份，连接部门、应用与工作权限。<br />飞书优先，密码备用，账号由企业确认后开通。</p>
        <div class="identity-illustration" aria-hidden="true">
          <div class="illustration-top"><span class="status-dot"></span>统一身份 · 合成场景</div>
          <div class="identity-center"><span class="avatar">林</span><div><strong>林舟</strong><small>演示员工 · 质量研究部</small></div><SafetyCertificateOutlined class="verified-icon" /></div>
          <div class="connector"></div>
          <div class="connected-apps"><span><AppstoreOutlined /> 应用入口</span><span><TeamOutlined /> 部门权限</span><span><LockOutlined /> 账号安全</span></div>
        </div>
        <div class="story-footnote"><SafetyCertificateOutlined /> 同一员工的两种登录方式，对应同一账号与有效权限</div>
      </section>

      <section class="login-card panel" aria-label="员工登录原型">
        <span class="kicker">欢迎回来</span><h2>进入海滨工作台</h2>
        <p class="muted">仅使用合成身份演示，无需真实密码。</p>
        <div class="login-methods" role="group" aria-label="登录方式">
          <button type="button" :class="{ active: mode === 'feishu' }" @click="mode = 'feishu'; resetMessage()">飞书登录 <small>推荐</small></button>
          <button type="button" :class="{ active: mode === 'password' }" @click="mode = 'password'; resetMessage()">密码备用</button>
        </div>
        <a-form layout="vertical" @finish="signIn">
          <a-form-item label="切换演示身份">
            <a-select v-model:value="selectedId" :options="identities" aria-label="切换演示身份" size="large" @change="resetMessage" />
          </a-form-item>
          <a-form-item v-if="mode === 'feishu'" label="模拟飞书结果">
            <a-select v-model:value="scenario" size="large" aria-label="模拟飞书结果" @change="resetMessage">
              <a-select-option value="success">按当前员工状态模拟登录</a-select-option>
              <a-select-option value="unbound">未绑定身份 · 联系管理员</a-select-option>
              <a-select-option value="unopened">账号未开通 · 联系管理员</a-select-option>
              <a-select-option value="service-failure">飞书服务失败 · 允许重试</a-select-option>
            </a-select>
          </a-form-item>
          <div v-else class="password-placeholder"><LockOutlined /><div><strong>使用演示密码</strong><span>无需填写真实密码。已修改的密码始终不可查看。</span></div></div>
          <div class="account-link"><span>统一演示账号</span><strong>{{ selected?.accountId || '待受控开通' }}</strong></div>
          <a-alert v-if="error" class="login-error" :message="error" type="error" show-icon role="alert" />
          <a-button type="primary" size="large" html-type="button" block :loading="busy" class="login-submit" @click="signIn">{{ mode === 'feishu' ? '模拟飞书登录' : '使用演示密码登录' }} <ArrowRightOutlined /></a-button>
          <a-button type="link" class="forgot-button" @click="openRecovery">忘记密码 / 找回账号</a-button>
        </a-form>
        <div class="login-card-note"><SafetyCertificateOutlined /><span>没有公众注册入口<br />未开通、未绑定或停用账号，请联系管理员</span></div>
      </section>
    </div>
    <div class="login-disclaimer">交互原型 / 合成数据 / 尚未连接 HBOS 后端</div>
  </div>

  <a-modal :open="Boolean(firstPasswordId)" title="首次登录 · 设置自己的密码" :footer="null" :closable="false" :mask-closable="false" :keyboard="false" :width="520">
    <div class="stack">
      <a-alert message="演示临时密码仅用于首次登录，完成改密后才能进入工作台。" type="warning" show-icon />
      <div class="security-summary"><LockOutlined /><div><strong>创建新的演示密码</strong><p>这里模拟密码设置结果，不采集、显示或保存真实密码。管理员不能查看修改后的当前密码。</p></div></div>
      <a-checkbox v-model:checked="firstPasswordConfirmed">确认以新的演示密码替换临时密码</a-checkbox>
      <a-alert v-if="firstPasswordError" :message="firstPasswordError" type="error" show-icon />
      <a-button type="primary" size="large" block :disabled="!firstPasswordConfirmed" :loading="busy" @click="finishFirstPassword">完成演示改密并进入工作台</a-button>
    </div>
  </a-modal>

  <a-modal v-model:open="recoveryOpen" title="忘记密码 / 找回账号" :footer="null" :mask-closable="false" :width="560">
    <div class="stack recovery-body">
      <a-steps size="small" :current="recoveryStep" :items="[{ title: '重新验证' }, { title: '确认恢复' }, { title: '结果' }]" />
      <a-alert message="合成流程演示，不发送验证码、邮件或真实恢复链接。" type="info" show-icon />
      <template v-if="recoveryStep === 0">
        <p class="muted">将恢复 {{ selected?.name }} 的同一演示账号，恢复操作不会建立第二账号。</p>
        <a-checkbox v-model:checked="recoveryIdentity">模拟通过本人身份重新验证</a-checkbox>
        <a-checkbox v-model:checked="recoveryMfa">模拟通过已配置的 MFA 验证</a-checkbox>
        <a-button type="primary" :disabled="!recoveryIdentity || !recoveryMfa" @click="recoveryStep = 1">验证完成，继续</a-button>
      </template>
      <template v-else-if="recoveryStep === 1">
        <div class="security-summary"><SafetyCertificateOutlined /><div><strong>确认恢复 {{ selected?.name }} 的账号</strong><p>演示恢复会使密码备用入口重新进入首次改密流程。飞书绑定、员工资料和原有权限继续对应同一账号。</p></div></div>
        <a-alert v-if="recoveryError" :message="recoveryError" type="error" show-icon />
        <a-button type="primary" :loading="busy" @click="finishRecovery">确认执行演示恢复</a-button>
        <a-button :disabled="busy" @click="recoveryStep = 0">返回验证</a-button>
      </template>
      <template v-else-if="recoveryResult">
        <a-result status="success" title="演示账号恢复已完成" sub-title="演示已保存到本机。请使用密码备用入口，首次使用必须改密。" />
        <a-button type="primary" block @click="useRecoveredPassword">返回密码备用入口</a-button>
      </template>
    </div>
  </a-modal>
</template>

<style scoped>
.login-page { min-height: auto; padding: 18px 4vw 22px; color: #213c32; background: radial-gradient(ellipse at 15% 40%, #dff1e4 0, transparent 55%), #f5f8f5; }
.login-topline { max-width: 1120px; display: flex; align-items: center; justify-content: flex-end; margin: auto; }
.login-layout { max-width: 1120px; display: grid; grid-template-columns: 1.2fr 1fr; gap: 64px; align-items: center; margin: 28px auto 30px; }
.login-story .kicker { font-size: 11px; letter-spacing: .17em; font-weight: 700; color: #547d64; }.login-story h1 { font-size: clamp(30px, 3vw, 44px); line-height: 1.45; letter-spacing: -.055em; margin: 17px 0 18px; font-weight: 650; }.story-description { color: #6a7d70; font-size: 15px; line-height: 1.95; }.identity-illustration { max-width: 458px; margin-top: 35px; padding: 20px 24px; background: rgba(255,255,255,.78); border: 1px solid #d5e6d8; border-radius: 18px; box-shadow: 0 14px 32px #40644808; }.illustration-top { color: #7d9181; font-size: 11px; letter-spacing: .1em; display: flex; align-items: center; gap: 7px; }.status-dot { width: 5px; height: 5px; background: #559b69; border-radius: 50%; }.identity-center { display: flex; gap: 12px; align-items: center; padding: 20px 0 8px; }.avatar { display: grid; place-items: center; width: 47px; height: 47px; border-radius: 14px; background: #e3f0e5; color: #49815d; font-size: 19px; }.identity-center strong { display: block; font-size: 15px; }.identity-center small { display: block; color: #819083; margin-top: 3px; font-size: 11px; }.verified-icon { margin-left: auto; font-size: 22px; color: #60a173; }.connector { height: 18px; border-left: 1px dashed #bfd8c4; margin-left: 24px; }.connected-apps { border-top: 1px solid #e0ebe2; padding-top: 18px; display: flex; justify-content: space-between; gap: 10px; font-size: 11px; color: #66806d; }.connected-apps span { display: flex; gap: 7px; align-items: center; }.story-footnote { margin-top: 25px; color: #77917e; display: flex; gap: 8px; font-size: 11px; align-items: center; }
.login-card { padding: 36px; border-radius: 20px; border: 1px solid #e2eae3; background: white; box-shadow: 0 24px 55px #244b3110; }.login-card .kicker { color: #73a17e; font-size: 12px; }.login-card h2 { font-size: 25px; letter-spacing: -.02em; margin: 8px 0 9px; }.login-card > .muted { font-size: 12px; }.login-methods { margin: 26px 0 23px; padding: 4px; background: #f1f5f1; border-radius: 9px; display: flex; }.login-methods button { width: 50%; border: none; background: transparent; border-radius: 6px; height: 40px; color: #748277; font-size: 13px; cursor: pointer; }.login-methods button.active { background: white; color: #326c49; box-shadow: 0 2px 5px #183a2010; font-weight: 600; }.login-methods small { background: #e6f1e6; color: #518663; border-radius: 4px; padding: 2px 4px; margin-left: 4px; font-size: 9px; }.account-link { display: flex; justify-content: space-between; gap: 10px; font-size: 11px; color: #859087; margin: 4px 0 17px; }.account-link strong { font-weight: 500; color: #627466; overflow-wrap: anywhere; text-align: right; }.password-placeholder { padding: 15px; background: #f8faf8; border: 1px dashed #d6e2d7; border-radius: 8px; display: flex; gap: 11px; margin-bottom: 18px; color: #67816e; }.password-placeholder strong { display: block; font-size: 12px; color: #4d6553; }.password-placeholder span { display: block; font-size: 11px; line-height: 1.6; margin-top: 4px; }.login-submit { height: 46px; }.login-error { margin-bottom: 16px; }.forgot-button { display: block; margin: 8px auto 15px; font-size: 12px; }.login-card-note { border-top: 1px solid #edf1ed; padding-top: 17px; display: flex; justify-content: center; align-items: center; gap: 9px; color: #8d998f; font-size: 10px; line-height: 1.8; }.login-disclaimer { text-align: center; color: #798b7e; letter-spacing: .04em; font-size: 11px; }.security-summary { background: #f6f9f6; padding: 18px; border: 1px solid #e3ebe3; border-radius: 10px; display: flex; gap: 14px; }.security-summary > .anticon { color: #528361; font-size: 22px; }.security-summary strong { display: block; font-size: 14px; }.security-summary p { color: #7d8b7f; font-size: 12px; line-height: 1.7; margin: 6px 0 0; }.recovery-body { padding-top: 12px; }.stack { display: flex; flex-direction: column; gap: 18px; }.login-methods button:focus-visible { outline: 3px solid #82b898; outline-offset: 2px; }
@media (max-width: 1020px) { .login-layout { gap: 35px; margin-top: 25px; }.login-card { padding: 28px; }.login-story h1 { font-size: 33px; }.connected-apps { flex-wrap: wrap; } }
@media (max-width: 760px) { .login-page { padding: 18px; }.login-layout { display: block; max-width: 430px; margin-top: 20px; }.login-story { margin-bottom: 24px; }.login-story h1 { font-size: 28px; }.story-description { font-size: 13px; }.identity-illustration, .story-footnote { display: none; }.login-card { padding: 24px; }.login-disclaimer { font-size: 10px; } }
</style>
