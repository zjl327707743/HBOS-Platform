import { defineStore } from 'pinia'
import { ref } from 'vue'
import { listDoctype } from '@/api/lims'

export interface Coa {
  name: string
  sample: string
  batch_no?: string
  material_code?: string
  material_name?: string
  spec_version?: string
  report_status?: string
  qa_reviewer?: string
  qa_reviewed_at?: string
  published_by?: string
  published_at?: string
  pdf_attachment?: string
}

export const useCoaStore = defineStore('coa', () => {
  const coas = ref<Coa[]>([])
  const loading = ref(false)
  const loaded = ref(false)

  async function fetchAll(force = false) {
    if (loaded.value && !force) return coas.value
    loading.value = true
    try {
      coas.value = await listDoctype<Coa>('HBOS COA', [
        'name', 'sample', 'batch_no', 'material_code', 'material_name',
        'spec_version', 'report_status', 'qa_reviewer', 'qa_reviewed_at',
        'published_by', 'published_at', 'pdf_attachment',
      ], {}, 100, 'creation desc')
      loaded.value = true
    } finally {
      loading.value = false
    }
    return coas.value
  }

  return { coas, loading, loaded, fetchAll }
})
