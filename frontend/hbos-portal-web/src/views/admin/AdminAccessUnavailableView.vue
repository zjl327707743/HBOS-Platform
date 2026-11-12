<script setup lang="ts">
import { iamSession } from '@/services/iamAccess'
import PageHeading from '@/components/iam/PageHeading.vue'
import PortalStatusScreen from '@/components/portal/PortalStatusScreen.vue'
</script>

<template>
  <section class="r6-page">
    <PageHeading title="暂不能进入此管理页面" description="管理权限尚未确认，暂时不能在此操作。" />
    <PortalStatusScreen
      title="暂未确认管理权限"
      :description="iamSession.error || '管理权限与业务数据查看权限分别核验。请联系管理员确认你的管理范围。'"
      home-label="返回工作台" />
  </section>
</template>
