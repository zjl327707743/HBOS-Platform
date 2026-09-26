<template>
  <section class="inventory-page draft-page">
    <nav class="draft-crumb" aria-label="面包屑">
      <RouterLink to="/hbos/inventory">仓储库存</RouterLink>
      <span aria-hidden="true">/</span>
      <span>批次</span>
      <span aria-hidden="true">/</span>
      <span>{{ batchName }}</span>
    </nav>

    <div class="draft-head">
      <div v-if="state === 'ready'">
        <h1>批次 {{ batch?.batchId }}</h1>
        <p>
          {{ batch?.itemName || '（主数据无名称）' }}
          · <span class="draft-mono draft-muted">{{ batch?.itemCode }}</span>
        </p>
      </div>
      <div v-else>
        <h1>批次</h1>
        <p>{{ batchName }}</p>
      </div>

      <div v-if="state === 'ready'" class="draft-head-meta">
        <span class="draft-status" :class="releaseTone(batch?.releaseStatus)">
          <component :is="releaseIcon" />
          {{ batch?.releaseStatus || '放行状态未知' }}
        </span>
        <div v-if="batch?.releaseSource" class="draft-release-source">
          放行来源：{{ batch.releaseSource }}
        </div>
      </div>
    </div>

    <div v-if="state === 'loading'" class="inventory-dest glass-surface" aria-busy="true" aria-label="正在加载批次">
      <div class="intake-pane-body">
        <div class="draft-skel draft-skel-line" style="width: 34%"></div>
        <div class="draft-skel draft-skel-row"></div>
        <div class="draft-skel draft-skel-row"></div>
      </div>
    </div>

    <div v-else-if="state === 'missing'" class="inventory-dest glass-surface">
      <div class="intake-pane-body">
        <div class="inventory-state err">
          <StopOutlined class="inventory-state-icon" />
          <h3>找不到这个批次</h3>
          <p>批次号可能不对，或该批次已被删除。批次由入库提交时自动创建，删除它需要 System Manager 权限。</p>
          <div class="inventory-state-actions">
            <a-button type="primary" @click="$router.push('/hbos/inventory')">返回库存概览</a-button>
          </div>
        </div>
      </div>
    </div>

    <template v-else>
      <div class="draft-grid">
        <div class="draft-col">
          <!-- 本页核心产物，放最前 -->
          <div class="inventory-dest glass-surface">
            <div class="intake-pane-head">
              <h2>货位卡 / 待检证</h2>
              <span class="intake-sub">提交入库时自动生成</span>
            </div>
            <div class="intake-pane-body">
              <!-- 有附件 -->
              <div v-if="cardFile" class="draft-attach">
                <div class="draft-attach-ic"><FilePdfOutlined /></div>
                <div class="draft-attach-main">
                  <b>{{ cardFile.fileName }}</b>
                  <p>
                    {{ formatDate(cardFile.createdAt) }}
                    <template v-if="cardFile.size"> · {{ formatSize(cardFile.size) }}</template>
                  </p>
                  <div class="draft-attach-actions">
                    <a-button type="primary" @click="printCard">打印</a-button>
                    <a-button :href="cardFile.url" target="_blank" download>下载</a-button>
                    <a-button :loading="regenerating" @click="confirmRegenerate">
                      <ReloadOutlined /> 重新生成
                    </a-button>
                  </div>
                </div>
              </div>

              <!-- 没有附件：分清「入库单还没提交」与「提交了但没生成出来」 -->
              <div v-else-if="entrySubmitted" class="draft-verdict warn" style="margin: 0">
                <WarningOutlined />
                <div>
                  <b>货位卡 / 待检证尚未生成。</b><br />
                  入库单已经提交了，卡片本该同时生成——多半是生成时出错。
                  生成失败<b>不影响入库本身</b>，账面不受影响。
                  <div class="draft-attach-actions">
                    <a-button type="primary" :loading="regenerating" @click="confirmRegenerate">
                      <ReloadOutlined /> 重新生成
                    </a-button>
                  </div>
                </div>
              </div>

              <div v-else-if="canRegenerate" class="draft-verdict info" style="margin: 0">
                <InfoCircleOutlined />
                <div>
                  这个批次的入库单<b>还没提交</b>，所以货位卡 / 待检证还没有生成。<br />
                  提交后就自动出，不需要在这里手动生成。
                </div>
              </div>

              <div v-else class="draft-verdict info" style="margin: 0">
                <InfoCircleOutlined />
                <div>
                  这个批次没有货位卡 / 待检证。它是<b>外部已有批次</b>或由其他流程建立的，
                  不是本工作台的入库流程生成的——所以没有自动生成卡片。
                </div>
              </div>

              <p v-if="canRegenerate" class="draft-note">
                「重新生成」会替换上一次生成的那份。人工上传到本批次的其他附件不受影响。
              </p>
            </div>
          </div>

          <div class="inventory-dest glass-surface">
            <div class="intake-pane-head"><h2>批次信息</h2></div>
            <div class="intake-pane-body">
              <dl class="draft-kv">
                <div>
                  <dt>物料</dt>
                  <dd>
                    <b>{{ batch?.itemName || '（主数据无名称）' }}</b>
                    <span class="draft-mono draft-muted">{{ batch?.itemCode }}</span>
                  </dd>
                </div>
                <div>
                  <dt>生产日期</dt>
                  <dd :class="{ 'draft-muted': !batch?.manufacturingDate }">
                    <span class="draft-mono">{{ batch?.manufacturingDate || '未填' }}</span>
                  </dd>
                </div>
                <div>
                  <dt>有效期至</dt>
                  <dd :class="{ 'draft-muted': !batch?.expiryDate }">
                    <span class="draft-mono">{{ batch?.expiryDate || '未填' }}</span>
                  </dd>
                </div>
                <div v-for="row in detailRows" :key="row.label">
                  <dt>{{ row.label }}</dt>
                  <dd :class="{ 'draft-muted': !row.value }">{{ row.value || '未填' }}</dd>
                </div>
              </dl>
              <p class="draft-note">
                这几项在提交入库时定下，之后不再改动。要改请找管理员——它们印在已发出的货位卡上。
              </p>
            </div>
          </div>

          <div v-if="batch?.packaging.length" class="inventory-dest glass-surface">
            <div class="intake-pane-head"><h2>包装构成 / 件数</h2></div>
            <div class="intake-pane-body" style="padding: 0">
              <table class="draft-table">
                <thead><tr><th>容器</th><th>单件重量</th><th>件数</th></tr></thead>
                <tbody>
                  <tr v-for="(row, i) in batch?.packaging" :key="i">
                    <td>{{ row.containerType }}</td>
                    <td class="draft-mono">{{ row.unitWeight.toFixed(3) }} kg</td>
                    <td class="draft-mono">{{ row.count }}</td>
                  </tr>
                </tbody>
                <tfoot>
                  <tr><td colspan="2">合计</td><td colspan="2">{{ packagingTotal }}</td></tr>
                </tfoot>
              </table>
            </div>
          </div>

          <div v-if="rawLines.length" class="inventory-dest glass-surface">
            <div class="intake-pane-head">
              <h2>标签原文</h2>
              <span class="intake-sub">照片没法搜，文字可以</span>
            </div>
            <div class="intake-pane-body">
              <div class="intake-rawlines">
                <div v-for="(line, i) in rawLines" :key="i" class="intake-rawline">
                  <span>{{ i + 1 }}</span>
                  <code class="draft-rawcode">{{ line }}</code>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- 右：库存 + 放行 -->
        <div class="draft-col">
          <div class="inventory-dest glass-surface">
            <div class="intake-pane-head"><h2>库存</h2></div>
            <div class="intake-pane-body">
              <div v-if="stockState === 'error'" class="inventory-state err" style="padding: 0">
                <StopOutlined class="inventory-state-icon" />
                <h3>取不到这批判次的库存</h3>
                <p>这次查询失败——<b>不代表这一批没有库存</b>。请重试。</p>
              </div>
              <dl v-else-if="stock.length" class="draft-kv">
                <div v-for="row in stock" :key="row.warehouse">
                  <dt>{{ row.warehouseLabel }}</dt>
                  <dd>
                    <span class="draft-mono">{{ row.qty.toFixed(3) }}</span>
                    <span v-if="row.uom" class="draft-muted"> {{ row.uom }}</span>
                  </dd>
                </div>
              </dl>
              <p v-else class="draft-note" style="margin: 0">
                当前没有库存。批次存在但账面数量为零——可能已全部出库。
              </p>
            </div>
          </div>

          <div class="inventory-dest glass-surface">
            <div class="intake-pane-head">
              <h2>质量放行</h2>
              <span class="intake-sub">LIMS 只读投影</span>
            </div>
            <div class="intake-pane-body">
              <dl class="draft-kv">
                <div>
                  <dt>放行状态</dt>
                  <dd>
                    <span class="draft-status" :class="releaseTone(batch?.releaseStatus)">
                      <component :is="releaseIcon" />
                      {{ batch?.releaseStatus || '未知' }}
                    </span>
                  </dd>
                </div>
                <div>
                  <dt>放行日期</dt>
                  <dd :class="{ 'draft-muted': !batch?.releaseDate }">
                    <span class="draft-mono">{{ batch?.releaseDate || '未填' }}</span>
                  </dd>
                </div>
                <div>
                  <dt>合格证号</dt>
                  <dd :class="{ 'draft-muted': !batch?.certificateNo }">
                    <span class="draft-mono">{{ batch?.certificateNo || '未填' }}</span>
                  </dd>
                </div>
                <div>
                  <dt>LIMS 引用</dt>
                  <dd :class="{ 'draft-muted': !batch?.limsReference }">
                    <span class="draft-mono">{{ batch?.limsReference || '未填' }}</span>
                  </dd>
                </div>
              </dl>
              <div class="draft-verdict info">
                <LockOutlined />
                <div>
                  放行状态由 <b>LIMS</b> 写入，仓库侧只读。出库时系统会校验它——未放行的批次出不去。
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div v-if="cardFile" class="draft-actionbar">
        <span class="draft-actionbar-note">
          打印货位卡贴到货架，打印待检证随实物流转。两者是同一个 PDF。
        </span>
        <a-button type="primary" size="large" @click="printCard">
          <PrinterOutlined /> 打印货位卡 / 待检证
        </a-button>
      </div>
    </template>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import { Modal } from 'ant-design-vue'
