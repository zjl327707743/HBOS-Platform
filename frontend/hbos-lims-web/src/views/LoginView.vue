<template>
  <div class="login-wrap">
    <div class="login-card">
      <div class="brand">
        <div class="brand-mark"><el-icon :size="20"><Platform /></el-icon></div>
        <div>
          <div class="brand-name">海滨LIMS</div>
          <div class="brand-sub">Laboratory Information System</div>
        </div>
      </div>

      <h1>登录系统</h1>
      <p class="desc">使用 Frappe 账号登录，权限由系统角色控制（LIMS Analyst / Reviewer / Manager）</p>

      <el-form :model="form" label-position="top" size="large" @submit.prevent="doLogin">
        <el-form-item label="账号">
          <el-input v-model="form.usr" placeholder="Administrator" />
        </el-form-item>
        <el-form-item label="密码">
          <el-input v-model="form.pwd" type="password" show-password placeholder="请输入密码" @keyup.enter="doLogin" />
        </el-form-item>
        <el-button type="primary" size="large" style="width:100%" :loading="loading" @click="doLogin">
          登录
        </el-button>
        <div v-if="errorMsg" class="error-msg">{{ errorMsg }}</div>
      </el-form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import { Platform } from '@element-plus/icons-vue'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const loading = ref(false)
const errorMsg = ref('')

const form = reactive({ usr: 'Administrator', pwd: '' })

async function doLogin() {
  if (!form.usr || !form.pwd) {
    errorMsg.value = '请输入账号和密码'
    return
  }
  loading.value = true
  errorMsg.value = ''
  const ok = await auth.login(form.usr, form.pwd)
  loading.value = false
  if (ok) {
    // 强制整页跳转，确保 session Cookie 生效并重置前端状态
    const redirect = new URLSearchParams(window.location.search).get('redirect') || '/dashboard'
    window.location.href = redirect
  } else {
    errorMsg.value = '登录失败，请检查账号密码'
  }
}
</script>

<style scoped>
.login-wrap {
  min-height: 100vh;
  display: grid;
  place-items: center;
  background: linear-gradient(160deg, var(--sidebar) 0%, var(--sidebar-2) 100%);
  padding: 22px;
}

.login-card {
  width: 380px;
  background: var(--surface);
  border-radius: 12px;
  padding: 32px 30px;
  box-shadow: 0 16px 48px rgba(0, 0, 0, 0.24);
}

.brand { display: flex; align-items: center; gap: 10px; margin-bottom: 26px; }
.brand-mark {
  width: 40px; height: 40px; border-radius: 10px;
  background: var(--primary); color: #fff;
  display: grid; place-items: center;
}
.brand-name { font-size: 17px; font-weight: 700; color: var(--ink); }
.brand-sub { font-size: 11px; color: var(--muted); margin-top: 2px; }

h1 { font-size: 20px; color: var(--ink); }
.desc { font-size: 12px; color: var(--muted); margin: 8px 0 22px; line-height: 1.6; }

.error-msg { margin-top: 12px; font-size: 12px; color: var(--danger); }
</style>
