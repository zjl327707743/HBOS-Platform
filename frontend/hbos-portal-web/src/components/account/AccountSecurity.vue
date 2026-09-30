<template>
  <section class="setting-card glass-surface account-security">
    <h3>账号与安全</h3>
    <p>密码与飞书使用同一个 HBOS 账号。修改登录方式会保留原有角色与业务资料。</p>
    <a-alert v-if="error" :message="error" type="warning" show-icon />
    <a-alert v-if="notice" :message="notice" type="success" show-icon />
    <a-skeleton v-if="!status" active />
    <template v-else>
      <a-descriptions :column="1" size="small">
        <a-descriptions-item label="登录名">{{ status.login_name }}</a-descriptions-item>
        <a-descriptions-item label="密码">{{ status.has_password ? '已设置' : '仅飞书登录 · 尚未设置密码' }}</a-descriptions-item>
        <a-descriptions-item label="飞书">{{ status.feishu_bound ? '已绑定' : '未绑定' }}</a-descriptions-item>
        <a-descriptions-item label="邮箱恢复">{{ status.mail_recovery_available ? '可用' : '当前无可用邮件恢复渠道' }}</a-descriptions-item>
      </a-descriptions>
      <a-alert v-if="!status.feishu_configured" message="飞书尚未完成企业配置，现有密码登录可继续使用。" type="info" show-icon />
      <a-alert v-if="status.administrator && !status.administrator_link_enabled" message="Administrator 飞书绑定需 Owner 专门启用，原密码应急入口保留。" type="info" show-icon />
      <form class="security-form" @submit.prevent="verify">
        <div v-if="status.has_password && status.feishu_bound" class="security-actions">
          <a-button :type="passwordMode ? 'primary' : 'default'" :disabled="busy" @click="chooseVerification(false)">使用原密码验证</a-button>
          <a-button :type="!passwordMode ? 'primary' : 'default'" :disabled="busy || !status.feishu_stepup_available" @click="chooseVerification(true)">忘记原密码 · 本人飞书验证码</a-button>
        </div>
        <label :for="passwordMode ? 'security-current-password' : 'security-feishu-code'">{{ passwordMode ? '当前密码，验证本人身份' : '飞书收件验证码，验证本人身份' }}</label>
        <a-input-password v-if="passwordMode" id="security-current-password" v-model:value="password" autocomplete="current-password" />
        <template v-else>
          <a-button :disabled="!status.feishu_stepup_available || busy" @click="sendCode">发送验证码到本人飞书</a-button>
          <a-input id="security-feishu-code" v-model:value="code" inputmode="numeric" autocomplete="one-time-code" placeholder="6 位安全验证码" />
          <p v-if="!status.feishu_stepup_available">飞书收件验证码尚不可用，请使用已验证恢复邮箱或管理员受控恢复。</p>
        </template>
        <template v-if="tmpId"><label for="security-otp">账号原有二次认证</label><a-input id="security-otp" v-model:value="otp" autocomplete="one-time-code" /></template>
        <a-button html-type="submit" :loading="busy" :disabled="passwordMode ? !password : !code">{{ verified ? '重新验证本人身份' : '验证本人身份' }}</a-button>
      </form>
      <div class="security-actions">
        <a-button v-if="!status.feishu_bound" :disabled="!verified || !status.feishu_configured || (status.administrator && !status.administrator_link_enabled)" @click="bind">绑定本人飞书</a-button>
        <a-button v-else danger :disabled="!verified || !status.has_password || !verifiedWithPassword" @click="unlink">解绑飞书（须原密码验证）</a-button>
        <a-button type="link" @click="router.push('/hbos/reset-password')">找回密码与恢复</a-button>
      </div>
      <p v-if="status.feishu_bound && !status.has_password">请先设置密码，才能解绑最后一个登录方式。</p>
      <form class="security-form" @submit.prevent="changePassword">
        <label for="security-new-password">{{ status.has_password ? '新登录密码' : '设置登录密码' }}</label>
        <a-input-password id="security-new-password" v-model:value="newPassword" autocomplete="new-password" />
        <label for="security-confirm-password">再次输入密码</label>
        <a-input-password id="security-confirm-password" v-model:value="confirmation" autocomplete="new-password" />
        <a-button type="primary" html-type="submit" :loading="busy" :disabled="!verified || !newPassword || newPassword !== confirmation">保存密码</a-button>
      </form>
      <a-collapse v-if="status.can_admin_recover" class="admin-recovery">
        <a-collapse-panel key="recovery" header="管理员受控恢复">
          <p>核对本人身份与账号所有权后签发 15 分钟有效的一次性凭据。不会直接改密；Administrator 保留原生应急恢复。</p>
          <a-input v-model:value="recoveryUser" placeholder="目标 HBOS User 标识" autocomplete="off" />
          <a-textarea v-model:value="recoveryReason" placeholder="身份核验依据（至少 12 个字符，记录审计）" />
          <a-button :disabled="!verified || !recoveryUser || recoveryReason.length < 12" @click="issueRecovery">签发恢复凭据</a-button>
          <p v-if="recoveryKey">一次性凭据：<code>{{ recoveryKey }}</code>。仅私下交付已核验本人，在恢复页输入。</p>
        </a-collapse-panel>
      </a-collapse>
    </template>
  </section>
