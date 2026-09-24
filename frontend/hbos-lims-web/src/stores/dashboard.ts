import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { useTaskStore } from './task'

export const useDashboardStore = defineStore('dashboard', () => {
  const taskStore = useTaskStore()
  const kpi = ref({ pending: 0, testing: 0, review: 0, coa: 0 })
  const rhythmByGroup = ref<{ label: string; value: number }[]>([])
  const distribution = ref<{ name: string; value: number; color: string }[]>([])
  const loading = ref(false)

  const taskCount = computed(() => taskStore.tasks.length)
  const tasksOverdue = computed(() => taskStore.tasks.filter((t) => t.overdue === '是').length)
  const tasksTodayDue = computed(() => {
    const today = new Date().toISOString().slice(0, 10)
    return taskStore.tasks.filter((t) => t.due_date === today && t.status !== '已批准').length
  })
  const tasksOos = computed(() => taskStore.tasks.filter((t) => ['OOS候选', 'OOS锁定'].includes(t.status)).length)

  async function loadAll() {
    loading.value = true
    try {
      await taskStore.fetchBoard()
      const tasks = taskStore.tasks

      kpi.value.pending = tasks.filter((t) => ['待分配', '已分配'].includes(t.status)).length
      kpi.value.testing = tasks.filter((t) => ['检验中'].includes(t.status)).length
      kpi.value.review = tasks.filter((t) => ['已提交', '已复核'].includes(t.status)).length
      kpi.value.coa = 0 // COA 发布计数由 coa store 提供

      // 按检验组统计
      const groupMap = new Map<string, number>()
      for (const t of tasks) {
        const g = t.lab_department || '未分组'
        groupMap.set(g, (groupMap.get(g) || 0) + 1)
      }
      rhythmByGroup.value = [...groupMap.entries()].map(([label, value]) => ({ label, value }))

      // 状态分布
      const statusMap = new Map<string, number>()
      for (const t of tasks) {
        statusMap.set(t.status, (statusMap.get(t.status) || 0) + 1)
      }
      const colorByStatus: Record<string, string> = {
        待分配: '#9aa8a3', 已分配: '#5f8d80', 检验中: '#d1871d',
        已提交: '#2b6cb0', 已复核: '#2b8a73', 已批准: '#1d8a5b',
        OOS候选: '#c24d3f', OOS锁定: '#a93a2d',
      }
      distribution.value = [...statusMap.entries()].map(([name, value]) => ({
        name, value, color: colorByStatus[name] || '#dbe5e1',
      }))
    } finally {
      loading.value = false
    }
  }

  return { kpi, rhythmByGroup, distribution, loading, taskCount, tasksOverdue, tasksTodayDue, tasksOos, loadAll }
})
