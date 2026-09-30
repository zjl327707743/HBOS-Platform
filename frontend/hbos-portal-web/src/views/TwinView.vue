<template>
  <div class="twin-page">
    <div class="kt-breadcrumb">
      <RouterLink to="/hbos">工作台</RouterLink><RightOutlined />
      <RouterLink to="/hbos/apps">应用中心</RouterLink><RightOutlined />
      <span>设备与工艺</span>
    </div>
    <header class="kt-page-heading">
      <div><h1>设备与工艺</h1><p>在设备旁边，展开有依据的理解。</p></div>
      <a-button @click="$router.push('/hbos/knowledge')"><ReadOutlined /> 知识助理</a-button>
    </header>

    <div class="twin-tabs hbos-glass-g2">
      <button class="active" type="button"><DeploymentUnitOutlined /> 设备认知</button>
      <button type="button" disabled>工艺示教 <small>后续阶段</small></button>
      <button type="button" disabled>数据回放 <small>未接入</small></button>
      <a-tag class="target-tag">目标设备 M607B / WD102</a-tag>
    </div>

    <a-alert v-if="pageError" type="error" show-icon :message="pageError" class="twin-alert" />
    <a-skeleton v-else-if="loading" active :paragraph="{ rows: 12 }" class="twin-skeleton" />

    <div v-else-if="manifest" class="twin-workspace">
      <TwinViewer :manifest="manifest" @select="onSelect" @ready="viewerReady = true" />
      <aside class="twin-side hbos-glass-g2">
        <div class="panel-tabs"><button type="button" class="active">部件信息</button><button type="button" disabled>相关知识</button></div>

        <div v-if="mappingLoading" class="side-loading"><a-spin /><span>正在核验部件映射…</span></div>
        <div v-else-if="mapping" class="selection-body">
          <div class="selection-icon"><AimOutlined /></div>
          <a-tag :color="mapping.status === 'verified' ? 'green' : 'default'">
            {{ mapping.status === 'verified' ? '已核部件' : '待核部件' }}
          </a-tag>
          <h3>{{ mapping.display_name }}</h3>
          <p>{{ mapping.status === 'verified' ? '该显示名称来自服务器受控映射。' : '当前节点没有经人工确认的语义，不依据模型名称猜测。' }}</p>
          <dl>
            <dt>稳定节点</dt><dd>{{ mapping.asset_id }}</dd>
            <dt>目标设备</dt><dd>{{ mapping.equipment_id }} / WD102</dd>
            <dt>部件标识</dt><dd>{{ mapping.component_id || '待核' }}</dd>
            <dt>工艺步骤</dt><dd>{{ mapping.process_step_id || '未绑定' }}</dd>
            <dt>知识关联</dt><dd>{{ mapping.knowledge_link_available ? '已发布映射' : '尚未发布' }}</dd>
            <dt>现场数据</dt><dd>未接入</dd>
          </dl>
        </div>
        <div v-else class="selection-empty">
          <div class="selection-icon"><SelectOutlined /></div>
          <h3>{{ viewerReady ? '选择一个部件' : '模型载入后可选择部件' }}</h3>
          <p>点击三维模型中的区域，使用 GLB 内稳定 `asset_id` 查询服务器映射。</p>
        </div>

        <div class="twin-side-bottom">
          <a-button
            type="primary"
            block
            :disabled="!manifest"
            @click="openEquipmentKnowledge"
          ><ReadOutlined /> 检索 M607B 设备知识 <ArrowRightOutlined /></a-button>
          <p>{{ mapping?.knowledge_link_available ? '已核部件上下文会随请求传递，知识 App 仍会重新授权资料。' : '先按 M607B 设备范围检索；待核节点不会被当作部件语义。' }}</p>
        </div>
      </aside>
    </div>

    <section v-if="manifest" class="twin-truth hbos-glass-g2">
      <div><SafetyCertificateOutlined /><span><strong>{{ manifest.fit_disclaimer }}</strong><small>模型用于浏览理解，不能替代工程测量。</small></span></div>
      <div><DisconnectOutlined /><span><strong>未接现场</strong><small>没有伪造温度、压力、批次或 LIVE 状态。</small></span></div>
      <div><BranchesOutlined /><span><strong>版本可追溯</strong><small>{{ manifest.model_revision }} · {{ manifest.viewer_revision }}</small></span></div>
    </section>

    <section class="journey-strip hbos-glass-g1">
      <div><b>01</b><span><strong>浏览与定位</strong><small>让真实设备模型成为理解起点</small></span></div>
      <RightOutlined />
      <div><b>02</b><span><strong>选择一个部件</strong><small>用稳定 asset_id 核验上下文</small></span></div>
      <RightOutlined />
      <div><b>03</b><span><strong>展开相关知识</strong><small>由知识 App 再次授权资料</small></span></div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import {
  AimOutlined,
  ArrowRightOutlined,
  BranchesOutlined,
  DeploymentUnitOutlined,
  DisconnectOutlined,
  ReadOutlined,
  RightOutlined,
  SafetyCertificateOutlined,
  SelectOutlined,
} from '@ant-design/icons-vue'
import type { TwinComponentMapping, TwinManifest } from '@/contracts/p1'
import { getTwinComponentMapping, getTwinManifest, getTwinStatus } from '@/services/p1Api'
import TwinViewer from '@/components/twin/TwinViewer.vue'

