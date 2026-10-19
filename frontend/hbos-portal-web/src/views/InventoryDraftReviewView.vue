<template>
  <section class="inventory-page draft-page">
    <nav class="draft-crumb" aria-label="面包屑">
      <RouterLink to="/hbos/inventory">仓储库存</RouterLink>
      <span aria-hidden="true">/</span>
      <RouterLink to="/hbos/inventory/intake">入库拍照识别</RouterLink>
      <span aria-hidden="true">/</span>
      <span>草稿复核</span>
    </nav>

    <div class="draft-head">
      <div>
        <h1>草稿复核</h1>
        <p>这是识别建出的<b>草稿</b>，还没入账。确认无误后提交，系统随即生成货位卡与待检证。</p>
      </div>
      <div v-if="state === 'ready'" class="draft-head-meta">
        <div class="draft-docno">{{ draft?.name }}</div>
        <span class="draft-status draft"><InfoCircleOutlined /> 草稿 · 未入账</span>
      </div>
    </div>

    <!-- 加载中：骨架与最终布局同尺寸，不跳变 -->
    <div v-if="state === 'loading'" class="inventory-dest glass-surface" aria-busy="true" aria-label="正在加载草稿">
      <div class="intake-pane-body">
        <div class="draft-skel draft-skel-line" style="width: 38%"></div>
        <div class="draft-skel draft-skel-row"></div>
        <div class="draft-skel draft-skel-row"></div>
        <div class="draft-skel draft-skel-row"></div>
      </div>
    </div>

    <!-- 找不到 -->
    <div v-else-if="state === 'missing'" class="inventory-dest glass-surface">
      <div class="intake-pane-body">
        <div class="inventory-state err">
          <StopOutlined class="inventory-state-icon" />
          <h3>找不到这张草稿</h3>
          <p>单号可能已被删除，或链接不对。<b>草稿还没入账</b>——如果它曾经存在，账面不会有任何记录。</p>
          <div class="inventory-state-actions">
            <a-button type="primary" @click="$router.push('/hbos/inventory/intake')">回到入库拍照识别</a-button>
            <a-button @click="$router.push('/hbos/inventory')">查看库存概览</a-button>
          </div>
        </div>
      </div>
    </div>

    <!-- 不是拍照识别建的草稿 -->
    <div v-else-if="state === 'notIntake'" class="inventory-dest glass-surface">
      <div class="intake-pane-body">
        <div class="inventory-state err">
          <StopOutlined class="inventory-state-icon" />
          <h3>这张单不是拍照识别建的</h3>
          <p>
            本页只复核「入库拍照识别」生成的那类草稿（单上记着批次来源）。
            这张单没有该标记，请到仓库工作台的库存单据里处理。
          </p>
          <div class="inventory-state-actions">
            <a-button type="primary" @click="$router.push('/hbos/inventory')">返回库存概览</a-button>
          </div>
        </div>
      </div>
    </div>

    <!-- 已提交 -->
    <div v-else-if="state === 'submitted'" class="inventory-dest glass-surface">
      <div class="intake-pane-body">
        <div class="inventory-state ok">
          <CheckCircleOutlined class="inventory-state-icon" />
          <h3>已提交入库</h3>
          <p>
            账面已入账，货位卡与待检证已生成，挂在批次 <b>{{ draft?.batch }}</b> 的附件里。
          </p>
          <div class="inventory-state-actions">
            <a-button type="primary" @click="goBatch">去批次打印货位卡 / 待检证</a-button>
            <a-button @click="$router.push('/hbos/inventory/intake')">再收一张</a-button>
            <a-button danger :loading="cancelling" @click="confirmCancel">
              <RollbackOutlined /> 取消这张入库单
            </a-button>
          </div>
        </div>
      </div>
    </div>

    <!-- 已取消 -->
    <div v-else-if="state === 'cancelled'" class="inventory-dest glass-surface">
      <div class="intake-pane-body">
        <div class="inventory-state">
          <StopOutlined class="inventory-state-icon" />
          <h3>这张入库单已取消</h3>
          <p>
            货已从目标货位扣回，账面等于没入过。已取消的单据改不了，需要重做请重新收一张。
            <template v-if="draft?.batch">
              <br /><b>批次上的货位卡 / 待检证不会自动删除</b>——去批次页重新生成即可覆盖。
            </template>
          </p>
          <div class="inventory-state-actions">
            <a-button v-if="draft?.batch" type="primary" @click="goBatch">
              去批次页重新生成卡片
            </a-button>
            <a-button @click="$router.push('/hbos/inventory/intake')">重新收一张</a-button>
          </div>
        </div>
      </div>
    </div>

    <template v-else>
      <div class="draft-grid">
        <div class="draft-col">
          <!-- 单据内容 -->
          <div class="inventory-dest glass-surface">
            <div class="intake-pane-head">
              <h2>单据内容</h2>
              <span class="intake-sub">复核用，读起来像单据</span>
            </div>
            <div class="intake-pane-body">
              <dl class="draft-kv">
                <div>
                  <dt>物料</dt>
                  <dd>
                    <b>{{ draft?.item.itemName || '（主数据无名称）' }}</b>
                    <span class="draft-mono draft-muted">{{ draft?.item.itemCode }}</span>
                  </dd>
                </div>
                <div>
                  <dt>入库货位</dt>
                  <dd>{{ warehouseShortLabel(draft?.item.warehouse) }}</dd>
                </div>
                <div>
                  <dt>数量</dt>
                  <dd><span class="draft-mono">{{ qtyText }}</span> {{ draft?.item.uom }}</dd>
                </div>
                <div>
                  <dt>批次</dt>
                  <dd>
                    <button type="button" class="draft-link" @click="goBatch">{{ draft?.item.batchNo }}</button>
                  </dd>
                </div>
                <div>
                  <dt>来源类型</dt>
                  <dd :class="{ 'draft-muted': !batch?.sourceType }">{{ batch?.sourceType || '未设置' }}</dd>
                </div>
              </dl>
              <p class="draft-note">
                单据类型固定为「物料入库」。数量可在下方动作条修改，改完提交即生效。
              </p>
            </div>
          </div>

          <!-- 批次信息 -->
          <div class="inventory-dest glass-surface">
            <div class="intake-pane-head">
              <h2>批次信息</h2>
              <span class="intake-sub">识别读不到、由操作员照标签补的</span>
            </div>
            <div class="intake-pane-body">
              <dl class="draft-kv">
                <div v-for="row in batchRows" :key="row.label">
                  <dt>{{ row.label }}</dt>
                  <dd :class="{ 'draft-muted': !row.value }">{{ row.value || '未填' }}</dd>
                </div>
              </dl>
              <div v-if="missingBatchFields.length" class="draft-verdict" :class="isOutsourced ? 'warn' : 'info'">
                <WarningOutlined v-if="isOutsourced" />
                <InfoCircleOutlined v-else />
                <div v-if="isOutsourced">
                  <b>本批来源是外购，这三项没填（{{ missingBatchFields.join(' / ') }}）。</b><br />
                  外购料的<b>待检证</b>要印这三项。请回上一步补填后再生成草稿——现在提交，
                  待检证上会缺这几栏，收货方可能不认。
                </div>
                <div v-else>
                  有 {{ missingBatchFields.length }} 项没填（{{ missingBatchFields.join(' / ') }}）。
                  这几项主要是<b>外购料的待检证</b>要用——本批来源是<b>自产</b>，可以不填。
                  若这张标签其实是外购的，请回上一步改来源并补填。
                </div>
              </div>

              <!-- 来源类型未知时不下结论：不替他判断「能不能不填」 -->
              <div v-if="!batch?.sourceType" class="draft-verdict warn">
                <WarningOutlined />
                <div>
                  这一批的<b>来源类型</b>没有记录，平台无法判断上面缺的几项能不能不填。
                  提交前请自行确认——若为外购，待检证需要这几栏。
                </div>
              </div>
            </div>
          </div>

          <!-- 包装构成 -->
          <div v-if="batch?.packaging.length" class="inventory-dest glass-surface">
            <div class="intake-pane-head"><h2>包装构成 / 件数</h2></div>
            <div class="intake-pane-body" style="padding: 0">
              <table class="draft-table">
                <thead>
                  <tr><th>容器</th><th>单件重量</th><th>件数</th></tr>
                </thead>
                <tbody>
                  <tr v-for="(row, i) in batch?.packaging" :key="i">
                    <td>{{ row.containerType }}</td>
                    <td class="draft-mono">{{ row.unitWeight.toFixed(3) }} kg</td>
                    <td class="draft-mono">{{ row.count }}</td>
                  </tr>
                </tbody>
                <tfoot>
                  <tr>
                    <td colspan="2">合计</td>
                    <td colspan="2">{{ packagingTotal }}</td>
                  </tr>
                </tfoot>
              </table>
            </div>
          </div>

          <!-- 标签原文 -->
          <div v-if="rawLines.length" class="inventory-dest glass-surface">
            <div class="intake-pane-head">
              <h2>标签原文</h2>
              <span class="intake-sub">人工校对后留存，可检索</span>
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

        <!-- 右：原始凭证 -->
        <div class="draft-col">
          <div class="inventory-dest glass-surface">
            <div class="intake-pane-head">
              <h2>原始凭证</h2>
              <span class="intake-sub">照片随单据留存</span>
            </div>
            <div class="intake-pane-body">
              <div v-if="photo" class="draft-photo-wrap">
                <img class="draft-photo" :src="photo.url" alt="标签照片" />
                <button class="intake-zoom" type="button" @click="zoomOpen = true">
                  <ZoomInOutlined /> 放大查看
                </button>
              </div>
              <p v-else class="draft-note" style="margin: 0">
                这张草稿上没有照片。识别时未上传，或照片已被移除——不影响入库，但就没有原始凭证可对了。
              </p>
            </div>
          </div>

          <div class="inventory-dest glass-surface">
            <div class="intake-pane-head"><h2>货位卡 / 待检证</h2></div>
            <div class="intake-pane-body">
              <div class="draft-verdict info" style="margin: 0">
                <InfoCircleOutlined />
                <div>
                  提交后才生成。系统会在提交的同一刻把「待检证 + 货位卡」做成一个 PDF，
                  挂到批次 <b>{{ draft?.batch }}</b> 上——提交完直接带你去取。
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 动作条：提交是唯一 Primary -->
      <div class="draft-actionbar">
        <span class="draft-actionbar-note">
          提交后会立刻入账，并生成货位卡与待检证。<b>提交前请对着照片核对数量与货位。</b>
        </span>
        <a-button :loading="discarding" @click="confirmDiscard">
          <DeleteOutlined /> 放弃这张草稿
        </a-button>
        <a-button type="primary" size="large" :loading="submitting" @click="confirmSubmit">
          <SendOutlined /> {{ submitting ? '提交中…' : '提交入库' }}
        </a-button>
      </div>
    </template>

    <a-modal :open="zoomOpen" :footer="null" width="90vw" @cancel="zoomOpen = false">
      <img v-if="photo" :src="photo.url" alt="标签照片放大" style="width: 100%" />
    </a-modal>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { Modal } from 'ant-design-vue'
