<template>
  <main class="login-page">
    <div class="login-aurora one"></div><div class="login-aurora two"></div>
    <section class="login-card hbos-glass-g3">
      <RouterLink class="login-brand" to="/hbos">
        <span>H</span><div><strong>HBOS</strong><small>海滨智能运营工作台</small></div>
      </RouterLink>
      <div class="login-icon"><SafetyCertificateOutlined /></div>
      <p class="eyebrow">企业内部使用</p>
      <h1>登录 HBOS</h1>
      <p class="login-copy">企业成员可直接用飞书进入。已有 HBOS 账号请先用密码登录，再绑定本人飞书。</p>

      <a-alert
        v-if="callbackMessage"
        :type="callbackTone"
        show-icon
        :message="callbackMessage"
        class="login-alert"
      />

      <form class="account-form" @submit.prevent="submitAccountLogin">
        <label for="hbos-username">账号</label>
        <a-input
          id="hbos-username"
          v-model:value="username"
          size="large"
          autocomplete="username"
          placeholder="请输入 HBOS 内部账号"
          :disabled="submitting"
        />
        <label for="hbos-password">密码</label>
        <a-input-password
          id="hbos-password"
          v-model:value="password"
          size="large"
          autocomplete="current-password"
          placeholder="请输入密码"
          :disabled="submitting"
        />
        <template v-if="tmpId"><label for="login-otp">原有二次认证验证码</label><a-input-password id="login-otp" v-model:value="otp" autocomplete="one-time-code" /></template>
        <a-button
          type="primary"
          size="large"
          block
          html-type="submit"
          :loading="submitting"
          :disabled="!canSubmit"
        >进入工作台</a-button>
      </form>
      <RouterLink :to="username.trim().toLowerCase() === 'administrator' ? '/hbos/reset-password?administrator=1' : '/hbos/reset-password'">忘记密码或账号恢复</RouterLink>

      <div class="login-divider"><span>或</span></div>
      <a-skeleton v-if="loading" active :paragraph="{ rows: 1 }" />
      <template v-else>
        <a-button
          class="feishu-button"
          size="large"
          block
          :disabled="!status?.configured"
          @click="beginFeishuLogin"
        ><MessageOutlined /> 使用飞书登录</a-button>
        <div v-if="status?.configured" class="login-status ready"><CheckCircleOutlined /> 飞书授权入口已配置 · 登录时核验企业与成员</div>
        <div v-else class="login-status waiting"><ClockCircleOutlined /> 飞书企业成员登录尚未完成配置</div>
      </template>

      <div class="trust-chain">
        <span>企业身份</span><ArrowRightOutlined /><span>Frappe Session</span><ArrowRightOutlined /><span>应用授权</span><ArrowRightOutlined /><span>资料与设备范围</span>
      </div>
      <RouterLink to="/hbos/login?existing=1" @click="focusExistingAccount">已有账号：密码登录后绑定飞书</RouterLink>
      <footer><SafetyCertificateOutlined /> 无已有绑定的获准成员首次进入会开通普通账号，无默认密码；设密可在账号与安全中按需完成。</footer>
    </section>
  </main>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  ArrowRightOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  MessageOutlined,
  SafetyCertificateOutlined,
} from '@ant-design/icons-vue'
import type { FeishuLoginStatus } from '@/contracts/p1'
import { FrappeRequestError, loginWithPassword } from '@/services/frappeClient'
import { getFeishuLoginStatus } from '@/services/p1Api'
import { usePortalStore } from '@/stores/portal'

const route = useRoute()
const router = useRouter()
const portal = usePortalStore()
const loading = ref(true)
const submitting = ref(false)
const status = ref<FeishuLoginStatus | null>(null)
const error = ref<string | null>(null)
const username = ref('')
const password = ref('')
const otp = ref('')
const tmpId = ref('')

