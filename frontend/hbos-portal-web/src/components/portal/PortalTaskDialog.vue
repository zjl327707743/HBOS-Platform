<script setup lang="ts">
import { watch } from 'vue'
import { useRouter } from 'vue-router'
import type { UnifiedTaskDTO } from '@/contracts/portal'
import { openBusinessRoute } from '@/services/businessNavigation'

const props = defineProps<{ task: UnifiedTaskDTO | null }>()
const emit = defineEmits<{ close: [] }>()
const router = useRouter()
let returnFocus: HTMLElement | null = null
watch(() => props.task, (task, previous) => {
  if (task && !previous) returnFocus = document.activeElement instanceof HTMLElement ? document.activeElement : null
}, { flush: 'sync' })
function restoreFocus() {
  const element = returnFocus
  returnFocus = null
  if (element?.isConnected && !element.closest('[inert]')) element.focus({ preventScroll: true })
}

function enter() {
  const task = props.task
  if (!task) return
  emit('close')
  void openBusinessRoute(router, task.appId, task.deepLink)
}
</script>
<template>
  <a-modal :open="Boolean(task)" :title="task?.title" :footer="null" :width="640" wrap-class-name="v10-dialog" :focus-trigger-after-close="false" :after-close="restoreFocus" @cancel="$emit('close')">
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
