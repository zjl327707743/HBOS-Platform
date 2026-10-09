<template>
  <div class="twin-page" :class="{'has-workspace':!!manifest,'is-demo':session?.mode==='production'}">
    <div class="twin-breadcrumb"><RouterLink to="/hbos">工作台</RouterLink><span> / </span><span>设备与工艺</span></div>
    <header class="twin-heading"><div><p class="eyebrow">EQUIPMENT & PROCESS</p><h1>设备与工艺</h1><p>从真实设备出发，理解每一步。</p></div><span class="review-badge">私有交互候选 · 待整体评审</span></header>
    <div v-if="catalogLoading" class="blank-state" role="status">正在读取受保护目录…</div>
    <div v-if="pageError" class="error-card" role="alert"><strong>{{ pageError }}</strong><button @click="loadCatalog">重新核验</button></div>
    <TwinCatalog v-if="catalog" :entries="catalog.entries" :selected="selectedEntry" @choose="chooseEntry" />
    <div v-if="catalog && !catalog.entries.length && !pageError" class="blank-state">当前会话没有可查看的设备。目录只显示允许访问的内容。</div>
    <div v-if="availability" class="blank-state" role="status"><span class="blank-icon">◈</span><h2>{{ availability }}</h2><p>资产准备和分发确认分别记录，确认后在本工作区继续评审。</p><button @click="loadCatalog">重新核验可用性</button></div>
    <div v-if="entryLoading" class="blank-state" role="status">正在核验设备、成员与版本…</div>
    <template v-if="manifest && session">
      <div class="workspace-heading"><div><h2>{{ manifest.label }}</h2><span>设备身份已确认 · 几何适用性待核</span></div><div class="workspace-actions"><button :aria-expanded="partsOpen" @click="partsOpen=!partsOpen">☷ 部件目录</button><button :aria-expanded="infoOpen" @click="infoOpen=!infoOpen">ⓘ 信息与版本</button></div></div>
      <div class="mode-bar"><div class="mode-tabs" aria-label="工作区模式"><button :aria-pressed="session.mode==='browse'" @click="exitDemo">设备浏览</button><button :aria-pressed="session.mode==='production'" :disabled="!productionReady" @click="enterDemo">生产示教</button></div><label v-if="manifest.equipment_ids.length>1" class="device-select">当前讲解设备<select :value="session.equipmentId" @change="chooseEquipment(($event.target as HTMLSelectElement).value)"><option v-for="eq in manifest.equipment_ids" :key="eq">{{ eq }}</option></select></label><button class="knowledge-link" @click="openKnowledge">设备知识 ↗</button></div>
      <div class="twin-workspace" :class="{ 'with-parts':partsOpen }">
        <aside v-if="partsOpen" class="parts-panel" aria-label="候选部件目录">
          <div class="parts-heading"><strong>候选部件目录</strong><button aria-label="折叠部件目录" @click="partsOpen=false">×</button></div>
          <label class="search-label">搜索当前目录<input v-model="search" type="search" placeholder="搜索部件名称…" /></label>
          <p class="candidate-note">名称来自候选目录，几何可定位；业务部件身份仍待核。</p>
          <p v-if="partsError" class="local-error" role="status">{{ partsError }}</p>
          <div class="part-list"><button v-for="group in filteredGroups" :key="group.group_id" :class="{active:selectedGroup?.group_id===group.group_id}" @click="chooseGroup(group)"><span>{{ group.label }}</span><small>{{ group.asset_ids.length }} 个当前成员 · 候选</small></button></div>
          <p v-if="!filteredGroups.length && !partsError" class="candidate-note">没有匹配的当前成员。</p>
          <div class="parts-footer">未接入现场数据<br />未知节点仅使用设备级知识入口</div>
        </aside>
        <div class="canvas-column">
          <TwinViewer :key="manifest.entry_id + ':' + manifest.model_sha256" ref="viewer" :manifest="manifest" :process="process" :session="session" :scheduler="scheduler" @select="selectAsset" @ready="onViewerReady" @fatal="failProtected" @manual="session.followCamera=false" @error="viewerError=$event" @metrics="metrics=$event" @process-error="processError=$event; exitDemo()" @restore="exitDemo" @context-lost="onContextLost" />
          <div v-if="mappingLoading || mapping || selectedGroup || mappingError" class="selection-panel" aria-live="polite">
            <div><small>{{ mapping?.status==='verified' ? '已核部件' : '候选 / 待核节点' }}</small><strong>{{ mappingLoading ? '正在核验当前节点…' : mapping?.display_name || selectedGroup?.label || '映射暂时不可用' }}</strong><p>{{ mappingError || (mapping?.status==='verified' ? '受控映射已核验，知识资料仍由知识模块授权。' : '可进行几何观察，不将候选名称作为已核业务身份。') }}</p></div>
            <div class="selection-actions"><button @click="viewer?.focusSelected()">聚焦</button><button @click="viewer?.toggleIsolate()">隔离</button><button @click="viewer?.hideSelected()">隐藏</button><button @click="clearSelection">清空</button></div>
          </div>
        </div>
      </div>
      <div v-if="processError" class="local-error" role="status">{{ processError }} 静态浏览继续可用。</div>
      <TwinProcessPanel v-if="session.mode==='production'" :session="session" :ready="productionReady" @seek="seekTo" @toggle="togglePlay" @replay="replay" @speed="setSpeed" @follow="session.followCamera=$event; scheduler.invalidate()" @exit="exitDemo" />
      <div v-else class="browse-note"><span>◎ 选择设备部件，使用聚焦、隔离与恢复。</span><button :disabled="!productionReady" @click="enterDemo">进入生产原理演示 →</button></div>
      <section v-if="infoOpen" class="version-panel" aria-label="真实性与版本信息"><div class="version-heading"><h3>本次候选的依据与边界</h3><button aria-label="关闭信息面板" @click="infoOpen=false">×</button></div><div class="truth-grid"><div><strong>设备身份</strong><span>Owner 已确认</span></div><div><strong>几何与外观</strong><span>现场适用性待核；照片拟合非实测</span></div><div><strong>内部与工艺</strong><span>程序原理示意，非操作规程</span></div><div><strong>现场数据</strong><span>未接入；温度、压力、阀位均缺失</span></div></div><dl><dt>模型 SHA</dt><dd>{{ manifest.model_sha256 }}</dd><dt>模型 / 映射</dt><dd>{{ manifest.model_revision }} / {{ manifest.mapping_revision }}</dd><dt>过程 / 绑定</dt><dd>{{ manifest.process_revision }} / {{ manifest.binding_revision }}</dd><dt>镜头 / 演示</dt><dd>{{ manifest.camera_revision }} / {{ manifest.demo_revision }} · seed {{ manifest.demo_seed }}</dd><dt>知识 L1</dt><dd>保留 equipment_id、q、auto；新增协议待知识窗口确认</dd><dt>分发 / 视觉</dt><dd>仅合成私有评审范围；整体视觉与发布均未批准</dd></dl><p v-if="metrics">当前场景资源：{{ metrics.geometries }} geometry / {{ metrics.textures }} texture；解析 {{ metrics.parseMs.toFixed(0) }}ms。此计数不代表完整内存无泄漏证明。</p><details class="review-metrics"><summary>本机私有验证数据</summary><p>只记录当前浏览器的加载、响应与资源计数。</p><button @click="captureReviewSnapshot">生成本机验证快照</button><button v-if="manifest.review_only" :disabled="!viewerReady" @click="reviewGraphicsRecovery">检验本机图形恢复</button><p v-if="graphicsReview" role="status">{{ graphicsReview }}</p><pre v-if="reviewSnapshot" data-testid="twin-review-snapshot">{{ reviewSnapshot }}</pre></details></section>
      <details class="v1-plan"><summary>完整 V1 后续项 · 整体视觉确认后在同一分支补齐</summary><p>两机过滤、CIP/SIP、顶部附件候选专题、演示对照与模块演示模式{{ manifest.equipment_ids.includes('M607B') ? '，以及 M607B 专属夹套讲解' : '' }}。未接入专题不会伪装为可用。L2/L3 等待唯一知识协议，不新建问答系统。</p></details>
      <p v-if="viewerError && !viewerReady" class="local-error" role="status">{{ viewerError }}</p>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import TwinCatalog from '@/components/twin/TwinCatalog.vue'
