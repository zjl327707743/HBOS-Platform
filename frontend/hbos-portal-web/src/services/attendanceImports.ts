import { iamCommand } from './iamAccess'

export interface ImportSummary {
  import_type?: string; total_rows?: number; matched_rows?: number; success_rows?: number
  created_checkins?: number; created_attendance?: number; existing_attendance?: number
  skipped_duplicates?: number; failed_rows?: number; auto_attendance_used?: boolean
  period_start?: string; period_end?: string; notes?: string
  created?: number; protected?: number; total?: number
}
export interface ImportArtifact {
  event_name: string; expected_inputs: string; log_name?: string
  scope: string; date_from: string; date_to: string; summary: ImportSummary
}
const base='hb_attendance_app.hbos_attendance.portal.imports.'
export const previewScopedImport=(params:Record<string,unknown>)=>iamCommand<ImportArtifact>(base+'preview_import',params)
export const executeScopedImport=(params:Record<string,unknown>)=>iamCommand<ImportArtifact>(base+'execute_import',params)