import {
  CheckCircleOutlined,
  ClockCircleOutlined,
  FilePdfOutlined,
  InfoCircleOutlined,
  LockOutlined,
  PrinterOutlined,
  ReloadOutlined,
  StopOutlined,
  WarningOutlined,
} from '@ant-design/icons-vue'
import {
  getAttachments,
  getBatch,
  getBatchStock,
  hasSubmittedIntakeEntry,
  regenerateBatchCards,
  releaseTone,
  type BatchDetail,
  type BatchStockRow,
} from '@/services/inventoryDocs'
import { FrappeHttpError } from '@/services/frappeClient'

const route = useRoute()

type ViewState = 'loading' | 'ready' | 'missing'
const state = ref<ViewState>('loading')

const batch = ref<BatchDetail | null>(null)
const stock = ref<BatchStockRow[]>([])
// 'error' 与「空」必须分开：查不到 ≠ 没有
const stockState = ref<'loading' | 'ready' | 'error'>('loading')
const cardFile = ref<{ url: string; fileName: string; createdAt?: string; size?: number } | null>(null)
const regenerating = ref(false)
/** 该批次有没有已提交的拍照识别入库单——决定「卡片为何不在」的文案 */
const entrySubmitted = ref(false)

const batchName = computed(() => String(route.params.batchName || ''))

