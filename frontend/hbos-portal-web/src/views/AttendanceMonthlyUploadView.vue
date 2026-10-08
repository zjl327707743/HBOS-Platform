<template>
  <section class="mu-page">
    <header class="mu-head">
      <div>
        <span class="page-kicker">ATTENDANCE · 数据与导入</span>
        <h1>上传月度考勤表</h1>
        <p>考勤机导出的月度汇总 Excel，写入月度暂存；与「导入考勤机导出表」的逐条流水口径不同。</p>
      </div>
    </header>

    <a-alert v-if="error" type="error" show-icon :message="error" class="mu-alert" />

    <div class="mu-grid">
      <section class="mu-panel glass-surface">
        <h2>选择文件</h2>

        <div class="mu-fields">
          <div class="mu-field">
            <label>月份</label>
            <a-select v-model:value="month" :options="monthOptions" style="width: 100%" />
          </div>
          <div class="mu-field">
            <label>年份</label>
            <a-select v-model:value="year" :options="yearOptions" style="width: 100%" />
          </div>
        </div>

        <div class="mu-field">
          <label>Excel 文件</label>
          <a-upload-dragger
            :file-list="fileList"
            :before-upload="onPick"
            :max-count="1"
            accept=".xlsx"
            :disabled="uploading"
            @remove="onRemove"
          >
            <p class="ant-upload-drag-icon"><CloudUploadOutlined /></p>
            <p class="ant-upload-text">点击或拖拽 Excel 到此处</p>
          </a-upload-dragger>
        </div>

        <div class="mu-actions">
          <a-button
            type="primary"
            :disabled="!file || uploading"
            :loading="uploading"
            @click="submit"
          >上传并生成考勤</a-button>
        </div>

        <p class="mu-note">
          逐条打卡流水请用「导入考勤机导出表」；本页写入的是月度暂存，用于后续对账。
        </p>
      </section>

      <section class="mu-panel glass-surface">
        <h2>本次处理结果</h2>

        <div v-if="!result" class="mu-hint">
          上传并解析后，这里显示本次处理的员工数、打卡记录、考勤记录以及迟到与缺勤统计。
        </div>
        <template v-else>
          <div class="mu-defs">
            <div class="mu-def"><span class="k">处理员工数</span><span class="v">{{ result.employees ?? 0 }}</span></div>
            <div class="mu-def"><span class="k">打卡记录</span><span class="v">{{ result.checkins ?? 0 }}</span></div>
            <div class="mu-def"><span class="k">考勤记录</span><span class="v">{{ result.attendance ?? 0 }}</span></div>
            <div class="mu-def"><span class="k">迟到次数</span><span class="v">{{ result.late ?? 0 }}</span></div>
            <div class="mu-def"><span class="k">缺勤天数</span><span class="v">{{ result.absent ?? 0 }}</span></div>
          </div>
          <div class="mu-actions">
            <a-button @click="gotoMonthlyReport">查看月度考勤汇总</a-button>
          </div>
        </template>
      </section>
    </div>
  </section>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { CloudUploadOutlined } from '@ant-design/icons-vue'
import type { UploadFile } from 'ant-design-vue'
import { callFrappeMethod } from '@/services/frappeClient'
import { forgetCsrfToken } from '@/services/frappeUpload'

const router = useRouter()

const ENDPOINT = 'hb_attendance_app.hbos_attendance.page.hbos_monthly_upload.upload.process_excel'

interface UploadResult {
  employees?: number
  checkins?: number
  attendance?: number
  late?: number
  absent?: number
}

const month = ref('7')
const year = ref('2026')
const file = ref<File | null>(null)
const fileList = ref<UploadFile[]>([])
const uploading = ref(false)
const error = ref('')
const result = ref<UploadResult | null>(null)

const monthOptions = Array.from({ length: 12 }, (_, i) => ({
  value: String(i + 1),
  label: `${i + 1}月`,
}))
const yearOptions = ['2025', '2026', '2027'].map((y) => ({ value: y, label: y }))

function onPick(picked: File) {
  if (!picked.name.toLowerCase().endsWith('.xlsx')) {
    error.value = '请上传 .xlsx 格式的月度汇总表。'
    return false
  }
  error.value = ''
  result.value = null
  file.value = picked
  fileList.value = [{ uid: '-1', name: picked.name, status: 'done' } as UploadFile]
  return false // 不交给 a-upload 处理，统一走 submit
}

