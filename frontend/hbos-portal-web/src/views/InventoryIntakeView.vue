<template>
  <section class="inventory-page intake-page">
    <div class="inventory-page-head">
      <div>
        <h1>入库拍照识别</h1>
        <p>拍标签 → 识别 → 人工校对 → 生成<strong>草稿</strong>入库单。识别结果不直接入账。</p>
      </div>
    </div>

    <!-- ① ② ③ ④ 是真序列：顺序不能换，跳过会出错，所以编号有意义 -->
    <ol class="intake-steps" aria-label="当前进度">
      <li v-for="s in steps" :key="s.n" :class="s.state">
        <b>{{ s.n }}</b> {{ s.label }}
      </li>
    </ol>

    <div class="intake-work">
      <!-- ============ 左：照片 + 识别（校对时全程要对着照片，故粘住） ============ -->
      <div class="intake-photo-col">
        <div class="inventory-dest glass-surface">
          <div class="intake-pane-head">
            <h2>① 标签照片</h2>
            <span class="intake-sub">原始凭证，随草稿留存</span>
          </div>

          <div class="intake-pane-body">
            <div v-if="!photoUrl" class="intake-drop">
              <p>拍摄或选择产品标签照片。照片仅在内网处理，不出内网。</p>
              <input
                ref="fileInput"
                type="file"
                accept="image/jpeg,image/png,image/webp"
                hidden
                @change="onPickFile"
              />
              <a-button type="primary" :loading="uploading" @click="fileInput?.click()">
                <CameraOutlined /> 选择 / 拍摄照片
              </a-button>
              <p class="intake-hint">支持 JPG / PNG / WebP，单张不超过 5 MB</p>
              <a-alert
                v-if="uploadError"
                type="error"
                show-icon
                class="intake-mt"
                :message="uploadError"
              />
            </div>

            <div v-else>
              <div class="intake-thumb-wrap">
                <img class="intake-thumb" :src="frappeAssetUrl(photoUrl)" alt="标签照片" />
                <button class="intake-zoom" type="button" @click="zoomOpen = true">
                  <ZoomInOutlined /> 放大查看
                </button>
              </div>
              <div class="intake-photo-actions">
                <a-button @click="fileInput?.click()">重新选择照片</a-button>
                <span class="intake-hint">{{ photoName }}</span>
              </div>
              <input
                ref="fileInput"
                type="file"
                accept="image/jpeg,image/png,image/webp"
                hidden
                @change="onPickFile"
              />
            </div>
          </div>
        </div>

        <div class="inventory-dest glass-surface">
          <div class="intake-pane-head"><h2>② 识别</h2></div>
          <div class="intake-pane-body">
            <div v-if="context?.service.available" class="intake-service ok">
              <CheckCircleOutlined />
              <div>
                识别服务已连接
                <div class="intake-backends">
                  <span
                    v-for="(b, key) in context.service.backends"
                    :key="key"
                    class="intake-tag"
                    :class="{ ok: b.available, off: !b.available }"
                  >
                    {{ key }} {{ b.available ? '可用' : '未装依赖' }}
                  </span>
                </div>
              </div>
            </div>
            <div v-else-if="context" class="intake-service warn">
              <StopOutlined />
              <div>
                <b>识别服务当前不可用。</b><br />
                {{ context.service.reason || '未启动或不可达' }}<br />
                你仍可照标签直接填写右侧校对区，正常生成草稿入库单——只是没有自动识别。
              </div>
            </div>

            <label class="intake-field">
              <span class="intake-label">来源类型</span>
              <a-select v-model:value="sourceType" style="width: 100%">
                <a-select-option v-for="s in context?.source_types || []" :key="s" :value="s">
                  {{ s }}
                </a-select-option>
              </a-select>
            </label>

            <a-button
              v-if="context?.service.available"
              type="primary"
              block
              class="intake-mt"
              :disabled="!photoUrl"
              :loading="recognizing"
              @click="runRecognize"
            >
              {{ recognizing ? '识别中…' : '开始识别' }}
            </a-button>

            <a-alert
              v-if="recognizeError"
              type="warning"
              show-icon
              class="intake-mt"
              :message="recognizeError"
            />
          </div>
        </div>
      </div>

      <!-- ============ 右：校对 ============ -->
      <div class="inventory-dest glass-surface">
        <div class="intake-pane-head">
          <h2>③ 人工校对</h2>
          <span class="intake-sub">标签上印的信息全部列在这里</span>
        </div>

        <div class="intake-pane-body">
          <!-- 未上传 / 已上传待识别 -->
          <div v-if="!result && !recognizing" class="inventory-state">
            <CameraOutlined class="inventory-state-icon" />
            <h3>{{ photoUrl ? '照片已就位，等待识别' : '还没有可校对的内容' }}</h3>
            <p v-if="photoUrl">
              点左侧的「开始识别」。识别完成后标签上印的信息会按字段预填到这里——识别读不准的小字留空，由你照标签补。
            </p>
            <p v-else>
              先在左侧选择标签照片，再点「开始识别」。识别结果会预填到这里，没读到的留空由你照标签补。
            </p>
          </div>

          <!-- 识别中：骨架与最终布局同尺寸，不跳变 -->
          <div v-else-if="recognizing" aria-busy="true" aria-label="正在识别">
            <div v-for="n in 6" :key="n" class="intake-skel-row">
              <div class="intake-skel intake-skel-label"></div>
              <div class="intake-skel intake-skel-input"></div>
            </div>
          </div>

          <!-- 已生成草稿 -->
          <div v-else-if="created" class="inventory-state ok">
            <CheckCircleOutlined class="inventory-state-icon" />
            <h3>已生成草稿入库单 {{ created.name }}</h3>
            <p>
              <b>未入账。</b>请打开草稿复核，确认无误后自行提交。
              提交后系统会自动生成货位卡与待检证（一个 PDF），挂在对应批次的附件里。
            </p>
            <p v-if="created.filled.length" class="intake-hint">
              本次补进物料主数据：{{
                created.filled.map((f) => `${f.label} = ${f.value}`).join('、')
              }}
            </p>
            <div class="inventory-state-actions">
              <a-button type="primary" @click="openDraft">打开草稿复核</a-button>
              <a-button @click="openBatch">先看批次</a-button>
              <a-button @click="resetForNext">再收一张</a-button>
            </div>
          </div>

          <!-- 校对内容 -->
          <template v-else>
            <div class="intake-verdict" :class="result?.needs_review ? 'warn' : 'ok'">
              <WarningOutlined v-if="result?.needs_review" />
              <CheckCircleOutlined v-else />
              <span v-if="result?.needs_review">有字段需要核对（橙框）。请确认无误后再生成草稿。</span>
              <span v-else>未发现可疑字段。仍建议对照照片与下方原文逐行确认一次。</span>
            </div>

            <!-- A. 识别到的字段 -->
            <section class="intake-group">
              <div class="intake-group-head">
                <h3>识别到的字段</h3>
                <span class="intake-note">代码是所有印刷信息里最可靠的一项；品名以主数据为准。</span>
              </div>

              <!-- 品名不由本页决定：打印取的是主数据 item_name，故只读展示对照 -->
              <div class="intake-field">
                <span class="intake-label">产品名称（主数据为准，不可在此修改）</span>
                <div class="intake-pair">
                  <span>将打印：<b>{{ fields.product_name || '（主数据无名称）' }}</b></span>
                  <span v-if="productNameDiffers" class="intake-warn-text">
                    AI 读作：<code>{{ rawFields.product_name }}</code> ← 与主数据不符，请核对物料代码
                  </span>
                </div>
              </div>

              <div
                v-for="f in OCR_FIELDS"
                :key="f.key"
                v-show="f.key !== 'product_name'"
                class="intake-field"
                :class="{ needs: hasHint(f.key) }"
              >
                <span class="intake-label">
                  {{ f.label }}
                  <span v-if="confidence[f.key] != null" class="intake-conf">
                    置信度 {{ confidence[f.key] }}
                  </span>
                </span>
                <a-input
                  v-model:value="fields[f.key]"
                  @change="onItemCodeChange(f.key)"
                />
                <div
                  v-if="rawFields[f.key] != null && rawFields[f.key] !== fields[f.key]"
                  class="intake-raw-read"
                >
                  AI 原读作：<code>{{ rawFields[f.key] }}</code>
                </div>
                <ul v-if="hasHint(f.key)" class="intake-hints">
                  <li v-for="(h, i) in hints[f.key]" :key="i">{{ h }}</li>
                </ul>
              </div>

              <div v-if="itemHint" class="intake-hint intake-mt" v-html="itemHint"></div>
            </section>

            <!-- B. 物料级（须人工填） -->
            <section class="intake-group">
              <div class="intake-group-head">
                <h3>物料级补充</h3>
                <span class="intake-must">须人工填写</span>
                <span class="intake-note">
                  标签上是小字，识别读不准，须照标签人工填写。填了会写回物料主数据，该物料以后每批都带上；主数据已有值的会锁住，不会被覆盖。
                </span>
              </div>
              <div v-for="item in MASTER_FIELDS" :key="item.key" class="intake-field">
                <span class="intake-label">
                  {{ item.label }}
                  <span
                    v-if="masterState[item.key]"
                    class="intake-master-state"
                    :class="masterState[item.key]?.has ? 'has' : 'empty'"
                  >
                    {{ masterState[item.key]?.has ? '主数据已有' : '须人工填' }}
                  </span>
                </span>
                <a-select
                  v-if="item.options"
                  v-model:value="extra[item.key]"
                  style="width: 100%"
                  :disabled="Boolean(masterState[item.key]?.has)"
                >
                  <a-select-option value="">（未设置）</a-select-option>
                  <a-select-option v-for="o in item.options" :key="o" :value="o">{{ o }}</a-select-option>
                </a-select>
                <a-input
                  v-else
                  v-model:value="extra[item.key]"
                  :placeholder="item.placeholder"
                  :disabled="Boolean(masterState[item.key]?.has)"
                />
              </div>
            </section>

            <!-- C. 本批信息（须人工填） -->
            <section class="intake-group">
              <div class="intake-group-head">
                <h3>本批信息</h3>
                <span class="intake-must">须人工填写</span>
                <span class="intake-note">
                  不在识别字段里，须照标签人工填写。逐批不同，写在对应批次上；主要是外购料的待检证要用。
                </span>
              </div>
              <div v-for="item in BATCH_FIELDS" :key="item.key" class="intake-field">
                <span class="intake-label">{{ item.label }}</span>
                <a-input v-model:value="extra[item.key]" :placeholder="item.placeholder" />
              </div>
            </section>

            <!-- D. 包装构成 -->
            <section class="intake-group">
              <div class="intake-group-head">
                <h3>包装构成 / 件数</h3>
                <span class="intake-note">照标签逐条填「容器类型 + 单件重量 + 件数」，件数自动汇总，便于与标签核对。</span>
              </div>
              <div v-for="(row, i) in packagingRows" :key="i" class="intake-pkg-row">
                <a-select v-model:value="row.container_type" placeholder="容器">
                  <a-select-option v-for="t in CONTAINER_TYPES" :key="t" :value="t">{{ t }}</a-select-option>
                </a-select>
                <a-input-number v-model:value="row.unit_weight" :min="0" :step="0.001" placeholder="单件重量 kg" style="width: 100%" />
                <a-input-number v-model:value="row.count" :min="0" :step="1" placeholder="件数" style="width: 100%" />
                <a-button type="text" danger aria-label="删除本行" @click="packagingRows.splice(i, 1)">
                  <CloseOutlined />
                </a-button>
              </div>
              <a-button size="small" class="intake-mt" @click="addPackagingRow">
                <PlusOutlined /> 添加一行
              </a-button>
              <div v-if="packagingSummary" class="intake-pkg-sum">合计 {{ packagingSummary }}</div>
            </section>

            <!-- E. 标签原文逐行（可改：改了会生效才配做成输入框） -->
            <section class="intake-group">
              <div class="intake-group-head">
                <h3>标签原文逐行</h3>
                <span class="intake-note">
                  对着照片逐行核，读错的字直接改。这些行不打印，但会存进批次便于日后检索——照片没法搜，文字可以。
                </span>
              </div>
              <div v-if="rawLines.length" class="intake-rawlines">
                <div v-for="(line, i) in rawLines" :key="i" class="intake-rawline">
                  <span>{{ i + 1 }}</span>
                  <input v-model="rawLines[i]" />
                </div>
              </div>
              <p v-else class="intake-hint">
                本次识别没有返回原文（后端可能未提供）。「须人工填写」那几项照照片直接填即可。
              </p>
              <a-button v-if="rawLines.length" size="small" class="intake-mt" @click="restoreRawLines">
                <UndoOutlined /> 恢复识别原文
              </a-button>
            </section>

            <!--
              ④ 生成草稿 —— 2026-09-28 从**视口底部 sticky 的一条**改到校对区里。

              改的直接原因是 Owner 反馈：这两个字段钉在屏幕最下沿，「太靠下了，
              不容易被看到」，而它们是必填、每次都要填。放回文档流后在校对区末尾，
              顺着读下来就到。

              另一个疑点（**未验证**）：sticky 条距视口底只有 ~60px，装不下两百多
              像素的下拉面板；Owner 还报过「下拉框跑到上边、脱离选择框」。本机量不到
              真实弹层坐标（Browser 面板视口高度为 0），无法证实也无法排除。
              详见 global.css 里 `.intake-final` 的注释。
            -->
            <section class="intake-group intake-final">
              <div class="intake-group-head">
                <h3>④ 生成草稿</h3>
                <span class="intake-note">
                  填了货位与数量才能生成。生成的是<b>草稿</b>，不直接入账。
                </span>
              </div>
              <div class="intake-final-fields">
                <label class="intake-field">
                  <span class="intake-label">货位 <em>*</em></span>
                  <a-select
                    v-model:value="warehouse"
                    show-search
                    :filter-option="filterWarehouse"
                    placeholder="请选择货位"
                    style="width: 100%"
                  >
                    <a-select-option
                      v-for="w in context?.warehouses || []"
                      :key="w.value"
                      :value="w.value"
                    >
                      {{ w.label }}{{ w.parent ? `（${w.parent.split(' - ')[0]}）` : '' }}
                    </a-select-option>
                  </a-select>
                </label>
                <label class="intake-field">
                  <span class="intake-label">数量（kg）</span>
                  <a-input-number
                    v-model:value="qty"
                    :min="0"
                    :step="0.001"
                    placeholder="0.000"
                    style="width: 100%"
                  />
                </label>
              </div>
              <a-alert
                v-if="createError"
                type="error"
                show-icon
                class="intake-mt"
                :message="createError"
              />
              <a-button
                type="primary"
                size="large"
                class="intake-mt"
                :loading="creating"
                :disabled="!warehouse || !qty"
                @click="createDraft"
              >
                {{ creating ? '生成中…' : '生成草稿（不直接入账）' }}
              </a-button>
            </section>
          </template>
        </div>
      </div>
    </div>

    <!-- 放大查看：小字标签必须读得清，所以放大是功能而非装饰 -->
    <a-modal :open="zoomOpen" :footer="null" width="90vw" @cancel="zoomOpen = false">
      <img v-if="photoUrl" :src="frappeAssetUrl(photoUrl)" alt="标签照片放大" style="width: 100%" />
    </a-modal>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import {
  CameraOutlined,
  CheckCircleOutlined,
  CloseOutlined,
  PlusOutlined,
  StopOutlined,
  UndoOutlined,
  WarningOutlined,
  ZoomInOutlined,
} from '@ant-design/icons-vue'
import {
  createIntakeDraft,
  getIntakeContext,
  lookupItemMaster,
  recognizeLabel,
  uploadLabelPhoto,
  type CreatedDraft,
  type IntakeContext,
  type ItemMasterGaps,
  type PackagingRow,
  type RecognizeResult,
} from '@/services/intake'
import { FrappeHttpError, frappeAssetUrl } from '@/services/frappeClient'