import TwinViewer from '@/components/twin/TwinViewer.vue'
import TwinProcessPanel from '@/components/twin/TwinProcessPanel.vue'
import type { CandidateGroup, Catalog, CatalogEntry, DemoSession, ProcessBundle, TwinManifest, TwinMapping, TwinParts, ViewerMetrics } from '@/types/twin'
import { getCatalog, getManifest, getMapping, getParts, getProcess, protectedFailure } from '@/services/twin/twinApi'
import { createScheduler } from '@/composables/twin/scheduler'
import { contextKey, Generation, knowledgeQuery, makeSession, seek } from '@/composables/twin/session'

const router=useRouter(), route=useRoute(), scheduler=createScheduler(), loadingGeneration=new Generation(), selectionGeneration=new Generation()
const catalog=ref<Catalog|null>(null), catalogLoading=ref(true), entryLoading=ref(false), pageError=ref(''), availability=ref(''), selectedEntry=ref('')
const manifest=ref<TwinManifest|null>(null), parts=ref<TwinParts|null>(null), process=ref<ProcessBundle|null>(null), session=ref<DemoSession|null>(null)
const mapping=ref<TwinMapping|null>(null), mappingLoading=ref(false), mappingError=ref(''), selectedGroup=ref<CandidateGroup|null>(null), search=ref('')
const partsError=ref(''),processError=ref(''),viewerError=ref(''),viewerReady=ref(false),partsOpen=ref(true),infoOpen=ref(false),metrics=ref<ViewerMetrics|null>(null)
const viewer=ref<InstanceType<typeof TwinViewer>|null>(null), sessions=new Map<string,DemoSession>()
const reviewSnapshot=ref('');let entryStarted=0,manifestReadyMs=0,interactiveMs:number|null=null
const graphicsReview=ref('')
function onViewerReady(){viewerReady.value=true;recordInteractive();if(graphicsReview.value==='正在模拟图形丢失并重新核验…')graphicsReview.value='图形已恢复，同一模型已重新核验；示教保持暂停。'}
function onContextLost(){viewerReady.value=false;if(session.value)session.value.paused=true}
function reviewGraphicsRecovery(){graphicsReview.value=viewer.value?.reviewGraphicsRecovery()?'正在模拟图形丢失并重新核验…':'当前浏览器不支持该项模拟。'}
function recordInteractive(){if(productionReady.value&&interactiveMs===null)interactiveMs=performance.now()-entryStarted}
function captureReviewSnapshot(){const data=viewer.value?.reviewSnapshot();if(data)reviewSnapshot.value=JSON.stringify({...data,entry_timing:{choose_to_manifest_ms:manifestReadyMs,choose_to_interactive_ms:interactiveMs,choose_to_first_render_ms:data.load.model_request_to_first_render_ms===null?null:data.load.request_started_at_ms-entryStarted+data.load.model_request_to_first_render_ms}},null,2)}
let disposed=false, catalogEpoch=0, permissionCheck:ReturnType<typeof setInterval>|null=null
const filteredGroups=computed(()=> (parts.value?.groups||[]).filter(g=>(!g.equipment_id||g.equipment_id===session.value?.equipmentId)&&g.label.toLowerCase().includes(search.value.trim().toLowerCase())))
const productionReady=computed(()=>Boolean(process.value?.modes.includes('production')&&session.value&&process.value.bindings[session.value.equipmentId]&&!processError.value&&viewerReady.value))
function errorText(e:unknown,fallback:string){return e instanceof Error?e.message:fallback}
function invalidateSelection(){selectionGeneration.next();mapping.value=null;mappingLoading.value=false;mappingError.value='';selectedGroup.value=null}
function clearSelection(){invalidateSelection();viewer.value?.selectIds([])}
function resetEntry(){graphicsReview.value='';loadingGeneration.next();invalidateSelection();if(session.value)session.value.paused=true;manifest.value=null;process.value=null;parts.value=null;session.value=null;partsError.value='';processError.value='';viewerError.value='';viewerReady.value=false;availability.value='';entryLoading.value=false;metrics.value=null}
function failProtected(message:string){resetEntry();sessions.clear();catalog.value=null;pageError.value=message}
function deviceSession(m:TwinManifest,equipment:string){const key=contextKey(m,equipment);if(!sessions.has(key))sessions.set(key,reactive(makeSession(m,equipment)));return sessions.get(key)!}
function chooseEquipment(equipment:string){if(!manifest.value?.equipment_ids.includes(equipment))return;if(session.value)session.value.paused=true;invalidateSelection();viewer.value?.selectIds([]);session.value=deviceSession(manifest.value,equipment);scheduler.invalidate()}
async function loadCatalog(){
  const token=++catalogEpoch;catalogLoading.value=true;pageError.value=''
  try{const c=await getCatalog();if(disposed||token!==catalogEpoch)return;catalog.value=c
    if(manifest.value){const active=manifest.value,current=c.entries.find(e=>e.entry_id===active.entry_id);if(!current||current.availability!=='READY'){failProtected('当前设备查看范围或成员批准已失效，展示已停止。');return}
      const checked=await getManifest(active.entry_id,active.model_sha256);if(disposed||token!==catalogEpoch)return
      if(manifest.value===active&&['model_sha256','mapping_revision','mapping_sha256','process_revision','process_sha256','binding_revision','camera_revision','demo_revision','demo_seed'].some(k=>checked[k as keyof TwinManifest]!==active[k as keyof TwinManifest])){failProtected('资源版本已变更，旧场景已关闭，请重新打开。');return}}
    if(!manifest.value&&!entryLoading.value){const requested=String(route.query.entry||selectedEntry.value||'');const entry=c.entries.find(e=>e.entry_id===requested)||c.entries[0];if(entry)await chooseEntry(entry)}
  }catch(e){if(disposed||token!==catalogEpoch)return;if(protectedFailure(e))failProtected(errorText(e,'登录或设备权限已失效。'));else pageError.value=errorText(e,'设备目录暂时不可用。')}
  finally{if(token===catalogEpoch)catalogLoading.value=false}
}
async function chooseEntry(entry:CatalogEntry){
  resetEntry();entryStarted=performance.now();interactiveMs=null;reviewSnapshot.value='';selectedEntry.value=entry.entry_id;search.value='';pageError.value=''
  void router.replace({path:'/hbos/twin',query:{entry:entry.entry_id}})
  if(entry.availability!=='READY'){availability.value=entry.availability==='MEMBERS_PENDING'?'资产成员范围等待 Owner 确认':'当前已知设备的交互制品尚不可用';return}
  const token=loadingGeneration.next();entryLoading.value=true
  try{
    const m=await getManifest(entry.entry_id);if(disposed||!loadingGeneration.isCurrent(token))return
    manifestReadyMs=performance.now()-entryStarted;session.value=deviceSession(m,m.equipment_ids[0]!);manifest.value=m;entryLoading.value=false
    const results=await Promise.allSettled([getParts(m),getProcess(m)]);if(disposed||!loadingGeneration.isCurrent(token))return
    const [p,d]=results
    if(p.status==='fulfilled'){if(p.value.entry_id===m.entry_id&&p.value.model_sha256===m.model_sha256&&p.value.mapping_revision===m.mapping_revision)parts.value=p.value;else partsError.value='候选目录与当前模型不兼容。'}else if(protectedFailure(p.reason)){failProtected(errorText(p.reason,'设备查看权限已失效。'));return}else partsError.value=errorText(p.reason,'候选目录暂时不可用。')
    if(d.status==='fulfilled'){if(d.value.entry_id===m.entry_id&&d.value.model_sha256===m.model_sha256&&d.value.mapping_revision===m.mapping_revision&&d.value.process_revision===m.process_revision&&d.value.binding_revision===m.binding_revision)process.value=d.value;else processError.value='当前示教配置与模型版本不兼容。'}else if(protectedFailure(d.reason)){failProtected(errorText(d.reason,'设备查看权限已失效。'));return}else processError.value=errorText(d.reason,'当前示教配置不兼容。')
    recordInteractive()
  }catch(e){if(disposed||!loadingGeneration.isCurrent(token))return;if(protectedFailure(e))failProtected(errorText(e,'设备权限或资源版本已失效。'));else availability.value=errorText(e,'设备资源暂时不可用。')}
  finally{if(loadingGeneration.isCurrent(token))entryLoading.value=false}
}
async function selectAsset(assetId:string|null){
  invalidateSelection();const m=manifest.value, s=session.value;if(!assetId||!m||!s)return
  const token=selectionGeneration.next(),key=s.contextKey,equipment=s.equipmentId;mappingLoading.value=true
  try{const result=await getMapping(m,equipment,assetId);if(disposed||!selectionGeneration.isCurrent(token)||session.value?.contextKey!==key||manifest.value?.model_sha256!==m.model_sha256)return
    if(result.model_sha256!==m.model_sha256||result.mapping_revision!==m.mapping_revision||result.equipment_id!==equipment||result.asset_id!==assetId){mappingError.value='映射响应与当前选择不兼容。';return}mapping.value=result
  }catch(e){if(disposed||!selectionGeneration.isCurrent(token))return;if(protectedFailure(e))failProtected(errorText(e,'设备查看权限已失效。'));else mappingError.value=errorText(e,'节点映射暂时不可用。')}
  finally{if(selectionGeneration.isCurrent(token))mappingLoading.value=false}
}
function chooseGroup(group:CandidateGroup){if(group.equipment_id&&group.equipment_id!==session.value?.equipmentId)chooseEquipment(group.equipment_id);invalidateSelection();selectedGroup.value=group;viewer.value?.selectIds(group.asset_ids);viewer.value?.focusIds(group.asset_ids)}
function enterDemo(){if(!session.value||!productionReady.value)return;invalidateSelection();session.value.mode='production';session.value.paused=true;scheduler.invalidate()}
function exitDemo(){if(!session.value)return;session.value.mode='browse';session.value.paused=true;session.value.followCamera=false;invalidateSelection();scheduler.invalidate()}
function seekTo(time:number){if(session.value){seek(session.value,time);scheduler.invalidate()}}
function togglePlay(){if(!session.value||!productionReady.value)return;if(session.value.time>=60)session.value.time=0;session.value.paused=!session.value.paused;scheduler.invalidate()}
function replay(){if(session.value&&productionReady.value){session.value.time=0;session.value.paused=false;scheduler.invalidate()}}
function setSpeed(value:number){if(session.value&&[.5,1,2].includes(value)){session.value.speed=value;scheduler.invalidate()}}
function openKnowledge(){if(!manifest.value||!session.value)return;session.value.paused=true;void router.push({path:'/hbos/knowledge',query:knowledgeQuery(session.value.equipmentId,mapping.value,manifest.value)})}
function hidden(){if(document.hidden&&session.value)session.value.paused=true;else if(!document.hidden)void loadCatalog()}
const unsubscribe=scheduler.subscribe(dt=>{const s=session.value;if(!s||s.paused||s.mode==='browse')return false;seek(s,s.time+dt*s.speed);if(s.time>=60)s.paused=true;return !s.paused})
onMounted(()=>{void loadCatalog();document.addEventListener('visibilitychange',hidden);window.addEventListener('focus',loadCatalog);permissionCheck=setInterval(()=>{if(!document.hidden&&manifest.value)void loadCatalog()},30000)})
onBeforeUnmount(()=>{disposed=true;catalogEpoch++;resetEntry();sessions.clear();if(permissionCheck)clearInterval(permissionCheck);document.removeEventListener('visibilitychange',hidden);window.removeEventListener('focus',loadCatalog);unsubscribe();scheduler.stop()})
</script>

