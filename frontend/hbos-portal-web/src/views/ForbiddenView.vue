<script setup lang="ts">
import PortalStatusScreen from '@/components/portal/PortalStatusScreen.vue'
</script>

<template>
  <PortalStatusScreen code="403" title="暂时没有此页面的访问权限"
    description="查看当前账号可用的应用，或联系有权限的管理员核对访问范围。" show-apps />
</template>