const router = useRouter()

// --- 状态 ---
const context = ref<IntakeContext | null>(null)
const photoUrl = ref('')
const photoDocName = ref('')
const photoName = ref('')
const fileInput = ref<HTMLInputElement | null>(null)
const uploading = ref(false)
const uploadError = ref('')

const result = ref<RecognizeResult | null>(null)
const recognizing = ref(false)
const recognizeError = ref('')
const sourceType = ref('自产')

const fields = ref<Record<string, string>>({})
const rawFields = ref<Record<string, string | null>>({})
const hints = ref<Record<string, string[]>>({})
const confidence = ref<Record<string, number>>({})
const rawLines = ref<string[]>([])
const rawTextBaseline = ref('')

const extra = ref<Record<string, string>>({})
const masterState = ref<Record<string, { has: boolean } | null>>({})
const itemHint = ref('')

export interface DraftPackagingRow {
  container_type: string
  unit_weight: number | null
  count: number | null
}

const packagingRows = ref<DraftPackagingRow[]>([])

function addPackagingRow() {
  packagingRows.value.push({ container_type: '', unit_weight: null, count: null })
}

const warehouse = ref<string | undefined>(undefined)
const qty = ref<number | null>(null)
const creating = ref(false)
const createError = ref('')
const created = ref<CreatedDraft | null>(null)
const zoomOpen = ref(false)

