<template>
  <section class="up-page">
    <header class="up-head">
      <div>
        <span class="page-kicker">ATTENDANCE · 数据与导入</span>
        <h1>导入考勤机导出表</h1>
        <p>上传考勤机月度导出表，先识别、再确认导入。识别不会写入任何数据。</p>
      </div>
    </header>

    <!-- 三步流程：选表 → 识别 → 导入。步骤条是信息不是装饰——
         失败时用户需要知道该退回哪一步。 -->
    <div class="up-steps glass-surface">
      <a-steps :current="currentStep" size="small" :items="stepItems" />
    </div>

    <a-alert
      v-if="error"
      type="error"
      show-icon
      :message="error"
      description="若持续失败，请改用侧栏底部的「管理后台」直接导入。"
      class="up-alert"
    />

    <div class="up-grid">
      <section class="up-panel glass-surface">
        <h2>文件与识别</h2>
        <p class="up-hint">只接受考勤机导出的月度汇总表（.xlsx）。</p>

        <a-upload-dragger
          :file-list="fileList"
          :before-upload="onPick"
          :max-count="1"
          accept=".xlsx"
          :disabled="busy"
          @remove="onRemove"
        >
          <p class="ant-upload-drag-icon"><InboxOutlined /></p>
          <p class="ant-upload-text">点击或拖拽 Excel 到此处</p>
          <p class="ant-upload-hint">上传后先点「识别并预览」，确认无误再导入</p>
        </a-upload-dragger>

        <div class="up-actions">
          <a-button
            type="primary"
            :disabled="!fileUrl || busy"
            :loading="previewing"
            @click="doPreview"
          >识别并预览</a-button>
          <a-button
            danger
            :disabled="!preview || busy"
            :loading="importing"
            @click="doImport"
          >确认导入</a-button>
        </div>

        <div v-if="preview" class="up-defs">
          <div class="up-def"><span class="k">批次号</span><span class="v">{{ preview.log_name }}</span></div>
          <div class="up-def"><span class="k">识别类型</span><span class="v">{{ preview.import_type || '—' }}</span></div>
          <div class="up-def"><span class="k">日期范围</span><span class="v">{{ preview.period_start || '—' }} 至 {{ preview.period_end || '—' }}</span></div>
          <div class="up-def"><span class="k">员工行数</span><span class="v">{{ preview.identity_rows ?? 0 }}</span></div>
          <div class="up-def"><span class="k">日期列数</span><span class="v">{{ (preview.mapping_summary?.daily_columns || []).length }}</span></div>
          <div class="up-def"><span class="k">表头行</span><span class="v">{{ preview.mapping_summary?.header_row ?? '—' }}</span></div>
        </div>
      </section>

      <section class="up-panel glass-surface">
        <h2>导入结果</h2>
        <p class="up-hint">确认导入后才会写入打卡流水与考勤结果。</p>

        <div v-if="!result" class="up-empty">完成预览后可确认导入。</div>
        <template v-else>
          <div class="up-defs">
            <div class="up-def"><span class="k">匹配员工数</span><span class="v">{{ result.matched_rows ?? 0 }}</span></div>
            <div class="up-def"><span class="k">成功行数</span><span class="v">{{ result.success_rows ?? 0 }}</span></div>
            <div class="up-def"><span class="k">写入打卡流水</span><span class="v">{{ result.created_checkins ?? 0 }}</span></div>
            <div class="up-def"><span class="k">跳过重复记录</span><span class="v">{{ result.skipped_duplicates ?? 0 }}</span></div>
            <div class="up-def"><span class="k">生成 Attendance</span><span class="v">{{ result.created_attendance ?? 0 }}</span></div>
            <div class="up-def"><span class="k">已存在考勤结果</span><span class="v">{{ result.existing_attendance ?? 0 }}</span></div>
            <div class="up-def"><span class="k">失败记录</span><span class="v">{{ result.failed_rows ?? 0 }}</span></div>
            <div class="up-def"><span class="k">自动考勤</span><span class="v">{{ result.auto_attendance_used ? '已触发' : '未触发' }}</span></div>
          </div>
          <p class="up-note">{{ result.notes }}</p>
          <div class="up-links">
            <a-button size="small" @click="goto('list', 'import-log')">查看考勤导入日志</a-button>
            <a-button size="small" @click="goto('report', 'checkins')">查看打卡流水</a-button>
            <a-button size="small" @click="goto('report', 'results')">查看考勤结果</a-button>
          </div>
        </template>
      </section>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { InboxOutlined } from '@ant-design/icons-vue'
import type { UploadFile } from 'ant-design-vue'
import { callFrappeMethod } from '@/services/frappeClient'
import { uploadToFrappe } from '@/services/frappeUpload'

const router = useRouter()

const IMPORT_LOG_ENDPOINT =
  'hb_attendance_app.hbos_attendance.doctype.hbos_attendance_import_log.hbos_attendance_import_log'

interface PreviewResult {
  log_name: string
  import_type?: string
  period_start?: string
  period_end?: string
  identity_rows?: number
  mapping_summary?: { daily_columns?: unknown[]; header_row?: number }
}