const detailRows = computed(() => [
  { label: '供货单位', value: batch.value?.supplierName },
  { label: '生产单位', value: batch.value?.manufacturer },
  { label: '原厂批号', value: batch.value?.supplierBatchNo },
  { label: '储存条件', value: batch.value?.storageCondition },
  { label: '生产车间', value: batch.value?.workshop },
  { label: '效期类型', value: batch.value?.shelfLifeType },
])

const rawLines = computed(() =>
  (batch.value?.labelText || '').split('\n').filter((line) => line.trim() !== ''),
)

const packagingTotal = computed(() => {
  const rows = batch.value?.packaging || []
  return rows.map((r) => `${r.count}${r.containerType}`).join('') || '—'
})

/**
 * 能否重新生成：只有本工作台的入库流程建的批次才有意义。
 * 判据用现有的 `hbos_release_status`（该字段由 `setup.py` 创建、带默认值「待检」，
 * 因此**本流程建的批次一定有值**）；外部已有批次通常为空。
 * 拿不准时不显示按钮——比显示一个会报错的按钮好。
 */
const canRegenerate = computed(() => Boolean(batch.value?.releaseStatus))

const releaseIcon = computed(() => {
  const tone = releaseTone(batch.value?.releaseStatus)
  if (tone === 'released') return CheckCircleOutlined
  if (tone === 'blocked') return WarningOutlined
  return ClockCircleOutlined
})

