<template>
  <section class="setting-card glass-surface diagnostics">
    <h3>管理员应用诊断</h3><p>检查已安装 App、Provider、路由、当前账号授权和构建版本。不会给被检查账号增加权限。</p>
    <a-space wrap><a-input v-model:value="user" placeholder="留空检查当前管理员，或输入已有 User" /><a-button :loading="busy" @click="load">检查</a-button></a-space>
    <a-alert v-if="error" :message="error" type="warning" show-icon />
    <template v-if="result"><p>构建：{{ result.build.build_id || result.build.status }} · 提交 {{ result.build.source_commit?.slice(0, 12) }}</p><p>已安装：{{ result.installed_apps.join('、') }}</p><div v-for="app in result.apps" :key="app.app_id" class="diagnostic-row"><strong>{{ app.title || app.app_id }}</strong><a-tag :color="app.visible ? 'green' : 'orange'">{{ app.visible ? '可见' : '未显示' }}</a-tag><small>{{ app.reason }} · {{ app.route }} · {{ app.capabilities?.join(' / ') }}</small></div><p v-if="result.failures.length">Provider 注册失败 {{ result.failures.length }} 项，请检查服务端受保护日志。</p></template>
  </section>
</template>
<script setup lang="ts">
import { ref } from 'vue'
import { callFrappeMethod } from '@/services/frappeClient'
interface Result { installed_apps: string[]; build: { build_id?: string; source_commit?: string; status?: string }; apps: { app_id: string; title?: string; visible: boolean; reason: string; route?: string; capabilities?: string[] }[]; failures: unknown[] }
const user = ref(''), busy = ref(false), error = ref(''), result = ref<Result | null>(null)
async function load() { busy.value = true; error.value = ''; try { result.value = await callFrappeMethod('hbos_portal.api.diagnostics.get_diagnostics', { user: user.value || undefined }) } catch { error.value = '诊断未完成，请核对目标账号是否存在且已启用。' } finally { busy.value = false } }
</script>
<style scoped>.diagnostics{padding:22px}.diagnostics p,.diagnostics small{color:#64748b;line-height:1.7}.diagnostic-row{padding:12px 0;border-bottom:1px solid #e8edf6}.diagnostic-row small{display:block}.diagnostic-row strong{margin-right:12px}</style>