import {
  CheckCircleOutlined,
  DeleteOutlined,
  InfoCircleOutlined,
  RollbackOutlined,
  SendOutlined,
  StopOutlined,
  WarningOutlined,
  ZoomInOutlined,
} from '@ant-design/icons-vue'
import {
  cancelIntakeDraft,
  discardIntakeDraft,
  getAttachments,
  getBatch,
  getIntakeDraft,
  submitIntakeDraft,
  warehouseShortLabel,
  type BatchDetail,
  type IntakeDraft,
} from '@/services/inventoryDocs'
import { FrappeHttpError } from '@/services/frappeClient'

const route = useRoute()
const router = useRouter()

type ViewState = 'loading' | 'ready' | 'missing' | 'notIntake' | 'submitted' | 'cancelled'

const state = ref<ViewState>('loading')
const draft = ref<IntakeDraft | null>(null)
const batch = ref<BatchDetail | null>(null)
const photo = ref<{ url: string; fileName: string } | null>(null)

const submitting = ref(false)
const discarding = ref(false)
const cancelling = ref(false)
const zoomOpen = ref(false)

const draftName = computed(() => String(route.params.draftName || ''))

const qtyText = computed(() => {
  const value = draft.value?.item.qty ?? 0
  return Number.isInteger(value) ? String(value) : value.toFixed(3)
})

