<template>
  <a-tooltip title="消息与通知">
    <a-button class="top-icon-button" type="text" shape="circle" aria-label="打开消息与通知" @click="open = true"><BellOutlined /></a-button>
  </a-tooltip>
  <a-drawer v-model:open="open" title="消息与通知" :width="420" placement="right" root-class-name="hbos-notification-drawer">
    <a-alert message="消息通知尚未接入" description="业务待办请在“我的工作”查看。" type="info" show-icon />
    <a-button style="margin-top:20px" type="primary" @click="open = false; router.push('/hbos/work')">查看我的工作</a-button>
  </a-drawer>
</template>
<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { BellOutlined } from '@ant-design/icons-vue'
const open = ref(false)
const router = useRouter()
</script>