const statusMessages: Record<string, string> = {
  cancelled: '已取消飞书授权，HBOS 未建立会话。',
  config_required: '飞书登录尚未完成真实联调配置。',
  invalid_state: '登录状态已过期、已使用或与当前浏览器不匹配，请重新发起。',
  identity_unmapped: '企业成员自动开通尚未启用。',
  existing_account_requires_link: '当前浏览器已有 HBOS 账号。请在“我的与设置 → 账号与安全”验证密码及 MFA 后绑定本人飞书；没有自动创建另一账号。',
  identity_conflict: '该企业身份或自动账号存在冲突，请联系管理员核对。',
  identity_revoked: '此身份的旧绑定已撤销或更换。请验证原账号或联系管理员，通过受控账号归属流程恢复。',
  account_busy: '账号正在完成另一项操作，请重新发起授权。',
  same_identity: '新旧飞书身份相同，没有更改绑定。',
  personal_account_required: '接任者须先使用自己的永久个人账号；此回调不会开户或签发管理员会话。',
  operation_invalid: '账号变更验证会话无效，请重新发起。',
  account_changed: '账号登录方式已更换，旧会话已失效，请重新登录。',
  onboarding_dependency_missing: '登录名组件尚未部署，请管理员更新 Portal 依赖。',
  member_scope_denied: '此成员不在当前应用已批准的通讯录数据范围内。',
  account_disabled: '对应 HBOS 账号已停用或不允许从此入口登录。',
  tenant_rejected: '当前企业租户未获准访问 HBOS。',
  tenant_evidence_missing: '授权响应缺少企业标识，无法核验企业归属。',
  application_tenant_mismatch: '应用所属企业与当前 Site 保存企业不一致，请由管理员核对。',
  member_identity_mismatch: '授权人员标识与内部成员接口不一致，未建立会话。',
  member_status_missing: '成员状态证据缺失：请管理员开通应用身份“获取用户受雇信息 contact:user.employee:readonly”并发布生效。',
  member_status_invalid: '内部成员状态字段类型无法验证，未建立会话。',
  member_inactive: '飞书成员尚未激活。',
  member_disabled: '飞书成员已冻结或停用。',
  member_departed: '飞书成员已离职或退出，不能进入 HBOS。',
  member_department_missing: '成员部门证据缺失，请管理员核对实际准入政策。',
  member_api_failed: '内部成员接口未通过，请核对已发布的成员权限和应用数据范围。',
  external_member_rejected: '当前身份为外部成员，不能进入 HBOS。',
  exchange_failed: '飞书身份核验失败，未建立 HBOS 会话。',
  session_required: '请先登录后继续访问原页面。',
  signed_out: '已安全退出当前账号。',
}
const callbackMessage = computed(() => {
  const message = error.value || statusMessages[String(route.query.status || '')] || null
  const trace = typeof route.query.trace === 'string' && /^[a-f0-9]{16}$/.test(route.query.trace) ? route.query.trace : ''
  return message && trace ? `${message} 诊断编号：${trace}` : message
})
const callbackTone = computed(() => ['cancelled', 'signed_out'].includes(String(route.query.status || '')) ? 'info' : 'warning')
const canSubmit = computed(() => Boolean(username.value.trim() && password.value && !submitting.value))
function focusExistingAccount() { document.getElementById('hbos-username')?.focus() }

function safeRedirectTarget(): string {
  const value = typeof route.query.redirect_to === 'string' ? route.query.redirect_to : '/hbos'
  return value.startsWith('/hbos') && !value.startsWith('/hbos/login') ? value : '/hbos'
}

async function submitAccountLogin() {
  if (!canSubmit.value) return
  submitting.value = true
  error.value = null
  try {
    const result = await loginWithPassword(username.value.trim(), password.value, otp.value, tmpId.value)
    if (result.tmp_id && result.verification) { tmpId.value = result.tmp_id; return }
    if (!tmpId.value || otp.value) password.value = ''
    portal.clearSession()
    await portal.bootstrap()
    await router.replace(safeRedirectTarget())
  } catch (caught) {
    portal.clearSession()
    error.value = caught instanceof FrappeRequestError
      ? caught.message
      : '登录验证失败，请稍后重试。'
  } finally {
    if (!tmpId.value || error.value) password.value = ''
    submitting.value = false
  }
}