<style scoped>
.twin-page{display:grid;gap:12px;min-width:0;color:#314760;--twin-viewer-height:clamp(380px,calc(100dvh - 450px),620px)}.twin-page.is-demo{--twin-viewer-height:clamp(320px,calc(100dvh - 590px),540px)}.has-workspace .twin-heading{padding:0}.has-workspace .twin-heading h1{font-size:24px;margin:0 0 3px}.has-workspace .twin-heading .eyebrow{display:none}.review-metrics{font-size:12px;color:#65738a;margin-top:16px}.review-metrics button{border:1px solid #dfe4ec;background:white;border-radius:8px;min-height:36px;padding:0 12px;cursor:pointer}.review-metrics pre{font-size:11px;white-space:pre-wrap;word-break:break-all;max-height:420px;overflow:auto;background:#f4f5f9;padding:12px}.twin-breadcrumb{font-size:12px;color:#8290a2;display:flex;gap:8px}.twin-breadcrumb a{color:inherit}.twin-heading{display:flex;justify-content:space-between;align-items:center;gap:18px;padding:3px 0 6px}.twin-heading h1{font-size:30px;letter-spacing:-.7px;margin:4px 0 6px;color:#25415e}.twin-heading p{margin:0;color:#7d8899;font-size:14px}.twin-heading .eyebrow{font-size:10px;letter-spacing:1.8px;color:#8580a4}.review-badge{background:#edeaf5;color:#7c6d96;border:1px solid #e2dcec;font-size:12px;border-radius:9px;padding:9px 12px;white-space:nowrap}.workspace-heading{display:flex;justify-content:space-between;align-items:center;gap:12px;margin-top:4px}.workspace-heading h2{font-size:21px;margin:0 0 3px;color:#30465e}.workspace-heading span{font-size:12px;color:#8b8e9a}.workspace-actions{display:flex;gap:8px}.workspace-actions button,.mode-bar button,.browse-note button,.selection-actions button,.blank-state button,.error-card button{min-height:38px;background:#ffffffc9;border:1px solid #dfe4ec;border-radius:9px;color:#69748b;padding:8px 12px;font-size:12px;cursor:pointer}.mode-bar{display:flex;gap:14px;align-items:center;justify-content:space-between;background:#ffffff80;border:1px solid #e2e7ee;border-radius:12px;padding:6px}.mode-tabs{display:flex;gap:4px}.mode-tabs button{border:0;background:none;font-size:13px;padding:9px 16px}.mode-tabs button[aria-pressed=true]{background:#ebe8f7;color:#6a5f9d}.mode-bar .knowledge-link{border:0;background:none;color:#766ba1;margin-left:auto}.device-select{display:flex;align-items:center;gap:8px;font-size:12px;color:#77869b}.device-select select{min-height:36px;border:1px solid #dfe4ec;background:white;border-radius:7px;padding:0 8px;color:#4d637c}.twin-workspace{display:grid;grid-template-columns:minmax(0,1fr);gap:14px;align-items:start}.twin-workspace.with-parts{grid-template-columns:220px minmax(0,1fr)}.canvas-column{min-width:0}.parts-panel{border:1px solid #e1e6ee;background:#ffffffa8;border-radius:17px;overflow:hidden;display:flex;flex-direction:column;max-height:var(--twin-viewer-height);min-height:var(--twin-viewer-height)}.parts-heading{display:flex;justify-content:space-between;align-items:center;padding:15px 14px 8px}.parts-heading strong{font-size:14px}.parts-heading button,.version-heading button{border:0;background:none;font-size:20px;color:#9299a7;min-width:32px;min-height:32px;cursor:pointer}.search-label{font-size:0;padding:0 14px}.search-label input{width:100%;font-size:12px;padding:10px;border:1px solid #e3e6ed;border-radius:8px;min-height:38px;background:#fafbfd;color:#41546c}.candidate-note{font-size:11px;line-height:1.6;padding:0 14px;color:#9396a3;margin:10px 0}.part-list{overflow-y:auto;min-height:0;flex:1;padding:2px 8px 12px}.part-list button{display:block;width:100%;text-align:left;border:1px solid transparent;border-radius:9px;background:none;padding:12px 8px;cursor:pointer;color:#52647b}.part-list button:hover{background:#f2f3f8}.part-list button.active{background:#eeebf8;border-color:#ddd5ec;color:#72618f}.part-list span{font-size:13px;display:block;line-height:1.5}.part-list small{display:block;font-size:10px;color:#9397a5;margin-top:4px}.parts-footer{font-size:11px;line-height:1.6;padding:14px;border-top:1px solid #e9ebf1;color:#969ba9}.selection-panel{display:flex;justify-content:space-between;align-items:center;gap:15px;border:1px solid #e0ddec;border-radius:12px;background:#f7f5fd;margin-top:10px;padding:15px}.selection-panel small{font-size:11px;color:#8e7c9e;display:block}.selection-panel strong{display:block;font-size:15px;margin:4px 0}.selection-panel p{font-size:12px;color:#818398;margin:0;line-height:1.6}.selection-actions{display:flex;gap:6px;flex-wrap:wrap;flex-shrink:0}.selection-actions button{font-size:12px;background:white}.browse-note{display:flex;justify-content:space-between;align-items:center;gap:10px;font-size:12px;color:#8d93a1}.browse-note button{background:none;border:0;color:#766b9f}.version-panel{border:1px solid #dfe5ed;border-radius:16px;padding:20px;background:#ffffffbb}.version-heading{display:flex;justify-content:space-between;align-items:center}.version-heading h3{font-size:16px;margin:0 0 14px}.truth-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:12px}.truth-grid strong,.truth-grid span{display:block;font-size:12px}.truth-grid span{font-size:11px;margin-top:5px;color:#8b91a0;line-height:1.6}.version-panel dl{display:grid;grid-template-columns:105px 1fr;gap:9px;font-size:11px;margin:20px 0 0;line-height:1.6}.version-panel dt{color:#929aaa}.version-panel dd{margin:0;word-break:break-all;color:#65738a}.version-panel>p{font-size:11px;color:#969aaa;line-height:1.6}.v1-plan{font-size:12px;line-height:1.8;color:#8a91a2;border-top:1px solid #e2e7ee;padding-top:12px}.v1-plan summary{cursor:pointer}.v1-plan p{margin-bottom:0}.blank-state{padding:48px 24px;background:#ffffffa8;border:1px solid #e2e6ee;border-radius:18px;text-align:center;color:#8c96a8;min-height:260px;display:grid;place-content:center;justify-items:center;gap:12px}.blank-state h2{font-size:20px;color:#5b6a82;margin:0}.blank-state p{font-size:13px;margin:0}.blank-icon{font-size:38px;color:#a299ba}.error-card{padding:20px;border-radius:14px;border:1px solid #e8c9c4;background:#fff6f4;display:flex;justify-content:space-between;align-items:center;gap:12px;font-size:14px;color:#8b5d54}.local-error{font-size:12px;color:#9b7651;padding:8px 14px;line-height:1.6}button:disabled{opacity:.45;cursor:not-allowed}.twin-page button:focus-visible,.twin-page input:focus-visible,.twin-page select:focus-visible,.twin-page summary:focus-visible{outline:3px solid #655cf0;outline-offset:2px}@media(max-width:1150px){.twin-workspace.with-parts{grid-template-columns:190px minmax(0,1fr)}.truth-grid{grid-template-columns:repeat(2,1fr)}.selection-panel{align-items:flex-start;flex-direction:column}}@media(max-width:700px){.twin-heading{align-items:flex-start;flex-direction:column;gap:12px}.twin-heading h1{font-size:27px}.workspace-heading{align-items:flex-start;flex-direction:column}.twin-workspace.with-parts{grid-template-columns:minmax(0,1fr)}.parts-panel{min-height:0;max-height:300px}.parts-footer{display:none}.mode-bar{flex-wrap:wrap}.device-select{order:3;padding:4px 10px;width:100%}.browse-note{align-items:flex-start;flex-direction:column}.version-panel{padding:15px}.version-panel dl{grid-template-columns:80px 1fr}.truth-grid{grid-template-columns:1fr}.mode-tabs button{padding:9px 12px}}@media(prefers-reduced-motion:reduce){*{transition:none!important;scroll-behavior:auto!important}}
</style>