// --- 静态字段表（与后端 FIELD_LABELS / api 参数一一对应） ---
const OCR_FIELDS = [
  { key: 'product_name', label: '产品名称' },
  { key: 'item_code', label: '物料代码' },
  { key: 'batch_no', label: '批号' },
  { key: 'manufacturing_date', label: '生产日期' },
  { key: 'expiry_date', label: '有效期至' },
]

const MASTER_FIELDS = [
  { key: 'storage_condition', label: '储存条件', placeholder: '如：储存温度不超过30℃' },
  { key: 'workshop', label: '生产车间', placeholder: '如：六车间B线' },
  { key: 'shelf_life_type', label: '效期类型', placeholder: '', options: ['复检期', '有效期'] },
]

/** 界面 key → 物料主数据字段名。与后端 api.ITEM_GAP_FIELDS 白名单一致。 */
const MASTER_FIELD_MAP: Record<string, keyof ItemMasterGaps> = {
  storage_condition: 'hbos_storage_condition',
  workshop: 'hbos_workshop',
  shelf_life_type: 'hbos_shelf_life_type',
}

const BATCH_FIELDS = [
  { key: 'supplier_name', label: '供货单位', placeholder: '照标签填写' },
  { key: 'manufacturer', label: '生产单位', placeholder: '照标签填写' },
  { key: 'supplier_batch_no', label: '原厂批号', placeholder: '外购标签上的原厂批号' },
]

