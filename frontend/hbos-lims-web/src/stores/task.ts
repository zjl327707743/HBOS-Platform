import { defineStore } from 'pinia'
import { ref } from 'vue'
import { runReport } from '@/api/lims'

export interface TaskRow {
  task_name: string
  sample: string
  material_name: string
  batch_no: string
  item_name: string
  lab_department: string
  assignee: string
  priority: string
  assigned_date: string
  due_date: string
  status: string
  overdue: string
}

export const useTaskStore = defineStore('task', () => {
  const tasks = ref<TaskRow[]>([])
  const loading = ref(false)

  async function fetchBoard(filters: Record<string, unknown> = {}) {
    loading.value = true
    try {
      const res = await runReport('待检任务看板', filters)
      tasks.value = (res.result || []) as unknown as TaskRow[]
      return tasks.value
    } finally {
      loading.value = false
    }
  }

  return { tasks, loading, fetchBoard }
})