function onRemove() {
  file.value = null
  fileList.value = []
  result.value = null
  error.value = ''
  return true
}

/**
 * 这个端点接收的是**原始文件字节**（它自己读 multipart 里的 "file"），
 * 不是先 upload_file 拿 file_url——所以这里不能复用 uploadToFrappe，
 * 而是自己带 CSRF token 直接 POST。
 */
async function submit() {
  if (!file.value) return
  uploading.value = true
  error.value = ''
  try {
    const form = new FormData()
    form.append('file', file.value)
    form.append('month', month.value)
    form.append('year', year.value)

    const send = async (token: string) =>
      fetch(`/api/method/${ENDPOINT}`, {
        method: 'POST',
        headers: { 'X-Frappe-CSRF-Token': token, 'X-Requested-With': 'XMLHttpRequest' },
        body: form,
        credentials: 'same-origin',
      })

    // 注意：这条路径**不走** frappeUpload.uploadToFrappe——本端点接收的是原始
    // 文件字节，而那个封装是先 upload_file 拿 file_url。故 token 在这里独立取，
    // forgetCsrfToken() 只是把它的模块级缓存一并作废，避免两处缓存不一致。
    let token = await getToken()
    let response = await send(token)
    if (response.status === 403) {
      forgetCsrfToken()
      token = await getToken()
      response = await send(token)
    }

    const payload = await response.json().catch(() => null)
    if (!response.ok || !payload || payload.exc) {
      throw new Error(plainMessage(payload?._server_messages || payload?.exc || `上传失败（HTTP ${response.status}）`))
    }
    result.value = (payload.message || {}) as UploadResult
  } catch (cause) {
    result.value = null
    error.value = (cause instanceof Error && cause.message) || '上传失败'
  } finally {
    uploading.value = false
  }
}

async function getToken(): Promise<string> {
  return callFrappeMethod<string>('hb_attendance_app.hbos_attendance.file_api.get_csrf_token')
}

/** Frappe 的错误信息是嵌套 JSON 字符串，剥一层再显示。 */
function plainMessage(raw: unknown): string {
  const text = String(raw)
  try {
    const parsed = JSON.parse(text)
    const first = Array.isArray(parsed) ? parsed[0] : parsed
    const inner = typeof first === 'string' ? JSON.parse(first) : first
    return String(inner?.message || inner?.exc || text).replace(/<[^>]+>/g, '').trim()
  } catch {
    return text.replace(/<[^>]+>/g, '').trim().slice(0, 300)
  }
}

function gotoMonthlyReport() {
  router.push('/hbos/attendance/report/monthly')
}
</script>

<style scoped>
.mu-page { display: grid; gap: 16px; }

.mu-head h1 { margin: 6px 0 4px; font-size: 30px; line-height: 38px; }
.mu-head p { margin: 0; font-size: 14px; line-height: 22px; color: var(--hbos-text-secondary); max-width: 70ch; }
.mu-alert { margin: 0; }

.mu-grid { display: grid; grid-template-columns: minmax(0, 420px) minmax(0, 1fr); gap: 16px; align-items: start; }

.mu-panel { padding: 20px; border-radius: var(--hbos-radius-card); }
.mu-panel h2 { margin: 0 0 16px; font-size: 16px; line-height: 24px; font-weight: 600; }

.mu-fields { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 14px; }
.mu-field { display: flex; flex-direction: column; gap: 4px; margin-bottom: 14px; }
.mu-field label { font-size: 12px; line-height: 20px; color: var(--hbos-text-secondary); }

.mu-actions { display: flex; gap: 10px; margin-top: 4px; }

.mu-hint { padding: 24px 0; font-size: 14px; line-height: 22px; color: var(--hbos-text-muted); }

.mu-defs { display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 0 20px; border-top: 1px solid var(--hbos-border-default); }
.mu-def { display: flex; flex-direction: column; gap: 2px; padding: 10px 0; border-bottom: 1px solid var(--hbos-border-default); }
.mu-def .k { font-size: 12px; line-height: 20px; color: var(--hbos-text-muted); }
.mu-def .v { font-size: 30px; line-height: 38px; font-weight: 600; color: var(--hbos-text-primary); font-variant-numeric: tabular-nums; }

.mu-note { margin: 14px 0 0; font-size: 12px; line-height: 20px; color: var(--hbos-text-muted); }

@media (max-width: 900px) { .mu-grid { grid-template-columns: 1fr; } }
</style>
