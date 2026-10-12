<template>
  <div class="system-state-page">
    <div class="state-visual notfound"><ExperimentOutlined /></div>
    <h1>LIMS 前台页面待设计</h1>
    <p>这个入口已保留在 HBOS Portal。页面结构和业务操作将在开发规范确认后实现；当前不展示示例业务数据。</p>
    <a-button type="primary" @click="$router.push('/hbos/apps')">返回应用中心</a-button>
  </div>
</template>

<script setup lang="ts">
import { ExperimentOutlined } from '@ant-design/icons-vue'
</script>