const rawLines = computed(() =>
  (batch.value?.labelText || '').split('\n').filter((line) => line.trim() !== ''),
)

const batchRows = computed(() => [
  { label: '供货单位', value: batch.value?.supplierName },
  { label: '生产单位', value: batch.value?.manufacturer },
  { label: '原厂批号', value: batch.value?.supplierBatchNo },
  { label: '储存条件', value: batch.value?.storageCondition },
  { label: '生产车间', value: batch.value?.workshop },
  { label: '效期类型', value: batch.value?.shelfLifeType },
])

/** 只有「外购料待检证要用」的那三项值得提醒；储存/车间/效期是物料级，缺了也不阻塞 */
const BATCH_CRITICAL = new Set(['供货单位', '生产单位', '原厂批号'])

const isOutsourced = computed(() => batch.value?.sourceType === '外购')

const missingBatchFields = computed(() =>
  batchRows.value.filter((row) => BATCH_CRITICAL.has(row.label) && !row.value).map((r) => r.label),
)

const packagingTotal = computed(() => {
  const rows = batch.value?.packaging || []
  return rows.map((r) => `${r.count}${r.containerType}`).join('') || '—'
})

function goBatch() {
  const name = draft.value?.batch
  if (name) void router.push(`/hbos/inventory/batch/${encodeURIComponent(name)}`)
}