const CONTAINER_TYPES = ['件', '听', '瓶', '桶', '袋', '箱']

// --- 派生 ---
const stepIndex = computed(() => {
  if (created.value) return 4
  if (result.value) return 3
  if (photoUrl.value) return 2
  return 1
})

const steps = computed(() =>
  [
    { n: '①', label: '标签照片' },
    { n: '②', label: '识别' },
    { n: '③', label: '人工校对' },
    { n: '④', label: '生成草稿' },
  ].map((s, i) => ({
    ...s,
    state: i + 1 < stepIndex.value ? 'done' : i + 1 === stepIndex.value ? 'current' : '',
  })),
)

const productNameDiffers = computed(() => {
  const ai = rawFields.value.product_name
  const shown = fields.value.product_name
  return Boolean(ai) && String(ai) !== String(shown)
})

const packagingSummary = computed(() => {
  const totals: Record<string, number> = {}
  const order: string[] = []
  for (const row of packagingRows.value) {
    const key = row.container_type || ''
    if (!key) continue
    if (!(key in totals)) {
      totals[key] = 0
      order.push(key)
    }
    totals[key] = (totals[key] ?? 0) + Number(row.count || 0)
  }
  const text = order.map((k) => `${totals[k]}${k}`).join('')
  return text
})

function hasHint(key: string) {
  return Boolean(hints.value[key]?.length)
}

