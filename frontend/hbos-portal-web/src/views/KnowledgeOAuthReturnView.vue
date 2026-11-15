<template>
  <main class="kb-oauth-return">
    <h1>连接我的助手</h1>
    <p v-if="invalid">连接请求无效。请回到助手重新发起连接。</p>
    <p v-else>正在确认当前账号，请稍候。</p>
    <RouterLink v-if="invalid" to="/hbos/knowledge">返回知识库</RouterLink>
  </main>
</template>
<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { oauthConsentReturnPath } from '@/services/knowledgeOAuthGuidance'
const route = useRoute()
const invalid = ref(false)
onMounted(() => {
  const path = oauthConsentReturnPath(route.query)
  if (!path) { invalid.value = true; return }
  window.location.replace(path)
})
</script>
<style scoped>
.kb-oauth-return { max-width: 40rem; margin: 4rem auto; padding: 1.5rem; }
</style>
