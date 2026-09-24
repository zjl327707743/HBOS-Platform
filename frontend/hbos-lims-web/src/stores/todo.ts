import { defineStore } from 'pinia'
import { reactive, ref } from 'vue'
import { getMyTodoSummary, getMyTodos } from '@/api/todo'
import type { TodoFilters, TodoItem, TodoSummary } from '@/api/todo'
import {
  emptySummary,
  normalizeTodoItem,
  retainPreviousOnError,
  sortTodoItems,
} from '@/features/todos/todoModel'

export const useTodoStore = defineStore('todo', () => {
  const summary = ref<TodoSummary>(emptySummary())
  const items = ref<TodoItem[]>([])
  const filteredSummary = ref<TodoSummary>(emptySummary())
  const filters = reactive<TodoFilters>({ limit: 20, offset: 0 })
  const loading = ref(false)
  const error = ref<string | null>(null)
  const generatedAt = ref<string | null>(null)
  const listLoaded = ref(false)

  function errorMessage(reason: unknown): string {
    return reason instanceof Error ? reason.message : '待办数据加载失败'
  }

  async function fetchSummary(options: { preserveOnError?: boolean } = {}) {
    const preserveOnError = options.preserveOnError ?? true
    loading.value = true
    try {
      const response = await getMyTodoSummary()
      summary.value = retainPreviousOnError(summary.value, response.summary, false)
      generatedAt.value = response.generated_at
      error.value = null
      return response
    } catch (reason) {
      if (!preserveOnError) summary.value = emptySummary()
      error.value = errorMessage(reason)
      return null
    } finally {
      loading.value = false
    }
  }

  async function fetchList() {
    loading.value = true
    try {
      const response = await getMyTodos({ ...filters })
      items.value = sortTodoItems(response.items.map(normalizeTodoItem))
      filteredSummary.value = response.filtered_summary
      generatedAt.value = response.generated_at
      listLoaded.value = true
      error.value = null
      return response
    } catch (reason) {
      error.value = errorMessage(reason)
      return null
    } finally {
      loading.value = false
    }
  }

  async function refreshAll() {
    await Promise.all([fetchSummary(), fetchList()])
  }

  function setFilters(next: Partial<TodoFilters>) {
    Object.assign(filters, next)
  }

  function resetFilters() {
    Object.assign(filters, { module: undefined, owner_type: undefined, status: undefined, priority: undefined, overdue: undefined, keyword: undefined, limit: 20, offset: 0 })
  }

  function removeResolved(todoKey: string) {
    items.value = items.value.filter((item) => item.todo_key !== todoKey)
  }

  function clearForLogout() {
    summary.value = emptySummary()
    filteredSummary.value = emptySummary()
    items.value = []
    resetFilters()
    generatedAt.value = null
    listLoaded.value = false
    error.value = null
    loading.value = false
  }

  return {
    summary,
    items,
    filteredSummary,
    filters,
    loading,
    error,
    generatedAt,
    listLoaded,
    fetchSummary,
    fetchList,
    refreshAll,
    setFilters,
    resetFilters,
    removeResolved,
    clearForLogout,
  }
})
