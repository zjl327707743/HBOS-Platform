<script setup lang="ts">import { iamSession } from '@/services/iamAccess'</script>
<template><section class="iam-panel"><h1>暂不能进入此管理页面</h1><p>{{ iamSession.error || '当前账号没有此项管理能力，或服务端尚未确认访问范围。' }}</p><p>管理权和业务数据读取权分别核验，请联系对应负责人。</p><RouterLink to="/hbos">返回工作台</RouterLink></section></template>