const loading = ref(true)
const manifest = ref<TwinManifest | null>(null)
const pageError = ref<string | null>(null)
const mapping = ref<TwinComponentMapping | null>(null)
const mappingLoading = ref(false)
const viewerReady = ref(false)
const router = useRouter()

function openEquipmentKnowledge() {
  if (!manifest.value) return
  const query: Record<string, string> = {
    equipment_id: manifest.value.equipment_id,
    q: `${manifest.value.equipment_id} 设备维护、工艺与接口`,
    auto: '1',
  }
  if (mapping.value?.status === 'verified' && mapping.value.knowledge_link_available) {
    query.asset_id = mapping.value.asset_id
    if (mapping.value.component_id) query.component_id = mapping.value.component_id
  }
  void router.push({ path: '/hbos/knowledge', query })
}

async function onSelect(assetId: string | null) {
  mapping.value = null
  pageError.value = null
  if (!assetId || !manifest.value) return
  mappingLoading.value = true
  try {
    mapping.value = await getTwinComponentMapping(manifest.value.equipment_id, assetId)
  } catch (error) {
    pageError.value = error instanceof Error ? error.message : '部件映射暂时不可用。'
  } finally {
    mappingLoading.value = false
  }
}

onMounted(async () => {
  try {
    const status = await getTwinStatus()
    if (!status.can_enter) throw new Error('当前账号没有设备模块访问权限。')
    if (!status.asset_root_configured) throw new Error('私有模型制品目录尚未配置。')
    manifest.value = await getTwinManifest('M607B')
  } catch (error) {
    pageError.value = error instanceof Error ? error.message : '设备服务暂时不可用。'
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.twin-page{display:grid;gap:18px}.kt-breadcrumb{display:flex;align-items:center;gap:7px;color:var(--hbos-text-muted);font-size:11px}.kt-breadcrumb a{color:inherit}.kt-breadcrumb span{color:#3f557a;font-weight:700}.kt-page-heading{display:flex;align-items:flex-end;justify-content:space-between;gap:18px}.kt-page-heading h1{margin:0;color:#193661;font-size:31px;letter-spacing:-.8px}.kt-page-heading p{margin:6px 0 0;color:var(--hbos-text-muted)}
.twin-tabs{display:flex;align-items:center;gap:4px;padding:7px;border-radius:17px}.twin-tabs button{padding:10px 14px;border:0;border-radius:11px;background:transparent;color:#73829a;font-size:11px;font-weight:700}.twin-tabs button.active{background:rgba(92,99,245,.10);color:#5260e7}.twin-tabs button:disabled{cursor:not-allowed}.twin-tabs small{margin-left:4px;color:#9aa6b9;font-size:8px}.target-tag{margin-left:auto}.twin-alert,.twin-skeleton{padding:22px;border-radius:20px;background:rgba(255,255,255,.66)}
.twin-workspace{display:grid;grid-template-columns:minmax(0,1fr) 315px;gap:16px}.twin-side{display:flex;min-height:650px;flex-direction:column;border-radius:25px;overflow:hidden}.panel-tabs{display:grid;grid-template-columns:1fr 1fr;padding:7px;border-bottom:1px solid rgba(65,91,138,.08)}.panel-tabs button{padding:10px;border:0;border-radius:10px;background:transparent;color:#8290a4;font-size:11px;font-weight:700}.panel-tabs button.active{background:rgba(93,101,245,.09);color:#5361e7}.selection-body,.selection-empty{padding:22px}.selection-icon{display:grid;width:44px;height:44px;place-items:center;margin-bottom:16px;border-radius:14px;background:linear-gradient(135deg,#6a64ff,#4aa7ff);color:#fff;font-size:19px}.selection-body>.ant-tag{float:right;margin-top:-59px}.selection-body h3,.selection-empty h3{margin:0 0 8px;color:#243f68;font-size:17px}.selection-body>p,.selection-empty p{margin:0;color:#77879f;font-size:11px;line-height:1.65}.selection-body dl{display:grid;grid-template-columns:82px 1fr;gap:11px 10px;margin:22px 0;padding:16px;border-radius:16px;background:rgba(246,249,253,.80);font-size:10px}.selection-body dt{color:#8996aa}.selection-body dd{margin:0;color:#405674;word-break:break-all}.side-loading{display:grid;flex:1;place-content:center;justify-items:center;gap:10px;color:#75869f;font-size:11px}.twin-side-bottom{margin-top:auto;padding:18px;border-top:1px solid rgba(65,91,138,.08)}.twin-side-bottom .ant-btn{height:42px;border:0;border-radius:12px;background:linear-gradient(135deg,#5b63ff,#46a1ff)}.twin-side-bottom p{margin:9px 0 0;text-align:center;color:#8794a8;font-size:9px;line-height:1.5}
.twin-truth{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;padding:14px;border-radius:20px}.twin-truth>div{display:grid;grid-template-columns:auto 1fr;gap:10px;align-items:center;padding:11px;border-radius:14px;background:rgba(255,255,255,.55)}.twin-truth>div>:first-child{color:#5f6bf4;font-size:18px}.twin-truth strong,.twin-truth small{display:block}.twin-truth strong{font-size:11px}.twin-truth small{margin-top:3px;color:#8491a4;font-size:9px}.journey-strip{display:grid;grid-template-columns:1fr auto 1fr auto 1fr;align-items:center;gap:14px;padding:18px;border-radius:20px}.journey-strip>div{display:grid;grid-template-columns:auto 1fr;gap:11px;align-items:center}.journey-strip b{color:#606af3;font-size:12px}.journey-strip strong,.journey-strip small{display:block}.journey-strip strong{font-size:11px}.journey-strip small{margin-top:3px;color:#8491a5;font-size:9px}.journey-strip>:not(div){color:#9aa8bc}
@media(max-width:1200px){.twin-workspace{grid-template-columns:1fr}.twin-side{min-height:0}.twin-truth{grid-template-columns:1fr 1fr 1fr}}@media(max-width:700px){.kt-page-heading{align-items:flex-start;flex-direction:column}.twin-tabs{overflow-x:auto}.target-tag{display:none}.twin-truth{grid-template-columns:1fr}.journey-strip{grid-template-columns:1fr}.journey-strip>:not(div){display:none}}
</style>
