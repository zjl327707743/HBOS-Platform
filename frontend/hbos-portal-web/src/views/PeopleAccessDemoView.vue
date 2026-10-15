<template>
  <div v-if="portalDataSource === 'mock'" class="iam-page">
    <div class="iam-page-heading"><div><h1>人员与权限</h1><p>按组织岗位管理人员与角色</p></div><span class="iam-version">前端复刻 · 演示模式</span></div>
    <nav class="iam-page-tabs" aria-label="人员与权限页面"><RouterLink to="/hbos/admin/people">人员信息</RouterLink><RouterLink to="/hbos/admin/roles">权限管理</RouterLink><span>组织岗位 → 角色权限 → 人员任职</span></nav>
    <PeopleInformation v-if="route.name === 'admin-people'" /><RoleManagement v-else />
  </div>
</template>
<script setup lang="ts">
import { useRoute } from 'vue-router'
import { portalDataSource } from '@/services/portalProvider'
import PeopleInformation from '@/components/peopleAccess/PeopleInformation.vue'
import RoleManagement from '@/components/peopleAccess/RoleManagement.vue'
import '@/styles/peopleAccess.css'
const route = useRoute()
</script>