function beginFeishuLogin() {
  const redirectTo = encodeURIComponent(safeRedirectTarget())
  window.location.assign(`/api/method/hbos_portal.auth.feishu.start?redirect_to=${redirectTo}`)
}

onMounted(async () => {
  try {
    status.value = await getFeishuLoginStatus()
  } catch {
    status.value = null
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.login-page{position:relative;display:grid;min-height:100vh;place-items:center;overflow:hidden;padding:28px;background:linear-gradient(145deg,#edf4fc,#f7f9ff 45%,#eef8f5)}
.login-aurora{position:absolute;border-radius:50%;filter:blur(80px);opacity:.35}.login-aurora.one{width:430px;height:430px;left:-120px;top:-80px;background:#766cff}.login-aurora.two{width:480px;height:480px;right:-150px;bottom:-100px;background:#4bd4bf}
.login-card{position:relative;z-index:1;width:min(520px,100%);padding:34px 36px;border-radius:30px;box-shadow:0 34px 110px rgba(48,70,111,.15)}
.login-brand{display:flex;align-items:center;gap:10px;color:#203b66}.login-brand>span{display:grid;width:34px;height:34px;place-items:center;border-radius:11px;background:linear-gradient(135deg,#6861ff,#4aa6ff);color:#fff;font-weight:900}.login-brand strong,.login-brand small{display:block}.login-brand strong{font-size:16px}.login-brand small{margin-top:2px;color:#8390a4;font-size:9px}
.login-icon{display:grid;width:58px;height:58px;place-items:center;margin:26px auto 14px;border-radius:18px;background:linear-gradient(135deg,#3375ff,#17b6b2);color:#fff;font-size:26px;box-shadow:0 16px 36px rgba(40,115,224,.22)}
.eyebrow{text-align:center;color:#6d7da1;font-size:10px;font-weight:800;letter-spacing:.15em}.login-card h1{margin:7px 0 9px;text-align:center;color:#19365f;font-size:30px;letter-spacing:-.8px}.login-copy{margin:0 auto 20px;max-width:420px;text-align:center;color:#6f809a;font-size:12px;line-height:1.75}
.login-alert{margin-bottom:17px;border-radius:13px}.account-form{display:grid;gap:9px}.account-form label{color:#4f6180;font-size:11px;font-weight:700}.account-form :deep(.ant-input-affix-wrapper),.account-form :deep(.ant-input){border-radius:12px}.account-form>.ant-btn{height:46px;margin-top:5px;border:0;border-radius:13px;background:linear-gradient(135deg,#4f65fa,#3ca9ee);font-weight:700}
.login-divider{display:flex;align-items:center;gap:12px;margin:18px 0;color:#97a3b5;font-size:10px}.login-divider::before,.login-divider::after{height:1px;flex:1;background:rgba(65,91,138,.1);content:""}.feishu-button{height:44px;border-radius:13px}.login-status{display:flex;align-items:center;justify-content:center;gap:7px;margin-top:10px;font-size:10px}.login-status.ready{color:#168763}.login-status.waiting{color:#9a7838}
.trust-chain{display:flex;align-items:center;justify-content:center;gap:7px;margin:22px 0 15px;color:#7988a0;font-size:9px;flex-wrap:wrap}.trust-chain>:nth-child(even){color:#a7b2c3}.login-card footer{display:flex;align-items:center;justify-content:center;gap:7px;padding-top:14px;border-top:1px solid rgba(65,91,138,.09);color:#76869e;font-size:9px}
@media(max-width:560px){.login-page{padding:14px}.login-card{padding:24px 20px;border-radius:22px}.login-icon{margin-top:20px}.trust-chain{display:none}}
</style>
