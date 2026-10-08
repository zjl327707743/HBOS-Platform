<template>
  <a-config-provider :theme="hbosAntdTheme" :locale="zhCN">
    <RouterView />
  </a-config-provider>
</template>

<script setup lang="ts">
// AntD 默认是英文 locale：空表格显示 "No data"、日期选择器是英文月份、
// 分页是 "Page 1 of 3"。整个门户是中文界面，统一在根上换成中文，
// 否则每个页面各配一次、迟早漏掉一处。
import zhCN from 'ant-design-vue/es/locale/zh_CN'
import { hbosAntdTheme } from '@/theme/antdTheme'
</script>