interface ImportResult {
  log_name?: string
  matched_rows?: number
  success_rows?: number
  created_checkins?: number
  skipped_duplicates?: number
  created_attendance?: number
  existing_attendance?: number
  failed_rows?: number
  auto_attendance_used?: boolean
  notes?: string
}

const fileList = ref<UploadFile[]>([])
const fileUrl = ref('')
const busy = ref(false)
const previewing = ref(false)
const importing = ref(false)
const error = ref('')
const preview = ref<PreviewResult | null>(null)
const result = ref<ImportResult | null>(null)

const currentStep = computed(() => {
  if (result.value) return 3
  if (preview.value) return 2
  if (fileUrl.value) return 1
  return 0
})

const stepItems = [
  { title: '选择表格' },
  { title: '识别并预览' },
  { title: '确认导入' },
]

// 交给 a-upload 自己管列表，返回 false 阻止其默认上传（我们手动走 upload_file）
function onPick(file: File) {
  void upload(file)
  return false
}

function onRemove() {
  fileUrl.value = ''
  preview.value = null
  result.value = null
  error.value = ''
  return true
}

async function upload(file: File) {
  if (!file.name.toLowerCase().endsWith('.xlsx')) {
    error.value = '请上传 .xlsx 格式的考勤机月度导出表。'
    return
  }
  busy.value = true
  error.value = ''
  preview.value = null
  result.value = null
  try {
    const uploaded = await uploadToFrappe(file, {
      doctype: 'HBOS Attendance Import Log',
      isPrivate: true,
    })
    fileUrl.value = uploaded.fileUrl
    fileList.value = [{ uid: '-1', name: uploaded.fileName, status: 'done' } as UploadFile]
  } catch (cause) {
    fileUrl.value = ''
    fileList.value = []
    error.value = (cause instanceof Error && cause.message) || '上传失败'
  } finally {
    busy.value = false
  }
}

async function doPreview() {
  if (!fileUrl.value) return
  previewing.value = true
  error.value = ''
  try {
    preview.value = await callFrappeMethod<PreviewResult>(`${IMPORT_LOG_ENDPOINT}.preview_import`, {
      source_file: fileUrl.value,
    })
  } catch (cause) {
    preview.value = null
    error.value = (cause instanceof Error && cause.message) || '识别失败'
  } finally {
    previewing.value = false
  }
}

async function doImport() {
  if (!fileUrl.value) return
  importing.value = true
  error.value = ''
  try {
    result.value = await callFrappeMethod<ImportResult>(`${IMPORT_LOG_ENDPOINT}.run_import`, {
      source_file: fileUrl.value,
      log_name: preview.value?.log_name || '',
      create_missing_employees: 1,
    })
  } catch (cause) {
    result.value = null
    error.value = (cause instanceof Error && cause.message) || '导入失败'
  } finally {
    importing.value = false
  }
}

function goto(kind: 'list' | 'report', slug: string) {
  router.push(`/hbos/attendance/${kind}/${slug}`)
}
</script>

<style scoped>
.up-page { display: grid; gap: 16px; }

.up-head h1 { margin: 6px 0 4px; font-size: 30px; line-height: 38px; }
.up-head p { margin: 0; font-size: 14px; line-height: 22px; color: var(--hbos-text-secondary); }

.up-steps { padding: 14px 20px; border-radius: var(--hbos-radius-card); }
.up-alert { margin: 0; }

.up-grid { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); gap: 16px; }

.up-panel { padding: 20px; border-radius: var(--hbos-radius-card); }
.up-panel h2 { margin: 0 0 4px; font-size: 16px; line-height: 24px; font-weight: 600; }
.up-hint { margin: 0 0 16px; font-size: 12px; line-height: 20px; color: var(--hbos-text-muted); }

.up-actions { display: flex; gap: 10px; margin-top: 16px; }

.up-empty { padding: 28px 0; font-size: 14px; line-height: 22px; color: var(--hbos-text-muted); }

/* 定义列表取代指标卡墙：这些是只读事实，不是 KPI（与报表页同一取舍） */
.up-defs { display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 0 20px; margin-top: 16px; border-top: 1px solid var(--hbos-border-default); }
.up-def { display: flex; flex-direction: column; gap: 2px; padding: 10px 0; border-bottom: 1px solid var(--hbos-border-default); }
.up-def .k { font-size: 12px; line-height: 20px; color: var(--hbos-text-muted); }
.up-def .v { font-size: 14px; line-height: 22px; font-weight: 500; color: var(--hbos-text-primary); word-break: break-word; font-variant-numeric: tabular-nums; }

.up-note { margin: 14px 0 0; font-size: 12px; line-height: 20px; color: var(--hbos-text-secondary); }
.up-links { display: flex; gap: 8px; flex-wrap: wrap; margin-top: 14px; padding-top: 14px; border-top: 1px solid var(--hbos-border-default); }

@media (max-width: 900px) {
  .up-grid { grid-template-columns: 1fr; }
}
</style>
