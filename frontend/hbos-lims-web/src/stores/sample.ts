import { defineStore } from 'pinia'
import { ref } from 'vue'
import { listDoctype, getDoc, runReport } from '@/api/lims'

export interface Sample {
  name: string
  material_code?: string
  material_name?: string
  batch_no?: string
  sample_type?: string
  sample_source?: string
  specification?: string
  spec_version?: string
  priority?: string
  status?: string
  test_due_date?: string
  creation?: string
  requestor?: string
  oos_locked?: number
}

export const useSampleStore = defineStore('sample', () => {
  const samples = ref<Sample[]>([])
  const loading = ref(false)
  const loaded = ref(false)

  async function fetchAll(force = false) {
    if (loaded.value && !force) return samples.value
    loading.value = true
    try {
      samples.value = await listDoctype<Sample>('HBOS Sample', [
        'name', 'material_code', 'material_name', 'batch_no', 'sample_type',
        'sample_source', 'specification', 'spec_version', 'priority', 'status',
        'test_due_date', 'creation', 'requestor', 'oos_locked',
      ], {}, 100, 'creation desc')
      loaded.value = true
    } finally {
      loading.value = false
    }
    return samples.value
  }

  async function fetchByName(name: string): Promise<Sample> {
    return getDoc<Sample>('HBOS Sample', name)
  }

  // 使用样品台账报表（含状态/优先级汇总）
  async function fetchLedgerReport(filters: Record<string, unknown> = {}) {
    const res = await runReport('样品台账', filters)
    return res
  }

  return { samples, loading, loaded, fetchAll, fetchByName, fetchLedgerReport }
})
