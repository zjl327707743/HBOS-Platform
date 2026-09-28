<template>
  <div class="portal-embed">
    <a-alert v-if="error" type="error" show-icon :message="error" />
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
const title = ref('业务应用')

onMounted(async () => {
  const appId = String(route.query.app ?? '')
  const stablePath = String(route.query.path ?? '')

  if (!appId || !stablePath) {
    error.value = '缺少业务应用参数'
    return
  }

  try {
    // 同源前提由 Vite 代理保证：Frappe 发 X-Frame-Options: SAMEORIGIN，
    // 浏览器可见来源不一致时该 iframe 会被直接拦截。
    src.value = await resolveBusinessRoute(appId, stablePath)
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : '业务页面加载失败'
  }
})
</script>

<style scoped>
.portal-embed {
  height: 100%;
  min-height: 60vh;
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