onMounted(async () => {
  try {
    const loaded = await getIntakeDraft(draftName.value)

    if (!loaded.isIntakeDraft) {
      state.value = 'notIntake'
      return
    }
    // 提交过 / 已取消的单子都没有草稿可复核——直接给对应落点，**别掉进可编辑表单**
    if (loaded.docstatus === 1) {
      draft.value = loaded
      state.value = 'submitted'
      return
    }
    if (loaded.docstatus === 2) {
      draft.value = loaded
      state.value = 'cancelled'
      return
    }

    draft.value = loaded

    // 批次与照片各自独立取，任一个失败不影响整页（review 仍可进行）
    const [batchResult, files] = await Promise.allSettled([
      loaded.batch ? getBatch(loaded.batch) : Promise.resolve(null),
      getAttachments('Stock Entry', loaded.name),
    ])

    if (batchResult.status === 'fulfilled') batch.value = batchResult.value

    if (files.status === 'fulfilled') {
      const found = files.value.find((f) => /\.(png|jpe?g|webp)$/i.test(f.fileName))
      if (found) photo.value = { url: found.url, fileName: found.fileName }
    }

    state.value = 'ready'
  } catch (error) {
    if (error instanceof FrappeHttpError) {
      state.value = error.status === 404 ? 'missing' : 'missing'
      return
    }
    state.value = 'missing'
  }
})

function confirmSubmit() {
  if (!draft.value) return
  Modal.confirm({
    title: '提交这张入库单？',
    content: `提交后 ${qtyText.value} ${draft.value.item.uom} ${
      draft.value.item.itemName || draft.value.item.itemCode
    } 会立刻入账，并生成货位卡与待检证。提交后如需撤销，可在本页取消（会反向过账）。`,
    okText: '确认提交',
    cancelText: '再核对一下',
    onOk: async () => {
      await doSubmit()
    },
  })
}

async function doSubmit() {
  if (!draft.value) return
  submitting.value = true
  try {
    await submitIntakeDraft(draft.value.name)
    state.value = 'submitted'
  } catch (error) {
    Modal.error({
      title: '提交失败',
      content: error instanceof FrappeHttpError ? error.message : '提交未成功，请重试。',
    })
  } finally {
    submitting.value = false
  }
}

/**
 * 取消已提交的入库单。
 *
 * 批次上那份「待检证 + 货位卡」是 `on_submit` 钩子生成的，**没有对应的
 * `on_cancel` 清理**——所以取消后卡片会留在批次附件里。文案必须说出来，
 * 否则用户以为单据取消了卡片就没了。
 */
function confirmCancel() {
  if (!draft.value) return
  Modal.confirm({
    title: '取消这张入库单？',
    content:
      '货会从目标货位扣回，账面等于没入过。' +
      '注意：批次上已生成的「货位卡 / 待检证」不会跟着删除——若这批货要重做，去批次页重新生成一次即可覆盖。',
    okText: '确认取消',
    okType: 'danger',
    cancelText: '再想想',
    onOk: async () => {
      if (!draft.value) return
      cancelling.value = true
      try {
        await cancelIntakeDraft(draft.value.name)
        state.value = 'cancelled'
      } catch (error) {
        Modal.error({
          title: '取消失败',
          content: error instanceof FrappeHttpError ? error.message : '操作未成功，请重试。',
        })
      } finally {
        cancelling.value = false
      }
    },
  })
}

function confirmDiscard() {
  if (!draft.value) return
  // 文案要说清两件事：删的是什么、以及**批次不会被一起删**。
  // 后者容易误解——批次可能是这张草稿之前就存在的（后端是「确保存在、只补空」）。
  Modal.confirm({
    title: '放弃这张草稿？',
    content:
      '草稿、以及随草稿留存的标签照片会一起丢弃，不可恢复。' +
      '批次本身不会被删除——它可能在这张草稿之前就已经存在。',
    okText: '放弃草稿',
    okType: 'danger',
    cancelText: '保留',
    onOk: async () => {
      discarding.value = true
      try {
        await discardIntakeDraft(draft.value!.name)
        void router.push('/hbos/inventory/intake')
      } catch (error) {
        Modal.error({
          title: '放弃失败',
          content: error instanceof FrappeHttpError ? error.message : '操作未成功，请重试。',
        })
      } finally {
        discarding.value = false
      }
    },
  })
}
</script>
