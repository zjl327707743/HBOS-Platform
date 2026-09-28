<template>
  <div class="portal-embed">
    <div v-if="loading" class="portal-embed-loading">
      <a-spin />
      <p class="portal-embed-loading-text">业务页面加载中…</p>
    </div>
    <a-alert v-else-if="error" type="error" show-icon :message="error" />
    <iframe
      v-else-if="src"
      :src="src"
      :title="title"
      class="portal-embed-frame"
    ></iframe>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { resolveBusinessRoute } from '@/services/portalProvider'

const route = useRoute()
const src = ref('')
const error = ref('')
const loading = ref(false)
const title = ref('业务应用')

onMounted(async () => {
  const appId = String(route.query.app ?? '')
  const stablePath = String(route.query.path ?? '')

  if (!appId || !stablePath) {
    error.value = '缺少业务应用参数'
    return
  }

  loading.value = true
  try {
    // 同源前提由 Vite 代理保证：Frappe 发 X-Frame-Options: SAMEORIGIN，
    // 浏览器可见来源不一致时该 iframe 会被直接拦截。
    const resolved = await resolveBusinessRoute(appId, stablePath)
    // mock 模式会原样返回 URL 提供的 path；只接受同源绝对路径，
    // 否则第三方页面会被嵌进门户外壳。非字符串（如 __proto__ 命中
    // Object.prototype）同样在此拦下。
    if (
      typeof resolved !== 'string'
      || !resolved.startsWith('/')
      || resolved.startsWith('//')
    ) {
      error.value = '业务页面地址无效'
      return
    }
    src.value = resolved
  } catch (cause) {
    error.value = (cause instanceof Error && cause.message) || '业务页面加载失败'
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.portal-embed {
  height: 100%;
  min-height: 60vh;
}

.portal-embed-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  min-height: 60vh;
}

.portal-embed-loading-text {
  margin: 0;
  color: rgba(0, 0, 0, 0.45);
}

.portal-embed-frame {
  width: 100%;
  height: 100%;
  min-height: 60vh;
  border: 0;
  border-radius: 12px;
  background: #fff;
}
</style>
