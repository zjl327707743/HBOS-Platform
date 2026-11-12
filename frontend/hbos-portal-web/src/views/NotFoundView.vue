<script setup lang="ts">
import PortalBrand from '@/components/portal/PortalBrand.vue'
import PortalStatusScreen from '@/components/portal/PortalStatusScreen.vue'
</script>

<template>
  <div class="v10-standalone">
    <header class="v10-standalone-brand"><PortalBrand /></header>
    <main class="v10-standalone-content">
      <nav class="v10-context" aria-label="当前位置"><RouterLink to="/hbos">工作台</RouterLink><span aria-current="page">页面不存在</span></nav>
      <PortalStatusScreen code="404" title="这个页面暂时找不到"
        description="链接可能已变更。返回工作台，或从应用中心查找你要使用的入口。" show-apps />
      <footer class="v10-footer">海滨智能工作平台 <span>HBOS · WORKSPACE</span></footer>
    </main>
  </div>
</template>