function filterWarehouse(input: string, option: { children?: string }) {
  return String(option.children || '').toLowerCase().includes(input.toLowerCase())
}

// --- 生命周期 ---
onMounted(async () => {
  try {
    context.value = await getIntakeContext()
  } catch {
    context.value = null
  }
})

// --- ① 选照片 ---
async function onPickFile(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return

  uploadError.value = ''
  uploading.value = true
  try {
    const uploaded = await uploadLabelPhoto(file)
    photoUrl.value = uploaded.file_url
    photoDocName.value = uploaded.name
    photoName.value = `${file.name} · ${(file.size / 1024 / 1024).toFixed(1)} MB`
    // 换照片 = 换一张标签，上一张的识别结果与手工补录都不能留
    resetRecognitionState()
  } catch (error) {
    uploadError.value =
      error instanceof FrappeHttpError ? error.message : '照片上传失败，请重试。'
  } finally {
    uploading.value = false
    input.value = ''
  }
}

function resetRecognitionState() {
  result.value = null
  fields.value = {}
  rawFields.value = {}
  hints.value = {}
  confidence.value = {}
  rawLines.value = []
  rawTextBaseline.value = ''
  extra.value = {}
  masterState.value = {}
  itemHint.value = ''
  packagingRows.value = []
  createError.value = ''
  created.value = null
  recognizeError.value = ''
}

