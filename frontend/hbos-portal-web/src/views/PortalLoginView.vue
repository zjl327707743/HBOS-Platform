<template>
  <div class="system-state-page login-page">
    <div class="state-visual login">
      <LockOutlined />
    </div>
    <div class="state-code">HBOS PORTAL</div>
    <h1>登录海滨智能运营工作台</h1>
    <p>使用 Frappe 账号登录。登录状态由当前浏览器会话保持，仅用于本机开发工作台。</p>

    <a-form class="login-form" :model="form" layout="vertical" @finish="onSubmit">
      <a-form-item label="账号" name="usr" :rules="[{ required: true, message: '请输入账号' }]">
        <a-input
          v-model:value="form.usr"
          size="large"
          autocomplete="username"
          placeholder="Administrator"
        />
      </a-form-item>
      <a-form-item label="密码" name="pwd" :rules="[{ required: true, message: '请输入密码' }]">
        <a-input-password
          v-model:value="form.pwd"
          size="large"
          autocomplete="current-password"
          placeholder="请输入密码"
        />
      </a-form-item>

      <a-alert v-if="error" class="login-error" type="error" show-icon :message="error" />

      <a-button type="primary" html-type="submit" size="large" block :loading="submitting">
        登录
      </a-button>
    </a-form>
  </div>
</template>

<script setup lang="ts">
import { isSafeInternalPath } from '@/services/internalPath'
import { reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { LockOutlined } from '@ant-design/icons-vue'
import { usePortalStore } from '@/stores/portal'

const portal = usePortalStore()
const route = useRoute()
const router = useRouter()

const form = reactive({ usr: '', pwd: '' })
const submitting = ref(false)
const error = ref<string | null>(null)

/** 只接受站内绝对路径，避免 redirect 参数造成开放重定向。 */
function safeRedirect(value: unknown): string {
  if (typeof value !== 'string') return '/hbos'
  if (!isSafeInternalPath(value)) return '/hbos'
  return value
}

async function onSubmit() {
  submitting.value = true
  error.value = null
  try {
    await portal.signIn(form.usr, form.pwd)
    await router.replace(safeRedirect(route.query.redirect))
  } catch {
    error.value = '账号或密码不正确，或服务暂时不可用。'
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.system-state-page.login-page {
  min-height: 100vh;
}

.state-visual.login {
  color: #6b62ff;
  background: linear-gradient(135deg, #ebe9ff, #e4f4ff);
}

.login-form {
  width: min(360px, 100%);
  text-align: left;
}

.login-error {
  margin-bottom: var(--hbos-space-4);
}
</style>
