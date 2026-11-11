<script setup lang="ts">
import { useRouter } from 'vue-router'
import type { UnifiedTaskDTO } from '@/contracts/portal'
import { openBusinessRoute } from '@/services/businessNavigation'

const props = defineProps<{ task: UnifiedTaskDTO | null }>()
const emit = defineEmits<{ close: [] }>()
const router = useRouter()

function enter() {
  const task = props.task
  if (!task) return
  emit('close')
  void openBusinessRoute(router, task.appId, task.deepLink)
}
</script>
<template>
  <a-modal :open="Boolean(task)" :title="task?.title" :footer="null" :width="640" wrap-class-name="v10-dialog" @cancel="$emit('close')">
    <div v-if="task" class="v10-task-dialog">
      <a-tag>{{ task.appTitle }}</a-tag>
      <p>{{ task.description }}</p>
      <p v-if="task.dueLabel">截止或完成时间：{{ task.dueLabel }}</p>
      <p v-if="task.domainStatus">当前状态：{{ task.domainStatus }}</p>
      <div class="v10-actions">
        <a-button type="primary" @click="enter">{{ task.actionLabel || '进入来源应用' }}</a-button>
        <a-button @click="$emit('close')">关闭</a-button>
      </div>
    </div>
  </a-modal>
</template>