// --- ② 识别 ---
async function runRecognize() {
  if (!photoUrl.value) return
  recognizing.value = true
  recognizeError.value = ''
  const samePhoto = rawTextBaseline.value !== '' && rawLines.value.length > 0
  const preservedLines = samePhoto ? [...rawLines.value] : []
  const preservedExtra = { ...extra.value }
  const preservedPkg: DraftPackagingRow[] = [...packagingRows.value]

  try {
    const data = await recognizeLabel(photoUrl.value, sourceType.value)
    result.value = data
    fields.value = Object.fromEntries(
      Object.entries(data.fields || {}).map(([k, v]) => [k, v == null ? '' : String(v)]),
    )
    rawFields.value = data.raw_fields || {}
    hints.value = data.hints || {}
    confidence.value = data.confidence || {}

    // 同一张照片重识别时保留操作员已改过的行——OCR 对同一张图的结果是确定的，
    // 拿回原值只会把改动冲掉。（换照片时 resetRecognitionState 已清空基线）
    const freshText = String(data.raw_text || '')
    if (!samePhoto) {
      rawLines.value = freshText.split('\n')
    } else {
      rawLines.value = preservedLines
    }
    rawTextBaseline.value = freshText

    // 手工补录的值也接住
    extra.value = preservedExtra
    packagingRows.value = preservedPkg

    await refreshItemMaster(fields.value.item_code || '')
  } catch (error) {
    // 服务端的中文提示已在 FrappeHttpError 里取出；不把 traceback 带进界面
    recognizeError.value =
      error instanceof FrappeHttpError
        ? `识别未完成：${error.message}`
        : '识别未完成。可重试，或改用人工录入。'
  } finally {
    recognizing.value = false
  }
}

function restoreRawLines() {
  rawLines.value = rawTextBaseline.value.split('\n')
}

// --- ③ 物料主数据回显（防抖 + 丢弃迟到响应） ---
//
// 两个坑：① 必须绑在 item_code 变化上（操作员改正代码后要跟着换物料）；
// ② 连着改几次代码会发出多个请求，先发的可能后到，会把上一个物料的值标在当前物料头上。
let lookupTimer: ReturnType<typeof setTimeout> | null = null
let lookupSeq = 0

function onItemCodeChange(key: string) {
  if (key !== 'item_code') return
  if (lookupTimer) clearTimeout(lookupTimer)
  lookupTimer = setTimeout(() => void refreshItemMaster(fields.value.item_code || ''), 350)
}