</template>
<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { getSecurity, reauthenticate, requestFeishuCode, verifyFeishuCode, startLink, setPassword, unlinkFeishu, adminIssueRecovery, type SecurityStatus } from '@/services/accountApi'
import { clearFrappeCsrfToken } from '@/services/frappeClient'
const router = useRouter()
const status = ref<SecurityStatus | null>(null)
const password = ref(''), newPassword = ref(''), confirmation = ref(''), code = ref(''), otp = ref(''), tmpId = ref('')
const recoveryUser = ref(''), recoveryReason = ref(''), recoveryKey = ref('')
const verified = ref(false), busy = ref(false), error = ref(''), notice = ref('')
const useFeishu = ref(false), verifiedWithPassword = ref(false)
const passwordMode = computed(() => Boolean(status.value?.has_password && !useFeishu.value))
function chooseVerification(feishu: boolean) { useFeishu.value = feishu; verified.value = false; verifiedWithPassword.value = false; password.value = ''; code.value = ''; otp.value = ''; tmpId.value = '' }
async function run(fn: () => Promise<void>) { busy.value = true; error.value = ''; notice.value = ''; try { await fn() } catch { verified.value = false; error.value = '操作未完成：请检查本人验证、密码策略、绑定冲突或企业配置，并重新验证后再试。' } finally { busy.value = false } }
async function verify() { await run(async () => { const result = passwordMode.value ? await reauthenticate(password.value, otp.value, tmpId.value) : await verifyFeishuCode(code.value, otp.value, tmpId.value); if (result.mfa_required) { tmpId.value = result.tmp_id || ''; notice.value = '请完成原有二次认证。'; return }; verified.value = true; verifiedWithPassword.value = passwordMode.value; password.value = ''; code.value = ''; otp.value = ''; tmpId.value = ''; notice.value = '本人验证完成，5 分钟内可执行一次安全操作。' }) }
async function sendCode() { await run(async () => { await requestFeishuCode(); notice.value = '验证码已发送到当前账号绑定的本人飞书。' }) }
async function bind() { await run(async () => { const result = await startLink(); verified.value = false; window.location.assign(result.authorize_url) }) }
async function changePassword() { await run(async () => { if (newPassword.value !== confirmation.value) return; try { const result = await setPassword(newPassword.value); verified.value = false; clearFrappeCsrfToken(); status.value = await getSecurity(); notice.value = `密码已保存，登录名：${result.login_name}。其他旧会话已失效。` } finally { newPassword.value = ''; confirmation.value = '' } }) }
async function unlink() { await run(async () => { await unlinkFeishu(); verified.value = false; status.value = await getSecurity(); notice.value = '飞书已解绑，原账号和业务资料保留。' }) }
async function issueRecovery() { await run(async () => { const result = await adminIssueRecovery(recoveryUser.value, recoveryReason.value); verified.value = false; recoveryKey.value = result.recovery_key }) }
onMounted(() => run(async () => { status.value = await getSecurity() }))
</script>
<style scoped>
.account-security{padding:22px}.account-security h3{margin:0 0 8px}.account-security p{color:#64748b;line-height:1.7}.security-form{display:grid;gap:10px;margin:18px 0}.security-form label{font-weight:600}.security-actions{display:flex;gap:10px;flex-wrap:wrap}.admin-recovery{margin-top:18px}.admin-recovery :deep(.ant-input),.admin-recovery :deep(.ant-btn){margin-top:10px}
</style>