function formatDate(value?: string) {
  return value ? String(value).slice(0, 16) : ''
}

function formatSize(bytes?: number) {
  if (!bytes) return ''
  return bytes >= 1024 * 1024
    ? `${(bytes / 1024 / 1024).toFixed(1)} MB`
    : `${Math.round(bytes / 1024)} KB`
}

function printCard() {
  if (!cardFile.value) return
  // 打印由浏览器负责；多开一个页签让用户自己按 Ctrl/⌘+P——比在 SPA 内嵌 PDF 渲染器稳
  window.open(cardFile.value.url, '_blank', 'noopener')
}

function confirmRegenerate() {
  Modal.confirm({
    title: '重新生成货位卡 / 待检证？',
    content: '将重新生成该批次的「待检证 + 货位卡」并替换上一次生成的那份。人工上传的其他附件不受影响。',
    okText: '重新生成',
    cancelText: '取消',
    onOk: async () => {
      await doRegenerate()
    },
  })
}

async function doRegenerate() {
  if (!batch.value) return
  regenerating.value = true
  try {
    await regenerateBatchCards(batch.value.name)
    await loadAttachments()
    // 生成成功后卡片就位，这张批次必然已有提交过的入库单
    entrySubmitted.value = true
  } catch (error) {
    Modal.error({
      title: '重新生成失败',
      content:
        error instanceof FrappeHttpError
          ? error.message
          : '生成未成功。若反复失败，请联系管理员查看错误日志。',
    })
  } finally {
    regenerating.value = false
  }
}

async function loadAttachments() {
  const files = await getAttachments('Batch', batchName.value)
  cardFile.value = files.find((f) => f.fileName.toLowerCase().endsWith('.pdf')) || null
}

onMounted(async () => {
  try {
    batch.value = await getBatch(batchName.value)
    state.value = 'ready'

    // 库存与附件各自独立取，任一失败不影响其余内容
    const [stockResult, filesResult, entryResult] = await Promise.allSettled([
      getBatchStock(batchName.value),
      getAttachments('Batch', batchName.value),
      hasSubmittedIntakeEntry(batchName.value),
    ])
    if (stockResult.status === 'fulfilled') {
      stock.value = stockResult.value
      stockState.value = 'ready'
    } else {
      // **不把失败当空**：查不到这一批的库存，与「这一批没有库存」是两回事
      stockState.value = 'error'
    }
    if (filesResult.status === 'fulfilled') {
      cardFile.value =
        filesResult.value.find((f) => f.fileName.toLowerCase().endsWith('.pdf')) || null
    }
    if (entryResult.status === 'fulfilled') entrySubmitted.value = entryResult.value
  } catch {
    state.value = 'missing'
  }
})
</script>