async function refreshItemMaster(code: string) {
  const trimmed = (code || '').trim()
  const seq = ++lookupSeq

  if (!trimmed) {
    masterState.value = {}
    itemHint.value = '先识别出物料代码，这里会自动带出主数据里已有的值。'
    return
  }

  const master = await lookupItemMaster(trimmed)
  // 迟到的响应：期间代码又变了，丢弃
  if (seq !== lookupSeq) return

  if (!master) {
    masterState.value = {}
    itemHint.value = '<b>该物料尚未建档</b>，无法带出主数据；请先建档再入库。'
    return
  }

  const next: Record<string, { has: boolean } | null> = {}
  let emptyCount = 0
  for (const item of MASTER_FIELDS) {
    // 界面 key → 物料主数据字段名（与后端 api.ITEM_GAP_FIELDS 白名单一一对应）
    const masterField = MASTER_FIELD_MAP[item.key]
    const value = masterField ? String(master[masterField] || '').trim() : ''
    if (value) {
      // 主数据已有：填进去并锁住，让操作员知道这项不用管
      next[item.key] = { has: true }
      extra.value[item.key] = value
    } else {
      next[item.key] = { has: false }
      if (masterState.value[item.key]?.has) extra.value[item.key] = ''
      emptyCount += 1
    }
  }
  masterState.value = next
  itemHint.value = emptyCount
    ? `主数据里有 <b>${emptyCount}</b> 项为空，<b>请照标签填</b>（OCR 读不准这几项小字）。填了会写回主数据，该物料以后每批自动带上；已有值不会被覆盖。`
    : '该物料这三项主数据都已有值，无需重复填写。'
}

// --- ④ 生成草稿 ---
async function createDraft() {
  if (!result.value || !warehouse.value || !qty.value) return
  creating.value = true
  createError.value = ''

  try {
    // 物料级：主数据已有值的（输入框被禁用、值已回填）不重复提交，只提交补空的
    const ext: Record<string, string | null> = {}
    const payload: Record<string, string | null> = {}
    for (const item of MASTER_FIELDS) {
      const locked = Boolean(masterState.value[item.key]?.has)
      ext[item.key] = locked ? null : (extra.value[item.key] || '') || null
    }
    for (const item of BATCH_FIELDS) {
      payload[item.key] = (extra.value[item.key] || '') || null
    }

    created.value = await createIntakeDraft({
      item_code: fields.value.item_code || '',
      batch_no: fields.value.batch_no || '',
      qty: qty.value,
      warehouse: warehouse.value,
      file_url: photoUrl.value,
      file_name: photoDocName.value,
      source_type: sourceType.value,
      manufacturing_date: fields.value.manufacturing_date || null,
      expiry_date: fields.value.expiry_date || null,
      storage_condition: ext.storage_condition,
      workshop: ext.workshop,
      shelf_life_type: ext.shelf_life_type,
      supplier_name: payload.supplier_name,
      manufacturer: payload.manufacturer,
      supplier_batch_no: payload.supplier_batch_no,
      packaging: packagingRows.value
        .filter((r) => r.container_type)
        .map((r) => ({
          container_type: r.container_type,
          unit_weight: r.unit_weight ?? 0,
          count: r.count ?? 0,
        })),
      label_text: rawLines.value.join('\n'),
    })
  } catch (error) {
    createError.value =
      error instanceof FrappeHttpError ? error.message : '生成失败，请重试。'
  } finally {
    creating.value = false
  }
}

function openDraft() {
  if (!created.value) return
  // 草稿复核已前端化 —— 留在 Portal 内，不再跳 ERPNext 原生表单
  void router.push(`/hbos/inventory/draft/${encodeURIComponent(created.value.name)}`)
}

function openBatch() {
  if (!created.value) return
  void router.push(`/hbos/inventory/batch/${encodeURIComponent(created.value.batch)}`)
}

function resetForNext() {
  photoUrl.value = ''
  photoDocName.value = ''
  photoName.value = ''
  warehouse.value = undefined
  qty.value = null
  resetRecognitionState()
}

void router
</script>
